"""MATLAB vibration adapter - file-in/file-out contract.

Defines the canonical file-based contract for single-channel vibration
CSV analysis through a MATLAB adapter boundary:

  Input:  request.json + vibration.csv  (placed by Adri core)
  Output: features.json, raw_output.mat, spectrum.png, run_log.txt

This module preserves one file contract across two execution backends:
- MATLAB via ``matlab -batch`` when a CLI is configured
- NumPy fallback when MATLAB is unavailable

Every response and persisted artifact records which backend produced
it via the ``backend`` field. Consumers must not assume MATLAB
execution unless ``backend == "matlab"``.

MATLAB executable resolution order:
1. ``inputs["matlab_executable"]``
2. ``ADRI_MATLAB_EXECUTABLE``
3. ``matlab`` on ``PATH``

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

# Backend identifier: "matlab" when real MATLAB executes, "numpy_fallback" now.
BACKEND = "numpy_fallback"
MATLAB_EXECUTABLE_ENV = "ADRI_MATLAB_EXECUTABLE"


def _resolve_matlab_executable(configured: str | None = None) -> str | None:
    """Resolve the MATLAB executable from request, env, or PATH."""
    candidate = configured or os.getenv(MATLAB_EXECUTABLE_ENV)
    if candidate:
        resolved = shutil.which(candidate)
        if resolved is not None:
            return resolved
        if os.path.isfile(candidate):
            return candidate
        return None
    return shutil.which("matlab")


def _resolve_backend(configured: str | None = None) -> str:
    """Return the active backend identifier."""
    return "matlab" if _resolve_matlab_executable(configured) else BACKEND


# --- Registration manifest (adapter contract section 1) ---

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
                "contract. Executes via matlab -batch when configured, "
                "otherwise via the NumPy fallback."
            ),
            "input_schema": {
                "type": "object",
                "required": ["artifact_id", "file_path", "run_dir"],
                "properties": {
                    "artifact_id": {"type": "string"},
                    "file_path": {"type": "string"},
                    "run_dir": {"type": "string"},
                    "matlab_executable": {"type": "string"},
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


# --- Health check (adapter contract section 8) ---


def health() -> dict[str, Any]:
    """Return adapter health status."""
    configured = os.getenv(MATLAB_EXECUTABLE_ENV)
    matlab_executable = _resolve_matlab_executable()
    backend = _resolve_backend()
    return {
        "adapter_id": REGISTRATION["adapter_id"],
        "status": "healthy" if matlab_executable else "degraded",
        "tool_reachable": matlab_executable is not None,
        "backend": backend,
        "message": (
            f"MATLAB CLI resolved to {matlab_executable}. Active backend: {backend}."
            if matlab_executable
            else (
                f"Configured MATLAB executable not found: {configured}. "
                f"Active backend: {backend}."
                if configured
                else (
                    f"MATLAB CLI not configured. Set {MATLAB_EXECUTABLE_ENV} "
                    f"or put matlab on PATH. Active backend: {backend}."
                )
            )
        ),
    }


# --- Invocation: analyze_vibration_csv ---


def analyze_vibration_csv(request: dict[str, Any]) -> dict[str, Any]:
    """Execute the file-in/file-out vibration analysis contract."""
    invocation_id = request.get("invocation_id", "")
    operation_id = request.get("operation_id", "")
    inputs = request.get("inputs", {})
    log_lines: list[str] = []
    t0 = time.monotonic()

    def _log(message: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        log_lines.append(f"[{timestamp}] {message}")

    requested_matlab = inputs.get("matlab_executable")
    matlab_executable = _resolve_matlab_executable(requested_matlab)
    backend = _resolve_backend(requested_matlab)
    _log(f"Invocation {invocation_id} started. Backend: {backend}.")

    if operation_id != "analyze_vibration_csv":
        return _error_response(
            invocation_id,
            "INVALID_INPUT",
            f"Unknown operation '{operation_id}'.",
            False,
        )

    artifact_id = inputs.get("artifact_id")
    file_path = inputs.get("file_path")
    run_dir = inputs.get("run_dir")

    if not artifact_id or not file_path or not run_dir:
        return _error_response(
            invocation_id,
            "INVALID_INPUT",
            "'artifact_id', 'file_path', and 'run_dir' are required.",
            False,
        )

    os.makedirs(run_dir, exist_ok=True)

    request_manifest = {
        "invocation_id": invocation_id,
        "operation_id": operation_id,
        "artifact_id": artifact_id,
        "source_file": file_path,
        "backend": backend,
        "matlab_executable": matlab_executable,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(os.path.join(run_dir, "request.json"), request_manifest)
    _log("Wrote request.json.")

    if requested_matlab and matlab_executable is None:
        _log(f"Configured MATLAB executable not found: {requested_matlab}")
        _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
        return _error_response(
            invocation_id,
            "TOOL_UNAVAILABLE",
            f"Configured MATLAB executable not found: {requested_matlab}",
            False,
        )

    csv_dest = os.path.join(run_dir, "vibration.csv")
    if not os.path.isfile(file_path):
        _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
        return _error_response(
            invocation_id,
            "INVALID_ARTIFACT",
            f"File not found: {file_path}",
            False,
        )
    shutil.copy2(file_path, csv_dest)
    _log("Copied source CSV to run directory.")

    artifacts_written: list[str] = ["request.json", "vibration.csv"]

    if backend == "matlab":
        script_path = os.path.join(os.path.dirname(__file__), "run_analysis.m")
        batch_command = _build_matlab_batch_command(run_dir, script_path)
        _log(f"Running MATLAB batch command: {batch_command}")

        try:
            _run_matlab_batch(
                matlab_executable=matlab_executable,
                batch_command=batch_command,
                cwd=run_dir,
            )
        except subprocess.CalledProcessError as exc:
            _log(f"MATLAB execution failed: {exc}")
            if exc.stdout:
                _log(f"MATLAB stdout: {exc.stdout.strip()}")
            if exc.stderr:
                _log(f"MATLAB stderr: {exc.stderr.strip()}")
            if not os.path.isfile(os.path.join(run_dir, "run_log.txt")):
                _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
            return _error_response(
                invocation_id,
                "INTERNAL",
                "MATLAB execution failed.",
                False,
            )

        required_outputs = (
            "features.json",
            "raw_output.mat",
            "spectrum.png",
            "run_log.txt",
        )
        missing_outputs = [
            name
            for name in required_outputs
            if not os.path.isfile(os.path.join(run_dir, name))
        ]
        if missing_outputs:
            _log(f"MATLAB run missing outputs: {missing_outputs}")
            if not os.path.isfile(os.path.join(run_dir, "run_log.txt")):
                _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
            return _error_response(
                invocation_id,
                "INTERNAL",
                f"MATLAB run did not produce required outputs: {missing_outputs}",
                False,
            )

        with open(os.path.join(run_dir, "features.json")) as file_obj:
            features = json.load(file_obj)
        for key in (
            "dominant_peak_frequencies_hz",
            "dominant_peak_magnitudes",
        ):
            value = features.get(key, [])
            if isinstance(value, list):
                continue
            if value is None:
                features[key] = []
            else:
                features[key] = [float(value)]
        features["backend"] = backend
        _write_json(os.path.join(run_dir, "features.json"), features)
        artifacts_written.extend(required_outputs)
        sample_rate = float(features["sample_rate_hz"])
        _log("Read features.json from MATLAB output.")
    else:
        try:
            data = np.genfromtxt(csv_dest, delimiter=",", names=True, dtype=float)
        except Exception as exc:
            _log(f"CSV parse error: {exc}")
            _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
            return _error_response(
                invocation_id,
                "INVALID_ARTIFACT",
                f"Failed to parse CSV: {exc}",
                False,
            )

        if data.dtype.names is None or not (
            {"time_s", "accel_m_s2"} <= set(data.dtype.names)
        ):
            _log("CSV missing required columns: time_s, accel_m_s2.")
            _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
            return _error_response(
                invocation_id,
                "INVALID_ARTIFACT",
                "CSV must have header 'time_s,accel_m_s2'.",
                False,
            )

        time_s = data["time_s"]
        accel = data["accel_m_s2"]
        num_samples = len(time_s)

        if num_samples < 2:
            _log("CSV has fewer than 2 data rows.")
            _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
            return _error_response(
                invocation_id,
                "INVALID_ARTIFACT",
                "CSV must have at least 2 data rows.",
                False,
            )

        _log(f"Parsed {num_samples} samples.")

        dt = np.median(np.diff(time_s))
        sample_rate = 1.0 / dt
        duration_s = float(time_s[-1] - time_s[0]) + dt
        rms = float(np.sqrt(np.mean(accel ** 2)))

        n = len(accel)
        fft_vals = np.fft.rfft(accel)
        fft_mag = (2.0 / n) * np.abs(fft_vals)
        freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)
        fft_mag[0] = 0.0
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
                freqs,
                fft_mag,
                peaks_hz,
            )
            artifacts_written.append("spectrum.png")
            _log("Wrote spectrum.png.")
        except Exception as exc:
            _log(f"spectrum.png skipped (headless export failed): {exc}")

        elapsed = time.monotonic() - t0
        _log(f"Invocation completed in {elapsed:.3f}s.")
        _write_log(os.path.join(run_dir, "run_log.txt"), log_lines)
        artifacts_written.append("run_log.txt")

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
        "unit": "m/s^2",
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


def _matlab_literal(path: str) -> str:
    """Return a MATLAB-safe single-quoted path literal."""
    return path.replace("\\", "/").replace("'", "''")


def _build_matlab_batch_command(run_dir: str, script_path: str) -> str:
    """Build the deterministic MATLAB -batch command."""
    script_dir = os.path.dirname(script_path)
    script_name = os.path.splitext(os.path.basename(script_path))[0]
    return (
        f"addpath('{_matlab_literal(script_dir)}'); "
        f"cd('{_matlab_literal(run_dir)}'); "
        f"{script_name};"
    )


def _run_matlab_batch(
    matlab_executable: str | None,
    batch_command: str,
    cwd: str,
) -> subprocess.CompletedProcess[str]:
    """Execute the MATLAB CLI for one batch run."""
    if matlab_executable is None:
        raise FileNotFoundError("MATLAB executable was not resolved.")
    return subprocess.run(
        [matlab_executable, "-batch", batch_command],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _write_json(path: str, data: Any) -> None:
    with open(path, "w") as file_obj:
        json.dump(data, file_obj, indent=2, default=str)


def _write_log(path: str, lines: list[str]) -> None:
    with open(path, "w") as file_obj:
        file_obj.write("\n".join(lines) + "\n")


def _write_minimal_mat(
    path: str,
    arrays: dict[str, np.ndarray],
    backend: str = "numpy_fallback",
) -> None:
    """Write a minimal MATLAB Level 5 MAT-file."""
    header_text = (
        "MATLAB 5.0 MAT-file, Adri matlab_vibration adapter, "
        f"backend={backend}"
    )
    header = header_text.encode("ascii")
    header = header + b" " * (116 - len(header))
    header += b"\x00" * 8
    header += b"\x00\x01"
    header += b"IM"

    elements = b""
    for name, arr in arrays.items():
        elements += _mat_matrix_element(name, np.asarray(arr, dtype=np.float64))

    with open(path, "wb") as file_obj:
        file_obj.write(header + elements)


def _mat_matrix_element(name: str, arr: np.ndarray) -> bytes:
    """Encode one numeric array as a miMATRIX element."""
    mi_matrix = 14
    mi_uint32 = 5
    mi_int32 = 5
    mi_double = 9
    mi_int8 = 1
    mx_double_class = 6

    flags_bytes = struct.pack("<II", mx_double_class, 0)
    flags_sub = struct.pack("<II", mi_uint32, 8) + flags_bytes

    if arr.ndim == 1:
        dims = (1, arr.shape[0])
    else:
        dims = arr.shape
    dims_data = struct.pack(f"<{len(dims)}i", *dims)
    dims_sub = struct.pack("<II", mi_int32, len(dims_data)) + _pad8(dims_data)

    name_data = name.encode("ascii")
    name_sub = struct.pack("<II", mi_int8, len(name_data)) + _pad8(name_data)

    pr_data = arr.astype(np.float64).tobytes()
    pr_sub = struct.pack("<II", mi_double, len(pr_data)) + _pad8(pr_data)

    payload = flags_sub + dims_sub + name_sub + pr_sub
    tag = struct.pack("<II", mi_matrix, len(payload))
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
        peak_indices = [int(np.argmin(np.abs(freqs - frequency))) for frequency in peaks_hz]
        ax.plot(
            freqs[peak_indices],
            fft_mag[peak_indices],
            "rv",
            markersize=6,
            label="peaks",
        )
        ax.legend()
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude")
    ax.set_title("FFT Spectrum - single-channel vibration")
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
