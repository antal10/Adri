"""In-memory ontology store per DEC-010.

Shape:
- Entities: dict keyed by entity_id, values are full property dicts.
- Relationships: list of (source_id, relationship_type, target_id) triples.

Query operations (5):
- get(entity_id) -> entity or None
- list_by_type(entity_type) -> list
- relationships_from(source_id) -> list of triples
- relationships_to(target_id) -> list of triples
- exists(entity_id) -> bool
"""

from __future__ import annotations

from typing import Any


# Allowed entity types per ontology.md
ENTITY_TYPES = frozenset({
    "Component",
    "Interface",
    "Material",
    "SpatialRegion",
    "Signal",
    "SignalChain",
    "TransferFunction",
    "Sensor",
    "Actuator",
    "DAQChannel",
    "Subsystem",
    "Artifact",
    "Constraint",
})

# Allowed relationship types per ontology.md
RELATIONSHIP_TYPES = frozenset({
    "mounts_to",
    "contains",
    "senses",
    "drives",
    "feeds",
    "constrains",
    "bounded_by",
    "controls",
    "implements",
    "part_of",
    "derived_from",
    "references",
    "located_in",
    "made_of",
})

# Required universal properties per ontology.md
UNIVERSAL_PROPERTIES = ("id", "name", "source_adapter", "source_artifact", "created_at")

Triple = tuple[str, str, str]


class OntologyStore:
    """In-memory ontology store. Not persisted (DEC-010)."""

    def __init__(self) -> None:
        self._entities: dict[str, dict[str, Any]] = {}
        self._relationships: list[Triple] = []

    # --- Mutators ---

    def add_entity(self, entity: dict[str, Any]) -> None:
        """Add an entity to the store.

        Raises ValueError if the entity has no 'id', if the id already exists,
        or if 'type' is not a recognised ontology entity type.
        """
        entity_id = entity.get("id")
        if not entity_id:
            raise ValueError("Entity must have a non-empty 'id'.")
        if entity_id in self._entities:
            raise ValueError(f"Entity '{entity_id}' already exists.")
        entity_type = entity.get("type")
        if entity_type not in ENTITY_TYPES:
            raise ValueError(
                f"Unknown entity type '{entity_type}'. "
                f"Must be one of: {sorted(ENTITY_TYPES)}"
            )
        self._entities[entity_id] = entity

    def add_relationship(self, source_id: str, rel_type: str, target_id: str) -> None:
        """Add a relationship triple to the store.

        Raises ValueError if the relationship type is unrecognised or if
        source/target entities do not exist in the store.
        """
        if rel_type not in RELATIONSHIP_TYPES:
            raise ValueError(
                f"Unknown relationship type '{rel_type}'. "
                f"Must be one of: {sorted(RELATIONSHIP_TYPES)}"
            )
        if source_id not in self._entities:
            raise ValueError(f"Source entity '{source_id}' does not exist.")
        if target_id not in self._entities:
            raise ValueError(f"Target entity '{target_id}' does not exist.")
        self._relationships.append((source_id, rel_type, target_id))

    # --- Query operations (DEC-010) ---

    def get(self, entity_id: str) -> dict[str, Any] | None:
        """Get entity by ID, or None if not found."""
        return self._entities.get(entity_id)

    def list_by_type(self, entity_type: str) -> list[dict[str, Any]]:
        """List all entities of a given type."""
        return [e for e in self._entities.values() if e.get("type") == entity_type]

    def relationships_from(self, source_id: str) -> list[Triple]:
        """List all relationship triples originating from source_id."""
        return [t for t in self._relationships if t[0] == source_id]

    def relationships_to(self, target_id: str) -> list[Triple]:
        """List all relationship triples targeting target_id."""
        return [t for t in self._relationships if t[2] == target_id]

    def exists(self, entity_id: str) -> bool:
        """Check whether an entity ID exists in the store."""
        return entity_id in self._entities
