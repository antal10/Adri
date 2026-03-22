# Recommendation Schema

Every recommendation Adri produces must conform to this schema. The schema
enforces the "evidence over opinion" principle: no recommendation is valid
without evidence, explicit assumptions, identified risks, and a stated
confidence level.

---

## Schema fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier (e.g., `REC-001`). |
| `title` | string | yes | Short, descriptive title. |
| `goal` | string | yes | The objective this recommendation addresses. |
| `verdict` | enum: `recommended`, `acceptable`, `not_recommended`, `insufficient_data` | yes | Overall assessment. |
| `evidence` | list of Evidence | yes (min 1) | Data, simulation results, or derivations supporting the verdict. |
| `assumptions` | list of Assumption | yes (may be empty with justification) | Conditions assumed true but not verified. If empty, `no_assumptions_rationale` is required. |
| `no_assumptions_rationale` | string | conditional | Required when `assumptions` list is empty. Explains why no assumptions are needed (e.g., direct measurement with no modeling). |
| `risks` | list of Risk | yes (may be empty with justification) | What could go wrong if the recommendation is followed. |
| `confidence` | Confidence | yes | How certain Adri is in this recommendation. |
| `alternatives` | list of Alternative | no | Other options considered and why they were not preferred. |
| `trace` | list of string (entity IDs) | yes | Ontology entities and relationships traversed to reach this recommendation. |

### Evidence

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | enum: `data`, `simulation`, `derivation`, `datasheet`, `reference` | yes | Category of evidence. |
| `source` | string | yes | Where the evidence comes from (artifact ID, adapter name, citation). |
| `summary` | string | yes | One-sentence description of what the evidence shows. |
| `value` | string or number | no | The specific data point, if applicable. |
| `unit` | string | no | Unit of the value, if applicable. |

### Assumption

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier (e.g., `A-01`). |
| `statement` | string | yes | The assumption, stated as a falsifiable claim. |
| `basis` | string | yes | Why this assumption is reasonable (prior data, convention, user input). |
| `impact_if_wrong` | enum: `low`, `medium`, `high`, `critical` | yes | Consequence severity if the assumption is false. |

### Risk

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier (e.g., `R-01`). |
| `description` | string | yes | What could go wrong. |
| `likelihood` | enum: `low`, `medium`, `high` | yes | How likely this risk is. |
| `severity` | enum: `low`, `medium`, `high`, `critical` | yes | Impact if the risk materializes. |
| `mitigation` | string | no | Suggested mitigation, if one exists. |

### Confidence

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `level` | enum: `high`, `moderate`, `low`, `speculative` | yes | Overall confidence level. |
| `rationale` | string | yes | Why this confidence level was assigned. |
| `limiting_factor` | string | yes | The single weakest link in the evidence or assumption chain. |

### Alternative

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Short name for the alternative. |
| `summary` | string | yes | What this alternative entails. |
| `reason_not_preferred` | string | yes | Why it was ranked below the primary recommendation. |

---

## How confidence is assessed

Confidence is determined by the weakest link in the chain from evidence to
verdict.

| Level | Criteria |
|-------|----------|
| `high` | All evidence is quantitative (data or simulation), assumptions are few and well-founded, no high-severity risks. |
| `moderate` | Evidence is mostly quantitative but at least one assumption has `medium` or `high` impact-if-wrong, or one risk has `medium` likelihood and `high` severity. |
| `low` | Evidence relies partly on datasheets or references without independent verification, or multiple assumptions have `high` impact-if-wrong. |
| `speculative` | Evidence is incomplete, key assumptions are unverified, or the recommendation extrapolates beyond available data. Adri flags this explicitly and recommends what additional data would raise confidence. |

The `limiting_factor` field identifies the single element (an assumption, a
missing data source, a risk) that most constrains confidence. This tells the
engineer exactly what to investigate to improve the recommendation.

## How assumptions are tracked

Assumptions are not fire-and-forget. They follow a lifecycle:

1. **Created.** An assumption is stated when a recommendation is generated.
   It includes its basis and impact-if-wrong.
2. **Referenced.** The assumption's ID is referenced by any recommendation
   that depends on it. Multiple recommendations may share assumptions.
3. **Validated or invalidated.** When new evidence arrives (a test result,
   a simulation, a measurement), assumptions can be checked. If an assumption
   is invalidated, every recommendation that depends on it is flagged for
   re-evaluation.
4. **Retired.** Once an assumption is validated with evidence, it is
   reclassified as evidence and the recommendation's confidence may be updated.

This lifecycle ensures that as the engineer gathers more data, Adri's
recommendations improve rather than stagnate.

---

## Example — North-star use case (UC-01)

```yaml
id: REC-001
title: Rear suspension sensor package — Tier 2 (predictive maintenance)
goal: >
  Select and place sensors on the rear suspension subsystem to enable
  predictive maintenance capability.
verdict: recommended

evidence:
  - type: simulation
    source: MATLAB adapter / modal analysis of rear upright
    summary: First three natural frequencies are 85 Hz, 210 Hz, 440 Hz.
    value: [85, 210, 440]
    unit: Hz
  - type: datasheet
    source: ADXL345 datasheet (Analog Devices)
    summary: Bandwidth up to 1600 Hz, noise density 230 ug/sqrt(Hz).
  - type: derivation
    source: Nyquist analysis
    summary: >
      Sampling at 1000 Hz captures all three modes with margin
      (1000 > 2 * 440).

assumptions:
  - id: A-01
    statement: >
      The rear upright geometry in the CAD model accurately represents the
      as-built part.
    basis: CAD model is revision-controlled and was updated after last manufacture.
    impact_if_wrong: high
  - id: A-02
    statement: >
      Operating vibration environment does not excite modes above 500 Hz
      with significant energy.
    basis: >
      Similar vehicles in FSAE competition show dominant vibration content
      below 400 Hz.
    impact_if_wrong: medium

risks:
  - id: R-01
    description: >
      Sensor mounting may alter local dynamics, shifting resonant frequencies.
    likelihood: low
    severity: medium
    mitigation: >
      Validate with a brief impact-hammer test after installation.
  - id: R-02
    description: >
      Cable routing from rear upright to DAQ introduces noise pickup from
      motor controller PWM.
    likelihood: medium
    severity: medium
    mitigation: Use shielded twisted-pair cable and route away from power cables.

confidence:
  level: moderate
  rationale: >
    Modal analysis is simulation-based (not measured), and the vibration
    environment assumption is based on analogous vehicles, not this specific
    car. Core signal-chain math is sound.
  limiting_factor: >
    A-01 (CAD accuracy) — if the as-built geometry differs from the model,
    the predicted natural frequencies may be wrong.

alternatives:
  - title: Tier 1 — basic telemetry only
    summary: Single accelerometer on each upright, sampled at 500 Hz.
    reason_not_preferred: >
      Insufficient bandwidth to capture the 440 Hz mode; cannot support
      predictive maintenance.
  - title: Tier 3 — real-time control readiness
    summary: >
      Add strain gauges and a high-speed DAQ (5 kHz), enabling closed-loop
      active damping.
    reason_not_preferred: >
      Requires active suspension hardware not currently in the vehicle;
      cost and complexity disproportionate to current goals.

trace:
  - subsystem:rear-suspension
  - component:rear-upright-left
  - interface:upright-mounting-face
  - sensor:adxl345-rear-left
  - signal:accel-rear-left
  - signal-chain:rear-left-vibration
  - daq-channel:ni9234-ch0
```

This example demonstrates every required field. The confidence is `moderate`
rather than `high` because the modal analysis is simulation-only and one
assumption carries `high` impact-if-wrong. The `limiting_factor` tells the
engineer exactly what to verify (CAD accuracy) to raise confidence.
