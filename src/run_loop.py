"""Run loop — bootstrap slice orchestrator.

Wires together the full ingest → validate → reason → validate pipeline:

1.  Register adapter (health check)
2.  Create Artifact entity in ontology store
3.  Invoke matlab_vibration adapter (file-in/file-out contract, DEC-013)
4.  L0-validate adapter response
5.  Normalize adapter entities into ontology store
6.  L0-validate all entities + relationships
7.  L1-validate entity provenance
8.  Invoke reasoning stub
9.  L0-validate recommendation
10. L1-validate recommendation consistency

Signal analysis (FFT, peak detection) executes inside the matlab_vibration
adapter. The numpy_fallback backend is active until a real MATLAB backend
is wired (DEC-016). Python is the data pipeline; analysis belongs to MATLAB.

Returns a RunResult with the recommendation, all validation results,
and pass/fail status.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from typing import Any

from adri.ontology_store import OntologyStore
from adapters.matlab_vibration.adapter import (
    REGISTRATION,
    analyze_vibration_csv,
    health,
)
from adapters.matlab_vibration.normalize import normalize_into_store
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


@dataclass
class RunResult:
    """Outcome of a single run-loop execution."""

    ok: bool = False
    recommendation: dict[str, Any] | None = None
    validation_results: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


def run(
    file_path: str,
    artifact_id: str = "artifact-001",
    invocation_id: str = "inv-001",
    run_dir: str | None = None,
) -> RunResult:
    """Execute the full bootstrap loop for a vibration CSV via matlab_vibration.

    Parameters
    ----------
    file_path : str
        Path to a vibration CSV (columns: time_s, accel_m_s2).
    artifact_id : str
        ID to assign to the source artifact entity.
    invocation_id : str
        ID for the adapter invocation.
    run_dir : str or None
        Directory for adapter run artifacts (features.json, raw_output.mat,
        spectrum.png, run_log.txt). Created as a tempdir if None (DEC-014).

    Returns
    -------
    RunResult
        Contains recommendation, all validation check results, and ok flag.
    """
    result = RunResult()
    all_checks: list[dict[str, Any]] = []

    # --- Step 1: Health check ---
    # "degraded" is accepted: MATLAB not on PATH, numpy_fallback active (DEC-016).
    # Only "unavailable" is a blocking failure.
    h = health()
    if h["status"] not in ("healthy", "degraded"):
        result.error = f"Adapter health check failed: {h.get('message', '')}"
        return result

    # --- Step 2: Create artifact entity ---
    store = OntologyStore()
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    store.add_entity({
        "id": artifact_id,
        "type": "Artifact",
        "name": file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path,
        "source_adapter": "core",
        "source_artifact": artifact_id,
        "created_at": now,
    })

    # --- Step 3: Invoke adapter ---
    _run_dir = run_dir or tempfile.mkdtemp(prefix="adri_run_")
    request = {
        "invocation_id": invocation_id,
        "adapter_id": REGISTRATION["adapter_id"],
        "operation_id": "analyze_vibration_csv",
        "inputs": {
            "artifact_id": artifact_id,
            "file_path": file_path,
            "run_dir": _run_dir,
        },
    }
    response = analyze_vibration_csv(request)

    # --- Step 4: L0-validate adapter response ---
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

    # --- Step 5: Normalize entities into ontology store ---
    summary = normalize_into_store(store, response, artifact_id)
    signal_id = summary["signal_id"]

    if signal_id is None:
        result.validation_results = all_checks
        result.error = "Adapter produced no Signal entity."
        return result

    # --- Step 5b: L1-validate adapter entity compliance ---
    capability = REGISTRATION["capabilities"][0]
    compliance_checks = validate_adapter_entity_compliance(response, capability)
    all_checks.extend(compliance_checks)
    if not l1_all_passed(compliance_checks):
        result.validation_results = all_checks
        result.error = "Adapter entity type compliance failed L1 validation."
        return result

    # --- Step 6: L0-validate all entities + relationships ---
    entity_checks = validate_all_entities(store)
    all_checks.extend(entity_checks)
    rel_checks = validate_all_relationships(store)
    all_checks.extend(rel_checks)

    if not l0_all_passed(entity_checks) or not l0_all_passed(rel_checks):
        result.validation_results = all_checks
        result.error = "Ontology store failed L0 validation."
        return result

    # --- Step 7: L1-validate entity provenance ---
    prov_checks = validate_entity_provenance(store)
    all_checks.extend(prov_checks)
    if not l1_all_passed(prov_checks):
        result.validation_results = all_checks
        result.error = "Entity provenance failed L1 validation."
        return result

    # --- Step 8: Invoke reasoning stub ---
    rec = generate_recommendation(
        store, response["outputs"], artifact_id, signal_id
    )

    # --- Step 9: L0-validate recommendation ---
    rec_l0 = validate_recommendation(rec)
    all_checks.extend(rec_l0)
    if not l0_all_passed(rec_l0):
        result.validation_results = all_checks
        result.error = "Recommendation failed L0 validation."
        return result

    # --- Step 10: L1-validate recommendation consistency ---
    rec_l1 = validate_recommendation_consistency(rec, store)
    all_checks.extend(rec_l1)
    if not l1_all_passed(rec_l1):
        result.validation_results = all_checks
        result.error = "Recommendation failed L1 validation."
        return result

    # --- All passed ---
    result.ok = True
    result.recommendation = rec
    result.validation_results = all_checks
    return result
