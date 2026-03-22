"""Python vibration adapter — bootstrap slice.

Implements the adapter contract for ingesting single-channel vibration
CSV files. Transport: direct function call (DEC-005).

Accepted CSV format:
- Columns: time_s, accel_m_s2
- Header row required
- All values are floats
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np


# --- Registration manifest (adapter contract §1) ---

REGISTRATION = {
    "adapter_id": "python_vibration",
    "adapter_version": "0.1.0",
    "tool_name": "Python (NumPy)",
    "tool_version": None,
    "capabilities": [
        {
            "operation_id": "ingest_vibration_csv",
            "description": (
                "Ingest a single-channel vibration CSV and compute FFT spectral peaks."
            ),
            "input_schema": {
                "type": "object",
                "required": ["artifact_id", "file_path"],
                "properties": {
                    "artifact_id": {"type": "string"},
                    "file_path": {"type": "string"},
                },
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "sample_rate": {"type": "number"},
                    "duration_s": {"type": "number"},
                    "num_samples": {"type": "integer"},
                    "peaks_hz": {"type": "array", "items": {"type": "number"}},
                    "peaks_amplitude": {"type": "array", "items": {"type": "number"}},
                },
            },
            "artifact_types": ["csv"],
            "entity_types_produced": ["Signal"],
            "idempotent": True,
            "side_effects": [],
        },
    ],
}


# --- Health check (adapter contract §8) ---


def health() -> dict[str, Any]:
    """Return adapter health status."""
    try:
        import numpy as np  # noqa: F811

        tool_reachable = True
        status = "healthy"
        message = f"NumPy {np.__version__} available."
    except ImportError:
        tool_reachable = False
        status = "unavailable"
        message = "NumPy is not installed."

    return {
        "adapter_id": REGISTRATION["adapter_id"],
        "status": status,
        "tool_reachable": tool_reachable,
        "message": message,
    }


# --- Invocation: ingest_vibration_csv ---


def ingest_vibration_csv(request: dict[str, Any]) -> dict[str, Any]:
    """Ingest a single-channel vibration CSV.

    Request must conform to the adapter contract invocation protocol (§3).
    Returns a response with Signal entity stub and spectral peak data.
    """
    invocation_id = request.get("invocation_id", "")
    operation_id = request.get("operation_id", "")
    inputs = request.get("inputs", {})

    # Validate operation_id
    if operation_id != "ingest_vibration_csv":
        return _error_response(
            invocation_id,
            code="INVALID_INPUT",
            message=f"Unknown operation '{operation_id}'.",
            recoverable=False,
        )

    artifact_id = inputs.get("artifact_id")
    file_path = inputs.get("file_path")

    if not artifact_id or not file_path:
        return _error_response(
            invocation_id,
            code="INVALID_INPUT",
            message="Both 'artifact_id' and 'file_path' are required in inputs.",
            recoverable=False,
        )

    # Read and parse CSV
    try:
        data = np.genfromtxt(
            file_path, delimiter=",", names=True, dtype=float
        )
    except Exception as exc:
        return _error_response(
            invocation_id,
            code="INVALID_ARTIFACT",
            message=f"Failed to parse CSV: {exc}",
            recoverable=False,
        )

    # Validate expected columns
    if data.dtype.names is None or not (
        {"time_s", "accel_m_s2"} <= set(data.dtype.names)
    ):
        return _error_response(
            invocation_id,
            code="INVALID_ARTIFACT",
            message="CSV must have columns 'time_s' and 'accel_m_s2'.",
            recoverable=False,
        )

    time_s = data["time_s"]
    accel = data["accel_m_s2"]
    num_samples = len(time_s)

    if num_samples < 2:
        return _error_response(
            invocation_id,
            code="INVALID_ARTIFACT",
            message="CSV must have at least 2 data rows.",
            recoverable=False,
        )

    # Compute sample rate from time column
    dt = np.median(np.diff(time_s))
    sample_rate = 1.0 / dt
    duration_s = float(time_s[-1] - time_s[0]) + dt

    # FFT and peak detection
    peaks_hz, peaks_amplitude = _find_spectral_peaks(accel, sample_rate)

    # Build Signal entity stub (domain: "time" — the CSV is a time-series)
    now = datetime.now(timezone.utc).isoformat()
    signal_entity = {
        "id": f"signal-accel-{artifact_id}",
        "type": "Signal",
        "name": "acceleration-channel-0",
        "source_adapter": REGISTRATION["adapter_id"],
        "source_artifact": artifact_id,
        "created_at": now,
        "domain": "time",
        "sample_rate": float(sample_rate),
        "bandwidth": float(sample_rate / 2.0),
        "unit": "m/s²",
    }

    return {
        "invocation_id": invocation_id,
        "status": "success",
        "outputs": {
            "sample_rate": float(sample_rate),
            "duration_s": float(duration_s),
            "num_samples": int(num_samples),
            "peaks_hz": [float(f) for f in peaks_hz],
            "peaks_amplitude": [float(a) for a in peaks_amplitude],
        },
        "entities_created": [signal_entity],
    }


def _find_spectral_peaks(
    signal: np.ndarray, sample_rate: float, threshold_ratio: float = 0.1
) -> tuple[list[float], list[float]]:
    """Compute FFT and return frequencies/amplitudes of peaks above threshold.

    Threshold is relative to the maximum amplitude in the spectrum.
    """
    n = len(signal)
    fft_vals = np.fft.rfft(signal)
    fft_mag = (2.0 / n) * np.abs(fft_vals)
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)

    # Skip DC component
    fft_mag[0] = 0.0

    max_mag = np.max(fft_mag)
    if max_mag == 0:
        return [], []

    threshold = threshold_ratio * max_mag

    # Find local maxima above threshold
    peaks_hz = []
    peaks_amplitude = []
    for i in range(1, len(fft_mag) - 1):
        if (
            fft_mag[i] > threshold
            and fft_mag[i] > fft_mag[i - 1]
            and fft_mag[i] > fft_mag[i + 1]
        ):
            peaks_hz.append(float(freqs[i]))
            peaks_amplitude.append(float(fft_mag[i]))

    return peaks_hz, peaks_amplitude


def _error_response(
    invocation_id: str,
    code: str,
    message: str,
    recoverable: bool,
) -> dict[str, Any]:
    """Build a contract-compliant error response."""
    return {
        "invocation_id": invocation_id,
        "status": "error",
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
        },
    }
