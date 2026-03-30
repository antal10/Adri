"""Run loop - bootstrap slice orchestrator.

Wires together the full ingest -> validate -> reason -> validate pipeline:

1. Register adapter (health check)
2. Create Artifact entity in ontology store
3. Invoke adapter (ingest CSV)
4. L0-validate adapter response
5. Merge adapter entities into ontology store
6. Assemble and evaluate optional signal constraints
7. L0-validate all entities + relationships
8. L1-validate entity provenance
9. Invoke reasoning stub
10. L0-validate recommendation
11. L1-validate recommendation consistency

Supports both vibration adapters documented for UC-02:
- ``python_vibration`` for direct CSV ingestion
- ``matlab_vibration`` for the file-in/file-out contract scaffold

Optional signal constraints are assembled by core context assembly,
bound to the produced ``Signal`` entity, and evaluated against the
maximum detected spectral peak frequency.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from adapters.matlab_vibration.adapter import (
    REGISTRATION as MATLAB_REGISTRATION,
    analyze_vibration_csv,
    health as matlab_health,
)
from adapters.matlab_vibration.normalize import normalize_into_store
from adapters.python_vibration.adapter import (
    REGISTRATION as PYTHON_REGISTRATION,
    health as python_health,
    ingest_vibration_csv,
)
from adri.context_assembly import add_constraint, bind_constraint
from adri.ontology_store import OntologyStore
from reasoning.constraint_evaluator import (
    ConstraintResult,
    evaluate_all_constraints,
    results_to_evidence,
    violations,
)
from reasoning.vibration_stub import generate_recommendation
from validators.l0_schema import (
    all_passed as l0_all_passed,
    validate_adapter_response,
    validate_all_entities,
    validate_all_relationships,
    validate_recommendation,
)
from validators.l1_consistency import (
    all_passed as l1_all_passed,
    validate_adapter_entity_compliance,
    validate_entity_provenance,
    validate_recommendation_consistency,
)


@dataclass(frozen=True)
class AdapterBinding:
    """Core-facing functions and metadata for one adapter."""

    registration: dict[str, Any]
    health_fn: Callable[[], dict[str, Any]]
    invoke_fn: Callable[[dict[str, Any]], dict[str, Any]]
    operation_id: str


ADAPTER_BINDINGS: dict[str, AdapterBinding] = {
    PYTHON_REGISTRATION["adapter_id"]: AdapterBinding(
        registration=PYTHON_REGISTRATION,
        health_fn=python_health,
        invoke_fn=ingest_vibration_csv,
        operation_id="ingest_vibration_csv",
    ),
    MATLAB_REGISTRATION["adapter_id"]: AdapterBinding(
        registration=MATLAB_REGISTRATION,
        health_fn=matlab_health,
        invoke_fn=analyze_vibration_csv,
        operation_id="analyze_vibration_csv",
    ),
}


@dataclass
class RunResult:
    """Outcome of a single run-loop execution."""

    ok: bool = False
    recommendation: dict[str, Any] | None = None
    validation_results: list[dict[str, Any]] = field(default_factory=list)
    constraint_results: list[ConstraintResult] = field(default_factory=list)
    error: str | None = None


def run(
    file_path: str,
    artifact_id: str = "artifact-001",
    invocation_id: str = "inv-001",
    adapter_id: str = "python_vibration",
    run_dir: str | None = None,
    signal_constraints: list[dict[str, Any]] | None = None,
) -> RunResult:
    """Execute the full bootstrap loop for a vibration CSV.

    Parameters
    ----------
    file_path : str
        Path to a vibration CSV (columns: time_s, accel_m_s2).
    artifact_id : str
        ID to assign to the source artifact entity.
    invocation_id : str
        ID for the adapter invocation.
    adapter_id : str
        Which registered vibration adapter to use. Supported values are
        ``python_vibration`` and ``matlab_vibration``.
    run_dir : str | None
        Required when ``adapter_id == "matlab_vibration"`` because that
        adapter persists flat run artifacts to a per-run directory.
    signal_constraints : list[dict[str, Any]] | None
        Optional list of Constraint definitions in the ``add_constraint``
        shape. During the bootstrap slice, they are bound to the produced
        Signal and evaluated against the maximum detected peak frequency.

    Returns
    -------
    RunResult
        Contains recommendation, validation results, constraint results,
        and overall pipeline status.
    """
    result = RunResult()
    all_checks: list[dict[str, Any]] = []
    adapter = ADAPTER_BINDINGS.get(adapter_id)

    if adapter is None:
        result.error = (
            f"Unsupported adapter '{adapter_id}'. "
            f"Expected one of {sorted(ADAPTER_BINDINGS)}."
        )
        return result

    health_result = adapter.health_fn()
    if health_result["status"] == "unavailable":
        result.error = (
            f"Adapter health check failed: {health_result.get('message', '')}"
        )
        return result
    if health_result["status"] not in {"healthy", "degraded"}:
        result.error = (
            f"Adapter health returned unknown status "
            f"'{health_result['status']}'."
        )
        return result

    store = OntologyStore()
    now = datetime.now(timezone.utc).isoformat()
    store.add_entity({
        "id": artifact_id,
        "type": "Artifact",
        "name": os.path.basename(file_path),
        "source_adapter": "core",
        "source_artifact": artifact_id,
        "created_at": now,
    })

    try:
        request = _build_request(
            adapter, artifact_id, invocation_id, file_path, run_dir
        )
    except ValueError as exc:
        result.error = str(exc)
        return result
    response = adapter.invoke_fn(request)

    resp_checks = validate_adapter_response(response)
    all_checks.extend(resp_checks)
    if not l0_all_passed(resp_checks):
        result.validation_results = all_checks
        result.error = "Adapter response failed L0 validation."
        return result

    if response["status"] != "success":
        err = response.get("error", {})
        result.validation_results = all_checks
        result.error = f"Adapter error: {err.get('message', 'unknown')}"
        return result

    signal_id = _merge_response_into_store(store, adapter_id, response, artifact_id)
    if not signal_id:
        result.validation_results = all_checks
        result.error = "Adapter produced no Signal entity."
        return result

    capability = adapter.registration["capabilities"][0]
    compliance_checks = validate_adapter_entity_compliance(response, capability)
    all_checks.extend(compliance_checks)
    if not l1_all_passed(compliance_checks):
        result.validation_results = all_checks
        result.error = "Adapter entity type compliance failed L1 validation."
        return result

    normalized_outputs = _reasoning_adapter_outputs(adapter_id, response["outputs"])
    constraint_results = _apply_signal_constraints(
        store,
        artifact_id,
        signal_id,
        normalized_outputs,
        signal_constraints or [],
    )
    result.constraint_results = constraint_results

    entity_checks = validate_all_entities(store)
    all_checks.extend(entity_checks)
    rel_checks = validate_all_relationships(store)
    all_checks.extend(rel_checks)
    if not l0_all_passed(entity_checks) or not l0_all_passed(rel_checks):
        result.validation_results = all_checks
        result.error = "Ontology store failed L0 validation."
        return result

    prov_checks = validate_entity_provenance(store)
    all_checks.extend(prov_checks)
    if not l1_all_passed(prov_checks):
        result.validation_results = all_checks
        result.error = "Entity provenance failed L1 validation."
        return result

    rec = generate_recommendation(store, normalized_outputs, artifact_id, signal_id)
    _apply_constraint_results(rec, constraint_results)

    rec_l0 = validate_recommendation(rec)
    all_checks.extend(rec_l0)
    if not l0_all_passed(rec_l0):
        result.validation_results = all_checks
        result.error = "Recommendation failed L0 validation."
        return result

    rec_l1 = validate_recommendation_consistency(rec, store)
    all_checks.extend(rec_l1)
    if not l1_all_passed(rec_l1):
        result.validation_results = all_checks
        result.error = "Recommendation failed L1 validation."
        return result

    result.ok = True
    result.recommendation = rec
    result.validation_results = all_checks
    return result


def _build_request(
    adapter: AdapterBinding,
    artifact_id: str,
    invocation_id: str,
    file_path: str,
    run_dir: str | None,
) -> dict[str, Any]:
    """Build a request object for the selected adapter."""
    inputs: dict[str, Any] = {
        "artifact_id": artifact_id,
        "file_path": file_path,
    }
    if adapter.registration["adapter_id"] == "matlab_vibration":
        if not run_dir:
            raise ValueError(
                "Adapter 'matlab_vibration' requires a run_dir for persisted outputs."
            )
        inputs["run_dir"] = run_dir

    return {
        "invocation_id": invocation_id,
        "adapter_id": adapter.registration["adapter_id"],
        "operation_id": adapter.operation_id,
        "inputs": inputs,
    }


def _merge_response_into_store(
    store: OntologyStore,
    adapter_id: str,
    response: dict[str, Any],
    artifact_id: str,
) -> str | None:
    """Merge adapter-created entities into the ontology store."""
    if adapter_id == "matlab_vibration":
        summary = normalize_into_store(store, response, artifact_id)
        return summary.get("signal_id")

    signal_id: str | None = None
    for entity in response.get("entities_created", []):
        store.add_entity(entity)
        if entity.get("type") == "Signal":
            signal_id = entity["id"]
            store.add_relationship(signal_id, "derived_from", artifact_id)
    return signal_id


def _reasoning_adapter_outputs(
    adapter_id: str, outputs: dict[str, Any]
) -> dict[str, Any]:
    """Normalize adapter-specific outputs into the reasoning stub shape."""
    if adapter_id != "matlab_vibration":
        return outputs

    features = outputs.get("features", {})
    sample_rate = float(features.get("sample_rate_hz", 0.0))
    duration_s = float(features.get("duration_s", 0.0))
    num_samples = int(round(sample_rate * duration_s)) if sample_rate else 0
    return {
        "sample_rate": sample_rate,
        "duration_s": duration_s,
        "num_samples": num_samples,
        "peaks_hz": features.get("dominant_peak_frequencies_hz", []),
        "peaks_amplitude": features.get("dominant_peak_magnitudes", []),
    }


def _apply_signal_constraints(
    store: OntologyStore,
    artifact_id: str,
    signal_id: str,
    adapter_outputs: dict[str, Any],
    signal_constraints: list[dict[str, Any]],
) -> list[ConstraintResult]:
    """Add and evaluate optional constraints for the produced Signal."""
    if not signal_constraints:
        return []

    peaks_hz = adapter_outputs.get("peaks_hz", [])
    if not peaks_hz:
        return []

    for spec in signal_constraints:
        add_constraint(
            store,
            constraint_id=spec["constraint_id"],
            name=spec["name"],
            bound_type=spec["bound_type"],
            bound_value=spec["bound_value"],
            unit=spec["unit"],
            tolerance=spec.get("tolerance"),
            source_artifact=artifact_id,
        )
        bind_constraint(store, signal_id, spec["constraint_id"])

    measurements = {signal_id: max(float(freq) for freq in peaks_hz)}
    return evaluate_all_constraints(store, measurements)


def _apply_constraint_results(
    recommendation: dict[str, Any],
    constraint_results: list[ConstraintResult],
) -> None:
    """Fold evaluated constraint results into recommendation evidence."""
    if not constraint_results:
        return

    recommendation["evidence"].extend(results_to_evidence(constraint_results))
    trace = recommendation.setdefault("trace", [])
    for result in constraint_results:
        if result.constraint_id not in trace:
            trace.append(result.constraint_id)

    if violations(constraint_results) and recommendation.get("verdict") != "insufficient_data":
        recommendation["verdict"] = "not_recommended"
