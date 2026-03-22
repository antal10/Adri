# Evaluation Strategy

This document defines how to determine whether an Adri output is correct. It
covers three output types — ontology graphs, adapter responses, and
recommendations — and specifies the criteria, method, and verdict for each.

## Why this matters

Without evaluation criteria, "it works" is subjective. The product charter's
bootstrap success criteria require a minimal reasoning loop that produces a
conforming recommendation. This document defines what "conforming" means and
how to check it.

---

## Output type 1: Ontology graph (artifact ingestion)

An adapter ingests an artifact and produces ontology entities. The graph is
correct when:

| Criterion | Check | Verdict |
|-----------|-------|---------|
| **Schema conformance** | Every entity has a valid type from ontology.md. Every relationship has valid source/target types per the relationship table. | pass / fail |
| **Property completeness** | Every required universal property (`id`, `name`, `source_adapter`, `source_artifact`, `created_at`) is present and non-empty. | pass / fail |
| **Property type correctness** | Property values match their declared types (e.g., `sample_rate` is a float, `domain` is one of the allowed enum values). | pass / fail |
| **Provenance** | `source_adapter` matches the adapter that created the entity. `source_artifact` references an existing artifact. | pass / fail |
| **No cross-domain relationships** | The adapter did not create relationships that span domains. Cross-domain links are created only during context assembly. | pass / fail |
| **Fidelity** | The entities faithfully represent the source artifact. A CAD assembly with 12 parts produces approximately 12 Component entities, not 1 and not 120. | manual review (with tolerance bounds if specified) |

### Method

Automated validation checks schema conformance, property completeness, type
correctness, and provenance. Fidelity requires a human or test oracle that
knows the expected entity count and structure for a given test artifact.

---

## Output type 2: Adapter response (tool invocation)

An adapter returns a response after an operation. The response is correct when:

| Criterion | Check | Verdict |
|-----------|-------|---------|
| **Protocol conformance** | Response contains all required fields per the adapter contract's invocation protocol. | pass / fail |
| **Output schema match** | `outputs` conforms to the operation's declared `output_schema`. | pass / fail |
| **Status consistency** | If `status` is `error` or `partial`, the `error` field is present. If `status` is `success`, `outputs` is present. | pass / fail |
| **Idempotency** | If the operation is declared `idempotent`, calling it twice with the same input produces the same output. | pass / fail (for idempotent operations only) |
| **Entity compliance** | Any `entities_created` conform to ontology graph criteria above. | pass / fail |
| **Error code validity** | Error codes are from the required set or are documented adapter-specific extensions prefixed with `adapter_id`. | pass / fail |

### Method

Automated validation for all criteria. Idempotency is tested by running the
same invocation twice and comparing outputs.

---

## Output type 3: Recommendation (reasoning output)

A recommendation is the primary output of Adri's reasoning. It is correct when:

| Criterion | Check | Verdict |
|-----------|-------|---------|
| **Schema conformance** | All required fields from recommendation_schema.md are present with correct types. | pass / fail |
| **Evidence grounding** | Every evidence item's `source` references a real artifact, adapter, or citation — not a fabricated source. | pass / fail |
| **Assumption quality** | Each assumption is stated as a falsifiable claim (not vague). `impact_if_wrong` is justified by the recommendation's dependency on that assumption. If assumptions list is empty, `no_assumptions_rationale` is present and credible. | manual review |
| **Confidence calibration** | The `confidence.level` is consistent with the confidence rubric in recommendation_schema.md, given the evidence types and assumption impacts present. | manual review (automatable with rubric rules) |
| **Trace validity** | Every entity ID in `trace` exists in the current ontology graph. | pass / fail |
| **Verdict-evidence consistency** | A `recommended` verdict is not paired with `speculative` confidence. An `insufficient_data` verdict has at least one evidence gap documented in assumptions or the confidence `limiting_factor`. | pass / fail |
| **Ontology alignment** | The recommendation does not reference entity types, relationship types, or properties absent from ontology.md. | pass / fail |
| **No hallucinated data** | Numerical values in evidence match the adapter outputs or source artifacts they cite. | manual review (automatable when adapter logs are available) |

### Method

Schema conformance, trace validity, verdict-evidence consistency, and ontology
alignment are automatable. Evidence grounding and hallucination checks require
access to adapter invocation logs. Assumption quality and confidence
calibration require human review until rubric-based automation is built.

---

## Test artifact strategy

To make evaluation repeatable, maintain a set of **reference artifacts** with
known-correct outputs:

| Artifact | Expected output | Use cases exercised |
|----------|----------------|---------------------|
| A small SOLIDWORKS assembly (3–5 parts) | Known entity count, relationship graph, property values | Ontology graph validation |
| A synthetic vibration dataset (known frequencies) | Known spectral peaks, modal parameters | UC-02, adapter response validation |
| A simple transfer function (2nd-order system) | Known gain/phase margins, step response | UC-03, adapter response validation |
| A synthetic audio recording (known tones + noise) | Known FFT peaks, SNR | UC-04, adapter response validation |

Reference artifacts and their expected outputs are stored together. When an
adapter or reasoning component changes, re-run against reference artifacts and
compare.

---

## Evaluation levels

Evaluation is applied at three levels, from cheapest to most expensive:

| Level | What it checks | When to run | Automated? |
|-------|---------------|-------------|------------|
| **L0 — Schema** | Structural conformance (fields, types, enums). | Every output, every time. | Yes |
| **L1 — Consistency** | Cross-references (trace IDs exist, evidence sources exist, confidence matches rubric). | Every output, every time. | Yes |
| **L2 — Fidelity** | Semantic correctness (entities match the real artifact, numbers match adapter outputs, assumptions are falsifiable). | On changes to adapters or reasoning logic, and periodically. | Partially (reference artifacts automate some; human review for the rest) |

Bootstrap phase requires L0 and L1 to pass for every output. L2 is applied
manually until automation is built.
