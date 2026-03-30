"""Tests for the context assembly module."""

from __future__ import annotations

import pytest

from adri.ontology_store import OntologyStore
from adri.context_assembly import (
    add_constraint,
    bind_constraint,
    link_by_shared_artifact,
    link_spatial_co_location,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store_with_signal(sid: str = "sig-001") -> OntologyStore:
    store = OntologyStore()
    store.add_entity({
        "id": sid,
        "type": "Signal",
        "name": "test-signal",
        "source_adapter": "python_vibration",
        "source_artifact": "art-001",
        "created_at": "2026-01-01T00:00:00+00:00",
        "domain": "time",
        "sample_rate": 1000.0,
    })
    return store


# =========================================================================
# add_constraint
# =========================================================================

class TestAddConstraint:
    def test_creates_entity_in_store(self):
        store = OntologyStore()
        entity = add_constraint(
            store,
            constraint_id="c-001",
            name="Max peak freq",
            bound_type="upper",
            bound_value=500.0,
            unit="Hz",
        )
        assert store.exists("c-001")
        assert entity["type"] == "Constraint"
        assert entity["bound_type"] == "upper"
        assert entity["bound_value"] == 500.0
        assert entity["unit"] == "Hz"

    def test_sets_universal_properties(self):
        store = OntologyStore()
        entity = add_constraint(
            store,
            constraint_id="c-002",
            name="Min bandwidth",
            bound_type="lower",
            bound_value=100.0,
            unit="Hz",
        )
        assert entity["source_adapter"] == "core"
        assert entity["source_artifact"] == "c-002"
        assert entity["created_at"]  # non-empty

    def test_range_bound_value(self):
        store = OntologyStore()
        entity = add_constraint(
            store,
            constraint_id="c-003",
            name="Freq band",
            bound_type="range",
            bound_value=[100.0, 500.0],
            unit="Hz",
        )
        assert entity["bound_value"] == [100.0, 500.0]

    def test_equality_with_tolerance(self):
        store = OntologyStore()
        entity = add_constraint(
            store,
            constraint_id="c-004",
            name="Target freq",
            bound_type="equality",
            bound_value=440.0,
            unit="Hz",
            tolerance=2.0,
        )
        assert entity["tolerance"] == 2.0

    def test_duplicate_id_raises(self):
        store = OntologyStore()
        add_constraint(
            store, constraint_id="c-001", name="A",
            bound_type="upper", bound_value=1.0, unit="Hz",
        )
        with pytest.raises(ValueError, match="already exists"):
            add_constraint(
                store, constraint_id="c-001", name="B",
                bound_type="upper", bound_value=2.0, unit="Hz",
            )


# =========================================================================
# bind_constraint
# =========================================================================

class TestBindConstraint:
    def test_creates_bounded_by_relationship(self):
        store = _make_store_with_signal()
        add_constraint(
            store, constraint_id="c-001", name="Max freq",
            bound_type="upper", bound_value=500.0, unit="Hz",
        )
        bind_constraint(store, "sig-001", "c-001")

        rels = store.relationships_from("sig-001")
        assert ("sig-001", "bounded_by", "c-001") in rels

    def test_nonexistent_entity_raises(self):
        store = OntologyStore()
        add_constraint(
            store, constraint_id="c-001", name="A",
            bound_type="upper", bound_value=1.0, unit="Hz",
        )
        with pytest.raises(ValueError, match="does not exist"):
            bind_constraint(store, "no-such-entity", "c-001")

    def test_nonexistent_constraint_raises(self):
        store = _make_store_with_signal()
        with pytest.raises(ValueError, match="does not exist"):
            bind_constraint(store, "sig-001", "no-such-constraint")

    def test_multiple_bindings(self):
        store = _make_store_with_signal()
        add_constraint(
            store, constraint_id="c-lo", name="Min",
            bound_type="lower", bound_value=10.0, unit="Hz",
        )
        add_constraint(
            store, constraint_id="c-hi", name="Max",
            bound_type="upper", bound_value=500.0, unit="Hz",
        )
        bind_constraint(store, "sig-001", "c-lo")
        bind_constraint(store, "sig-001", "c-hi")

        rels = store.relationships_from("sig-001")
        assert ("sig-001", "bounded_by", "c-lo") in rels
        assert ("sig-001", "bounded_by", "c-hi") in rels


# =========================================================================
# link_by_shared_artifact (scaffold)
# =========================================================================

class TestLinkBySharedArtifact:
    def test_returns_empty_list(self):
        store = _make_store_with_signal()
        result = link_by_shared_artifact(store)
        assert result == []


# =========================================================================
# link_spatial_co_location
# =========================================================================

class TestLinkSpatialCoLocation:
    def test_creates_located_in_relationships(self):
        store = OntologyStore()
        store.add_entity({
            "id": "comp-001", "type": "Component", "name": "Upright",
            "source_adapter": "solidworks", "source_artifact": "art-001",
            "created_at": "2026-01-01T00:00:00+00:00",
        })
        store.add_entity({
            "id": "sensor-001", "type": "Sensor", "name": "Accel",
            "source_adapter": "core", "source_artifact": "art-002",
            "created_at": "2026-01-01T00:00:00+00:00",
        })
        store.add_entity({
            "id": "region-rr", "type": "SpatialRegion",
            "name": "Rear-right wheel well",
            "source_adapter": "core", "source_artifact": "region-rr",
            "created_at": "2026-01-01T00:00:00+00:00",
        })

        created = link_spatial_co_location(
            store, "comp-001", "sensor-001", "region-rr"
        )
        assert len(created) == 2
        assert ("comp-001", "located_in", "region-rr") in created
        assert ("sensor-001", "located_in", "region-rr") in created

        # Verify in store
        assert ("comp-001", "located_in", "region-rr") in store.relationships_from("comp-001")
        assert ("sensor-001", "located_in", "region-rr") in store.relationships_from("sensor-001")

    def test_nonexistent_entity_raises(self):
        store = OntologyStore()
        store.add_entity({
            "id": "region-001", "type": "SpatialRegion", "name": "Zone",
            "source_adapter": "core", "source_artifact": "region-001",
            "created_at": "2026-01-01T00:00:00+00:00",
        })
        with pytest.raises(ValueError, match="does not exist"):
            link_spatial_co_location(store, "no-entity", "also-no", "region-001")


# =========================================================================
# Integration: add_constraint + bind + evaluate
# =========================================================================

class TestConstraintIntegration:
    """End-to-end: create constraint, bind to signal, evaluate."""

    def test_full_pipeline(self):
        from reasoning.constraint_evaluator import (
            evaluate_all_constraints,
            all_satisfied,
            results_to_evidence,
        )

        store = _make_store_with_signal()
        add_constraint(
            store, constraint_id="c-max-freq", name="Max peak frequency",
            bound_type="upper", bound_value=500.0, unit="Hz",
        )
        bind_constraint(store, "sig-001", "c-max-freq")

        # Signal's peak is at 300 Hz — should pass
        results = evaluate_all_constraints(store, {"sig-001": 300.0})
        assert len(results) == 1
        assert all_satisfied(results) is True

        evidence = results_to_evidence(results)
        assert len(evidence) == 1
        assert evidence[0]["type"] == "derivation"
        assert "satisfied" in evidence[0]["summary"]

    def test_violated_constraint(self):
        from reasoning.constraint_evaluator import (
            evaluate_all_constraints,
            all_satisfied,
            violations,
        )

        store = _make_store_with_signal()
        add_constraint(
            store, constraint_id="c-max-freq", name="Max peak frequency",
            bound_type="upper", bound_value=200.0, unit="Hz",
        )
        bind_constraint(store, "sig-001", "c-max-freq")

        results = evaluate_all_constraints(store, {"sig-001": 300.0})
        assert all_satisfied(results) is False
        v = violations(results)
        assert len(v) == 1
        assert v[0].margin < 0
