# Operating Doctrine

Process infrastructure for how Adri is built, reviewed, and merged.
This document is additive — it formalizes existing practice and does not
alter architecture, ontology, or adapter contracts.

*Adopted: DEC-018. Source: docs/adri_restart_brief.md, docs/00_foundation/product_charter.md.*

---

## 1. Product doctrine

Adri is:

| Property | Grounding |
|----------|-----------|
| Project/workspace centered | Restart brief: "personal engineering operating system." |
| Artifact first | Ontology: `Artifact` is a first-class entity. Adapter contract §6. |
| Adapter driven | Principle 2: core never talks to a tool directly. |
| Reproducible | DEC-014: per-run directory with source copies and manifests. |
| Auditable | DEC-016: backend labeling. L0/L1 validators. Decision log. |
| Tool agnostic at the orchestration layer | Principle 6: no dependency on any specific external tool. |

Adri is not:

| Exclusion | Source |
|-----------|--------|
| A CAD rewrite | Restart brief non-goals. |
| A MATLAB rewrite | Restart brief non-goals. |
| An LLM toy shell | Restart brief: "not a general-purpose AI chatbot." |
| A chat UI pretending to be engineering software | Restart brief: "not a chatbot … it orchestrates them." |

---

## 2. Role model

| Role | Responsibility |
|------|----------------|
| **Human (author / lead engineer)** | Architect. Doctrine owner. Merge authority. Arbiter of product direction. |
| **ChatGPT** | Spec writer. Packet writer. Architecture reviewer. Cross-slice consistency checker. |
| **Claude Code** | Primary narrow builder. |
| **Codex** | Adversarial reviewer or alternate builder on isolated branch. |
| **Local models** | Cheap triage. Structured extraction. Schema checking. Batch classification. |
| **Deterministic system** | Actual judge. L0/L1 validators, test suite, and deterministic gates are the authority on pass/fail — not LLM agreement. |

*Cross-reference: product_charter.md Stakeholders table.*

---

## 3. Gate list

Every slice must pass these gates before merge consideration.

| Gate | What it checks |
|------|----------------|
| **G0 — Scope** | Touched files from allowlist only. No surprise dependencies. No broad refactor. |
| **G1 — Contract** | Adapter input/output contract valid. Schema passes. Artifact names/locations correct. |
| **G2 — Validation** | L0 schema checks pass. L1 consistency/provenance checks pass. |
| **G3 — Runtime** | Tests pass. Smoke path works. Deterministic behavior acceptable. |
| **G4 — Evidence** | Outputs exist. Logs present. Provenance present. Backend labeling honest. |
| **G5 — Review** | PR/report packet generated. Diff understandable. Claims match implementation. |

### Human gate

The following actions require explicit human approval regardless of gate status:

- Merge to main
- Ontology changes (entity types, relationship types, properties)
- Adapter boundary changes (new contract fields, transport changes)
- Architecture changes (new layers, new dependencies, new subsystems)
- External side effects (pushes, deployments, messages to third parties)

LLM agreement never substitutes for these gates.

*Cross-reference: evaluation_strategy.md (L0, L1, L2 levels map to G2/G4).*

#### Change control gates

All file-system and git operations require explicit, separate approvals:

1. **Write gate**: file creates/edits require approval before execution.
2. **Commit gate**: staging and committing require approval after writes are verified.
3. **Push gate**: pushing to a remote requires approval after the commit is verified.

Gates are sequential. Approval of an earlier gate does not imply approval of
a later gate. When instructions conflict, the more restrictive instruction wins.

---

## 4. Unattended task boundaries

### Safe for unattended execution

- Narrow slice implementation within pre-approved file scope
- Test execution and regression checks
- Artifact contract validation
- L0/L1 validator runs
- Report/packet generation
- Doc sync from code reality
- Backlog decomposition into next slices
- Cross-model audit loops
- Benchmark runs

### Not safe unattended

- Architecture pivots
- Ontology surgery
- UI direction changes
- Large refactors
- Dependency sprawl
- Merge decisions
- Anything ambiguous

---

## 5. Phase/tier mapping

The operating doctrine uses "Phase 1–4" to describe the build roadmap.
`docs/00_foundation/end_vision.md` uses "Tier 0–4" to describe capability
levels. The content is the same; the numbering is offset by one because the
end vision counts the bootstrap as Tier 0.

| Operating doctrine | End vision | Description |
|--------------------|------------|-------------|
| Phase 1 — Substrate | Tier 0 — Bootstrap | Ontology, validators, run loop, artifact contracts, provenance, deterministic gates. |
| Phase 2 — Tool adapters | Tier 1 — Single-domain reasoning | Real tool boundaries added one at a time: Python → MATLAB → file/report → SOLIDWORKS. |
| Phase 3 — Workspace orchestration | Tier 2/3 — Cross-domain reasoning / Collaborative sessions | Project workspace, run history, job queue, artifact browser, cross-tool traceability. |
| Phase 4 — Unified operator surface | Tier 4 — Full vision | One place to launch jobs, inspect outputs, compare revisions, see provenance across tools. |

Neither naming scheme supersedes the other. The end vision tiers define
*what* Adri can do at each level. The operating doctrine phases describe
*how* the build proceeds. Use whichever is appropriate to the context.
