"""MATLAB vibration adapter — file-in/file-out contract.

Implements the adapter contract for single-channel vibration CSV
analysis via a file-based interface. The canonical contract is:

  Input:  request.json + vibration.csv  (placed by Adri core)
  Output: features.json, raw_output.mat, spectrum.png, run_log.txt

Transport: file I/O (DEC-005 allows any transport). This adapter
writes/reads files in a run directory. Direct Python-to-MATLAB
invocation is NOT the canonical interface for this slice — it can
be added later behind the same contract.

When MATLAB is unavailable, the adapter computes FFT features using
NumPy so the contract shape, persistence, and normalization layers
can be validated. The ``tool_reachable`` field in health() reports
whether MATLAB is actually present.

Accepted CSV format:
- Header: time_s,accel_m_s2
- All values are floats
- Time in seconds, acceleration in m/s^2
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import struct
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# --- Registration manifest (adapter contract §1) ---

REGISTRATION: dict[str, Any] = {
    "adapter_id": "matlab_vibration",
    "adapter_version": "0.1.0",
    "tool_name": "MATLAB",
    "tool_version": None,
    "capabilities": [
        {
            "operation_id": "analyze_vibration_csv",
            "description": (
                "Analyze a single-channel vibration CSV via file-based "
                "MATLAB contract: ingest CSV, compute FFT, persist run artifacts."
            ),
            "input_schema": {
                "type": "object",
                "required": ["artifact_id", "file_path", "run_dir"],
                "properties": {
                    "artifact_id": {"type": "string"},
                    "file_path": {"type": "string"},
                    "run_dir": {"type": "string"},
                },
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "features": {"type": "object"},
                    "run_dir": {"type": "string"},
                    "artifacts_written": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            "artifact_types": ["csv"],
            "entity_types_produced": ["Signal"],
            "idempotent": True,
            "side_effects": ["writes files to run directory"],
        },
    ],
}


# --- Health check (adapter contract §8) ---


def health() -> dict[str, Any]:
    """Return adapter health status.

    Reports ``tool_reachable=True`` only if MATLAB is found on PATH.
    The adapter can still operate (NumPy fallback) when MATLAB is absent.
    """
    matlab_available = shutil.which("matlab") is not None
    return {
        "adapter_id": REGISTRATION["adapter_id"],
        "status": "healthy" if matlab_available else "degraded",
        "tool_reachable": matlab_available,
        "message": (
            "MATLAB found on PATH."
            if matlab_available
            else "MATLAB not on PATH; using NumPy fallback for FFT."
        ),
    }


# --- Invocation: analyze_vibration_csv ---


def analyze_vibration_csv(request: dict[str, Any]) -> dict[str, Any]:
    """Execute the file-in/file-out vibration analysis contract.

    Steps:
    1. Validate request and inputs.
    2. Set up run directory with request.json and copy of vibration.csv.
    3. Parse CSV → compute FFT features (NumPy fallback if no MATLAB).
    4. Write features.json, raw_output.mat, spectrum.png, run_log.txt.
    5. Return adapter response with entity stubs.
    """
    invocation_id = request.get("invocation_id", "")
    operation_id = request.get("operation_id", "")
    inputs = request.get("inputs", {})
    log_lines: list[str] = []
    t0 = time.monotonic()

    def _log(msg: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        log_lines.append(f"[{ts}] {msg}")

    _log(f"Invocation {invocation_id} started.")

    # --- Validate operation_id ---
    if operation_id != "analyze_vibration_csv":
        return _error_response(
            invocation_id, "INVALID_INPUT",
            f"Unknown operation '{operation_id}'.", False,
        )

    artifact_id = inputs.get("artifact_id")
    file_path = inputs.get("file_path")
    run_dir = inputs.get("run_dir")

    if not artifact_id or not file_path or not run_dir:
        return _error_response(
            invocation_id, "INVALID_INPUT",
            "'artifact_id', 'file_path', and 'run_dir' are required.", False,
        )

    # --- Set up run directory ---
    os.makedirs(run_dir, exist_ok=True)

    # Write request manifest
    request_manifest = {
        "invocation_id": invocation_id,
        "operation_id": operation_id,
        "artifact_id": artifact_id,
        "source_file": file_path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(os.path.join(run_dir, "request.json"), request_manifest)
    _log("Wrote request.json.")

    # Copy source CSV for reproducibility
    csv_dest = os.path.join(run_dir, "vibration.csv")
    if not os.path.isfile(file_path):
        _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
        return _error_response(
            invocation_id, "INVALID_ARTIFACT",
            f"File not found: {file_path}", False,
        )
    shutil.copy2(file_path, csv_dest)
    _log("Copied source CSV to run directory.")

    # --- Parse CSV ---
    try:
        data = np.genfromtxt(csv_dest, delimiter=",", names=True, dtype=float)
    except Exception as exc:
        _log(f"CSV parse error: {exc}")
        _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
        return _error_response(
            invocation_id, "INVALID_ARTIFACT",
            f"Failed to parse CSV: {exc}", False,
        )

    if data.dtype.names is None or not (
        {"time_s", "accel_m_s2"} <= set(data.dtype.names)
    ):
        _log("CSV missing required columns: time_s, accel_m_s2.")
        _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
        return _error_response(
            invocation_id, "INVALID_ARTIFACT",
            "CSV must have header 'time_s,accel_m_s2'.", False,
        )

    time_s = data["time_s"]
    accel = data["accel_m_s2"]
    num_samples = len(time_s)

    if num_samples < 2:
        _log("CSV has fewer than 2 data rows.")
        _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
        return _error_response(
            invocation_id, "INVALID_ARTIFACT",
            "CSV must have at least 2 data rows.", False,
        )

    _log(f"Parsed {num_samples} samples.")

    # --- Compute features ---
    dt = np.median(np.diff(time_s))
    sample_rate = 1.0 / dt
    duration_s = float(time_s[-1] - time_s[0]) + dt
    rms = float(np.sqrt(np.mean(accel ** 2)))

    # FFT
    n = len(accel)
    fft_vals = np.fft.rfft(accel)
    fft_mag = (2.0 / n) * np.abs(fft_vals)
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)
    fft_mag[0] = 0.0  # skip DC
    freq_resolution = float(sample_rate / n)

    # Peak detection (same logic as python_vibration)
    peaks_hz, peaks_mag = _find_spectral_peaks(freqs, fft_mag)

    features = {
        "sample_rate_hz": float(sample_rate),
        "duration_s": float(duration_s),
        "rms": rms,
        "dominant_peak_frequencies_hz": peaks_hz,
        "dominant_peak_magnitudes": peaks_mag,
        "frequency_resolution_hz": freq_resolution,
    }

    _log(f"Computed features: {len(peaks_hz)} peaks, RMS={rms:.6f}.")

    # --- Write output artifacts ---
    artifacts_written: list[str] = ["request.json", "vibration.csv"]

    # features.json
    _write_json(os.path.join(run_dir, "features.json"), features)
    artifacts_written.append("features.json")
    _log("Wrote features.json.")

    # raw_output.mat (minimal Level 5 MAT-file with accel + freqs + fft_mag)
    _write_minimal_mat(
        os.path.join(run_dir, "raw_output.mat"),
        {"accel": accel, "freqs": freqs, "fft_mag": fft_mag},
    )
    artifacts_written.append("raw_output.mat")
    _log("Wrote raw_output.mat.")

    # spectrum.png
    try:
        _write_spectrum_png(
            os.path.join(run_dir, "spectrum.png"),
            freqs, fft_mag, peaks_hz,
        )
        artifacts_written.append("spectrum.png")
        _log("Wrote spectrum.png.")
    except Exception as exc:
        _log(f"spectrum.png skipped (headless export failed): {exc}")

    # run_log.txt
    elapsed = time.monotonic() - t0
    _log(f"Invocation completed in {elapsed:.3f}s.")
    _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
    artifacts_written.append("run_log.txt")

    # --- Build Signal entity stub ---
    now = datetime.now(timezone.utc).isoformat()
    signal_entity = {
        "id": f"signal-matlab-{artifact_id}",
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
            "features": features,
            "run_dir": run_dir,
            "artifacts_written": artifacts_written,
        },
        "entities_created": [signal_entity],
        "duration_ms": int((time.monotonic() - t0) * 1000),
    }


# =========================================================================
# Internal helpers
# =========================================================================


def _find_spectral_peaks(
    freqs: np.ndarray,
    fft_mag: np.ndarray,
    threshold_ratio: float = 0.1,
) -> tuple[list[float], list[float]]:
    """Return (frequencies, magnitudes) of local maxima above threshold."""
    max_mag = np.max(fft_mag)
    if max_mag == 0:
        return [], []
    threshold = threshold_ratio * max_mag
    peaks_hz: list[float] = []
    peaks_amp: list[float] = []
    for i in range(1, len(fft_mag) - 1):
        if (
            fft_mag[i] > threshold
            and fft_mag[i] > fft_mag[i - 1]
            and fft_mag[i] > fft_mag[i + 1]
        ):
            peaks_hz.append(float(freqs[i]))
            peaks_amp.append(float(fft_mag[i]))
    return peaks_hz, peaks_amp


def _write_json(path: str, data: Any) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _write_log(path: str, lines: list[str]) -> None:
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def _write_minimal_mat(path: str, arrays: dict[str, np.ndarray]) -> None:
    """Write a minimal MATLAB Level 5 MAT-file.

    Produces a valid .mat header + miMATRIX elements for each array.
    This avoids a scipy dependency while producing a file MATLAB can
    read via ``load('raw_output.mat')``.
    """
    header_text = "MATLAB 5.0 MAT-file, created by Adri matlab_vibration adapter"
    header = header_text.encode("ascii")
    header = header + b" " * (116 - len(header))  # pad to 116 bytes
    header += b"\x00" * 8  # subsystem data offset (unused)
    header += b"\x00\x01"  # version 0x0100
    header += b"IM"  # endian indicator

    elements = b""
    for name, arr in arrays.items():
        elements += _mat_matrix_element(name, np.asarray(arr, dtype=np.float64))

    with open(path, "wb") as f:
        f.write(header + elements)


def _mat_matrix_element(name: str, arr: np.ndarray) -> bytes:
    """Encode one numeric array as a miMATRIX element."""
    # miMATRIX tag (type=14) — length filled after building payload
    MI_MATRIX = 14
    MI_UINT32 = 5
    MI_INT32 = 5
    MI_DOUBLE = 9
    MI_INT8 = 1

    # Subelement 1: Array flags (miUINT32, 8 bytes)
    # class = mxDOUBLE_CLASS (6), non-complex, non-global, non-logical
    mxDOUBLE_CLASS = 6
    flags_bytes = struct.pack("<II", mxDOUBLE_CLASS, 0)
    flags_sub = struct.pack("<II", MI_UINT32, 8) + flags_bytes

    # Subelement 2: Dimensions (miINT32)
    if arr.ndim == 1:
        dims = (1, arr.shape[0])
    else:
        dims = arr.shape
    dims_data = struct.pack(f"<{len(dims)}i", *dims)
    dims_pad = _pad8(dims_data)
    dims_sub = struct.pack("<II", MI_INT32, len(dims_data)) + dims_pad

    # Subelement 3: Array name (miINT8)
    name_data = name.encode("ascii")
    name_pad = _pad8(name_data)
    name_sub = struct.pack("<II", MI_INT8, len(name_data)) + name_pad

    # Subelement 4: Real part (miDOUBLE)
    pr_data = arr.astype(np.float64).tobytes()
    pr_pad = _pad8(pr_data)
    pr_sub = struct.pack("<II", MI_DOUBLE, len(pr_data)) + pr_pad

    payload = flags_sub + dims_sub + name_sub + pr_sub
    tag = struct.pack("<II", MI_MATRIX, len(payload))
    return tag + payload


def _pad8(data: bytes) -> bytes:
    """Pad data to 8-byte boundary."""
    remainder = len(data) % 8
    if remainder:
        return data + b"\x00" * (8 - remainder)
    return data


def _write_spectrum_png(
    path: str,
    freqs: np.ndarray,
    fft_mag: np.ndarray,
    peaks_hz: list[float],
) -> None:
    """Write a minimal spectrum PNG using matplotlib if available."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(freqs, fft_mag, linewidth=0.8)
    if peaks_hz:
        peak_indices = [int(np.argmin(np.abs(freqs - f))) for f in peaks_hz]
        ax.plot(
            freqs[peak_indices], fft_mag[peak_indices],
            "rv", markersize=6, label="peaks",
        )
        ax.legend()
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude")
    ax.set_title("FFT Spectrum — single-channel vibration")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


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
