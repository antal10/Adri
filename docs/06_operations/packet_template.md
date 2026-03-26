# Packet Template

Standard form for proposing a work packet. Every packet follows this template
so that scope, dependencies, and acceptance criteria are explicit before work
begins.

## Fields

| Field | Required | Description |
|-------|----------|-------------|
| `Packet ID` | yes | Sequential identifier: `A-001`, `A-002`, etc. |
| `Title` | yes | One-line description of the deliverable. |
| `Status` | yes | One of: `proposed`, `approved`, `in-progress`, `complete`, `rejected`. |
| `Author` | yes | Who wrote the proposal. |
| `Date` | yes | Date proposed (YYYY-MM-DD). |
| `Scope` | yes | What this packet delivers. Bullet list, each item concrete and verifiable. |
| `Out of scope` | yes | What this packet explicitly does not do. Prevents scope creep. |
| `Dependencies` | yes | Packet IDs, decision IDs, or file paths that must exist before work starts. Use `none` if no dependencies. |
| `Files touched` | yes | Exhaustive list of files created or modified. |
| `Acceptance criteria` | yes | Conditions that must be true for the packet to be marked `complete`. Each criterion is pass/fail. |
| `Decision records` | no | DEC-IDs introduced by this packet, if any. |
| `Notes` | no | Anything else the reviewer needs. |

## Rules

1. A packet must be `approved` before any file writes begin.
2. A packet touches only the files listed in `Files touched`. Discovering that
   additional files need changes requires amending the packet and re-approval.
3. One packet = one reviewable change set, typically one branch/PR. Multiple
   commits are allowed if they remain within the approved packet scope. Do not
   bundle unrelated changes.
4. `Out of scope` is enforced: if work drifts into out-of-scope territory,
   stop and propose a new packet.
5. Acceptance criteria are evaluated before the packet is marked `complete`.
   If any criterion fails, the packet remains `in-progress`.

## Template

Copy and fill in:

~~~
### A-NNN: <Title>

| Field | Value |
|-------|-------|
| **Packet ID** | A-NNN |
| **Title** | |
| **Status** | proposed |
| **Author** | |
| **Date** | |

**Scope**
-

**Out of scope**
-

**Dependencies**
-

**Files touched**
-

**Acceptance criteria**
- [ ]

**Decision records**
-

**Notes**
-
~~~

## Example

### A-008: Real MATLAB backend for vibration adapter

| Field | Value |
|-------|-------|
| **Packet ID** | A-008 |
| **Title** | Real MATLAB backend for vibration adapter |
| **Status** | proposed |
| **Author** | antal10 |
| **Date** | 2026-03-25 |

**Scope**
- Add a MATLAB backend to `src/adapters/matlab_vibration/adapter.py` that invokes MATLAB via the file-in/file-out contract (DEC-013).
- Backend selection is determined by a parameter; `numpy_fallback` remains the default.
- All output artifacts record `backend: matlab` when the MATLAB path executes.
- Add one integration test gated on MATLAB availability (skipped when MATLAB is not installed).

**Out of scope**
- MATLAB Engine API for Python (direct in-process calls).
- Changes to the normalization layer (`normalize.py`).
- Changes to the adapter contract or ontology.
- CI configuration for MATLAB runners.

**Dependencies**
- DEC-013 (file-in/file-out contract)
- DEC-016 (contract scaffold with backend field)
- `src/adapters/matlab_vibration/adapter.py` (exists on main)

**Files touched**
- `src/adapters/matlab_vibration/adapter.py` (modified)
- `tests/test_matlab_vibration_adapter.py` (modified)

**Acceptance criteria**
- [ ] MATLAB backend produces `features.json`, `raw_output.mat`, `spectrum.png`, `run_log.txt` matching the contract in DEC-013.
- [ ] All output artifacts include `backend: matlab`.
- [ ] Existing `numpy_fallback` tests still pass unchanged.
- [ ] New MATLAB integration test passes when MATLAB is available and is skipped cleanly when it is not.
- [ ] L0/L1 validators pass on MATLAB-produced outputs.

**Decision records**
- none

**Notes**
- Local MATLAB environment requirements are to be confirmed during implementation.
