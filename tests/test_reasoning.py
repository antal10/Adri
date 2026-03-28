"""Tests for vibration reasoning stub."""

from __future__ import annotations

import pytest

from adri.ontology_store import OntologyStore
from reasoning.vibration_stub import generate_recommendation
from validators.l0_schema import (
    all_passed as l0_all_passed,
    failures as l0_failures,
    validate_recommendation,
)
from validators.l1_consistency import (
    all_passed as l1_all_passed,
    failures as l1_failures,
    validate_recommendation_consistency,
)


# --- Fixtures ---


def _make_store_and_outputs(
    peaks_hz: list[float] | None = None,
    peaks_amplitude: list[float] | None = None,
) -> tuple[OntologyStore, dict, str, str]:
    """Return (store, adapter_outputs, artifact_id, signal_id).

    adapter_outputs uses the matlab_vibration response["outputs"] shape
    (features sub-dict, DEC-013) as consumed by vibration_stub.
    """
    artifact_id = "artifact-vib-001"
    signal_id = "signal-matlab-artifact-vib-001"

    store = OntologyStore()
    store.add_entity({
        "id": artifact_id,
        "type": "Artifact",
        "name": "test_vibration.csv",
        "source_adapter": "core",
        "source_artifact": artifact_id,
        "created_at": "2026-03-22T00:00:00Z",
    })
    store.add_entity({
        "id": signal_id,
        "type": "Signal",
        "name": "acceleration-channel-0",
        "source_adapter": "matlab_vibration",
        "source_artifact": artifact_id,
        "created_at": "2026-03-22T00:00:00Z",
        "domain": "time",
        "sample_rate": 1000.0,
        "bandwidth": 500.0,
        "unit": "m/s²",
    })
    store.add_relationship(signal_id, "derived_from", artifact_id)

    if peaks_hz is None:
        peaks_hz = [80.0, 200.0, 450.0]
    if peaks_amplitude is None:
        peaks_amplitude = [0.5, 0.3, 0.2]

    outputs = {
        "features": {
            "sample_rate_hz": 1000.0,
            "duration_s": 1.0,
            "dominant_peak_frequencies_hz": peaks_hz,
            "dominant_peak_magnitudes": peaks_amplitude,
            "rms": 0.5,
            "frequency_resolution_hz": 1.0,
            "backend": "numpy_fallback",
        },
        "run_dir": "",
        "artifacts_written": [],
        "backend": "numpy_fallback",
    }

    return store, outputs, artifact_id, signal_id


# =========================================================================
# Basic structure
# =========================================================================


class TestRecommendationStructure:
    def test_returns_dict_with_required_fields(self):
        store, outputs, aid, sid = _make_store_and_outputs()
        rec = generate_recommendation(store, outputs, aid, sid)
        for field in ("id", "title", "goal", "verdict", "evidence",
                      "assumptions", "risks", "confidence", "trace"):
            assert field in rec, f"Missing field '{field}'"

    def test_id_format(self):
        store, outputs, aid, sid = _make_store_and_outputs()
        rec = generate_recommendation(store, outputs, aid, sid)
        assert rec["id"].startswith("REC-")

    def test_trace_contains_artifact_and_signal(self):
        store, outputs, aid, sid = _make_store_and_outputs()
        rec = generate_recommendation(store, outputs, aid, sid)
        assert aid in rec["trace"]
        assert sid in rec["trace"]


# =========================================================================
# Verdict logic
# =========================================================================


class TestVerdictLogic:
    def test_peaks_present_gives_recommended(self):
        store, outputs, aid, sid = _make_store_and_outputs(
            peaks_hz=[80.0, 200.0], peaks_amplitude=[0.5, 0.3]
        )
        rec = generate_recommendation(store, outputs, aid, sid)
        assert rec["verdict"] == "recommended"

    def test_no_peaks_gives_insufficient_data(self):
        store, outputs, aid, sid = _make_store_and_outputs(
            peaks_hz=[], peaks_amplitude=[]
        )
        rec = generate_recommendation(store, outputs, aid, sid)
        assert rec["verdict"] == "insufficient_data"

    def test_no_peaks_confidence_is_low(self):
        store, outputs, aid, sid = _make_store_and_outputs(
            peaks_hz=[], peaks_amplitude=[]
        )
        rec = generate_recommendation(store, outputs, aid, sid)
        assert rec["confidence"]["level"] == "low"

    def test_peaks_present_confidence_is_moderate(self):
        store, outputs, aid, sid = _make_store_and_outputs()
        rec = generate_recommendation(store, outputs, aid, sid)
        assert rec["confidence"]["level"] == "moderate"


# =========================================================================
# Evidence content
# =========================================================================


class TestEvidence:
    def test_evidence_contains_at_least_one(self):
        store, outputs, aid, sid = _make_store_and_outputs()
        rec = generate_recommendation(store, outputs, aid, sid)
        assert len(rec["evidence"]) >= 1

    def test_evidence_source_is_artifact_id(self):
        store, outputs, aid, sid = _make_store_and_outputs()
        rec = generate_recommendation(store, outputs, aid, sid)
        assert rec["evidence"][0]["source"] == aid

    def test_evidence_contains_peaks_when_present(self):
        store, outputs, aid, sid = _make_store_and_outputs(
            peaks_hz=[80.0, 200.0], peaks_amplitude=[0.5, 0.3]
        )
        rec = generate_recommendation(store, outputs, aid, sid)
        assert rec["evidence"][0]["value"] == [80.0, 200.0]
        assert rec["evidence"][0]["unit"] == "Hz"

    def test_evidence_no_value_when_no_peaks(self):
        store, outputs, aid, sid = _make_store_and_outputs(
            peaks_hz=[], peaks_amplitude=[]
        )
        rec = generate_recommendation(store, outputs, aid, sid)
        assert "value" not in rec["evidence"][0]


# =========================================================================
# Assumptions and risks
# =========================================================================


class TestAssumptionsAndRisks:
    def test_two_assumptions(self):
        store, outputs, aid, sid = _make_store_and_outputs()
        rec = generate_recommendation(store, outputs, aid, sid)
        assert len(rec["assumptions"]) == 2

    def test_two_risks(self):
        store, outputs, aid, sid = _make_store_and_outputs()
        rec = generate_recommendation(store, outputs, aid, sid)
        assert len(rec["risks"]) == 2

    def test_assumption_ids_unique(self):
        store, outputs, aid, sid = _make_store_and_outputs()
        rec = generate_recommendation(store, outputs, aid, sid)
        ids = [a["id"] for a in rec["assumptions"]]
        assert len(ids) == len(set(ids))

    def test_risk_ids_unique(self):
        store, outputs, aid, sid = _make_store_and_outputs()
        rec = generate_recommendation(store, outputs, aid, sid)
        ids = [r["id"] for r in rec["risks"]]
        assert len(ids) == len(set(ids))


# =========================================================================
# L0 + L1 validator integration
# =========================================================================


class TestValidatorIntegration:
    def test_l0_passes_with_peaks(self):
        store, outputs, aid, sid = _make_store_and_outputs()
        rec = generate_recommendation(store, outputs, aid, sid)
        results = validate_recommendation(rec)
        assert l0_all_passed(results), l0_failures(results)

    def test_l0_passes_without_peaks(self):
        store, outputs, aid, sid = _make_store_and_outputs(
            peaks_hz=[], peaks_amplitude=[]
        )
        rec = generate_recommendation(store, outputs, aid, sid)
        results = validate_recommendation(rec)
        assert l0_all_passed(results), l0_failures(results)

    def test_l1_passes_with_peaks(self):
        store, outputs, aid, sid = _make_store_and_outputs()
        rec = generate_recommendation(store, outputs, aid, sid)
        results = validate_recommendation_consistency(rec, store)
        assert l1_all_passed(results), l1_failures(results)

    def test_l1_passes_without_peaks(self):
        store, outputs, aid, sid = _make_store_and_outputs(
            peaks_hz=[], peaks_amplitude=[]
        )
        rec = generate_recommendation(store, outputs, aid, sid)
        results = validate_recommendation_consistency(rec, store)
        assert l1_all_passed(results), l1_failures(results)
