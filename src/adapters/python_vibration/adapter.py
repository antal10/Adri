"""Python vibration adapter — data pipeline only.

Implements the adapter contract for ingesting single-channel vibration
CSV files. Role: data pipeline — ingest, validate format, return a raw
time-series Signal entity with basic metadata.

Python does NOT perform signal analysis (FFT, peak detection, filtering).
Those operations belong to MATLAB. See CLAUDE.md tool ownership and
AGENTS.md constraint #8.

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
    "adapter_version": "0.2.0",
    "tool_name": "Python (NumPy)",
    "tool_version": None,
    "capabilities": [
        {
            "operation_id": "ingest_vibration_csv",
            "description": (
                "Ingest a single-channel vibration CSV and return a raw "
                "time-series Signal entity with basic metadata."
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
    Returns a Signal entity with basic metadata. Does not perform signal
    analysis — FFT and peak detection belong to MATLAB (CLAUDE.md tool
    ownership; AGENTS.md constraint #8).
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

    # Compute sample rate and duration from time column
    dt = np.median(np.diff(time_s))
    sample_rate = 1.0 / dt
    duration_s = float(time_s[-1] - time_s[0]) + dt

    # Build Signal entity (domain: "time" — the CSV is a time-series)
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
        },
        "entities_created": [signal_entity],
    }


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
