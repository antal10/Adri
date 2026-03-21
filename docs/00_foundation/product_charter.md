# Product Charter — Adri

## Mission

Build a personal engineering operating system that reasons across engineering
domains, invokes real tools, and produces evidence-backed recommendations.

*Source: `docs/adri_restart_brief.md`, Mission.*

## Scope

### In scope

- Ingestion and representation of multi-domain engineering artifacts (CAD,
  simulation data, schematics, signal datasets, audio, code).
- A shared ontology that enables cross-domain reasoning without ad-hoc mappings.
- Adapter-mediated integration with external tools (SOLIDWORKS, MATLAB,
  LabVIEW, Python, Docker, LM Studio, FL Studio, and future tools).
- Structured, evidence-backed recommendations with explicit assumptions, risks,
  and confidence levels.
- Workflow composition from small, well-defined operations.

### Out of scope

- General-purpose chatbot functionality.
- Reimplementing CAD, simulation, or DAQ capabilities — Adri orchestrates these
  tools, it does not replace them.
- Replacing engineering judgment — Adri augments the engineer's decisions.
- Commitment to any single programming language or runtime platform.
- Any code, configuration, or architecture from the prior ENGOS project.

## Stakeholders

| Role | Description |
|------|-------------|
| **Author / Lead engineer** | ECE masters student at JHU (signal processing specialization). Primary user, architect, and decision-maker. |
| **AI agents** | Claude, Codex, and future agents that contribute to design and implementation under the constraints in `AGENTS.md`. |
| **Future collaborators** | Engineers or researchers who may later contribute adapters or domain extensions. |

## Success Criteria — Bootstrap Phase

The bootstrap phase is complete when all of the following are true:

1. **Ontology defined.** The entity, relationship, and property schema in
   `docs/01_system_model/ontology.md` is stable enough to represent the
   north-star use case without schema changes.
2. **Adapter contract specified.** A formal tool contract exists that any
   adapter can implement, with clear input/output types, error handling
   requirements, and capability declarations.
3. **First adapter operational.** At least one adapter (Python or MATLAB)
   can ingest an artifact and return a structured result through the adapter
   contract.
4. **Minimal reasoning loop.** Adri can ingest one artifact, traverse the
   ontology, invoke one adapter, and produce one recommendation that conforms
   to the recommendation schema.
5. **Documentation is self-consistent.** All documentation files reference
   consistent vocabulary and do not contradict each other.

## Governing Principles

This project is governed by six first principles. All design decisions must be
traceable to one or more of these.

| # | Principle | Implication |
|---|-----------|-------------|
| 1 | Signals and systems thinking | Signals are first-class entities with spectra, noise models, and transfer functions. |
| 2 | Adapter-first architecture | Core never talks to a tool directly. Adapters are the only integration boundary. |
| 3 | Ontology over convention | Cross-domain reasoning uses a shared schema, not ad-hoc mappings. |
| 4 | Evidence over opinion | Recommendations cite data, simulation results, or derivations. |
| 5 | Composability | Small, well-defined operations chain into complex workflows. |
| 6 | Tool-agnostic core | The reasoning engine has no dependency on any specific external tool. |

*Source: `docs/adri_restart_brief.md`, First Principles.*
