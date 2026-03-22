# AGENTS.md — Instructions for AI Agents

This file is the entry point for any AI agent (Claude, Codex, or future agents)
working inside the Adri repository.

## What this repo is

Adri is an Engineering Operating System — a personal engineering assistant that
ingests engineering artifacts, reasons across domains, invokes real tools through
adapters, and produces evidence-backed recommendations.

This is NOT a chatbot, NOT a CAD/simulation/DAQ tool, and NOT a software-only
project. Adri orchestrates engineering tools; it does not replace them.

## Repo layout

```
CLAUDE.md                          — durable AI memory and vocabulary
AGENTS.md                          — this file (agent instructions)
README.md                          — public-facing project overview
docs/
  adri_restart_brief.md            — authoritative project brief
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

## Required vocabulary

Use these terms precisely. Do not invent synonyms.

| Term             | Meaning |
|------------------|---------|
| **Adapter**      | Interface between Adri's core and an external tool. |
| **Artifact**     | Any engineering object Adri can ingest (CAD file, signal dataset, schematic, etc.). |
| **Ontology**     | The shared schema that lets Adri reason across domains. |
| **Constraint**   | A named design constraint with a bound, unit, and type — a first-class ontology entity. |
| **Tool contract**| The API/interface an adapter must satisfy. |
| **Signal**       | A first-class entity with spectrum, noise model, and transfer function. |
| **Recommendation** | A structured output that includes evidence, assumptions, risks, and confidence. |

## Constraints for agents

1. **Authoritative sources.** Treat `docs/adri_restart_brief.md` as the
   authoritative project brief. Treat `CLAUDE.md` as the authoritative
   vocabulary and constraint set. Never contradict them.
2. **No invention.** Do not fabricate implementation details, technology choices,
   or architecture decisions that are not documented. If a decision has not been
   made, say so.
3. **No legacy assumptions.** There is no prior ENGOS code. Do not reference,
   assume, or reconstruct any.
4. **Ontology alignment.** Any new entity, relationship, or property you propose
   must be consistent with `docs/01_system_model/ontology.md`.
5. **Evidence standard.** Every recommendation must follow the schema in
   `docs/02_reasoning/recommendation_schema.md`. No hand-waving.
6. **Scope awareness.** Adri spans mechanical, electrical, signal processing,
   controls, and software domains. Do not assume a software-only context.
7. **Adapter boundary.** Never propose that Adri's core directly call an
   external tool. All tool interaction goes through an adapter.
8. **Conciseness.** Keep outputs rigorous and concise. No filler paragraphs.

## Handling ambiguity

When a question or task is ambiguous:

1. State the ambiguity explicitly.
2. List the reasonable interpretations (no more than three).
3. Identify which interpretation is most consistent with the restart brief and
   first principles.
4. Proceed with that interpretation, noting it as an assumption.
5. If no interpretation is clearly favored, ask the user before proceeding.

## How to navigate a task

1. Read `CLAUDE.md` first (always).
2. Read the restart brief if the task touches mission, vision, or principles.
3. Read the relevant `docs/` files for the domain of the task.
4. Check the ontology before proposing new entities or relationships.
5. Check the use-case catalogue to ground your work in concrete scenarios.
6. Produce output that follows existing document conventions (Markdown, same
   heading hierarchy, same vocabulary).
