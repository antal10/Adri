"""End-to-end tests for the bootstrap run loop."""

from __future__ import annotations

import os

import numpy as np
import pytest

from run_loop import run


def _write_three_tone_csv(path: str) -> None:
    """Write a 1-second, 1 kHz vibration CSV with three sine tones."""
    sample_rate = 1000.0
    duration_s = 1.0
    n = int(sample_rate * duration_s)
    t = np.linspace(0, duration_s, n, endpoint=False)
    accel = (
        1.0 * np.sin(2 * np.pi * 80 * t)
        + 0.6 * np.sin(2 * np.pi * 200 * t)
        + 0.3 * np.sin(2 * np.pi * 450 * t)
    )
    with open(path, "w") as f:
        f.write("time_s,accel_m_s2\n")
        for ti, ai in zip(t, accel):
            f.write(f"{ti:.6f},{ai:.6f}\n")


def _write_noise_only_csv(path: str) -> None:
    """Write a CSV with a constant-zero signal."""
    sample_rate = 1000.0
    n = 100
    t = np.arange(n) / sample_rate
    accel = np.zeros(n)
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
def three_tone_csv(tmp_path):
    path = str(tmp_path / "three_tone.csv")
    _write_three_tone_csv(path)
    return path


@pytest.fixture
def noise_csv(tmp_path):
    path = str(tmp_path / "noise_only.csv")
    _write_noise_only_csv(path)
    return path


@pytest.fixture
def run_dir(tmp_path):
    return str(tmp_path / "matlab_run")


class TestE2EThreeTonePython:
    """Full loop with the Python vibration adapter."""

    def test_run_succeeds(self, three_tone_csv):
        result = run(three_tone_csv, artifact_id="e2e-artifact-001")
        assert result.ok, result.error

    def test_no_validation_failures(self, three_tone_csv):
        result = run(three_tone_csv, artifact_id="e2e-artifact-001")
        failed = [check for check in result.validation_results if not check["passed"]]
        assert failed == [], failed

    def test_verdict_is_recommended(self, three_tone_csv):
        result = run(three_tone_csv, artifact_id="e2e-artifact-001")
        assert result.recommendation["verdict"] == "recommended"

    def test_evidence_contains_peaks(self, three_tone_csv):
        result = run(three_tone_csv, artifact_id="e2e-artifact-001")
        peaks = result.recommendation["evidence"][0].get("value", [])
        assert len(peaks) >= 3
        assert any(abs(peak - 80.0) < 5.0 for peak in peaks)


class TestE2ENoiseOnlyPython:
    """Noise-only path through the Python vibration adapter."""

    def test_run_succeeds(self, noise_csv):
        result = run(noise_csv, artifact_id="e2e-noise-001")
        assert result.ok, result.error

    def test_verdict_is_insufficient_data(self, noise_csv):
        result = run(noise_csv, artifact_id="e2e-noise-001")
        assert result.recommendation["verdict"] == "insufficient_data"

    def test_confidence_is_low(self, noise_csv):
        result = run(noise_csv, artifact_id="e2e-noise-001")
        assert result.recommendation["confidence"]["level"] == "low"


class TestE2EMatlabFallback:
    """Full loop with the matlab_vibration fallback backend."""

    def test_run_succeeds(self, three_tone_csv, run_dir):
        result = run(
            three_tone_csv,
            artifact_id="e2e-matlab-001",
            invocation_id="e2e-matlab-inv",
            adapter_id="matlab_vibration",
            run_dir=run_dir,
        )
        assert result.ok, result.error

    def test_validation_passes(self, three_tone_csv, run_dir):
        result = run(
            three_tone_csv,
            artifact_id="e2e-matlab-001",
            invocation_id="e2e-matlab-inv",
            adapter_id="matlab_vibration",
            run_dir=run_dir,
        )
        failed = [check for check in result.validation_results if not check["passed"]]
        assert failed == [], failed

    def test_run_artifacts_exist(self, three_tone_csv, run_dir):
        result = run(
            three_tone_csv,
            artifact_id="e2e-matlab-001",
            invocation_id="e2e-matlab-inv",
            adapter_id="matlab_vibration",
            run_dir=run_dir,
        )
        assert result.ok, result.error
        for filename in (
            "request.json",
            "vibration.csv",
            "features.json",
            "raw_output.mat",
            "run_log.txt",
        ):
            assert os.path.isfile(os.path.join(run_dir, filename)), filename


class TestE2EConstraints:
    """Constraint evaluation integrated through the orchestrator."""

    def test_satisfied_constraint_stays_recommended(self, three_tone_csv):
        result = run(
            three_tone_csv,
            artifact_id="e2e-constraint-pass",
            signal_constraints=[_max_peak_constraint(500.0)],
        )
        assert result.ok, result.error
        assert len(result.constraint_results) == 1
        assert result.constraint_results[0].passed is True
        assert result.recommendation["verdict"] == "recommended"
        assert any(
            item["source"] == "c-max-peak"
            for item in result.recommendation["evidence"]
        )

    def test_violated_constraint_becomes_not_recommended(self, three_tone_csv):
        result = run(
            three_tone_csv,
            artifact_id="e2e-constraint-fail",
            signal_constraints=[_max_peak_constraint(100.0)],
        )
        assert result.ok, result.error
        assert len(result.constraint_results) == 1
        assert result.constraint_results[0].passed is False
        assert result.recommendation["verdict"] == "not_recommended"
        assert "c-max-peak" in result.recommendation["trace"]
