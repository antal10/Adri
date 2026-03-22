"""L0 validator — structural schema conformance.

Checks entity types, property completeness/types, relationship type
validity, adapter response protocol, and recommendation schema. Run on
every output, every time (evaluation_strategy.md §L0).
"""

from __future__ import annotations

from typing import Any

from adri.ontology_store import (
    ENTITY_TYPES,
    RELATIONSHIP_TYPES,
    UNIVERSAL_PROPERTIES,
    OntologyStore,
)

# --- Result type ---

_Pass = dict[str, Any]  # {"check": str, "passed": True}
_Fail = dict[str, Any]  # {"check": str, "passed": False, "reason": str}


def _pass(check: str) -> _Pass:
    return {"check": check, "passed": True}


def _fail(check: str, reason: str) -> _Fail:
    return {"check": check, "passed": False, "reason": reason}


# --- Valid enum values per ontology.md / recommendation_schema.md ---

SIGNAL_DOMAINS = {"time", "frequency", "spatial"}
CONSTRAINT_BOUND_TYPES = {"upper", "lower", "equality", "range"}
TF_REPRESENTATIONS = {"zpk", "tf", "ss", "frd"}
TF_DOMAINS = {"continuous", "discrete"}

VERDICT_VALUES = {"recommended", "acceptable", "not_recommended", "insufficient_data"}
EVIDENCE_TYPES = {"data", "simulation", "derivation", "datasheet", "reference"}
IMPACT_VALUES = {"low", "medium", "high", "critical"}
LIKELIHOOD_VALUES = {"low", "medium", "high"}
SEVERITY_VALUES = {"low", "medium", "high", "critical"}
CONFIDENCE_LEVELS = {"high", "moderate", "low", "speculative"}

ADAPTER_STATUS_VALUES = {"success", "error", "partial"}
ADAPTER_ERROR_CODES = {
    "TOOL_UNAVAILABLE", "INVALID_INPUT", "INVALID_ARTIFACT", "TIMEOUT", "INTERNAL",
}


# =========================================================================
# Entity validation
# =========================================================================


def validate_entity(entity: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate a single entity dict. Returns list of check results."""
    results: list[dict[str, Any]] = []

    # Entity type valid
    etype = entity.get("type")
    if etype in ENTITY_TYPES:
        results.append(_pass("entity_type_valid"))
    else:
        results.append(_fail("entity_type_valid", f"Unknown type '{etype}'."))

    # Universal properties complete
    for prop in UNIVERSAL_PROPERTIES:
        val = entity.get(prop)
        if val is not None and val != "":
            results.append(_pass(f"universal_property_{prop}"))
        else:
            results.append(_fail(
                f"universal_property_{prop}",
                f"Missing or empty universal property '{prop}'.",
            ))

    # Type-specific property checks
    if etype == "Signal":
        results.extend(_validate_signal_properties(entity))
    elif etype == "Constraint":
        results.extend(_validate_constraint_properties(entity))
    elif etype == "TransferFunction":
        results.extend(_validate_tf_properties(entity))

    return results


def _validate_signal_properties(entity: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    domain = entity.get("domain")
    if domain is not None:
        if domain in SIGNAL_DOMAINS:
            results.append(_pass("signal_domain_enum"))
        else:
            results.append(_fail(
                "signal_domain_enum",
                f"Invalid signal domain '{domain}'. Must be one of {sorted(SIGNAL_DOMAINS)}.",
            ))

    sr = entity.get("sample_rate")
    if sr is not None and not isinstance(sr, (int, float)):
        results.append(_fail("signal_sample_rate_type", f"sample_rate must be numeric, got {type(sr).__name__}."))
    elif sr is not None:
        results.append(_pass("signal_sample_rate_type"))

    return results


def _validate_constraint_properties(entity: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    bt = entity.get("bound_type")
    if bt is not None:
        if bt in CONSTRAINT_BOUND_TYPES:
            results.append(_pass("constraint_bound_type_enum"))
        else:
            results.append(_fail(
                "constraint_bound_type_enum",
                f"Invalid bound_type '{bt}'.",
            ))
    return results


def _validate_tf_properties(entity: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    rep = entity.get("representation")
    if rep is not None:
        if rep in TF_REPRESENTATIONS:
            results.append(_pass("tf_representation_enum"))
        else:
            results.append(_fail("tf_representation_enum", f"Invalid representation '{rep}'."))

    dom = entity.get("domain")
    if dom is not None:
        if dom in TF_DOMAINS:
            results.append(_pass("tf_domain_enum"))
        else:
            results.append(_fail("tf_domain_enum", f"Invalid TF domain '{dom}'."))
    return results


def validate_all_entities(store: OntologyStore) -> list[dict[str, Any]]:
    """Validate every entity in the store."""
    results: list[dict[str, Any]] = []
    for etype in sorted(ENTITY_TYPES):
        for entity in store.list_by_type(etype):
            results.extend(validate_entity(entity))
    return results


# =========================================================================
# Relationship validation
# =========================================================================

# Allowed (source_type, target_type) pairs per ontology.md relationship table
_RELATIONSHIP_CONSTRAINTS: dict[str, set[tuple[str, str]]] = {
    "mounts_to": {
        ("Component", "Component"), ("Component", "Interface"),
        ("Sensor", "Component"), ("Sensor", "Interface"),
        ("Actuator", "Component"), ("Actuator", "Interface"),
    },
    "contains": {
        ("Subsystem", "Component"), ("Subsystem", "Sensor"),
        ("Subsystem", "Actuator"), ("Subsystem", "Interface"),
        ("Component", "Component"), ("Component", "Sensor"),
        ("Component", "Actuator"), ("Component", "Interface"),
    },
    "senses": {("Sensor", "Signal")},
    "drives": {("Actuator", "Component")},
    "feeds": {
        ("Signal", "SignalChain"), ("Signal", "DAQChannel"),
        ("Signal", "TransferFunction"),
        ("DAQChannel", "SignalChain"), ("DAQChannel", "DAQChannel"),
        ("DAQChannel", "TransferFunction"),
    },
    "constrains": {
        ("Interface", "Component"), ("Interface", "Sensor"), ("Interface", "Signal"),
        ("Material", "Component"), ("Material", "Sensor"), ("Material", "Signal"),
    },
    "bounded_by": {
        ("Component", "Constraint"), ("Sensor", "Constraint"),
        ("Subsystem", "Constraint"), ("Signal", "Constraint"),
    },
    "controls": {
        ("TransferFunction", "Signal"), ("TransferFunction", "Component"),
        ("Actuator", "Signal"), ("Actuator", "Component"),
    },
    "implements": {("TransferFunction", "SignalChain")},
    "part_of": {
        ("Component", "Subsystem"), ("Signal", "SignalChain"),
        ("DAQChannel", "SignalChain"),
    },
    "derived_from": {
        ("Signal", "Signal"), ("Signal", "Artifact"),
        ("TransferFunction", "Signal"), ("TransferFunction", "Artifact"),
    },
    "references": set(),  # source: Artifact, target: any entity — handled specially
    "located_in": {
        ("Component", "SpatialRegion"), ("Sensor", "SpatialRegion"),
        ("Actuator", "SpatialRegion"),
    },
    "made_of": {("Component", "Material")},
}


def validate_relationship(
    triple: tuple[str, str, str], store: OntologyStore
) -> list[dict[str, Any]]:
    """Validate a single relationship triple against ontology rules."""
    results: list[dict[str, Any]] = []
    source_id, rel_type, target_id = triple

    # Relationship type valid
    if rel_type not in RELATIONSHIP_TYPES:
        results.append(_fail(
            "relationship_type_valid",
            f"Unknown relationship type '{rel_type}'.",
        ))
        return results
    results.append(_pass("relationship_type_valid"))

    # Source/target types valid
    source = store.get(source_id)
    target = store.get(target_id)
    if source is None:
        results.append(_fail("relationship_source_exists", f"Source '{source_id}' not in store."))
        return results
    if target is None:
        results.append(_fail("relationship_target_exists", f"Target '{target_id}' not in store."))
        return results

    source_type = source.get("type", "")
    target_type = target.get("type", "")

    # Special case: 'references' allows Artifact -> any
    if rel_type == "references":
        if source_type == "Artifact":
            results.append(_pass("relationship_source_target_types"))
        else:
            results.append(_fail(
                "relationship_source_target_types",
                f"'references' requires source type Artifact, got '{source_type}'.",
            ))
    else:
        allowed = _RELATIONSHIP_CONSTRAINTS.get(rel_type, set())
        pair = (source_type, target_type)
        if pair in allowed:
            results.append(_pass("relationship_source_target_types"))
        else:
            results.append(_fail(
                "relationship_source_target_types",
                f"({source_type}, {rel_type}, {target_type}) is not allowed by ontology.md.",
            ))

    return results


def validate_all_relationships(store: OntologyStore) -> list[dict[str, Any]]:
    """Validate every relationship in the store against ontology rules."""
    results: list[dict[str, Any]] = []
    # Gather all triples by iterating over all entities as potential sources
    seen: set[tuple[str, str, str]] = set()
    for etype in sorted(ENTITY_TYPES):
        for entity in store.list_by_type(etype):
            for triple in store.relationships_from(entity["id"]):
                if triple not in seen:
                    seen.add(triple)
                    results.extend(validate_relationship(triple, store))
    return results


# =========================================================================
# Adapter response validation
# =========================================================================


def validate_adapter_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate adapter response conforms to invocation protocol (§3)."""
    results: list[dict[str, Any]] = []

    # Required fields
    for field in ("invocation_id", "status"):
        if field in response and response[field]:
            results.append(_pass(f"response_{field}_present"))
        else:
            results.append(_fail(f"response_{field}_present", f"Missing '{field}'."))

    # Status enum
    status = response.get("status")
    if status in ADAPTER_STATUS_VALUES:
        results.append(_pass("response_status_enum"))
    else:
        results.append(_fail("response_status_enum", f"Invalid status '{status}'."))

    # Status consistency
    if status == "success":
        if "outputs" in response:
            results.append(_pass("response_status_consistency"))
        else:
            results.append(_fail(
                "response_status_consistency",
                "Status is 'success' but 'outputs' is missing.",
            ))
    elif status in ("error", "partial"):
        if "error" in response:
            results.append(_pass("response_status_consistency"))
        else:
            results.append(_fail(
                "response_status_consistency",
                f"Status is '{status}' but 'error' is missing.",
            ))

    # Error object structure (if present)
    if "error" in response:
        err = response["error"]
        for field in ("code", "message", "recoverable"):
            if field in err:
                results.append(_pass(f"error_{field}_present"))
            else:
                results.append(_fail(f"error_{field}_present", f"Error missing '{field}'."))

    # Entity compliance: each entity_created must have valid type
    for entity in response.get("entities_created", []):
        etype = entity.get("type")
        if etype in ENTITY_TYPES:
            results.append(_pass(f"entity_created_type_{entity.get('id', '?')}"))
        else:
            results.append(_fail(
                f"entity_created_type_{entity.get('id', '?')}",
                f"Entity type '{etype}' not in ontology.",
            ))

    return results


# =========================================================================
# Recommendation validation
# =========================================================================

_REC_REQUIRED_FIELDS = ("id", "title", "goal", "verdict", "evidence",
                        "assumptions", "risks", "confidence", "trace")


def validate_recommendation(rec: dict[str, Any]) -> list[dict[str, Any]]:
    """L0 schema validation for a recommendation dict."""
    results: list[dict[str, Any]] = []

    # Required fields present
    for field in _REC_REQUIRED_FIELDS:
        if field in rec:
            results.append(_pass(f"rec_{field}_present"))
        else:
            results.append(_fail(f"rec_{field}_present", f"Missing required field '{field}'."))

    # Verdict enum
    verdict = rec.get("verdict")
    if verdict in VERDICT_VALUES:
        results.append(_pass("rec_verdict_enum"))
    else:
        results.append(_fail("rec_verdict_enum", f"Invalid verdict '{verdict}'."))

    # Evidence: at least one, each has required fields
    evidence = rec.get("evidence", [])
    if isinstance(evidence, list) and len(evidence) >= 1:
        results.append(_pass("rec_evidence_min_one"))
    else:
        results.append(_fail("rec_evidence_min_one", "Must have at least 1 evidence item."))

    for i, ev in enumerate(evidence if isinstance(evidence, list) else []):
        for field in ("type", "source", "summary"):
            if field in ev and ev[field]:
                results.append(_pass(f"evidence[{i}]_{field}"))
            else:
                results.append(_fail(f"evidence[{i}]_{field}", f"Evidence[{i}] missing '{field}'."))
        ev_type = ev.get("type")
        if ev_type in EVIDENCE_TYPES:
            results.append(_pass(f"evidence[{i}]_type_enum"))
        else:
            results.append(_fail(f"evidence[{i}]_type_enum", f"Invalid evidence type '{ev_type}'."))

    # Assumptions: list, each has required fields
    assumptions = rec.get("assumptions", [])
    if isinstance(assumptions, list):
        results.append(_pass("rec_assumptions_is_list"))
        if len(assumptions) == 0:
            # no_assumptions_rationale required
            if rec.get("no_assumptions_rationale"):
                results.append(_pass("rec_no_assumptions_rationale"))
            else:
                results.append(_fail(
                    "rec_no_assumptions_rationale",
                    "Assumptions list is empty but no_assumptions_rationale is missing.",
                ))
        for i, asn in enumerate(assumptions):
            for field in ("id", "statement", "basis", "impact_if_wrong"):
                if field in asn and asn[field]:
                    results.append(_pass(f"assumption[{i}]_{field}"))
                else:
                    results.append(_fail(f"assumption[{i}]_{field}", f"Assumption[{i}] missing '{field}'."))
            iiw = asn.get("impact_if_wrong")
            if iiw in IMPACT_VALUES:
                results.append(_pass(f"assumption[{i}]_impact_enum"))
            else:
                results.append(_fail(f"assumption[{i}]_impact_enum", f"Invalid impact '{iiw}'."))
    else:
        results.append(_fail("rec_assumptions_is_list", "assumptions must be a list."))

    # Risks: list, each has required fields
    risks = rec.get("risks", [])
    if isinstance(risks, list):
        results.append(_pass("rec_risks_is_list"))
        for i, risk in enumerate(risks):
            for field in ("id", "description", "likelihood", "severity"):
                if field in risk and risk[field]:
                    results.append(_pass(f"risk[{i}]_{field}"))
                else:
                    results.append(_fail(f"risk[{i}]_{field}", f"Risk[{i}] missing '{field}'."))
            if risk.get("likelihood") in LIKELIHOOD_VALUES:
                results.append(_pass(f"risk[{i}]_likelihood_enum"))
            else:
                results.append(_fail(f"risk[{i}]_likelihood_enum", f"Invalid likelihood."))
            if risk.get("severity") in SEVERITY_VALUES:
                results.append(_pass(f"risk[{i}]_severity_enum"))
            else:
                results.append(_fail(f"risk[{i}]_severity_enum", f"Invalid severity."))
    else:
        results.append(_fail("rec_risks_is_list", "risks must be a list."))

    # Confidence: required sub-fields
    confidence = rec.get("confidence", {})
    if isinstance(confidence, dict):
        for field in ("level", "rationale", "limiting_factor"):
            if field in confidence and confidence[field]:
                results.append(_pass(f"confidence_{field}"))
            else:
                results.append(_fail(f"confidence_{field}", f"Confidence missing '{field}'."))
        if confidence.get("level") in CONFIDENCE_LEVELS:
            results.append(_pass("confidence_level_enum"))
        else:
            results.append(_fail("confidence_level_enum", f"Invalid confidence level."))
    else:
        results.append(_fail("confidence_is_dict", "confidence must be a dict."))

    # Trace: list of strings
    trace = rec.get("trace", [])
    if isinstance(trace, list) and len(trace) >= 1:
        results.append(_pass("rec_trace_is_nonempty_list"))
    else:
        results.append(_fail("rec_trace_is_nonempty_list", "trace must be a non-empty list."))

    return results


# =========================================================================
# Convenience: all-passed check
# =========================================================================


def all_passed(results: list[dict[str, Any]]) -> bool:
    """Return True if every check in results passed."""
    return all(r["passed"] for r in results)


def failures(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only the failed checks."""
    return [r for r in results if not r["passed"]]
