"""Tests for the in-memory ontology store (DEC-010)."""

import pytest

from adri.ontology_store import (
    ENTITY_TYPES,
    RELATIONSHIP_TYPES,
    UNIVERSAL_PROPERTIES,
    OntologyStore,
)


def _make_entity(entity_id: str, entity_type: str = "Artifact", **overrides):
    """Helper to build a minimal valid entity dict."""
    base = {
        "id": entity_id,
        "type": entity_type,
        "name": f"test-{entity_id}",
        "source_adapter": "test",
        "source_artifact": entity_id,
        "created_at": "2026-03-22T00:00:00Z",
    }
    base.update(overrides)
    return base


# --- add_entity ---


class TestAddEntity:
    def test_add_valid_entity(self):
        store = OntologyStore()
        entity = _make_entity("e1")
        store.add_entity(entity)
        assert store.exists("e1")

    def test_reject_missing_id(self):
        store = OntologyStore()
        with pytest.raises(ValueError, match="non-empty 'id'"):
            store.add_entity({"type": "Artifact", "name": "x"})

    def test_reject_empty_id(self):
        store = OntologyStore()
        with pytest.raises(ValueError, match="non-empty 'id'"):
            store.add_entity({"id": "", "type": "Artifact", "name": "x"})

    def test_reject_duplicate_id(self):
        store = OntologyStore()
        store.add_entity(_make_entity("e1"))
        with pytest.raises(ValueError, match="already exists"):
            store.add_entity(_make_entity("e1"))

    def test_reject_unknown_entity_type(self):
        store = OntologyStore()
        with pytest.raises(ValueError, match="Unknown entity type"):
            store.add_entity(_make_entity("e1", entity_type="Bogus"))

    def test_all_ontology_entity_types_accepted(self):
        store = OntologyStore()
        for i, etype in enumerate(sorted(ENTITY_TYPES)):
            store.add_entity(_make_entity(f"e-{i}", entity_type=etype))
        assert len(store.list_by_type("Signal")) == 1


# --- add_relationship ---


class TestAddRelationship:
    def test_add_valid_relationship(self):
        store = OntologyStore()
        store.add_entity(_make_entity("a1", "Artifact"))
        store.add_entity(_make_entity("s1", "Signal"))
        store.add_relationship("s1", "derived_from", "a1")
        assert store.relationships_from("s1") == [("s1", "derived_from", "a1")]

    def test_reject_unknown_relationship_type(self):
        store = OntologyStore()
        store.add_entity(_make_entity("a1"))
        store.add_entity(_make_entity("a2"))
        with pytest.raises(ValueError, match="Unknown relationship type"):
            store.add_relationship("a1", "bogus_rel", "a2")

    def test_reject_missing_source(self):
        store = OntologyStore()
        store.add_entity(_make_entity("a1"))
        with pytest.raises(ValueError, match="Source entity"):
            store.add_relationship("nonexistent", "derived_from", "a1")

    def test_reject_missing_target(self):
        store = OntologyStore()
        store.add_entity(_make_entity("a1"))
        with pytest.raises(ValueError, match="Target entity"):
            store.add_relationship("a1", "derived_from", "nonexistent")


# --- get ---


class TestGet:
    def test_get_existing(self):
        store = OntologyStore()
        entity = _make_entity("e1")
        store.add_entity(entity)
        result = store.get("e1")
        assert result is not None
        assert result["id"] == "e1"

    def test_get_nonexistent_returns_none(self):
        store = OntologyStore()
        assert store.get("nope") is None


# --- list_by_type ---


class TestListByType:
    def test_list_by_type_returns_matching(self):
        store = OntologyStore()
        store.add_entity(_make_entity("s1", "Signal"))
        store.add_entity(_make_entity("s2", "Signal"))
        store.add_entity(_make_entity("a1", "Artifact"))
        signals = store.list_by_type("Signal")
        assert len(signals) == 2
        assert all(s["type"] == "Signal" for s in signals)

    def test_list_by_type_empty(self):
        store = OntologyStore()
        assert store.list_by_type("Signal") == []


# --- relationships_from / relationships_to ---


class TestRelationshipQueries:
    def test_relationships_from(self):
        store = OntologyStore()
        store.add_entity(_make_entity("s1", "Signal"))
        store.add_entity(_make_entity("a1", "Artifact"))
        store.add_entity(_make_entity("a2", "Artifact"))
        store.add_relationship("s1", "derived_from", "a1")
        store.add_relationship("s1", "derived_from", "a2")
        rels = store.relationships_from("s1")
        assert len(rels) == 2

    def test_relationships_from_empty(self):
        store = OntologyStore()
        assert store.relationships_from("nonexistent") == []

    def test_relationships_to(self):
        store = OntologyStore()
        store.add_entity(_make_entity("s1", "Signal"))
        store.add_entity(_make_entity("s2", "Signal"))
        store.add_entity(_make_entity("a1", "Artifact"))
        store.add_relationship("s1", "derived_from", "a1")
        store.add_relationship("s2", "derived_from", "a1")
        rels = store.relationships_to("a1")
        assert len(rels) == 2

    def test_relationships_to_empty(self):
        store = OntologyStore()
        assert store.relationships_to("nonexistent") == []


# --- exists ---


class TestExists:
    def test_exists_true(self):
        store = OntologyStore()
        store.add_entity(_make_entity("e1"))
        assert store.exists("e1") is True

    def test_exists_false(self):
        store = OntologyStore()
        assert store.exists("nope") is False


# --- Constants ---


class TestConstants:
    def test_entity_types_count(self):
        # 13 types per ontology.md (Component, Interface, Material,
        # SpatialRegion, Signal, SignalChain, TransferFunction, Sensor,
        # Actuator, DAQChannel, Subsystem, Artifact, Constraint)
        assert len(ENTITY_TYPES) == 13

    def test_relationship_types_count(self):
        # 14 types per ontology.md
        assert len(RELATIONSHIP_TYPES) == 14

    def test_universal_properties(self):
        assert set(UNIVERSAL_PROPERTIES) == {
            "id", "name", "source_adapter", "source_artifact", "created_at"
        }
