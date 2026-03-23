"""Tests for the MATLAB vibration adapter — file-in/file-out contract.

Covers:
- Registration manifest conformance
- Health check
- Success path: valid CSV → features.json, raw_output.mat, run_log.txt
- Failure paths: invalid header, missing file, bad schema
- Normalization into ontology store with provenance
- End-to-end: CSV → adapter → normalize → validate
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import numpy as np
import pytest

from adapters.matlab_vibration.adapter import (
    REGISTRATION,
    analyze_vibration_csv,
    health,
)
from adapters.matlab_vibration.normalize import normalize_into_store
from adri.ontology_store import OntologyStore
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
from reasoning.vibration_stub import generate_recommendation


# =========================================================================
# Fixtures
# =========================================================================


def _write_three_tone_csv(path: str) -> None:
    sample_rate = 1000.0
    n = 1000
    t = np.linspace(0, 1.0, n, endpoint=False)
    accel = (
        1.0 * np.sin(2 * np.pi * 80 * t)
        + 0.6 * np.sin(2 * np.pi * 200 * t)
        + 0.3 * np.sin(2 * np.pi * 450 * t)
    )
    with open(path, "w") as f:
        f.write("time_s,accel_m_s2\n")
        for ti, ai in zip(t, accel):
            f.write(f"{ti:.6f},{ai:.6f}\n")


def _write_zero_csv(path: str) -> None:
    n = 100
    t = np.arange(n) / 1000.0
    with open(path, "w") as f:
        f.write("time_s,accel_m_s2\n")
        for ti in t:
            f.write(f"{ti:.6f},0.000000\n")


def _write_bad_header_csv(path: str) -> None:
    with open(path, "w") as f:
        f.write("timestamp,value\n")
        f.write("0.0,1.0\n")
        f.write("0.001,2.0\n")


@pytest.fixture
def three_tone_csv(tmp_path):
    p = str(tmp_path / "vibration.csv")
    _write_three_tone_csv(p)
    return p


@pytest.fixture
def zero_csv(tmp_path):
    p = str(tmp_path / "vibration.csv")
    _write_zero_csv(p)
    return p


@pytest.fixture
def bad_header_csv(tmp_path):
    p = str(tmp_path / "bad_header.csv")
    _write_bad_header_csv(p)
    return p


@pytest.fixture
def run_dir(tmp_path):
    d = str(tmp_path / "run_001")
    return d


def _make_request(artifact_id, file_path, run_dir, invocation_id="inv-m-001"):
    return {
        "invocation_id": invocation_id,
        "operation_id": "analyze_vibration_csv",
        "inputs": {
            "artifact_id": artifact_id,
            "file_path": file_path,
            "run_dir": run_dir,
        },
    }


# =========================================================================
# Registration
# =========================================================================


class TestRegistration:
    def test_adapter_id(self):
        assert REGISTRATION["adapter_id"] == "matlab_vibration"

    def test_has_required_fields(self):
        for field in ("adapter_id", "adapter_version", "tool_name", "capabilities"):
            assert field in REGISTRATION

    def test_capability_entity_types_produced(self):
        cap = REGISTRATION["capabilities"][0]
        assert cap["entity_types_produced"] == ["Signal"]

    def test_capability_operation_id(self):
        cap = REGISTRATION["capabilities"][0]
        assert cap["operation_id"] == "analyze_vibration_csv"

    def test_idempotent(self):
        cap = REGISTRATION["capabilities"][0]
        assert cap["idempotent"] is True


# =========================================================================
# Health
# =========================================================================


class TestHealth:
    def test_health_returns_status(self):
        h = health()
        assert h["adapter_id"] == "matlab_vibration"
        assert h["status"] in ("healthy", "degraded")

    def test_health_reports_tool_reachable(self):
        h = health()
        assert isinstance(h["tool_reachable"], bool)


# =========================================================================
# Success path
# =========================================================================


class TestSuccessPath:
    def test_status_is_success(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        assert resp["status"] == "success"

    def test_invocation_id_echoed(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir, "inv-xyz")
        resp = analyze_vibration_csv(req)
        assert resp["invocation_id"] == "inv-xyz"

    def test_features_json_written(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        analyze_vibration_csv(req)
        assert os.path.isfile(os.path.join(run_dir, "features.json"))

    def test_raw_output_mat_written(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        analyze_vibration_csv(req)
        assert os.path.isfile(os.path.join(run_dir, "raw_output.mat"))

    def test_run_log_written(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        analyze_vibration_csv(req)
        assert os.path.isfile(os.path.join(run_dir, "run_log.txt"))

    def test_request_json_written(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        analyze_vibration_csv(req)
        assert os.path.isfile(os.path.join(run_dir, "request.json"))

    def test_vibration_csv_copied(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        analyze_vibration_csv(req)
        assert os.path.isfile(os.path.join(run_dir, "vibration.csv"))

    def test_features_has_required_keys(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        features = resp["outputs"]["features"]
        required = {
            "sample_rate_hz", "duration_s", "rms",
            "dominant_peak_frequencies_hz", "dominant_peak_magnitudes",
            "frequency_resolution_hz",
        }
        assert required <= set(features.keys())

    def test_sample_rate_correct(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        assert abs(resp["outputs"]["features"]["sample_rate_hz"] - 1000.0) < 1.0

    def test_detects_three_peaks(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        peaks = resp["outputs"]["features"]["dominant_peak_frequencies_hz"]
        assert len(peaks) >= 3

    def test_peak_near_80hz(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        peaks = resp["outputs"]["features"]["dominant_peak_frequencies_hz"]
        assert any(abs(p - 80.0) < 5.0 for p in peaks)

    def test_rms_is_positive(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        assert resp["outputs"]["features"]["rms"] > 0

    def test_frequency_resolution(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        assert resp["outputs"]["features"]["frequency_resolution_hz"] == pytest.approx(1.0, abs=0.1)

    def test_signal_entity_created(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        entities = resp.get("entities_created", [])
        assert len(entities) == 1
        assert entities[0]["type"] == "Signal"

    def test_signal_source_adapter(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        assert resp["entities_created"][0]["source_adapter"] == "matlab_vibration"

    def test_signal_source_artifact(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        assert resp["entities_created"][0]["source_artifact"] == "art-001"

    def test_features_json_is_valid_json(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        analyze_vibration_csv(req)
        with open(os.path.join(run_dir, "features.json")) as f:
            data = json.load(f)
        assert "sample_rate_hz" in data

    def test_mat_file_header(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        analyze_vibration_csv(req)
        with open(os.path.join(run_dir, "raw_output.mat"), "rb") as f:
            header = f.read(128)
        assert b"MATLAB 5.0" in header

    def test_artifacts_written_list(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        written = resp["outputs"]["artifacts_written"]
        assert "features.json" in written
        assert "raw_output.mat" in written
        assert "run_log.txt" in written
        assert "request.json" in written
        assert "vibration.csv" in written

    def test_duration_ms_present(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        assert "duration_ms" in resp
        assert isinstance(resp["duration_ms"], int)

    def test_l0_validates_response(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        checks = validate_adapter_response(resp)
        assert l0_all_passed(checks), [c for c in checks if not c["passed"]]


# =========================================================================
# Zero signal path
# =========================================================================


class TestZeroSignal:
    def test_success_with_zero_signal(self, zero_csv, run_dir):
        req = _make_request("art-zero", zero_csv, run_dir)
        resp = analyze_vibration_csv(req)
        assert resp["status"] == "success"

    def test_no_peaks(self, zero_csv, run_dir):
        req = _make_request("art-zero", zero_csv, run_dir)
        resp = analyze_vibration_csv(req)
        assert resp["outputs"]["features"]["dominant_peak_frequencies_hz"] == []

    def test_rms_near_zero(self, zero_csv, run_dir):
        req = _make_request("art-zero", zero_csv, run_dir)
        resp = analyze_vibration_csv(req)
        assert resp["outputs"]["features"]["rms"] == pytest.approx(0.0, abs=1e-9)


# =========================================================================
# Failure paths
# =========================================================================


class TestFailurePaths:
    def test_bad_header(self, bad_header_csv, run_dir):
        req = _make_request("art-bad", bad_header_csv, run_dir)
        resp = analyze_vibration_csv(req)
        assert resp["status"] == "error"
        assert resp["error"]["code"] == "INVALID_ARTIFACT"

    def test_missing_file(self, run_dir):
        req = _make_request("art-missing", "/nonexistent/file.csv", run_dir)
        resp = analyze_vibration_csv(req)
        assert resp["status"] == "error"
        assert resp["error"]["code"] == "INVALID_ARTIFACT"

    def test_wrong_operation_id(self, three_tone_csv, run_dir):
        req = _make_request("art-001", three_tone_csv, run_dir)
        req["operation_id"] = "wrong_op"
        resp = analyze_vibration_csv(req)
        assert resp["status"] == "error"
        assert resp["error"]["code"] == "INVALID_INPUT"

    def test_missing_artifact_id(self, three_tone_csv, run_dir):
        req = {
            "invocation_id": "inv-001",
            "operation_id": "analyze_vibration_csv",
            "inputs": {"file_path": three_tone_csv, "run_dir": run_dir},
        }
        resp = analyze_vibration_csv(req)
        assert resp["status"] == "error"
        assert resp["error"]["code"] == "INVALID_INPUT"

    def test_missing_run_dir(self, three_tone_csv):
        req = {
            "invocation_id": "inv-001",
            "operation_id": "analyze_vibration_csv",
            "inputs": {"artifact_id": "art-001", "file_path": three_tone_csv},
        }
        resp = analyze_vibration_csv(req)
        assert resp["status"] == "error"

    def test_error_response_has_required_fields(self, bad_header_csv, run_dir):
        req = _make_request("art-bad", bad_header_csv, run_dir)
        resp = analyze_vibration_csv(req)
        err = resp["error"]
        assert "code" in err
        assert "message" in err
        assert "recoverable" in err

    def test_error_recoverable_is_false(self, bad_header_csv, run_dir):
        req = _make_request("art-bad", bad_header_csv, run_dir)
        resp = analyze_vibration_csv(req)
        assert resp["error"]["recoverable"] is False

    def test_run_log_written_on_error(self, bad_header_csv, run_dir):
        req = _make_request("art-bad", bad_header_csv, run_dir)
        analyze_vibration_csv(req)
        assert os.path.isfile(os.path.join(run_dir, "run_log.txt"))


# =========================================================================
# Normalization & provenance
# =========================================================================


class TestNormalization:
    def _setup(self, three_tone_csv, run_dir):
        store = OntologyStore()
        now = datetime.now(timezone.utc).isoformat()
        store.add_entity({
            "id": "art-norm",
            "type": "Artifact",
            "name": "vibration.csv",
            "source_adapter": "core",
            "source_artifact": "art-norm",
            "created_at": now,
        })
        req = _make_request("art-norm", three_tone_csv, run_dir)
        resp = analyze_vibration_csv(req)
        summary = normalize_into_store(store, resp, "art-norm")
        return store, resp, summary

    def test_signal_added_to_store(self, three_tone_csv, run_dir):
        store, _, summary = self._setup(three_tone_csv, run_dir)
        assert summary["signal_id"] is not None
        assert store.exists(summary["signal_id"])

    def test_signal_source_adapter_is_matlab(self, three_tone_csv, run_dir):
        store, _, summary = self._setup(three_tone_csv, run_dir)
        sig = store.get(summary["signal_id"])
        assert sig["source_adapter"] == "matlab_vibration"

    def test_signal_source_artifact_correct(self, three_tone_csv, run_dir):
        store, _, summary = self._setup(three_tone_csv, run_dir)
        sig = store.get(summary["signal_id"])
        assert sig["source_artifact"] == "art-norm"

    def test_output_artifacts_created(self, three_tone_csv, run_dir):
        store, _, summary = self._setup(three_tone_csv, run_dir)
        # At minimum: features.json, raw_output.mat, run_log.txt
        assert len(summary["output_artifact_ids"]) >= 3

    def test_output_artifacts_in_store(self, three_tone_csv, run_dir):
        store, _, summary = self._setup(three_tone_csv, run_dir)
        for aid in summary["output_artifact_ids"]:
            assert store.exists(aid), f"Artifact {aid} not in store"

    def test_output_artifact_source_adapter(self, three_tone_csv, run_dir):
        store, _, summary = self._setup(three_tone_csv, run_dir)
        for aid in summary["output_artifact_ids"]:
            art = store.get(aid)
            assert art["source_adapter"] == "matlab_vibration"

    def test_output_artifact_source_artifact_points_to_source(self, three_tone_csv, run_dir):
        store, _, summary = self._setup(three_tone_csv, run_dir)
        for aid in summary["output_artifact_ids"]:
            art = store.get(aid)
            assert art["source_artifact"] == "art-norm"

    def test_references_relationships_created(self, three_tone_csv, run_dir):
        store, _, summary = self._setup(three_tone_csv, run_dir)
        refs = store.relationships_to("art-norm")
        ref_sources = {r[0] for r in refs if r[1] == "references"}
        for aid in summary["output_artifact_ids"]:
            assert aid in ref_sources

    def test_signal_derived_from_artifact(self, three_tone_csv, run_dir):
        store, _, summary = self._setup(three_tone_csv, run_dir)
        rels = store.relationships_from(summary["signal_id"])
        derived = [(s, r, t) for s, r, t in rels if r == "derived_from"]
        assert len(derived) == 1
        assert derived[0][2] == "art-norm"

    def test_l0_all_entities_pass(self, three_tone_csv, run_dir):
        store, _, _ = self._setup(three_tone_csv, run_dir)
        checks = validate_all_entities(store)
        assert l0_all_passed(checks), [c for c in checks if not c["passed"]]

    def test_l0_all_relationships_pass(self, three_tone_csv, run_dir):
        store, _, _ = self._setup(three_tone_csv, run_dir)
        checks = validate_all_relationships(store)
        assert l0_all_passed(checks), [c for c in checks if not c["passed"]]

    def test_l1_provenance_passes(self, three_tone_csv, run_dir):
        store, _, _ = self._setup(three_tone_csv, run_dir)
        checks = validate_entity_provenance(store)
        assert l1_all_passed(checks), [c for c in checks if not c["passed"]]

    def test_l1_entity_compliance_passes(self, three_tone_csv, run_dir):
        _, resp, _ = self._setup(three_tone_csv, run_dir)
        cap = REGISTRATION["capabilities"][0]
        checks = validate_adapter_entity_compliance(resp, cap)
        assert l1_all_passed(checks), [c for c in checks if not c["passed"]]


# =========================================================================
# End-to-end: CSV → adapter → normalize → reason → validate
# =========================================================================


class TestE2EMatlab:
    """Full slice: adapter → persistence → normalization → reasoning → validation."""

    def _run_full_slice(self, csv_path, run_dir, artifact_id="art-e2e"):
        store = OntologyStore()
        now = datetime.now(timezone.utc).isoformat()
        store.add_entity({
            "id": artifact_id,
            "type": "Artifact",
            "name": os.path.basename(csv_path),
            "source_adapter": "core",
            "source_artifact": artifact_id,
            "created_at": now,
        })

        req = _make_request(artifact_id, csv_path, run_dir)
        resp = analyze_vibration_csv(req)
        assert resp["status"] == "success", resp.get("error")

        summary = normalize_into_store(store, resp, artifact_id)
        signal_id = summary["signal_id"]

        # Translate features to adapter_outputs format for reasoning stub
        features = resp["outputs"]["features"]
        adapter_outputs = {
            "peaks_hz": features["dominant_peak_frequencies_hz"],
            "peaks_amplitude": features["dominant_peak_magnitudes"],
            "sample_rate": features["sample_rate_hz"],
            "duration_s": features["duration_s"],
            "num_samples": int(features["duration_s"] * features["sample_rate_hz"]),
        }

        rec = generate_recommendation(store, adapter_outputs, artifact_id, signal_id)
        return store, resp, summary, rec

    def test_e2e_success(self, three_tone_csv, run_dir):
        store, resp, summary, rec = self._run_full_slice(three_tone_csv, run_dir)
        assert rec["verdict"] == "recommended"

    def test_e2e_all_validation_passes(self, three_tone_csv, run_dir):
        store, resp, summary, rec = self._run_full_slice(three_tone_csv, run_dir)
        all_checks = []

        # L0 adapter response
        all_checks.extend(validate_adapter_response(resp))

        # L1 entity compliance
        cap = REGISTRATION["capabilities"][0]
        all_checks.extend(validate_adapter_entity_compliance(resp, cap))

        # L0 entities & relationships
        all_checks.extend(validate_all_entities(store))
        all_checks.extend(validate_all_relationships(store))

        # L1 provenance
        all_checks.extend(validate_entity_provenance(store))

        # L0 recommendation
        all_checks.extend(validate_recommendation(rec))

        # L1 recommendation consistency
        all_checks.extend(validate_recommendation_consistency(rec, store))

        failed = [c for c in all_checks if not c["passed"]]
        assert failed == [], failed

    def test_e2e_run_artifacts_exist(self, three_tone_csv, run_dir):
        self._run_full_slice(three_tone_csv, run_dir)
        for f in ("request.json", "vibration.csv", "features.json",
                   "raw_output.mat", "run_log.txt"):
            assert os.path.isfile(os.path.join(run_dir, f)), f"Missing: {f}"

    def test_e2e_provenance_chain(self, three_tone_csv, run_dir):
        store, _, summary, rec = self._run_full_slice(three_tone_csv, run_dir)
        # Signal → derived_from → source artifact
        signal_id = summary["signal_id"]
        rels = store.relationships_from(signal_id)
        assert any(r == "derived_from" and t == "art-e2e" for _, r, t in rels)
        # Trace includes artifact and signal
        assert "art-e2e" in rec["trace"]
        assert signal_id in rec["trace"]

    def test_e2e_zero_signal(self, zero_csv, run_dir):
        store, _, _, rec = self._run_full_slice(zero_csv, run_dir, "art-zero-e2e")
        assert rec["verdict"] == "insufficient_data"
        assert rec["confidence"]["level"] == "low"

    def test_e2e_features_json_matches_response(self, three_tone_csv, run_dir):
        _, resp, _, _ = self._run_full_slice(three_tone_csv, run_dir)
        with open(os.path.join(run_dir, "features.json")) as f:
            persisted = json.load(f)
        assert persisted == resp["outputs"]["features"]
