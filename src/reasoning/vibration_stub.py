"""Vibration reasoning stub — bootstrap slice.

Consumes an ontology store containing at least one Signal entity
produced by the python_vibration adapter, plus the adapter response
outputs (peaks_hz, peaks_amplitude). Produces a recommendation dict
conforming to recommendation_schema.md.

This is a deterministic rule-based stub (no LLM). Rules:
- Verdict: "recommended" if >= 1 peak detected, "insufficient_data" if 0.
- Confidence: "moderate" (single-channel, simulation-free).
- Assumptions: stationarity + no cross-axis coupling.
- Risks: mounting alteration + cable noise.
- Trace: artifact -> signal entity IDs used.
"""

from __future__ import annotations

from typing import Any

from adri.ontology_store import OntologyStore


def generate_recommendation(
    store: OntologyStore,
    adapter_outputs: dict[str, Any],
    artifact_id: str,
    signal_id: str,
) -> dict[str, Any]:
    """Build a recommendation from adapter outputs and ontology state.

    Parameters
    ----------
    store : OntologyStore
        Must contain the artifact and signal entities.
    adapter_outputs : dict
        The ``outputs`` dict from the adapter response (keys: peaks_hz,
        peaks_amplitude, sample_rate, duration_s, num_samples).
    artifact_id : str
        Entity ID of the source artifact.
    signal_id : str
        Entity ID of the signal entity created by the adapter.

    Returns
    -------
    dict
        A recommendation conforming to recommendation_schema.md.
    """
    peaks_hz: list[float] = adapter_outputs.get("peaks_hz", [])
    peaks_amplitude: list[float] = adapter_outputs.get("peaks_amplitude", [])
    sample_rate: float = adapter_outputs.get("sample_rate", 0.0)
    num_samples: int = adapter_outputs.get("num_samples", 0)

    # --- Verdict decision ---
    if len(peaks_hz) == 0:
        verdict = "insufficient_data"
        verdict_summary = "No spectral peaks detected; unable to characterize vibration modes."
        confidence_level = "low"
        confidence_rationale = (
            "FFT produced no peaks above threshold. Signal may be noise-only "
            "or measurement duration may be insufficient."
        )
        limiting_factor = "No detectable peaks — cannot identify vibration modes."
    else:
        verdict = "recommended"
        verdict_summary = (
            f"Detected {len(peaks_hz)} spectral peak(s). "
            f"Dominant frequency: {peaks_hz[0]:.1f} Hz."
        )
        confidence_level = "moderate"
        confidence_rationale = (
            "Based on single-channel FFT of measured data. No cross-axis "
            "or modal simulation corroboration."
        )
        limiting_factor = (
            "A-01 (stationarity) — if the signal is non-stationary, peak "
            "frequencies may not represent true modes."
        )

    # --- Evidence ---
    evidence: list[dict[str, Any]] = [
        {
            "type": "data",
            "source": artifact_id,
            "summary": (
                f"FFT of {num_samples} samples at {sample_rate:.0f} Hz "
                f"yielded {len(peaks_hz)} peak(s)."
            ),
        },
    ]
    if peaks_hz:
        evidence[0]["value"] = peaks_hz
        evidence[0]["unit"] = "Hz"

    # --- Assumptions ---
    assumptions: list[dict[str, Any]] = [
        {
            "id": "A-01",
            "statement": "Signal is stationary over the measurement window.",
            "basis": "Short acquisition duration relative to expected dynamics.",
            "impact_if_wrong": "high",
        },
        {
            "id": "A-02",
            "statement": "No significant cross-axis coupling affects this channel.",
            "basis": "Single-axis accelerometer aligned to primary vibration direction.",
            "impact_if_wrong": "medium",
        },
    ]

    # --- Risks ---
    risks: list[dict[str, Any]] = [
        {
            "id": "R-01",
            "description": (
                "Sensor mounting may alter local dynamics, shifting resonant frequencies."
            ),
            "likelihood": "low",
            "severity": "medium",
            "mitigation": "Validate with impact-hammer test after installation.",
        },
        {
            "id": "R-02",
            "description": (
                "Cable routing may introduce noise pickup from nearby power electronics."
            ),
            "likelihood": "medium",
            "severity": "medium",
            "mitigation": "Use shielded twisted-pair cable routed away from power lines.",
        },
    ]

    # --- Trace ---
    trace: list[str] = [artifact_id, signal_id]

    # --- Assemble recommendation ---
    rec: dict[str, Any] = {
        "id": _next_rec_id(store),
        "title": f"Vibration characterization — {_signal_name(store, signal_id)}",
        "goal": "Characterize vibration modes from single-channel accelerometer data.",
        "verdict": verdict,
        "evidence": evidence,
        "assumptions": assumptions,
        "risks": risks,
        "confidence": {
            "level": confidence_level,
            "rationale": confidence_rationale,
            "limiting_factor": limiting_factor,
        },
        "trace": trace,
    }

    return rec


# --- Helpers ---


def _signal_name(store: OntologyStore, signal_id: str) -> str:
    entity = store.get(signal_id)
    if entity:
        return entity.get("name", signal_id)
    return signal_id


def _next_rec_id(store: OntologyStore) -> str:
    """Generate a simple sequential recommendation ID.

    Scans existing entity IDs for REC-NNN pattern and increments.
    """
    max_n = 0
    for etype in ("Artifact", "Signal"):  # scan common types
        for entity in store.list_by_type(etype):
            eid = entity.get("id", "")
            if eid.startswith("REC-"):
                try:
                    n = int(eid[4:])
                    max_n = max(max_n, n)
                except ValueError:
                    pass
    return f"REC-{max_n + 1:03d}"
