# Use Cases

Each use case has a unique ID, title, domain coverage, input artifacts, goal,
and a description of Adri's role. The north-star use case is UC-01.

---

## UC-01 — Race-Car Sensor Nervous System Design

| Field | Value |
|-------|-------|
| **ID** | UC-01 |
| **Domains** | Mechanical (CAD), Electrical (sensors), Signal Processing, Data Acquisition |
| **Input artifacts** | SOLIDWORKS assembly (full car), subsystem topology, design constraints (budget, weight, channel count) |
| **Goal** | Design a distributed sensor placement that meets a specified capability tier (telemetry, predictive maintenance, real-time control, or digital-twin readiness). |

**Adri's role:**
- Ingest the CAD assembly and extract geometry, mounting surfaces, and
  subsystem boundaries through the SOLIDWORKS adapter.
- Propose sensor types and placements based on coverage, accessibility, and
  signal quality.
- Classify each sensing package by what it enables (basic telemetry through
  full digital-twin).
- Run signal-level feasibility checks: bandwidth, noise floor, Nyquist
  constraints, cable routing distances.
- Present trade-offs across capability tiers and let the engineer select.
- Produce a structured recommendation per the recommendation schema.

---

## UC-02 — Vibration Analysis from Test Data

| Field | Value |
|-------|-------|
| **ID** | UC-02 |
| **Domains** | Signal Processing, Mechanical |
| **Input artifacts** | Time-series acceleration data (CSV or MATLAB .mat), CAD model of the structure under test |
| **Goal** | Identify resonant frequencies, mode shapes, and damping ratios; compare measured results against simulation predictions. |

**Adri's role:**
- Ingest the acceleration dataset through the Python or MATLAB adapter.
- Compute power spectral densities, identify spectral peaks, and estimate
  modal parameters.
- If a CAD model is provided, map identified modes to structural components
  using the ontology.
- If a prior simulation exists, compare measured vs. predicted natural
  frequencies and flag discrepancies beyond a user-defined tolerance.
- Produce a recommendation: whether the structure meets vibration
  requirements, what to investigate if it does not.

---

## UC-03 — Control Loop Verification

| Field | Value |
|-------|-------|
| **ID** | UC-03 |
| **Domains** | Controls, Signal Processing, Data Acquisition |
| **Input artifacts** | LabVIEW VI (control block diagram), plant transfer function (MATLAB), sensor specifications |
| **Goal** | Verify that a control loop meets stability and performance requirements before deployment. |

**Adri's role:**
- Ingest the control block diagram through the LabVIEW adapter and the plant
  model through the MATLAB adapter.
- Combine controller and plant into the closed-loop transfer function.
- Evaluate stability margins (gain margin, phase margin), step response
  characteristics (overshoot, settling time), and bandwidth.
- Cross-check that the sensor's bandwidth, resolution, and noise floor are
  adequate for the required loop bandwidth.
- Produce a recommendation: pass/fail against requirements, with evidence
  from Bode/Nyquist analysis.

---

## UC-04 — Acoustic Environment Characterization

| Field | Value |
|-------|-------|
| **ID** | UC-04 |
| **Domains** | Signal Processing (audio/acoustic), Mechanical |
| **Input artifacts** | Audio recordings (.wav), microphone specifications, CAD model of the enclosure or environment |
| **Goal** | Characterize the acoustic environment (frequency response, reverberation, noise sources) and recommend treatment if needed. |

**Adri's role:**
- Ingest audio recordings through the FL Studio or Python adapter.
- Compute spectral analysis: FFT, 1/3-octave bands, RT60 estimation.
- If a CAD model of the enclosure is provided, correlate acoustic behavior
  with geometry (room modes, reflection paths).
- Identify dominant noise sources by frequency band.
- Produce a recommendation: whether the environment meets acoustic
  requirements, what treatment (absorption, isolation, damping) to consider.

---

## UC-05 — Multi-Physics Signal Chain Audit

| Field | Value |
|-------|-------|
| **ID** | UC-05 |
| **Domains** | Electrical, Signal Processing, Data Acquisition, Software |
| **Input artifacts** | Sensor datasheets (PDF/structured data), DAQ configuration (LabVIEW), signal conditioning schematic, processing pipeline (Python script) |
| **Goal** | Audit an end-to-end signal chain from physical measurand to stored data, verifying that no stage introduces unacceptable error, aliasing, or data loss. |

**Adri's role:**
- Ingest each stage of the signal chain as a separate artifact.
- Build the ontology subgraph: measurand, sensor, conditioning, ADC,
  digital filter, storage.
- Propagate signal properties through the chain: bandwidth narrows, noise
  accumulates, quantization adds error.
- Check Nyquist compliance at every analog-to-digital boundary.
- Flag any stage where signal-to-noise ratio, dynamic range, or bandwidth
  is the bottleneck.
- Produce a recommendation: pass/fail per stage, with the limiting stage
  identified and mitigation options listed.
