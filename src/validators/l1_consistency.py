"""L1 validator — cross-reference consistency.

Checks trace ID existence, source_artifact provenance, evidence source
references, verdict-evidence consistency, and entity type compliance
against adapter capability declarations. Run on every output, every
time (evaluation_strategy.md §L1).
"""

from __future__ import annotations

from typing import Any

from adri.ontology_store import OntologyStore


# --- Result helpers (same shape as l0_schema) ---


def _pass(check: str) -> dict[str, Any]:
    return {"check": check, "passed": True}


def _fail(check: str, reason: str) -> dict[str, Any]:
    return {"check": check, "passed": False, "reason": reason}


# =========================================================================
# Recommendation consistency
# =========================================================================


def validate_recommendation_consistency(
    rec: dict[str, Any], store: OntologyStore
) -> list[dict[str, Any]]:
    """L1 consistency checks for a recommendation against the ontology store."""
    results: list[dict[str, Any]] = []

    # Trace validity: every ID in trace exists in store
    trace = rec.get("trace", [])
    for entity_id in trace:
        if store.exists(entity_id):
            results.append(_pass(f"trace_exists_{entity_id}"))
        else:
            results.append(_fail(
                f"trace_exists_{entity_id}",
                f"Trace ID '{entity_id}' does not exist in ontology store.",
            ))

    # Evidence grounding: every evidence source references a known artifact
    # or adapter ID
    known_artifact_ids = {e["id"] for e in store.list_by_type("Artifact")}
    known_adapter_ids: set[str] = set()
    for etype in ("Signal", "Component", "Sensor"):  # extend as needed
        for e in store.list_by_type(etype):
            sa = e.get("source_adapter")
            if sa:
                known_adapter_ids.add(sa)
    # "core" is always a valid source adapter
    known_adapter_ids.add("core")

    evidence = rec.get("evidence", [])
    for i, ev in enumerate(evidence if isinstance(evidence, list) else []):
        source = ev.get("source", "")
        # Source must reference an artifact ID or an adapter ID
        if source in known_artifact_ids or source in known_adapter_ids:
            results.append(_pass(f"evidence[{i}]_source_grounded"))
        else:
            results.append(_fail(
                f"evidence[{i}]_source_grounded",
                f"Evidence[{i}] source '{source}' is not a known artifact or adapter.",
            ))

    # Verdict-evidence consistency
    verdict = rec.get("verdict")
    confidence = rec.get("confidence", {})
    conf_level = confidence.get("level") if isinstance(confidence, dict) else None

    if verdict == "recommended" and conf_level == "speculative":
        results.append(_fail(
            "verdict_confidence_consistency",
            "'recommended' verdict cannot be paired with 'speculative' confidence.",
        ))
    elif verdict == "insufficient_data":
        # Must have a limiting factor or assumption documenting the gap
        limiting = confidence.get("limiting_factor", "") if isinstance(confidence, dict) else ""
        if limiting:
            results.append(_pass("verdict_confidence_consistency"))
        else:
            results.append(_fail(
                "verdict_confidence_consistency",
                "'insufficient_data' verdict requires a confidence limiting_factor.",
            ))
    else:
        results.append(_pass("verdict_confidence_consistency"))

    return results


# =========================================================================
# Entity provenance consistency
# =========================================================================


def validate_entity_provenance(store: OntologyStore) -> list[dict[str, Any]]:
    """Check that every entity's source_artifact references an existing Artifact."""
    results: list[dict[str, Any]] = []

    # Collect all artifact IDs
    artifact_ids = {e["id"] for e in store.list_by_type("Artifact")}

    # Check every entity in the store
    from adri.ontology_store import ENTITY_TYPES
    for etype in sorted(ENTITY_TYPES):
        for entity in store.list_by_type(etype):
            source_artifact = entity.get("source_artifact", "")
            if source_artifact in artifact_ids:
                results.append(_pass(f"provenance_{entity['id']}"))
            else:
                results.append(_fail(
                    f"provenance_{entity['id']}",
                    f"source_artifact '{source_artifact}' is not a known Artifact.",
                ))

    return results


# =========================================================================
# Adapter entity type compliance
# =========================================================================


def validate_adapter_entity_compliance(
    response: dict[str, Any],
    capability: dict[str, Any],
) -> list[dict[str, Any]]:
    """Check that entities_created only contain types listed in entity_types_produced."""
    results: list[dict[str, Any]] = []
    allowed = set(capability.get("entity_types_produced", []))

    for entity in response.get("entities_created", []):
        etype = entity.get("type", "")
        eid = entity.get("id", "?")
        if etype in allowed:
            results.append(_pass(f"entity_type_compliance_{eid}"))
        else:
            results.append(_fail(
                f"entity_type_compliance_{eid}",
                f"Entity type '{etype}' not in capability's entity_types_produced {sorted(allowed)}.",
            ))

    return results


# =========================================================================
# Convenience
# =========================================================================


def all_passed(results: list[dict[str, Any]]) -> bool:
    """Return True if every check passed."""
    return all(r["passed"] for r in results)


def failures(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only failed checks."""
    return [r for r in results if not r["passed"]]
