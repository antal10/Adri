# CLAUDE.md — Adri Project Memory

## Identity
Adri is an Engineering Operating System / personal engineering assistant.
This repository is the canonical source of truth. There is no prior codebase to reference.

## Key context
- Clean restart of a prior concept called ENGOS. No old files are accessible.
- Author: ECE masters student at JHU (signal processing specialization).
- The project spans multiple engineering domains — do not assume software-only scope.

## Vocabulary
- **Adapter**: interface between Adri's core and an external tool (SOLIDWORKS, MATLAB, etc.)
- **Artifact**: any engineering object Adri can ingest (CAD file, signal dataset, schematic, etc.)
- **Constraint**: a named design constraint with a bound, unit, and type (upper/lower/equality/range)
- **Ontology**: the shared schema that lets Adri reason across domains
- **Recommendation**: a structured output with evidence, assumptions, risks, confidence, and trace
- **Signal**: a first-class ontology entity with spectrum, noise model, bandwidth, and transfer function
- **Tool contract**: the API/interface an adapter must satisfy

## Constraints
- Do not invent implementation details beyond what is documented.
- Do not assume access to any legacy ENGOS code or files.
- Treat `docs/adri_restart_brief.md` as the authoritative project brief.
- Keep documentation rigorous and concise. No filler.

## Repo structure
```
README.md                          — high-level project overview
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
    decision_log.md                — append-only architectural decision record
src/
  adri/
    ontology_store.py              — in-memory entity/relationship store (DEC-010)
  adapters/
    python_vibration/
      adapter.py                   — vibration CSV ingest + FFT peak detection
    matlab_vibration/
      adapter.py                   — MATLAB file-in/file-out vibration adapter
      normalize.py                 — normalize MATLAB outputs into ontology
  validators/
    l0_schema.py                   — L0 schema conformance checks
    l1_consistency.py              — L1 cross-reference consistency checks
  reasoning/
    vibration_stub.py              — deterministic vibration recommendation stub
  run_loop.py                      — 10-step bootstrap orchestrator
tests/
  test_ontology_store.py           — ontology store unit tests
  test_python_vibration_adapter.py — Python adapter unit tests
  test_matlab_vibration_adapter.py — MATLAB adapter + normalization tests
  test_validators.py               — L0/L1 validator unit tests
  test_reasoning.py                — reasoning stub unit tests
  test_run_loop.py                 — orchestrator unit tests
  test_e2e.py                      — end-to-end loop integration tests
```
