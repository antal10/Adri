"""Tests for the run_loop orchestrator."""

from __future__ import annotations

import os
import tempfile
from unittest import mock

import numpy as np
import pytest

from run_loop import RunResult, run


# --- Helper: generate a vibration CSV ---


def _write_vibration_csv(
    path: str,
    sample_rate: float = 1000.0,
    duration_s: float = 1.0,
    freq_hz: float = 80.0,
) -> None:
    """Write a synthetic vibration CSV with a single sine tone."""
    n = int(sample_rate * duration_s)
    t = np.linspace(0, duration_s, n, endpoint=False)
    accel = np.sin(2 * np.pi * freq_hz * t)
    with open(path, "w") as f:
        f.write("time_s,accel_m_s2\n")
        for ti, ai in zip(t, accel):
            f.write(f"{ti:.6f},{ai:.6f}\n")


@pytest.fixture
def csv_path(tmp_path):
    """Create a temp vibration CSV and return its path."""
    p = str(tmp_path / "vibration.csv")
    _write_vibration_csv(p, freq_hz=80.0)
    return p


@pytest.fixture
def empty_csv_path(tmp_path):
    """Create a CSV with headers but no data rows."""
    p = str(tmp_path / "empty.csv")
    with open(p, "w") as f:
        f.write("time_s,accel_m_s2\n")
    return p


# =========================================================================
# Happy path
# =========================================================================


class TestHappyPath:
    def test_run_succeeds(self, csv_path):
        result = run(csv_path)
        assert result.ok
        assert result.error is None
        assert result.recommendation is not None

    def test_recommendation_has_verdict(self, csv_path):
        result = run(csv_path)
        assert result.recommendation["verdict"] in ("recommended", "insufficient_data")

    def test_all_validations_passed(self, csv_path):
        result = run(csv_path)
        for check in result.validation_results:
            assert check["passed"], f"Failed: {check}"

    def test_custom_artifact_and_invocation_ids(self, csv_path):
        result = run(csv_path, artifact_id="my-artifact", invocation_id="my-inv")
        assert result.ok
        assert "my-artifact" in result.recommendation["trace"]


# =========================================================================
# Adapter failure paths
# =========================================================================


class TestAdapterFailures:
    def test_unhealthy_adapter(self, csv_path):
        with mock.patch(
            "run_loop.health",
            return_value={"adapter_id": "python_vibration", "status": "unavailable",
                          "tool_reachable": False, "message": "NumPy gone"},
        ):
            result = run(csv_path)
            assert not result.ok
            assert "health check" in result.error.lower()

    def test_adapter_returns_error(self, csv_path):
        error_response = {
            "invocation_id": "inv-001",
            "status": "error",
            "error": {
                "code": "INVALID_ARTIFACT",
                "message": "Bad file.",
                "recoverable": False,
            },
        }
        with mock.patch("run_loop.ingest_vibration_csv", return_value=error_response):
            result = run(csv_path)
            assert not result.ok
            assert "adapter error" in result.error.lower()

    def test_nonexistent_file(self):
        result = run("/nonexistent/path.csv")
        assert not result.ok
        # Adapter should fail to parse — error propagates through
        assert result.error is not None


# =========================================================================
# Validation failure paths
# =========================================================================


class TestValidationFailures:
    def test_bad_adapter_response_fails_l0(self, csv_path):
        """If adapter returns a response missing required fields, L0 catches it."""
        bad_response = {"status": "success"}  # missing invocation_id, outputs
        with mock.patch("run_loop.ingest_vibration_csv", return_value=bad_response):
            result = run(csv_path)
            assert not result.ok
            assert "L0" in result.error

    def test_adapter_producing_wrong_entity_type_flagged(self, csv_path):
        """If adapter produces an entity type outside its capability, L1 flags it."""
        bad_response = {
            "invocation_id": "inv-001",
            "status": "success",
            "outputs": {
                "sample_rate": 1000.0,
                "duration_s": 1.0,
                "num_samples": 1000,
                "peaks_hz": [80.0],
                "peaks_amplitude": [0.5],
            },
            "entities_created": [
                {
                    "id": "signal-accel-artifact-001",
                    "type": "Signal",
                    "name": "accel-ch0",
                    "source_adapter": "python_vibration",
                    "source_artifact": "artifact-001",
                    "created_at": "2026-03-22T00:00:00Z",
                    "domain": "time",
                    "sample_rate": 1000.0,
                    "bandwidth": 500.0,
                    "unit": "m/s²",
                },
                {
                    "id": "component-bad",
                    "type": "Component",
                    "name": "should-not-exist",
                    "source_adapter": "python_vibration",
                    "source_artifact": "artifact-001",
                    "created_at": "2026-03-22T00:00:00Z",
                },
            ],
        }
        with mock.patch("run_loop.ingest_vibration_csv", return_value=bad_response):
            result = run(csv_path)
            # Compliance checks capture that Component is not in entity_types_produced
            compliance_fails = [
                c for c in result.validation_results
                if not c["passed"] and "entity_type_compliance" in c["check"]
            ]
            assert len(compliance_fails) >= 1


# =========================================================================
# RunResult dataclass
# =========================================================================


class TestRunResult:
    def test_defaults(self):
        r = RunResult()
        assert r.ok is False
        assert r.recommendation is None
        assert r.validation_results == []
        assert r.error is None
