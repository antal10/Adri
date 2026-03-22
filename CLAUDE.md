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
```
