# Adapter Contract

The adapter contract is the formal interface between Adri's core and any
external tool. Every adapter must satisfy this contract. The contract is
tool-agnostic — it defines *what* an adapter must do, not *how*.

## Terminology

| Term | Definition |
|------|------------|
| **Adapter** | A module that translates between Adri's ontology and one external tool. |
| **Operation** | A single, well-defined action an adapter can perform. |
| **Capability** | A declared operation an adapter supports, discoverable at registration. |
| **Invocation** | One call from Adri's core to an adapter operation. |

---

## Contract requirements

### 1. Registration

An adapter must declare itself to Adri's core with a registration manifest:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `adapter_id` | string | yes | Unique identifier (e.g., `matlab`, `solidworks`). |
| `adapter_version` | string | yes | Semantic version of the adapter. |
| `tool_name` | string | yes | Human-readable name of the external tool. |
| `tool_version` | string | no | Version of the external tool, if detectable. |
| `capabilities` | list of Capability | yes (min 1) | Operations this adapter can perform. |

### 2. Capability declaration

Each capability describes one operation the adapter supports.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `operation_id` | string | yes | Unique within this adapter (e.g., `ingest_assembly`, `run_modal_analysis`). |
| `description` | string | yes | What this operation does, in one sentence. |
| `input_schema` | object | yes | JSON-Schema-style description of required and optional inputs. |
| `output_schema` | object | yes | JSON-Schema-style description of the output. |
| `artifact_types` | list of string | no | Ontology `Artifact` types this operation can consume (e.g., `SLDASM`, `mat`, `wav`). |
| `entity_types_produced` | list of string | yes | Ontology entity types this operation creates (e.g., `Component`, `Signal`). Empty list if the operation produces no entities. |
| `idempotent` | boolean | yes | Whether calling this operation twice with the same input produces the same output. |
| `side_effects` | list of string | no | Any effects outside Adri (e.g., "writes file to disk," "sends data to instrument"). |

### 3. Invocation protocol

Every invocation follows a request-response pattern.

**Request (core → adapter):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `invocation_id` | string | yes | Unique ID for this call (for tracing). |
| `operation_id` | string | yes | Which capability to invoke. |
| `inputs` | object | yes | Conforms to the operation's `input_schema`. |
| `timeout_ms` | int | no | Maximum time the adapter may take. Default: adapter-defined. |

**Response (adapter → core):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `invocation_id` | string | yes | Echoed from request. |
| `status` | enum: `success`, `error`, `partial` | yes | Outcome. |
| `outputs` | object | conditional | Conforms to the operation's `output_schema`. Required when status is `success` or `partial`. |
| `entities_created` | list of entity stubs | no | Ontology entities the adapter produced, with `source_adapter` and `source_artifact` set per ontology rules. |
| `error` | Error | conditional | Required when status is `error` or `partial`. |
| `duration_ms` | int | no | Actual execution time. |

### 4. Error handling

**Error object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | string | yes | Machine-readable error code. |
| `message` | string | yes | Human-readable explanation. |
| `recoverable` | boolean | yes | Whether retrying might succeed. |
| `detail` | object | no | Adapter-specific diagnostic data. |

**Required error codes** (every adapter must handle these):

| Code | Meaning |
|------|---------|
| `TOOL_UNAVAILABLE` | The external tool cannot be reached or is not installed. |
| `INVALID_INPUT` | Inputs do not conform to the operation's `input_schema`. |
| `INVALID_ARTIFACT` | The artifact cannot be parsed or is corrupted. |
| `TIMEOUT` | The operation exceeded the allowed time. |
| `INTERNAL` | An unexpected error within the adapter. |

Adapters may define additional error codes. Custom codes must be prefixed with
the adapter's `adapter_id` (e.g., `matlab.LICENSE_EXPIRED`).

### 5. Ontology compliance

- Every entity an adapter creates must have `source_adapter` set to the
  adapter's `adapter_id`.
- Every entity an adapter creates must have `source_artifact` set to the ID of
  the ingested artifact.
- Adapters must not create cross-domain relationships. Those are created during
  context assembly by Adri's core (per ontology extensibility rule #4).
- Adapters must only produce entity types listed in their capability's
  `entity_types_produced`.

### 6. Artifact lifecycle

Adri's core is responsible for creating the `Artifact` entity in the ontology
before invoking an adapter. The core sets:

- `id`: a unique identifier for this artifact.
- `name`: the artifact's filename or user-provided label.
- `source_adapter`: `"core"`.
- `source_artifact`: the artifact's own `id` (self-referential).
- `created_at`: the timestamp of ingestion.

The adapter receives the artifact's `id` in the invocation `inputs`. All
entities the adapter creates set their `source_artifact` to this ID.

### 7. Composability

Operations are the unit of composition. Adri's core composes workflows by
chaining adapter operations. An adapter must not assume it will be called in
any particular sequence. Each operation must be independently invocable.

### 8. Health check

Every adapter must implement a `health` operation (not listed in capabilities)
that returns:

| Field | Type | Description |
|-------|------|-------------|
| `adapter_id` | string | The adapter's identifier. |
| `status` | enum: `healthy`, `degraded`, `unavailable` | Current status. |
| `tool_reachable` | boolean | Whether the external tool can be contacted. |
| `message` | string | Human-readable status detail. |

---

## What the contract does NOT specify

- **Transport mechanism.** The contract defines message shapes, not whether
  they travel over HTTP, gRPC, function calls, or pipes. That is an
  implementation decision.
- **Language.** Adapters may be written in any language.
- **Authentication.** How an adapter authenticates with its tool is
  adapter-internal. The contract does not expose credentials.
- **Concurrency model.** Whether operations run sync or async is
  implementation-level. The contract defines one request, one response.
