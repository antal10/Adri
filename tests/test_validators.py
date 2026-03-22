"""Tests for L0 and L1 validators."""

from __future__ import annotations

import pytest

from adri.ontology_store import OntologyStore
from validators.l0_schema import (
    all_passed,
    failures,
    validate_adapter_response,
    validate_all_entities,
    validate_all_relationships,
    validate_entity,
    validate_recommendation,
    validate_relationship,
)
from validators.l1_consistency import (
    validate_adapter_entity_compliance,
    validate_entity_provenance,
    validate_recommendation_consistency,
)
from validators.l1_consistency import all_passed as l1_all_passed
from validators.l1_consistency import failures as l1_failures


# --- Helpers ---


def _artifact(eid: str = "artifact-001") -> dict:
    return {
        "id": eid,
        "type": "Artifact",
        "name": "test.csv",
        "source_adapter": "core",
        "source_artifact": eid,
        "created_at": "2026-03-22T00:00:00Z",
    }


def _signal(eid: str = "signal-001", artifact_id: str = "artifact-001") -> dict:
    return {
        "id": eid,
        "type": "Signal",
        "name": "accel-ch0",
        "source_adapter": "python_vibration",
        "source_artifact": artifact_id,
        "created_at": "2026-03-22T00:00:00Z",
        "domain": "time",
        "sample_rate": 1000.0,
        "bandwidth": 500.0,
        "unit": "m/s²",
    }


def _minimal_recommendation(
    trace: list[str] | None = None,
    verdict: str = "recommended",
    confidence_level: str = "moderate",
    evidence_source: str = "artifact-001",
) -> dict:
    return {
        "id": "REC-001",
        "title": "Test recommendation",
        "goal": "Test goal",
        "verdict": verdict,
        "evidence": [
            {
                "type": "data",
                "source": evidence_source,
                "summary": "Peak frequencies identified from FFT.",
                "value": [80, 200, 450],
                "unit": "Hz",
            },
        ],
        "assumptions": [
            {
                "id": "A-01",
                "statement": "Signal is stationary.",
                "basis": "Short measurement window.",
                "impact_if_wrong": "medium",
            },
        ],
        "risks": [
            {
                "id": "R-01",
                "description": "Unmeasured cross-axis coupling.",
                "likelihood": "low",
                "severity": "medium",
            },
        ],
        "confidence": {
            "level": confidence_level,
            "rationale": "Based on synthetic data.",
            "limiting_factor": "Single measurement point.",
        },
        "trace": trace or ["artifact-001", "signal-001"],
    }


def _populated_store() -> OntologyStore:
    store = OntologyStore()
    store.add_entity(_artifact())
    store.add_entity(_signal())
    store.add_relationship("signal-001", "derived_from", "artifact-001")
    return store


# =========================================================================
# L0 — Entity validation
# =========================================================================


class TestL0Entity:
    def test_valid_entity_passes(self):
        results = validate_entity(_signal())
        assert all_passed(results)

    def test_bad_entity_type_fails(self):
        entity = _signal()
        entity["type"] = "Bogus"
        results = validate_entity(entity)
        fails = failures(results)
        assert any("entity_type_valid" in f["check"] for f in fails)

    def test_missing_universal_property_fails(self):
        entity = _signal()
        del entity["name"]
        results = validate_entity(entity)
        fails = failures(results)
        assert any("universal_property_name" in f["check"] for f in fails)

    def test_empty_id_fails(self):
        entity = _signal()
        entity["id"] = ""
        results = validate_entity(entity)
        fails = failures(results)
        assert any("universal_property_id" in f["check"] for f in fails)

    def test_bad_signal_domain_enum_fails(self):
        entity = _signal()
        entity["domain"] = "invalid_domain"
        results = validate_entity(entity)
        fails = failures(results)
        assert any("signal_domain_enum" in f["check"] for f in fails)

    def test_signal_sample_rate_wrong_type_fails(self):
        entity = _signal()
        entity["sample_rate"] = "not_a_number"
        results = validate_entity(entity)
        fails = failures(results)
        assert any("signal_sample_rate_type" in f["check"] for f in fails)

    def test_validate_all_entities_in_store(self):
        store = _populated_store()
        results = validate_all_entities(store)
        assert all_passed(results)


# =========================================================================
# L0 — Relationship validation
# =========================================================================


class TestL0Relationship:
    def test_valid_relationship_passes(self):
        store = _populated_store()
        results = validate_relationship(
            ("signal-001", "derived_from", "artifact-001"), store
        )
        assert all_passed(results)

    def test_bad_relationship_type_fails(self):
        store = _populated_store()
        results = validate_relationship(
            ("signal-001", "bogus_rel", "artifact-001"), store
        )
        fails = failures(results)
        assert any("relationship_type_valid" in f["check"] for f in fails)

    def test_bad_source_target_type_pair_fails(self):
        store = _populated_store()
        # Artifact -> Signal via "derived_from" is not allowed
        # (only Signal->Signal, Signal->Artifact, TF->Signal, TF->Artifact)
        results = validate_relationship(
            ("artifact-001", "derived_from", "signal-001"), store
        )
        fails = failures(results)
        assert any("relationship_source_target_types" in f["check"] for f in fails)

    def test_validate_all_relationships_in_store(self):
        store = _populated_store()
        results = validate_all_relationships(store)
        assert all_passed(results)


# =========================================================================
# L0 — Adapter response validation
# =========================================================================


class TestL0AdapterResponse:
    def test_valid_success_response(self):
        resp = {
            "invocation_id": "inv-001",
            "status": "success",
            "outputs": {"peaks_hz": [80, 200, 450]},
            "entities_created": [_signal()],
        }
        results = validate_adapter_response(resp)
        assert all_passed(results)

    def test_valid_error_response(self):
        resp = {
            "invocation_id": "inv-001",
            "status": "error",
            "error": {
                "code": "INVALID_INPUT",
                "message": "Bad input.",
                "recoverable": False,
            },
        }
        results = validate_adapter_response(resp)
        assert all_passed(results)

    def test_missing_invocation_id_fails(self):
        resp = {"status": "success", "outputs": {}}
        results = validate_adapter_response(resp)
        fails = failures(results)
        assert any("invocation_id" in f["check"] for f in fails)

    def test_invalid_status_enum_fails(self):
        resp = {"invocation_id": "inv-001", "status": "bogus", "outputs": {}}
        results = validate_adapter_response(resp)
        fails = failures(results)
        assert any("status_enum" in f["check"] for f in fails)

    def test_success_without_outputs_fails(self):
        resp = {"invocation_id": "inv-001", "status": "success"}
        results = validate_adapter_response(resp)
        fails = failures(results)
        assert any("status_consistency" in f["check"] for f in fails)

    def test_error_without_error_field_fails(self):
        resp = {"invocation_id": "inv-001", "status": "error"}
        results = validate_adapter_response(resp)
        fails = failures(results)
        assert any("status_consistency" in f["check"] for f in fails)


# =========================================================================
# L0 — Recommendation validation
# =========================================================================


class TestL0Recommendation:
    def test_valid_recommendation_passes(self):
        rec = _minimal_recommendation()
        results = validate_recommendation(rec)
        assert all_passed(results), failures(results)

    def test_missing_required_field_fails(self):
        rec = _minimal_recommendation()
        del rec["verdict"]
        results = validate_recommendation(rec)
        fails = failures(results)
        assert any("rec_verdict_present" in f["check"] for f in fails)

    def test_bad_verdict_enum_fails(self):
        rec = _minimal_recommendation(verdict="bogus")
        results = validate_recommendation(rec)
        fails = failures(results)
        assert any("rec_verdict_enum" in f["check"] for f in fails)

    def test_empty_evidence_fails(self):
        rec = _minimal_recommendation()
        rec["evidence"] = []
        results = validate_recommendation(rec)
        fails = failures(results)
        assert any("rec_evidence_min_one" in f["check"] for f in fails)

    def test_empty_assumptions_requires_rationale(self):
        rec = _minimal_recommendation()
        rec["assumptions"] = []
        results = validate_recommendation(rec)
        fails = failures(results)
        assert any("no_assumptions_rationale" in f["check"] for f in fails)

    def test_empty_assumptions_with_rationale_passes(self):
        rec = _minimal_recommendation()
        rec["assumptions"] = []
        rec["no_assumptions_rationale"] = "Direct measurement, no modeling."
        results = validate_recommendation(rec)
        assert all_passed(results), failures(results)

    def test_bad_confidence_level_fails(self):
        rec = _minimal_recommendation(confidence_level="bogus")
        results = validate_recommendation(rec)
        fails = failures(results)
        assert any("confidence_level_enum" in f["check"] for f in fails)


# =========================================================================
# L1 — Recommendation consistency
# =========================================================================


class TestL1RecommendationConsistency:
    def test_valid_recommendation_passes(self):
        store = _populated_store()
        rec = _minimal_recommendation()
        results = validate_recommendation_consistency(rec, store)
        assert l1_all_passed(results), l1_failures(results)

    def test_dangling_trace_id_fails(self):
        store = _populated_store()
        rec = _minimal_recommendation(trace=["artifact-001", "nonexistent-id"])
        results = validate_recommendation_consistency(rec, store)
        fails = l1_failures(results)
        assert any("trace_exists_nonexistent-id" in f["check"] for f in fails)

    def test_ungrounded_evidence_source_fails(self):
        store = _populated_store()
        rec = _minimal_recommendation(evidence_source="unknown-source")
        results = validate_recommendation_consistency(rec, store)
        fails = l1_failures(results)
        assert any("evidence" in f["check"] and "grounded" in f["check"] for f in fails)

    def test_recommended_with_speculative_fails(self):
        store = _populated_store()
        rec = _minimal_recommendation(
            verdict="recommended", confidence_level="speculative"
        )
        results = validate_recommendation_consistency(rec, store)
        fails = l1_failures(results)
        assert any("verdict_confidence_consistency" in f["check"] for f in fails)

    def test_insufficient_data_without_limiting_factor_fails(self):
        store = _populated_store()
        rec = _minimal_recommendation(verdict="insufficient_data")
        rec["confidence"]["limiting_factor"] = ""
        results = validate_recommendation_consistency(rec, store)
        fails = l1_failures(results)
        assert any("verdict_confidence_consistency" in f["check"] for f in fails)


# =========================================================================
# L1 — Entity provenance
# =========================================================================


class TestL1Provenance:
    def test_valid_provenance_passes(self):
        store = _populated_store()
        results = validate_entity_provenance(store)
        assert l1_all_passed(results)

    def test_missing_artifact_ref_fails(self):
        store = OntologyStore()
        # Add a signal without its artifact in the store
        store.add_entity({
            "id": "orphan-signal",
            "type": "Signal",
            "name": "orphan",
            "source_adapter": "python_vibration",
            "source_artifact": "nonexistent-artifact",
            "created_at": "2026-03-22T00:00:00Z",
        })
        results = validate_entity_provenance(store)
        fails = l1_failures(results)
        assert any("provenance_orphan-signal" in f["check"] for f in fails)


# =========================================================================
# L1 — Adapter entity type compliance
# =========================================================================


class TestL1AdapterEntityCompliance:
    def test_compliant_entity_passes(self):
        capability = {"entity_types_produced": ["Signal"]}
        response = {"entities_created": [_signal()]}
        results = validate_adapter_entity_compliance(response, capability)
        assert l1_all_passed(results)

    def test_noncompliant_entity_fails(self):
        capability = {"entity_types_produced": ["Signal"]}
        response = {"entities_created": [_artifact()]}
        results = validate_adapter_entity_compliance(response, capability)
        fails = l1_failures(results)
        assert len(fails) == 1
        assert "entity_type_compliance" in fails[0]["check"]
