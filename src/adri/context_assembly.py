"""Context assembly — creates cross-domain relationships and constraints.

Per DEC-003, adapters must not create cross-domain relationships; only
context assembly does.  This module provides:

1. Constraint setup — create Constraint entities and bind them to
   entities via ``bounded_by`` relationships.
2. Cross-domain linking (scaffold) — when entities from different
   adapters share spatial, signal, or functional connections, context
   assembly creates the linking relationships.

Bootstrap scope: constraint setup is fully implemented.  Cross-domain
linking has a scaffold interface; the linking rules will be implemented
when a second domain adapter (e.g., CAD geometry) exists.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from adri.ontology_store import OntologyStore


# =========================================================================
# Constraint setup
# =========================================================================


def add_constraint(
    store: OntologyStore,
    *,
    constraint_id: str,
    name: str,
    bound_type: str,
    bound_value: Any,
    unit: str,
    tolerance: float | None = None,
    source_artifact: str | None = None,
) -> dict[str, Any]:
    """Create a Constraint entity in the store.

    Parameters
    ----------
    store : OntologyStore
    constraint_id : str
        Unique entity ID for the constraint.
    name : str
        Human-readable label (e.g., "Max peak frequency").
    bound_type : str
        One of: upper, lower, equality, range.
    bound_value : float or [float, float]
        The numeric bound.
    unit : str
        Unit of the constrained quantity.
    tolerance : float, optional
        For equality constraints, the acceptable deviation.
    source_artifact : str, optional
        Artifact ID to record as provenance for the created Constraint.
        When omitted, the Constraint is self-sourced by its own ID.

    Returns
    -------
    dict
        The created Constraint entity.
    """
    now = datetime.now(timezone.utc).isoformat()
    entity: dict[str, Any] = {
        "id": constraint_id,
        "type": "Constraint",
        "name": name,
        "source_adapter": "core",
        "source_artifact": source_artifact or constraint_id,
        "created_at": now,
        "bound_type": bound_type,
        "bound_value": bound_value,
        "unit": unit,
    }
    if tolerance is not None:
        entity["tolerance"] = tolerance
    store.add_entity(entity)
    return entity


def bind_constraint(
    store: OntologyStore,
    entity_id: str,
    constraint_id: str,
) -> None:
    """Create a ``bounded_by`` relationship: entity → constraint.

    Parameters
    ----------
    store : OntologyStore
    entity_id : str
        The entity subject to the constraint (must exist, type must be
        Component, Sensor, Subsystem, or Signal per ontology.md).
    constraint_id : str
        The Constraint entity (must exist).
    """
    store.add_relationship(entity_id, "bounded_by", constraint_id)


# =========================================================================
# Cross-domain linking (scaffold)
# =========================================================================


def link_by_shared_artifact(store: OntologyStore) -> list[tuple[str, str, str]]:
    """Create cross-domain relationships for entities sharing a source artifact.

    When two entities from different adapters reference the same
    ``source_artifact``, they describe different facets of the same
    physical object or dataset.  This function identifies those pairs
    and creates appropriate relationships.

    Bootstrap: returns an empty list.  Linking rules will be added when
    the second domain adapter exists and the relationship semantics are
    evidence-backed.

    Returns
    -------
    list of (source_id, rel_type, target_id) triples created.
    """
    # Scaffold — no linking rules yet.  The function signature and
    # integration point exist so that the run_loop (or a future
    # orchestrator) can call it after all adapters have run.
    return []


def link_spatial_co_location(
    store: OntologyStore,
    entity_a: str,
    entity_b: str,
    region_id: str,
) -> list[tuple[str, str, str]]:
    """Link two entities to the same SpatialRegion via ``located_in``.

    Creates ``located_in`` relationships from both entities to the given
    SpatialRegion.  If the SpatialRegion does not exist, the caller must
    create it first.

    Returns
    -------
    list of triples created.
    """
    created: list[tuple[str, str, str]] = []
    for eid in (entity_a, entity_b):
        store.add_relationship(eid, "located_in", region_id)
        created.append((eid, "located_in", region_id))
    return created
