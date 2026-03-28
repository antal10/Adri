"""MATLAB vibration adapter — file-in/file-out contract with MATLAB CLI backend.

Defines the canonical file-based contract for single-channel vibration
CSV analysis through a MATLAB adapter boundary:

  Input:  request.json + vibration.csv  (placed by Adri core)
  Output: features.json, raw_output.mat, spectrum.png, run_log.txt

Execution backends:
  "matlab"          — MATLAB CLI batch execution (matlab -batch).
                      Used when ``matlab`` is found on PATH.
  "numpy_fallback"  — Pure Python/NumPy computation.
                      Used when MATLAB is absent (development / CI).

Every response and persisted artifact records which backend produced
it via the ``backend`` field. Consumers must not assume MATLAB
execution unless ``backend == "matlab"``.

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
import subprocess
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Default backend identifier when MATLAB is absent.
BACKEND = "numpy_fallback"

# MATLAB CLI invocation timeout in seconds.
_MATLAB_TIMEOUT_S = 120


def _resolve_backend() -> str:
    """Return the active backend identifier.

    Returns "matlab" if MATLAB is found on PATH, otherwise "numpy_fallback".
    """
    if shutil.which("matlab") is not None:
        return "matlab"
    return BACKEND


# --- Registration manifest (adapter contract §1) ---

REGISTRATION: dict[str, Any] = {
    "adapter_id": "matlab_vibration",
    "adapter_version": "0.2.0",
    "tool_name": "MATLAB",
    "tool_version": None,
    "capabilities": [
        {
            "operation_id": "analyze_vibration_csv",
            "description": (
                "Analyze a single-channel vibration CSV via file-based "
                "contract. Uses MATLAB CLI backend when matlab is on PATH; "
                "falls back to NumPy otherwise. Backend is recorded in all outputs."
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
    ``backend`` reflects the actual execution backend (same as _resolve_backend()).
    """
    matlab_on_path = shutil.which("matlab") is not None
    backend = _resolve_backend()
    return {
        "adapter_id": REGISTRATION["adapter_id"],
        "status": "healthy" if matlab_on_path else "degraded",
        "tool_reachable": matlab_on_path,
        "backend": backend,
        "message": (
            f"MATLAB found on PATH. Active backend: {backend}."
            if matlab_on_path
            else f"MATLAB not on PATH. Active backend: {backend}."
        ),
    }


# --- Invocation: analyze_vibration_csv ---


def analyze_vibration_csv(request: dict[str, Any]) -> dict[str, Any]:
    """Execute the file-in/file-out vibration analysis contract.

    Steps:
    1. Validate request and inputs.
    2. Set up run directory with request.json and copy of vibration.csv.
    3. Parse CSV → validate format and extract time/accel arrays.
    4. Branch on backend:
       - "matlab": invoke analyze_vibration.m via MATLAB CLI batch mode.
       - "numpy_fallback": compute FFT features in Python.
    5. Write output artifacts (features.json, raw_output.mat, spectrum.png,
       run_log.txt) — by MATLAB or Python depending on backend.
    6. Return adapter response with entity stubs.
    """
    invocation_id = request.get("invocation_id", "")
    operation_id = request.get("operation_id", "")
    inputs = request.get("inputs", {})
    log_lines: list[str] = []
    t0 = time.monotonic()

    def _log(msg: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        log_lines.append(f"[{ts}] {msg}")

    backend = _resolve_backend()
    _log(f"Invocation {invocation_id} started. Backend: {backend}.")

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
        "backend": backend,
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

    # --- Parse CSV (always Python, for format validation and basic metadata) ---
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

    dt = np.median(np.diff(time_s))
    sample_rate = 1.0 / dt
    duration_s = float(time_s[-1] - time_s[0]) + dt

    # --- Branch on backend ---
    artifacts_written: list[str] = ["request.json", "vibration.csv"]
    features: dict[str, Any]

    if backend == "matlab":
        # Invoke MATLAB CLI. MATLAB writes features.json, raw_output.mat,
        # spectrum.png, and run_log.txt into run_dir.
        try:
            features = _run_matlab_analysis(run_dir, log_lines)
        except Exception as exc:
            _log(f"MATLAB execution failed: {exc}")
            _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
            return _error_response(
                invocation_id, "TOOL_EXECUTION_ERROR",
                f"MATLAB analysis failed: {exc}", False,
            )

        # Append Python orchestration log to MATLAB's run_log.txt.
        elapsed = time.monotonic() - t0
        _log(f"Invocation completed in {elapsed:.3f}s.")
        log_path = os.path.join(run_dir, "run_log.txt")
        if os.path.isfile(log_path):
            with open(log_path, "a") as f:
                f.write("\n--- Python orchestration log ---\n")
                f.write("\n".join(log_lines) + "\n")
        else:
            _write_log(log_path, log_lines)

        for fname in ("features.json", "raw_output.mat", "spectrum.png", "run_log.txt"):
            if os.path.isfile(os.path.join(run_dir, fname)):
                artifacts_written.append(fname)

    else:
        # NumPy fallback: Python computes features and writes all output artifacts.
        rms = float(np.sqrt(np.mean(accel ** 2)))

        n = len(accel)
        fft_vals = np.fft.rfft(accel)
        fft_mag = (2.0 / n) * np.abs(fft_vals)
        freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)
        fft_mag[0] = 0.0  # skip DC
        freq_resolution = float(sample_rate / n)

        peaks_hz, peaks_mag = _find_spectral_peaks(freqs, fft_mag)

        features = {
            "sample_rate_hz": float(sample_rate),
            "duration_s": float(duration_s),
            "rms": rms,
            "dominant_peak_frequencies_hz": peaks_hz,
            "dominant_peak_magnitudes": peaks_mag,
            "frequency_resolution_hz": freq_resolution,
            "backend": backend,
        }

        _log(f"Computed features: {len(peaks_hz)} peaks, RMS={rms:.6f}.")

        _write_json(os.path.join(run_dir, "features.json"), features)
        artifacts_written.append("features.json")
        _log("Wrote features.json.")

        _write_minimal_mat(
            os.path.join(run_dir, "raw_output.mat"),
            {"accel": accel, "freqs": freqs, "fft_mag": fft_mag},
            backend=backend,
        )
        artifacts_written.append("raw_output.mat")
        _log(f"Wrote raw_output.mat (produced by {backend}).")

        try:
            _write_spectrum_png(
                os.path.join(run_dir, "spectrum.png"),
                freqs, fft_mag, peaks_hz,
            )
            artifacts_written.append("spectrum.png")
            _log("Wrote spectrum.png.")
        except Exception as exc:
            _log(f"spectrum.png skipped (headless export failed): {exc}")

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
            "backend": backend,
        },
        "entities_created": [signal_entity],
        "duration_ms": int((time.monotonic() - t0) * 1000),
    }


# =========================================================================
# Internal helpers
# =========================================================================


def _run_matlab_analysis(run_dir: str, log_lines: list[str]) -> dict[str, Any]:
    """Invoke MATLAB CLI to run analyze_vibration.m in run_dir.

    Expects analyze_vibration.m to reside in the same directory as this module.
    After MATLAB exits cleanly, reads and returns the features dict from
    features.json written by the script.

    Raises RuntimeError on non-zero exit, timeout, or missing features.json.

    Note: run_dir must not contain single-quote characters. Standard
    tempfile.mkdtemp() paths are safe.
    """
    adapter_dir = os.path.dirname(os.path.abspath(__file__))
    m_script = os.path.join(adapter_dir, "analyze_vibration.m")

    if not os.path.isfile(m_script):
        raise RuntimeError(f"MATLAB script not found: {m_script}")

    def _ts() -> str:
        return datetime.now(timezone.utc).isoformat()

    batch_cmd = f"addpath('{adapter_dir}'); analyze_vibration('{run_dir}')"
    cmd = ["matlab", "-batch", batch_cmd]

    log_lines.append(f"[{_ts()}] Invoking MATLAB CLI batch mode.")
    logger.debug("MATLAB cmd: %s", cmd)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_MATLAB_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"MATLAB analysis timed out after {_MATLAB_TIMEOUT_S}s."
        )

    if result.stdout:
        log_lines.append(f"[{_ts()}] MATLAB stdout: {result.stdout.strip()[:500]}")
    if result.stderr:
        log_lines.append(f"[{_ts()}] MATLAB stderr: {result.stderr.strip()[:500]}")

    if result.returncode != 0:
        raise RuntimeError(
            f"MATLAB exited with code {result.returncode}. "
            f"stderr: {result.stderr.strip()[:200]}"
        )

    log_lines.append(f"[{_ts()}] MATLAB exited cleanly (code 0).")

    features_path = os.path.join(run_dir, "features.json")
    if not os.path.isfile(features_path):
        raise RuntimeError("MATLAB completed but features.json was not written.")

    with open(features_path) as f:
        features: dict[str, Any] = json.load(f)

    # Normalize MATLAB JSON output: older MATLAB versions may encode
    # empty arrays as null and single-element arrays as scalars.
    for key in ("dominant_peak_frequencies_hz", "dominant_peak_magnitudes"):
        val = features.get(key)
        if val is None:
            features[key] = []
        elif not isinstance(val, list):
            features[key] = [float(val)]

    log_lines.append(
        f"[{_ts()}] Features loaded from features.json: "
        f"{len(features.get('dominant_peak_frequencies_hz', []))} peak(s)."
    )
    return features


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


def _write_minimal_mat(
    path: str, arrays: dict[str, np.ndarray], backend: str = "numpy_fallback",
) -> None:
    """Write a minimal MATLAB Level 5 MAT-file.

    Produces a valid .mat header + miMATRIX elements for each array.
    This avoids a scipy dependency while producing a file MATLAB can
    read via ``load('raw_output.mat')``. The header text records which
    backend produced the file.
    """
    header_text = f"MATLAB 5.0 MAT-file, Adri matlab_vibration adapter, backend={backend}"
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
    MI_MATRIX = 14
    MI_UINT32 = 5
    MI_INT32 = 5
    MI_DOUBLE = 9
    MI_INT8 = 1

    mxDOUBLE_CLASS = 6
    flags_bytes = struct.pack("<II", mxDOUBLE_CLASS, 0)
    flags_sub = struct.pack("<II", MI_UINT32, 8) + flags_bytes

    if arr.ndim == 1:
        dims = (1, arr.shape[0])
    else:
        dims = arr.shape
    dims_data = struct.pack(f"<{len(dims)}i", *dims)
    dims_pad = _pad8(dims_data)
    dims_sub = struct.pack("<II", MI_INT32, len(dims_data)) + dims_pad

    name_data = name.encode("ascii")
    name_pad = _pad8(name_data)
    name_sub = struct.pack("<II", MI_INT8, len(name_data)) + name_pad

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
