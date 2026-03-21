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
- **Ontology**: the shared schema that lets Adri reason across domains
- **Tool contract**: the API/interface an adapter must satisfy

## Constraints
- Do not invent implementation details beyond what is documented.
- Do not assume access to any legacy ENGOS code or files.
- Treat `docs/adri_restart_brief.md` as the authoritative project brief.
- Keep documentation rigorous and concise. No filler.

## Repo structure
```
README.md              — high-level project overview
CLAUDE.md              — this file (durable AI instructions)
docs/
  adri_restart_brief.md — mission, vision, principles, next steps
```
