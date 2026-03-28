# CLAUDE.md — Adri Project Memory

## Identity

Adri is a personal engineering operating system — a native desktop application that acts as the central nucleus connecting world-class tools through clean adapters. Each tool does only what it is world-class at. Adri is the glue, not the engine.

This repository is the canonical source of truth. There is no prior codebase to reference.

## Key context

- Clean restart of a prior concept called ENGOS. No old files are accessible.
- Author: ECE masters student at JHU (signal processing specialization).
- The project spans multiple engineering domains — do not assume software-only scope.
- The nucleus must be bulletproof before reasoning is added. Reasoning (whether a cheap LLM call or a custom engine) is only viable on top of a working nucleus.
- The nucleus is: adapters plug in, outputs are ingested, ontology is populated, everything is visible in one clean window.

## Tool ownership — world-class tools for world-class use cases only

Each tool keeps its domain. Adri never reimplements what a tool already does well.

| Tool | Owns | Boundary |
|------|------|----------|
| **SOLIDWORKS** | Geometry, assemblies, BOM | No signal math, no DAQ |
| **MATLAB** | All signals and systems analysis — FFT, Butterworth filtering, modal analysis, frequency response, peak detection | No data plumbing, no geometry |
| **LabVIEW** | Real-time DAQ, instrumentation, sensor streaming | No signal analysis, no geometry |
| **Python** | Lightweight data pipeline only — ingest, resample, format, export | No signal math (no FFT, no Butterworth, no peak detection) |
| **FL Studio** | Acoustics, audio signal processing | No structural analysis |
| **LM Studio** | Local AI inference | Does not replace engineering judgment |

**The signal chain:** LabVIEW captures raw DAQ stream → writes file → Python ingests, resamples, formats, and exports a clean file → MATLAB reads it and does all signal analysis.

## Three operational phases

| Phase | What happens | Tools active |
|-------|-------------|-------------|
| **Phase 1 — Design** | Ingest CAD artifact, call MATLAB to analyze at design time, iterate. Ontology captures what the artifact is and what its predicted behavior should be. | SOLIDWORKS, MATLAB |
| **Phase 2 — Physical** | Artifact gets built. LabVIEW instruments it with real sensors and DAQ. Ontology already knows what the artifact is from Phase 1. | LabVIEW, Python (data pipeline) |
| **Phase 3 — Live** | MATLAB processes live LabVIEW stream in chunks at full accuracy. Adri surfaces updates to GUI, flags anomalies against Phase 1 design predictions. | LabVIEW, Python (pipeline), MATLAB |

## North-star use case

Race-car sensor nervous system design: ingest a fully populated CAD assembly, reason across geometry, sensing, telemetry, control, and digital-twin readiness, propose sensor placement and trade-offs.

## GUI

The GUI is a native desktop window. It is deferred but always the intended end state. The engineer sees all tool outputs in one place, organized cleanly. The engineer remains the decision-maker.

## Demo artifact

A dummy demo exists in the repo showing a suspension corner (wheel, shock, control arms, road bump) being analyzed across all four tools simultaneously. This is a vision communication artifact, not a prototype.

## Vocabulary

Use these terms precisely. Do not invent synonyms.

- **Adapter**: interface between Adri's core and an external tool (SOLIDWORKS, MATLAB, LabVIEW, Python, FL Studio, LM Studio)
- **Artifact**: any engineering object Adri can ingest (CAD file, signal dataset, schematic, audio recording, etc.)
- **Constraint**: a named design constraint with a bound, unit, and type (upper/lower/equality/range)
- **Nucleus**: the working foundation — adapters plug in, outputs are ingested, ontology is populated, everything is visible. Must be bulletproof before reasoning is added.
- **Ontology**: the shared schema that lets Adri reason across domains
- **Recommendation**: a structured output with evidence, assumptions, risks, confidence, and trace
- **Signal**: a first-class ontology entity with spectrum, noise model, bandwidth, and transfer function
- **Tool contract**: the API/interface an adapter must satisfy

## Constraints

- Do not invent implementation details beyond what is documented.
- Do not assume access to any legacy ENGOS code or files.
- Treat `docs/adri_restart_brief.md` as the authoritative project brief.
- Keep documentation rigorous and concise. No filler.
- Python is the data janitor. It does not do signal math. FFT, Butterworth filtering, and peak detection belong to MATLAB.
- The nucleus must work before reasoning is layered on top.

## Repo structure

```
README.md                          — public-facing project overview
CLAUDE.md                          — this file (durable AI instructions)
AGENTS.md                          — instructions for AI agents (Claude, Codex)
pyproject.toml                     — project metadata and dependencies
docs/
  adri_restart_brief.md            — mission, vision, principles, next steps
  00_foundation/
    product_charter.md             — mission, scope, success criteria
    end_vision.md                  — narrative end-state vision
    use_cases.md                   — use-case catalogue
  01_system_model/
    ontology.md                    — entity/relationship schema
  02_reasoning/
    recommendation_schema.md       — recommendation output format
  03_tooling/
    adapter_contract.md            — adapter interface specification
  04_validation/
    evaluation_strategy.md         — correctness criteria for Adri outputs
  05_governance/
    decision_log.md                — append-only architectural decision record (DEC-001 – DEC-018)
  06_operations/
    operating_doctrine.md          — process infrastructure, gates, role model
    packet_template.md             — work packet proposal format
src/
  adri/
    ontology_store.py              — in-memory entity/relationship store (DEC-010)
  adapters/
    python_vibration/
      adapter.py                   — vibration CSV ingest + FFT peak detection
    matlab_vibration/
      adapter.py                   — MATLAB contract scaffold (NumPy fallback backend)
      normalize.py                 — normalize adapter outputs into ontology
  validators/
    l0_schema.py                   — L0 schema conformance checks
    l1_consistency.py              — L1 cross-reference consistency checks
  reasoning/
    vibration_stub.py              — deterministic vibration recommendation stub
  run_loop.py                      — 10-step bootstrap orchestrator
tests/
  test_ontology_store.py           — ontology store unit tests
  test_python_vibration_adapter.py — Python adapter unit tests
  test_matlab_vibration_adapter.py — MATLAB contract scaffold + normalization tests
  test_validators.py               — L0/L1 validator unit tests
  test_reasoning.py                — reasoning stub unit tests
  test_run_loop.py                 — orchestrator unit tests
  test_e2e.py                      — end-to-end loop integration tests
```
