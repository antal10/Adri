# Adri

**Adri** is a personal engineering operating system — a native desktop application that acts as the central nucleus connecting world-class tools through clean adapters. Each tool does only what it is world-class at. Adri is the glue, not the engine.

## What problem does Adri solve?

Engineering work spans dozens of disconnected tools. CAD lives in SOLIDWORKS, signals and systems analysis lives in MATLAB, real-time DAQ lives in LabVIEW, acoustics live in FL Studio, local AI inference lives in LM Studio. No system reasons *across* these boundaries. The engineer switches tools, copies files, re-enters parameters, and stitches results together by hand.

Adri is the nucleus that sits between the engineer and every tool in their ecosystem. It ingests artifacts through adapters, populates a shared ontology, and makes everything visible in one clean window. The engineer remains the decision-maker. Adri is the connective tissue.

## Philosophy

**World-class tools for world-class use cases only.** Each tool keeps its domain. Adri never reimplements what a tool already does well.

| Tool | Owns | Does NOT do |
|------|------|-------------|
| SOLIDWORKS | Geometry, assemblies, BOM | Signal math, DAQ |
| MATLAB | All signals and systems analysis — FFT, filtering, modal analysis, frequency response, peak detection | Data plumbing, geometry |
| LabVIEW | Real-time DAQ, instrumentation, sensor streaming | Signal analysis, geometry |
| Python | Lightweight data pipeline — ingest, resample, format, export | Signal math (no FFT, no Butterworth, no peak detection) |
| FL Studio | Acoustics, audio signal processing | Structural analysis |
| LM Studio | Local AI inference | Replacing engineering judgment |

Python is the data janitor. It sits between LabVIEW and MATLAB. Its pipeline is: **Ingest → Resample → Format → Export**. No signal math. The correct chain is: LabVIEW captures the raw DAQ stream → writes a file → Python ingests, resamples, formats, and exports a clean file → MATLAB reads it and does all signal analysis.

## Three operational phases

Adri operates across the full lifecycle of an engineering artifact:

### Phase 1 — Design

Ingest a CAD artifact from SOLIDWORKS. Call MATLAB to analyze it at design time — modal analysis, frequency response, predicted dynamics. Iterate on the design. The ontology captures what the artifact *is* and what its predicted behavior *should be*.

### Phase 2 — Physical

The artifact gets built. LabVIEW instruments it with real sensors and DAQ. The ontology already knows what the artifact is from Phase 1 — it now links physical sensor channels to the geometry and predicted dynamics established during design.

### Phase 3 — Live operation

MATLAB processes the live LabVIEW stream in chunks at full accuracy. Adri surfaces updates to the GUI and flags anomalies against Phase 1 design predictions. Measured behavior is compared to predicted behavior. Discrepancies trigger investigation.

## North-star use case

**Race-car sensor nervous system design.**

Given a fully populated car CAD assembly, Adri collaborates with the engineer to:

- Reason across geometry, sensing, telemetry, control, and digital-twin readiness
- Propose optimal distributed sensor placement and sensing modalities
- Map each sensing package to what it enables (basic telemetry → predictive maintenance → real-time control → digital-twin readiness)
- Present trade-offs and let the engineer choose a tier

This use case exercises every core capability: artifact ingestion, cross-domain reasoning, tool invocation, and evidence-backed recommendation.

## Architecture

Adri's architecture is governed by six first principles and an append-only decision log (DEC-001 through DEC-018). See [`docs/05_governance/decision_log.md`](docs/05_governance/decision_log.md) for the full record.

### The nucleus must be bulletproof before reasoning is added

The nucleus is the foundation: adapters plug in, outputs are ingested, the ontology is populated, everything is visible in one clean window. Reasoning — whether a cheap LLM call or a custom engine — is only viable on top of a working nucleus. The current bootstrap slice validates this foundation.

### Adapter-first architecture

Adri's core never talks to a tool directly. Every tool interaction goes through an adapter that satisfies the [adapter contract](docs/03_tooling/adapter_contract.md). This means swapping SOLIDWORKS for another CAD tool requires only a new adapter, not a redesign.

### Ontology as shared language

Every artifact that enters Adri is decomposed into entities and relationships in a [shared ontology](docs/01_system_model/ontology.md). A query like "which sensors are affected if I stiffen this suspension member?" traverses the ontology from a mechanical component, through a mounting relationship, to a sensor entity, through a signal chain — crossing CAD, signal processing, and DAQ domains in one query.

## GUI

The GUI is a native desktop window. It is deferred but always the intended end state. The engineer sees all tool outputs in one place, organized cleanly. No web app, no Electron wrapper — a real desktop application where the engineer remains in control.

## Demo artifact

A dummy demo exists showing a suspension corner (wheel, shock, control arms, road bump) being analyzed across all four tools simultaneously — SOLIDWORKS owns geometry, MATLAB owns dynamics and frequency analysis, LabVIEW owns real-time sensors, Python handles the data pipeline. This is a vision communication artifact, not a prototype. It demonstrates the concept of the nucleus: one window, four tools, clean adapters, the engineer decides.

## Current status

**Bootstrap slice complete.** The first end-to-end loop works: ingest a vibration CSV, populate the ontology, validate at L0/L1, produce a recommendation, and validate it again.

### What exists

| Component | Location | Purpose |
|-----------|----------|---------|
| Ontology store | `src/adri/ontology_store.py` | In-memory entity/relationship store (DEC-010) |
| Python vibration adapter | `src/adapters/python_vibration/` | Ingest single-channel vibration CSV, compute FFT peaks |
| MATLAB vibration adapter | `src/adapters/matlab_vibration/` | File-in/file-out contract with `matlab -batch` execution when configured, plus NumPy fallback |
| L0 validator | `src/validators/l0_schema.py` | Schema conformance for entities, adapter responses, recommendations |
| L1 validator | `src/validators/l1_consistency.py` | Cross-reference consistency (trace, provenance, compliance) |
| Vibration reasoning stub | `src/reasoning/vibration_stub.py` | Deterministic rule-based recommendation from FFT peaks |
| Run loop | `src/run_loop.py` | 10-step orchestrator wiring the full pipeline |

### Running tests

```bash
pip install -e ".[dev]"
pytest
```

## Documentation

| Document | Purpose |
|----------|---------|
| [`docs/adri_restart_brief.md`](docs/adri_restart_brief.md) | Authoritative project brief |
| [`docs/00_foundation/product_charter.md`](docs/00_foundation/product_charter.md) | Mission, scope, success criteria |
| [`docs/00_foundation/end_vision.md`](docs/00_foundation/end_vision.md) | Narrative end-state vision |
| [`docs/00_foundation/use_cases.md`](docs/00_foundation/use_cases.md) | Use-case catalogue (UC-01 through UC-05) |
| [`docs/01_system_model/ontology.md`](docs/01_system_model/ontology.md) | Entity/relationship schema |
| [`docs/03_tooling/adapter_contract.md`](docs/03_tooling/adapter_contract.md) | Adapter interface specification |
| [`docs/05_governance/decision_log.md`](docs/05_governance/decision_log.md) | Append-only architectural decision record |
| [`docs/06_operations/operating_doctrine.md`](docs/06_operations/operating_doctrine.md) | Process infrastructure |
