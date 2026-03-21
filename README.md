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

**Bootstrap phase.** Documentation nucleus only — no implementation yet.

See [docs/adri_restart_brief.md](docs/adri_restart_brief.md) for the full project brief.
