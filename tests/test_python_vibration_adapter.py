"""Tests for the Python vibration adapter (adapter contract compliance)."""

from __future__ import annotations

import os
import tempfile

import pytest

from adapters.python_vibration.adapter import (
    REGISTRATION,
    health,
    ingest_vibration_csv,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SYNTHETIC_CSV = os.path.join(FIXTURES_DIR, "synthetic_vibration.csv")


# --- Registration manifest ---


class TestRegistration:
    def test_has_required_fields(self):
        for field in ("adapter_id", "adapter_version", "tool_name", "capabilities"):
            assert field in REGISTRATION

    def test_adapter_id(self):
        assert REGISTRATION["adapter_id"] == "python_vibration"

    def test_at_least_one_capability(self):
        assert len(REGISTRATION["capabilities"]) >= 1

    def test_capability_fields(self):
        cap = REGISTRATION["capabilities"][0]
        required = {
            "operation_id",
            "description",
            "input_schema",
            "output_schema",
            "entity_types_produced",
            "idempotent",
        }
        assert required <= set(cap.keys())

    def test_entity_types_produced_is_signal(self):
        cap = REGISTRATION["capabilities"][0]
        assert cap["entity_types_produced"] == ["Signal"]

    def test_idempotent_is_true(self):
        cap = REGISTRATION["capabilities"][0]
        assert cap["idempotent"] is True


# --- Health check ---


class TestHealth:
    def test_health_returns_healthy(self):
        result = health()
        assert result["adapter_id"] == "python_vibration"
        assert result["status"] == "healthy"
        assert result["tool_reachable"] is True


# --- Successful ingestion ---


def _make_request(file_path: str = SYNTHETIC_CSV, artifact_id: str = "art-001"):
    return {
        "invocation_id": "inv-001",
        "operation_id": "ingest_vibration_csv",
        "inputs": {
            "artifact_id": artifact_id,
            "file_path": file_path,
        },
    }


class TestIngestSuccess:
    def test_status_is_success(self):
        resp = ingest_vibration_csv(_make_request())
        assert resp["status"] == "success"

    def test_invocation_id_echoed(self):
        resp = ingest_vibration_csv(_make_request())
        assert resp["invocation_id"] == "inv-001"

    def test_outputs_present(self):
        resp = ingest_vibration_csv(_make_request())
        outputs = resp["outputs"]
        assert "sample_rate" in outputs
        assert "duration_s" in outputs
        assert "num_samples" in outputs
        # No signal-analysis outputs: FFT and peak detection belong to MATLAB.
        assert "peaks_hz" not in outputs
        assert "peaks_amplitude" not in outputs

    def test_sample_rate_is_1000(self):
        resp = ingest_vibration_csv(_make_request())
        assert abs(resp["outputs"]["sample_rate"] - 1000.0) < 1.0

    def test_signal_entity_created(self):
        resp = ingest_vibration_csv(_make_request())
        entities = resp["entities_created"]
        assert len(entities) == 1

    def test_signal_entity_type(self):
        resp = ingest_vibration_csv(_make_request())
        entity = resp["entities_created"][0]
        assert entity["type"] == "Signal"

    def test_signal_domain_is_time(self):
        resp = ingest_vibration_csv(_make_request())
        entity = resp["entities_created"][0]
        assert entity["domain"] == "time"

    def test_signal_has_universal_properties(self):
        resp = ingest_vibration_csv(_make_request())
        entity = resp["entities_created"][0]
        for prop in ("id", "name", "source_adapter", "source_artifact", "created_at"):
            assert prop in entity and entity[prop]

    def test_signal_source_adapter(self):
        resp = ingest_vibration_csv(_make_request())
        entity = resp["entities_created"][0]
        assert entity["source_adapter"] == "python_vibration"

    def test_signal_source_artifact(self):
        resp = ingest_vibration_csv(_make_request())
        entity = resp["entities_created"][0]
        assert entity["source_artifact"] == "art-001"


# --- Idempotency ---


class TestIdempotency:
    def test_same_input_same_output(self):
        req = _make_request()
        resp1 = ingest_vibration_csv(req)
        resp2 = ingest_vibration_csv(req)
        # Outputs should match (timestamps may differ, so compare outputs only)
        assert resp1["outputs"] == resp2["outputs"]
        assert resp1["status"] == resp2["status"]


# --- Error handling ---


class TestErrors:
    def test_invalid_operation_id(self):
        req = _make_request()
        req["operation_id"] = "bogus_op"
        resp = ingest_vibration_csv(req)
        assert resp["status"] == "error"
        assert resp["error"]["code"] == "INVALID_INPUT"

    def test_missing_artifact_id(self):
        req = _make_request()
        req["inputs"] = {"file_path": SYNTHETIC_CSV}
        resp = ingest_vibration_csv(req)
        assert resp["status"] == "error"
        assert resp["error"]["code"] == "INVALID_INPUT"

    def test_missing_file_path(self):
        req = _make_request()
        req["inputs"] = {"artifact_id": "art-001"}
        resp = ingest_vibration_csv(req)
        assert resp["status"] == "error"
        assert resp["error"]["code"] == "INVALID_INPUT"

    def test_nonexistent_file(self):
        req = _make_request(file_path="/tmp/does_not_exist.csv")
        resp = ingest_vibration_csv(req)
        assert resp["status"] == "error"
        assert resp["error"]["code"] == "INVALID_ARTIFACT"

    def test_malformed_csv(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write("not,a,valid,vibration,csv\n1,2,3,4,5\n")
            tmp_path = f.name
        try:
            req = _make_request(file_path=tmp_path)
            resp = ingest_vibration_csv(req)
            assert resp["status"] == "error"
            assert resp["error"]["code"] == "INVALID_ARTIFACT"
        finally:
            os.unlink(tmp_path)

    def test_error_has_required_fields(self):
        req = _make_request(file_path="/tmp/does_not_exist.csv")
        resp = ingest_vibration_csv(req)
        err = resp["error"]
        assert "code" in err
        assert "message" in err
        assert "recoverable" in err

    def test_error_recoverable_is_false(self):
        req = _make_request(file_path="/tmp/does_not_exist.csv")
        resp = ingest_vibration_csv(req)
        assert resp["error"]["recoverable"] is False
