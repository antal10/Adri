"""End-to-end test — full bootstrap loop.

Exercises the complete pipeline from synthetic vibration CSV through
adapter ingestion, ontology population, L0/L1 validation, reasoning
stub, and recommendation validation. This is the bootstrap success
criterion: ingest one artifact, produce one validated recommendation.
"""

from __future__ import annotations

import numpy as np
import pytest

from run_loop import run


# --- Synthetic CSV generation ---


def _write_three_tone_csv(path: str) -> None:
    """Write a 1-second, 1 kHz vibration CSV with three sine tones.

    Tones at 80 Hz, 200 Hz, and 450 Hz (matching UC-01 north-star
    example frequencies).
    """
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
    """Write a CSV with a constant-zero signal — guarantees no spectral peaks."""
    sample_rate = 1000.0
    n = 100
    t = np.arange(n) / sample_rate
    accel = np.zeros(n)
    with open(path, "w") as f:
        f.write("time_s,accel_m_s2\n")
        for ti, ai in zip(t, accel):
            f.write(f"{ti:.6f},{ai:.6f}\n")


@pytest.fixture
def three_tone_csv(tmp_path):
    p = str(tmp_path / "three_tone.csv")
    _write_three_tone_csv(p)
    return p


@pytest.fixture
def noise_csv(tmp_path):
    p = str(tmp_path / "noise_only.csv")
    _write_noise_only_csv(p)
    return p


# =========================================================================
# E2E: three-tone signal → recommended
# =========================================================================


class TestE2EThreeTone:
    """Full loop with a three-tone synthetic signal."""

    def test_run_succeeds(self, three_tone_csv):
        result = run(three_tone_csv, artifact_id="e2e-artifact-001")
        assert result.ok, result.error

    def test_no_validation_failures(self, three_tone_csv):
        result = run(three_tone_csv, artifact_id="e2e-artifact-001")
        failed = [c for c in result.validation_results if not c["passed"]]
        assert failed == [], failed

    def test_verdict_is_recommended(self, three_tone_csv):
        result = run(three_tone_csv, artifact_id="e2e-artifact-001")
        assert result.recommendation["verdict"] == "recommended"

    def test_evidence_contains_peaks(self, three_tone_csv):
        result = run(three_tone_csv, artifact_id="e2e-artifact-001")
        peaks = result.recommendation["evidence"][0].get("value", [])
        assert len(peaks) >= 3
        # Dominant peak should be near 80 Hz (tolerance for FFT bin resolution)
        assert any(abs(p - 80.0) < 5.0 for p in peaks), f"No peak near 80 Hz in {peaks}"

    def test_confidence_is_moderate(self, three_tone_csv):
        result = run(three_tone_csv, artifact_id="e2e-artifact-001")
        assert result.recommendation["confidence"]["level"] == "moderate"

    def test_trace_includes_artifact_and_signal(self, three_tone_csv):
        result = run(three_tone_csv, artifact_id="e2e-artifact-001")
        trace = result.recommendation["trace"]
        assert "e2e-artifact-001" in trace
        assert any(t.startswith("signal-") for t in trace)

    def test_recommendation_has_assumptions_and_risks(self, three_tone_csv):
        result = run(three_tone_csv, artifact_id="e2e-artifact-001")
        rec = result.recommendation
        assert len(rec["assumptions"]) >= 1
        assert len(rec["risks"]) >= 1

    def test_recommendation_id_format(self, three_tone_csv):
        result = run(three_tone_csv, artifact_id="e2e-artifact-001")
        assert result.recommendation["id"].startswith("REC-")


# =========================================================================
# E2E: noise-only signal → insufficient_data
# =========================================================================


class TestE2ENoiseOnly:
    """Full loop with noise-only data — exercises insufficient_data path."""

    def test_run_succeeds(self, noise_csv):
        result = run(noise_csv, artifact_id="e2e-noise-001")
        assert result.ok, result.error

    def test_no_validation_failures(self, noise_csv):
        result = run(noise_csv, artifact_id="e2e-noise-001")
        failed = [c for c in result.validation_results if not c["passed"]]
        assert failed == [], failed

    def test_verdict_is_insufficient_data(self, noise_csv):
        result = run(noise_csv, artifact_id="e2e-noise-001")
        assert result.recommendation["verdict"] == "insufficient_data"

    def test_confidence_is_low(self, noise_csv):
        result = run(noise_csv, artifact_id="e2e-noise-001")
        assert result.recommendation["confidence"]["level"] == "low"

    def test_limiting_factor_mentions_peaks(self, noise_csv):
        result = run(noise_csv, artifact_id="e2e-noise-001")
        lf = result.recommendation["confidence"]["limiting_factor"]
        assert "peak" in lf.lower()
