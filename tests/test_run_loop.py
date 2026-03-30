"""Tests for the run_loop orchestrator."""

from __future__ import annotations

from unittest import mock

import numpy as np
import pytest

import run_loop as run_loop_module
from run_loop import AdapterBinding, RunResult, run


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


def _max_peak_constraint(bound_value: float) -> dict[str, object]:
    return {
        "constraint_id": "c-max-peak",
        "name": "Max peak frequency",
        "bound_type": "upper",
        "bound_value": bound_value,
        "unit": "Hz",
    }


@pytest.fixture
def csv_path(tmp_path):
    """Create a temp vibration CSV and return its path."""
    path = str(tmp_path / "vibration.csv")
    _write_vibration_csv(path, freq_hz=80.0)
    return path


@pytest.fixture
def run_dir(tmp_path):
    """Create a per-run directory path for matlab_vibration."""
    return str(tmp_path / "run_001")


class TestHappyPath:
    def test_run_succeeds(self, csv_path):
        result = run(csv_path)
        assert result.ok
        assert result.error is None
        assert result.recommendation is not None

    def test_recommendation_has_verdict(self, csv_path):
        result = run(csv_path)
        assert result.recommendation["verdict"] in (
            "recommended",
            "insufficient_data",
        )

    def test_all_validations_passed(self, csv_path):
        result = run(csv_path)
        for check in result.validation_results:
            assert check["passed"], f"Failed: {check}"

    def test_custom_artifact_and_invocation_ids(self, csv_path):
        result = run(csv_path, artifact_id="my-artifact", invocation_id="my-inv")
        assert result.ok
        assert "my-artifact" in result.recommendation["trace"]

    def test_matlab_adapter_succeeds(self, csv_path, run_dir):
        result = run(
            csv_path,
            artifact_id="matlab-artifact",
            invocation_id="matlab-inv",
            adapter_id="matlab_vibration",
            run_dir=run_dir,
        )
        assert result.ok, result.error
        assert "matlab-artifact" in result.recommendation["trace"]
        assert any(
            trace_id.startswith("signal-matlab-")
            for trace_id in result.recommendation["trace"]
        )


class TestSignalConstraints:
    def test_constraint_results_record_pass(self, csv_path):
        result = run(
            csv_path,
            signal_constraints=[_max_peak_constraint(500.0)],
        )
        assert result.ok, result.error
        assert len(result.constraint_results) == 1
        assert result.constraint_results[0].passed is True
        assert result.recommendation["verdict"] == "recommended"
        assert "c-max-peak" in result.recommendation["trace"]
        assert any(
            item["source"] == "c-max-peak"
            for item in result.recommendation["evidence"]
        )

    def test_constraint_violation_changes_verdict(self, csv_path):
        result = run(
            csv_path,
            signal_constraints=[_max_peak_constraint(50.0)],
        )
        assert result.ok, result.error
        assert len(result.constraint_results) == 1
        assert result.constraint_results[0].passed is False
        assert result.recommendation["verdict"] == "not_recommended"

    def test_constraints_skipped_when_no_peaks(self, tmp_path):
        path = str(tmp_path / "noise.csv")
        with open(path, "w") as f:
            f.write("time_s,accel_m_s2\n0.000000,0.000000\n0.001000,0.000000\n")
        result = run(
            path,
            signal_constraints=[_max_peak_constraint(50.0)],
        )
        assert result.ok, result.error
        assert result.constraint_results == []
        assert result.recommendation["verdict"] == "insufficient_data"


class TestAdapterSelection:
    def test_unknown_adapter_fails(self, csv_path):
        result = run(csv_path, adapter_id="not_real")
        assert not result.ok
        assert "Unsupported adapter" in result.error

    def test_matlab_adapter_requires_run_dir(self, csv_path):
        result = run(csv_path, adapter_id="matlab_vibration")
        assert not result.ok
        assert "requires a run_dir" in result.error


class TestAdapterFailures:
    def test_unavailable_adapter(self, csv_path):
        unavailable_binding = AdapterBinding(
            registration=run_loop_module.PYTHON_REGISTRATION,
            health_fn=lambda: {
                "adapter_id": "python_vibration",
                "status": "unavailable",
                "tool_reachable": False,
                "message": "NumPy gone",
            },
            invoke_fn=run_loop_module.ingest_vibration_csv,
            operation_id="ingest_vibration_csv",
        )
        with mock.patch.dict(
            run_loop_module.ADAPTER_BINDINGS,
            {"python_vibration": unavailable_binding},
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
        error_binding = AdapterBinding(
            registration=run_loop_module.PYTHON_REGISTRATION,
            health_fn=run_loop_module.python_health,
            invoke_fn=lambda request: error_response,
            operation_id="ingest_vibration_csv",
        )
        with mock.patch.dict(
            run_loop_module.ADAPTER_BINDINGS,
            {"python_vibration": error_binding},
        ):
            result = run(csv_path)
        assert not result.ok
        assert "adapter error" in result.error.lower()

    def test_nonexistent_file(self):
        result = run("/nonexistent/path.csv")
        assert not result.ok
        assert result.error is not None


class TestValidationFailures:
    def test_bad_adapter_response_fails_l0(self, csv_path):
        bad_response = {"status": "success"}
        bad_binding = AdapterBinding(
            registration=run_loop_module.PYTHON_REGISTRATION,
            health_fn=run_loop_module.python_health,
            invoke_fn=lambda request: bad_response,
            operation_id="ingest_vibration_csv",
        )
        with mock.patch.dict(
            run_loop_module.ADAPTER_BINDINGS,
            {"python_vibration": bad_binding},
        ):
            result = run(csv_path)
        assert not result.ok
        assert "L0" in result.error

    def test_adapter_producing_wrong_entity_type_flagged(self, csv_path):
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
                    "unit": "m/s^2",
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
        bad_binding = AdapterBinding(
            registration=run_loop_module.PYTHON_REGISTRATION,
            health_fn=run_loop_module.python_health,
            invoke_fn=lambda request: bad_response,
            operation_id="ingest_vibration_csv",
        )
        with mock.patch.dict(
            run_loop_module.ADAPTER_BINDINGS,
            {"python_vibration": bad_binding},
        ):
            result = run(csv_path)
        assert not result.ok
        assert "compliance" in result.error.lower()
        compliance_fails = [
            check
            for check in result.validation_results
            if not check["passed"] and "entity_type_compliance" in check["check"]
        ]
        assert len(compliance_fails) >= 1
        assert result.recommendation is None


class TestRunResult:
    def test_defaults(self):
        result = RunResult()
        assert result.ok is False
        assert result.recommendation is None
        assert result.validation_results == []
        assert result.constraint_results == []
        assert result.error is None
