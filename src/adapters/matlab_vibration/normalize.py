"""Normalize MATLAB vibration adapter outputs into Adri ontology.

Backend-independent: works identically whether the adapter response
was produced by the NumPy fallback or a real MATLAB backend. Takes
the adapter response and populates the ontology store with:
- Signal entity (source_adapter=matlab_vibration, source_artifact=<csv artifact>)
- Artifact entities for each produced output file
- references relationships linking output artifacts to the source artifact
- derived_from relationship linking Signal to source Artifact
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from adri.ontology_store import OntologyStore
from adapters.matlab_vibration.adapter import REGISTRATION


def normalize_into_store(
    store: OntologyStore,
    response: dict[str, Any],
    source_artifact_id: str,
) -> dict[str, Any]:
    """Merge MATLAB adapter outputs into the ontology store.

    Parameters
    ----------
    store : OntologyStore
        Must already contain the source artifact entity.
    response : dict
        Adapter response from ``analyze_vibration_csv``.
    source_artifact_id : str
        Entity ID of the source vibration CSV artifact.

    Returns
    -------
    dict
        Summary with keys: signal_id, output_artifact_ids, relationships_added.
    """
    adapter_id = REGISTRATION["adapter_id"]
    now = datetime.now(timezone.utc).isoformat()
    outputs = response.get("outputs", {})
    run_dir = outputs.get("run_dir", "")
    artifacts_written = outputs.get("artifacts_written", [])

    signal_id: str | None = None
    output_artifact_ids: list[str] = []
    relationships_added: list[tuple[str, str, str]] = []

    # --- Add Signal entity from entities_created ---
    for entity in response.get("entities_created", []):
        store.add_entity(entity)
        if entity.get("type") == "Signal":
            signal_id = entity["id"]
            store.add_relationship(signal_id, "derived_from", source_artifact_id)
            relationships_added.append((signal_id, "derived_from", source_artifact_id))

    # --- Add Artifact entities for each output file ---
    # Skip vibration.csv (that's the source copy) and request.json (metadata)
    output_files = [
        f for f in artifacts_written
        if f not in ("vibration.csv", "request.json")
    ]

    for filename in output_files:
        art_id = f"output-{source_artifact_id}-{filename.replace('.', '-')}"
        file_path = os.path.join(run_dir, filename) if run_dir else filename
        store.add_entity({
            "id": art_id,
            "type": "Artifact",
            "name": filename,
            "source_adapter": adapter_id,
            "source_artifact": source_artifact_id,
            "created_at": now,
            "file_path": file_path,
        })
        output_artifact_ids.append(art_id)

    # --- Link output artifacts to source via derived_from ---
    # Artifact -> Artifact is not in the ontology relationship table for
    # derived_from (only Signal/TF -> Signal/Artifact). Instead we use
    # the `references` relationship (Artifact -> any entity).
    # Output artifacts reference the source artifact.
    for art_id in output_artifact_ids:
        store.add_relationship(art_id, "references", source_artifact_id)
        relationships_added.append((art_id, "references", source_artifact_id))

    # --- Link Signal to spectrum artifact if spectrum.png was produced ---
    if signal_id:
        spectrum_art_id = f"output-{source_artifact_id}-spectrum-png"
        if store.exists(spectrum_art_id):
            # Signal.spectrum property points to spectral representation
            signal_entity = store.get(signal_id)
            if signal_entity:
                signal_entity["spectrum"] = spectrum_art_id

    return {
        "signal_id": signal_id,
        "output_artifact_ids": output_artifact_ids,
        "relationships_added": relationships_added,
    }
