# Adri — Restart Brief

## Mission
Build a personal engineering operating system that reasons across engineering domains, invokes real tools, and produces evidence-backed recommendations.

## End Vision
Adri is a multi-modal engineering assistant that:
1. Ingests artifacts from any supported tool (CAD, simulation, DAQ, audio, code)
2. Maintains a unified ontology so cross-domain reasoning is native, not bolted on
3. Invokes tools through well-defined adapters (not brittle scripts)
4. Produces recommendations grounded in data, simulation, or first-principles analysis
5. Scales from single-query answers to long-running collaborative design sessions

## North-Star Use Case
**Race-car sensor nervous system design.**

Given: a fully populated car CAD assembly.
Adri collaborates with the engineer to:
- Analyze geometry and subsystem topology from the CAD model
- Propose distributed sensor placements optimized for coverage, cost, or fidelity
- Classify sensing modalities (accelerometers, strain gauges, thermocouples, LIDAR, etc.)
- Map each sensing package to what it enables: basic telemetry → predictive maintenance → real-time control → digital-twin readiness
- Present trade-offs and let the engineer choose a tier

This use case exercises every core capability: artifact ingestion, cross-domain reasoning, tool invocation, and evidence-backed recommendation.

## First Principles
1. **Signals and systems thinking** — every engineering domain produces signals; Adri treats them as first-class objects with spectra, noise models, and transfer functions.
2. **Adapter-first architecture** — Adri's core never talks to a tool directly. Adapters are the only integration boundary.
3. **Ontology over convention** — cross-domain reasoning requires a shared schema, not ad-hoc mappings.
4. **Evidence over opinion** — recommendations cite data, simulation results, or derivations. No hand-waving.
5. **Composability** — small, well-defined operations that chain into complex workflows.
6. **Tool-agnostic core** — the reasoning engine has no dependency on any specific external tool.

## Non-Goals
- Adri is **not** a general-purpose AI chatbot.
- Adri is **not** a CAD tool, a simulator, or a DAQ system — it orchestrates them.
- Adri does **not** replace engineering judgment — it augments it.
- Adri is **not** tied to a single programming language or platform.
- This project is **not** carrying forward any ENGOS implementation. Concepts may persist; code does not.

## Architecture Reset
This repository is a clean restart. The prior ENGOS concept explored similar ideas but is not available as source material. What carries over:
- The *idea* of a cross-domain engineering assistant
- The *vocabulary* (adapters, artifacts, ontology, tool contracts)
- The *north-star use case*

What does not carry over:
- Any code, configuration, or file structure
- Any specific technology choices
- Any assumptions about runtime or deployment

## What Comes Next
1. **Define the ontology schema** — what entities, relationships, and properties does Adri understand?
2. **Specify the adapter contract** — what must an adapter implement to be valid?
3. **Build a first adapter** — likely Python or MATLAB, since those are most accessible.
4. **Implement a minimal reasoning loop** — ingest one artifact, answer one question about it.
5. **Iterate toward the north-star** — each cycle adds a domain, a tool, or a capability.
