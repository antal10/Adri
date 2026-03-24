# Adri

**Adri** is an Engineering Operating System — a personal engineering assistant that ingests engineering artifacts, reasons across domains, invokes real tools, and produces evidence-backed recommendations.

## What problem does Adri solve?

Engineering work spans dozens of disconnected tools. CAD lives in SOLIDWORKS, analysis in MATLAB, control logic in LabVIEW, automation in Python, inference in local LLMs. No system reasons *across* these boundaries. Adri is that reasoning layer.

## North-star use case

Given a fully populated car CAD assembly, Adri collaborates with the engineer to design a race-car nervous system:

- Determine optimal distributed sensor placement
- Determine sensor types and sensing modalities
- Define what each sensing package enables (telemetry, control, digital-twin readiness)
- Support goals from minimal telemetry to full digital-twin

## Target tool ecosystem

Adri is designed to eventually work across:

| Tool | Role |
|------|------|
| SOLIDWORKS | CAD / geometry / assemblies |
| MATLAB | Analysis / simulation / signal processing |
| LabVIEW | Real-time control / data acquisition |
| Python | Scripting / ML / orchestration |
| Docker | Environment isolation / reproducibility |
| LM Studio | Local LLM inference |
| FL Studio | Audio / acoustic signal processing |

Other adapters may be added if they fit the ontology and tool contract.

## Current status

**Bootstrap slice complete.** The first end-to-end loop works: ingest a vibration CSV, populate the ontology, validate at L0/L1, produce a recommendation, and validate it again.

### What exists

| Component | Location | Purpose |
|-----------|----------|---------|
| Ontology store | `src/adri/ontology_store.py` | In-memory entity/relationship store (DEC-010) |
| Python vibration adapter | `src/adapters/python_vibration/` | Ingest single-channel vibration CSV, compute FFT peaks |
| MATLAB vibration adapter | `src/adapters/matlab_vibration/` | File-in/file-out contract scaffold (NumPy fallback; MATLAB backend not yet wired) |
| L0 validator | `src/validators/l0_schema.py` | Schema conformance for entities, adapter responses, recommendations |
| L1 validator | `src/validators/l1_consistency.py` | Cross-reference consistency (trace, provenance, compliance) |
| Vibration reasoning stub | `src/reasoning/vibration_stub.py` | Deterministic rule-based recommendation from FFT peaks |
| Run loop | `src/run_loop.py` | 10-step orchestrator wiring the full pipeline |

### Running tests

```bash
pip install -e ".[dev]"
pytest
```

See [docs/adri_restart_brief.md](docs/adri_restart_brief.md) for the full project brief.
