# Decision Log

Append-only record of architectural and design decisions for the Adri project.
Each entry captures what was decided, why, and which governing principle(s) it
traces to. Entries are never modified after creation — if a decision is
reversed, add a new entry that supersedes the old one.

## Format

| Field | Description |
|-------|-------------|
| `ID` | Sequential identifier: `DEC-001`, `DEC-002`, etc. |
| `Date` | Date the decision was made (YYYY-MM-DD). |
| `Decision` | What was decided, in one sentence. |
| `Rationale` | Why this decision was made (2–3 sentences max). |
| `Principle` | Which governing principle(s) this traces to (by number from the product charter). |
| `Supersedes` | ID of a prior decision this replaces, if any. |

---

## Decisions

### DEC-001
| Field | Value |
|-------|-------|
| **Date** | 2025-06-15 |
| **Decision** | Clean restart: no code, configuration, or architecture carries over from ENGOS. |
| **Rationale** | The prior project's implementation was inaccessible and its technology choices were never validated. Starting clean avoids inheriting unexamined assumptions. |
| **Principle** | 6 (Tool-agnostic core) |
| **Supersedes** | — |

### DEC-002
| Field | Value |
|-------|-------|
| **Date** | 2025-06-15 |
| **Decision** | Signals are first-class ontology entities, not properties of sensors. |
| **Rationale** | A signal exists independently of the sensor that produced it — it has its own spectrum, noise model, bandwidth, and transfer function. Modeling signals as entities enables signal-chain reasoning (UC-05) and cross-domain queries. |
| **Principle** | 1 (Signals and systems thinking), 3 (Ontology over convention) |
| **Supersedes** | — |

### DEC-003
| Field | Value |
|-------|-------|
| **Date** | 2025-06-15 |
| **Decision** | Adapters must not create cross-domain relationships; only context assembly does. |
| **Rationale** | If adapters create cross-domain links, they must know about other adapters' schemas, violating adapter independence. Deferring cross-domain links to context assembly keeps each adapter self-contained. |
| **Principle** | 2 (Adapter-first architecture), 6 (Tool-agnostic core) |
| **Supersedes** | — |

### DEC-004
| Field | Value |
|-------|-------|
| **Date** | 2025-06-15 |
| **Decision** | Recommendations require at least one evidence item; assumptions may be empty with explicit justification. |
| **Rationale** | A recommendation without evidence is an opinion (violates principle 4). However, some outputs — such as direct measurement reports — may legitimately have no assumptions. Requiring a `no_assumptions_rationale` when the list is empty prevents silent omission while accommodating genuine cases. |
| **Principle** | 4 (Evidence over opinion) |
| **Supersedes** | — |

### DEC-005
| Field | Value |
|-------|-------|
| **Date** | 2025-06-15 |
| **Decision** | The adapter contract defines message shapes, not transport mechanisms. |
| **Rationale** | Committing to a transport (HTTP, gRPC, function calls) before any adapter exists would constrain implementation without evidence. Defining shapes first lets the first adapter choose the simplest transport, and the contract remains valid regardless. |
| **Principle** | 5 (Composability), 6 (Tool-agnostic core) |
| **Supersedes** | — |

### DEC-006
| Field | Value |
|-------|-------|
| **Date** | 2026-03-21 |
| **Decision** | Bootstrap documentation is structured in numbered layers (00–05) to enforce dependency order. |
| **Rationale** | Later layers (tooling, validation, governance) depend on earlier layers (foundation, system model, reasoning). Numbering makes the dependency explicit and prevents circular references. |
| **Principle** | 5 (Composability) |
| **Supersedes** | — |

### DEC-007
| Field | Value |
|-------|-------|
| **Date** | 2026-03-22 |
| **Decision** | The `Workflow` entity type is removed from the ontology until adapter contract implementation clarifies its required relationships. |
| **Rationale** | `Workflow` was defined but no relationship connected it to any other entity, making it orphaned. Adding speculative relationships would violate the evidence-over-opinion principle. The entity will be reintroduced with proper relationships when the first composed workflow is implemented. |
| **Principle** | 4 (Evidence over opinion), 5 (Composability) |
| **Supersedes** | — |

### DEC-008
| Field | Value |
|-------|-------|
| **Date** | 2026-03-22 |
| **Decision** | Added `Constraint` entity type, `bounded_by` relationship, and `controls` relationship to the ontology. |
| **Rationale** | UC-01 requires design constraints (budget, weight, channel count) as first-class inputs, which the ontology could not represent. UC-03 requires control-loop authority (controller governs plant behavior), which had no relationship. Both additions are required by existing use cases, not speculative. |
| **Principle** | 1 (Signals and systems thinking), 3 (Ontology over convention) |
| **Supersedes** | — |

### DEC-009
| Field | Value |
|-------|-------|
| **Date** | 2026-03-22 |
| **Decision** | Made `entity_types_produced` required in the adapter contract capability declaration, and specified that Adri's core (not the adapter) creates Artifact entities before invocation. |
| **Rationale** | `entity_types_produced` was optional but the ontology compliance rule demanded adapters only produce listed types — unenforceable when omitted. Artifact entity creation responsibility was unspecified, blocking the first adapter implementation. Both are minimal fixes discovered during pre-implementation architectural review. |
| **Principle** | 2 (Adapter-first architecture), 4 (Evidence over opinion) |
| **Supersedes** | — |

### DEC-010
| Field | Value |
|-------|-------|
| **Date** | 2026-03-22 |
| **Decision** | The bootstrap ontology store is an in-memory dict-of-entities plus a list-of-relationship-triples, with five query operations sufficient for L0/L1 validation. |
| **Rationale** | Persistence and query optimization are premature without evidence from the first adapter. A minimal in-memory structure satisfies L0/L1 evaluation requirements while avoiding technology commitments (no database, no graph library). |
| **Principle** | 4 (Evidence over opinion), 6 (Tool-agnostic core) |
| **Supersedes** | — |

### DEC-011
| Field | Value |
|-------|-------|
| **Date** | 2026-03-22 |
| **Decision** | The first reasoning component is a domain-specific stub named `vibration_reasoning_stub`, not a general reasoning engine. |
| **Rationale** | A general engine requires composition, goal decomposition, and adapter selection — none of which have evidence-backed designs yet. A domain-specific stub for UC-02 (vibration analysis from test data) delivers the bootstrap success criterion (ingest one artifact, produce one recommendation) without premature generalization. The name includes "stub" to signal it will be replaced. |
| **Principle** | 4 (Evidence over opinion), 5 (Composability) |
| **Supersedes** | — |

### DEC-012
| Field | Value |
|-------|-------|
| **Date** | 2026-03-22 |
| **Decision** | Adding `no_risks_rationale` to the recommendation schema is deferred until the first L0 validator is implemented. |
| **Rationale** | The asymmetry between `assumptions` (which has `no_assumptions_rationale`) and `risks` (which does not) was identified during review. However, the first implementation slice (UC-02 vibration stub) will always produce at least one risk, so the field is not blocking. The first L0 validator implementation will determine whether the field is needed or whether an alternative enforcement is preferable. |
| **Principle** | 4 (Evidence over opinion) |
| **Supersedes** | — |

### DEC-013
| Field | Value |
|-------|-------|
| **Date** | 2026-03-23 |
| **Decision** | The MATLAB adapter uses a file-in/file-out contract: `request.json` + `vibration.csv` in, `features.json` + `raw_output.mat` + `spectrum.png` + `run_log.txt` out. No direct Python-to-MATLAB invocation. |
| **Rationale** | File-based contracts decouple Adri from MATLAB's runtime (engine API, compiled runtime, or CLI). The same contract works whether MATLAB executes natively, via MATLAB Runtime, or is replaced by a NumPy fallback. This preserves future compatibility without premature transport commitments (DEC-005). |
| **Principle** | 2 (Adapter-first architecture), 5 (Composability), 6 (Tool-agnostic core) |
| **Supersedes** | — |

### DEC-014
| Field | Value |
|-------|-------|
| **Date** | 2026-03-23 |
| **Decision** | Run artifacts are persisted as flat files in a per-run directory. No database, no generic storage subsystem. |
| **Rationale** | The first MATLAB slice needs reproducibility (source CSV copy, request manifest, raw outputs, logs) but no query capability beyond file reads. A flat directory per run is the simplest structure that satisfies provenance requirements without technology commitments. |
| **Principle** | 4 (Evidence over opinion), 6 (Tool-agnostic core) |
| **Supersedes** | — |

### DEC-015
| Field | Value |
|-------|-------|
| **Date** | 2026-03-23 |
| **Decision** | MATLAB-produced output artifacts are represented as `Artifact` entities linked to the source CSV via `references` relationships, not `derived_from`. |
| **Rationale** | The ontology's `derived_from` relationship is defined for `Signal`/`TransferFunction` sources, not `Artifact`→`Artifact`. Using `references` (which allows `Artifact`→any) correctly expresses "this output file references the source data" without inventing new relationship types. |
| **Principle** | 3 (Ontology over convention), 4 (Evidence over opinion) |
| **Supersedes** | — |

### DEC-016
| Field | Value |
|-------|-------|
| **Date** | 2026-03-23 |
| **Decision** | The MATLAB vibration adapter is a contract scaffold backed by a NumPy fallback. It does not invoke MATLAB. Every output artifact and response records the producing backend (`numpy_fallback` or `matlab`). |
| **Rationale** | DEC-013 correctly defined the file-in/file-out contract but did not distinguish contract shape from execution backend. The current implementation validates the contract, persistence, and normalization layers without MATLAB. Claiming MATLAB integration without actual invocation is misleading. The `backend` field in all outputs makes the execution source explicit and machine-readable. |
| **Principle** | 4 (Evidence over opinion) |
| **Supersedes** | Clarifies DEC-013 (contract is scaffold, not live MATLAB integration). |

### DEC-017
| Field | Value |
|-------|-------|
| **Date** | 2026-03-23 |
| **Decision** | DEC-015's phrasing "MATLAB-produced output artifacts" is corrected: output artifacts are produced by whichever backend is active (currently `numpy_fallback`). The `references` relationship choice remains valid regardless of backend. |
| **Rationale** | DEC-015's relationship design is correct but its language implied MATLAB execution. The relationship type choice (`references` over `derived_from` for Artifact→Artifact links) is backend-independent and does not need to change. Only the framing needed correction. |
| **Principle** | 4 (Evidence over opinion) |
| **Supersedes** | Corrects framing of DEC-015 (output artifacts are backend-produced, not necessarily MATLAB-produced). |
