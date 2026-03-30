"""Tests for the constraint evaluator."""

from __future__ import annotations

import pytest

from adri.ontology_store import OntologyStore
from reasoning.constraint_evaluator import (
    ConstraintResult,
    all_satisfied,
    evaluate_all_constraints,
    evaluate_constraint,
    results_to_evidence,
    violations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_constraint(
    cid: str = "c-001",
    name: str = "Test constraint",
    bound_type: str = "upper",
    bound_value=100.0,
    unit: str = "Hz",
    **extra,
) -> dict:
    c = {
        "id": cid,
        "type": "Constraint",
        "name": name,
        "source_adapter": "core",
        "source_artifact": cid,
        "created_at": "2026-01-01T00:00:00+00:00",
        "bound_type": bound_type,
        "bound_value": bound_value,
        "unit": unit,
    }
    c.update(extra)
    return c


def _make_signal(sid: str = "sig-001", **extra) -> dict:
    s = {
        "id": sid,
        "type": "Signal",
        "name": "test-signal",
        "source_adapter": "python_vibration",
        "source_artifact": "art-001",
        "created_at": "2026-01-01T00:00:00+00:00",
        "domain": "time",
        "sample_rate": 1000.0,
    }
    s.update(extra)
    return s


def _store_with_constraint_and_signal(
    bound_type="upper", bound_value=500.0, unit="Hz",
    tolerance=None,
) -> OntologyStore:
    """Build a store with one Signal bounded by one Constraint."""
    store = OntologyStore()
    ckwargs = {"bound_type": bound_type, "bound_value": bound_value, "unit": unit}
    if tolerance is not None:
        ckwargs["tolerance"] = tolerance
    store.add_entity(_make_constraint(**ckwargs))
    store.add_entity(_make_signal())
    store.add_relationship("sig-001", "bounded_by", "c-001")
    return store


# =========================================================================
# evaluate_constraint — upper bound
# =========================================================================

class TestUpperBound:
    def test_within_upper_bound(self):
        c = _make_constraint(bound_type="upper", bound_value=500.0, unit="Hz")
        r = evaluate_constraint(c, "sig-001", 300.0)
        assert r.passed is True
        assert r.margin == pytest.approx(200.0)
        assert r.bound_type == "upper"

    def test_at_upper_bound(self):
        c = _make_constraint(bound_type="upper", bound_value=500.0)
        r = evaluate_constraint(c, "sig-001", 500.0)
        assert r.passed is True
        assert r.margin == pytest.approx(0.0)

    def test_exceeds_upper_bound(self):
        c = _make_constraint(bound_type="upper", bound_value=500.0)
        r = evaluate_constraint(c, "sig-001", 600.0)
        assert r.passed is False
        assert r.margin == pytest.approx(-100.0)


# =========================================================================
# evaluate_constraint — lower bound
# =========================================================================

class TestLowerBound:
    def test_above_lower_bound(self):
        c = _make_constraint(bound_type="lower", bound_value=10.0, unit="Hz")
        r = evaluate_constraint(c, "sig-001", 50.0)
        assert r.passed is True
        assert r.margin == pytest.approx(40.0)

    def test_at_lower_bound(self):
        c = _make_constraint(bound_type="lower", bound_value=10.0)
        r = evaluate_constraint(c, "sig-001", 10.0)
        assert r.passed is True
        assert r.margin == pytest.approx(0.0)

    def test_below_lower_bound(self):
        c = _make_constraint(bound_type="lower", bound_value=10.0)
        r = evaluate_constraint(c, "sig-001", 5.0)
        assert r.passed is False
        assert r.margin == pytest.approx(-5.0)


# =========================================================================
# evaluate_constraint — equality bound
# =========================================================================

class TestEqualityBound:
    def test_exact_match(self):
        c = _make_constraint(bound_type="equality", bound_value=50.0, tolerance=0.0)
        r = evaluate_constraint(c, "sig-001", 50.0)
        assert r.passed is True
        assert r.margin == pytest.approx(0.0)

    def test_within_tolerance(self):
        c = _make_constraint(bound_type="equality", bound_value=50.0, tolerance=1.0)
        r = evaluate_constraint(c, "sig-001", 50.5)
        assert r.passed is True
        assert r.margin == pytest.approx(0.5)

    def test_outside_tolerance(self):
        c = _make_constraint(bound_type="equality", bound_value=50.0, tolerance=1.0)
        r = evaluate_constraint(c, "sig-001", 52.0)
        assert r.passed is False
        assert r.margin == pytest.approx(-1.0)

    def test_default_zero_tolerance(self):
        c = _make_constraint(bound_type="equality", bound_value=50.0)
        r = evaluate_constraint(c, "sig-001", 50.01)
        assert r.passed is False


# =========================================================================
# evaluate_constraint — range bound
# =========================================================================

class TestRangeBound:
    def test_within_range(self):
        c = _make_constraint(bound_type="range", bound_value=[100.0, 500.0], unit="Hz")
        r = evaluate_constraint(c, "sig-001", 300.0)
        assert r.passed is True
        assert r.margin == pytest.approx(200.0)  # min(300-100, 500-300)

    def test_at_lower_edge(self):
        c = _make_constraint(bound_type="range", bound_value=[100.0, 500.0])
        r = evaluate_constraint(c, "sig-001", 100.0)
        assert r.passed is True
        assert r.margin == pytest.approx(0.0)

    def test_at_upper_edge(self):
        c = _make_constraint(bound_type="range", bound_value=[100.0, 500.0])
        r = evaluate_constraint(c, "sig-001", 500.0)
        assert r.passed is True
        assert r.margin == pytest.approx(0.0)

    def test_below_range(self):
        c = _make_constraint(bound_type="range", bound_value=[100.0, 500.0])
        r = evaluate_constraint(c, "sig-001", 50.0)
        assert r.passed is False
        assert r.margin == pytest.approx(-50.0)

    def test_above_range(self):
        c = _make_constraint(bound_type="range", bound_value=[100.0, 500.0])
        r = evaluate_constraint(c, "sig-001", 600.0)
        assert r.passed is False
        assert r.margin == pytest.approx(-100.0)


# =========================================================================
# Error cases
# =========================================================================

class TestErrorCases:
    def test_unknown_bound_type_raises(self):
        c = _make_constraint(bound_type="bogus")
        with pytest.raises(ValueError, match="Unknown bound_type"):
            evaluate_constraint(c, "sig-001", 42.0)

    def test_upper_with_list_bound_raises(self):
        c = _make_constraint(bound_type="upper", bound_value=[1, 2])
        with pytest.raises(ValueError, match="scalar"):
            evaluate_constraint(c, "sig-001", 1.5)

    def test_range_with_scalar_bound_raises(self):
        c = _make_constraint(bound_type="range", bound_value=42.0)
        with pytest.raises(ValueError, match="\\[lo, hi\\]"):
            evaluate_constraint(c, "sig-001", 42.0)


# =========================================================================
# evaluate_all_constraints — store-level evaluation
# =========================================================================

class TestEvaluateAll:
    def test_single_constraint_pass(self):
        store = _store_with_constraint_and_signal(
            bound_type="upper", bound_value=500.0, unit="Hz",
        )
        results = evaluate_all_constraints(store, {"sig-001": 300.0})
        assert len(results) == 1
        assert results[0].passed is True

    def test_single_constraint_fail(self):
        store = _store_with_constraint_and_signal(
            bound_type="upper", bound_value=500.0,
        )
        results = evaluate_all_constraints(store, {"sig-001": 600.0})
        assert len(results) == 1
        assert results[0].passed is False

    def test_missing_measurement_skipped(self):
        store = _store_with_constraint_and_signal()
        results = evaluate_all_constraints(store, {})
        assert len(results) == 0

    def test_multiple_constraints_on_one_entity(self):
        store = OntologyStore()
        store.add_entity(_make_signal())
        store.add_entity(_make_constraint(
            cid="c-lower", name="Min freq", bound_type="lower", bound_value=10.0,
        ))
        store.add_entity(_make_constraint(
            cid="c-upper", name="Max freq", bound_type="upper", bound_value=500.0,
        ))
        store.add_relationship("sig-001", "bounded_by", "c-lower")
        store.add_relationship("sig-001", "bounded_by", "c-upper")

        results = evaluate_all_constraints(store, {"sig-001": 300.0})
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_multiple_entities_one_constraint(self):
        store = OntologyStore()
        store.add_entity(_make_constraint(
            bound_type="upper", bound_value=1000.0,
        ))
        store.add_entity(_make_signal(sid="sig-a"))
        store.add_entity(_make_signal(sid="sig-b"))
        store.add_relationship("sig-a", "bounded_by", "c-001")
        store.add_relationship("sig-b", "bounded_by", "c-001")

        results = evaluate_all_constraints(
            store, {"sig-a": 500.0, "sig-b": 1500.0}
        )
        assert len(results) == 2
        passed_ids = {r.entity_id for r in results if r.passed}
        failed_ids = {r.entity_id for r in results if not r.passed}
        assert passed_ids == {"sig-a"}
        assert failed_ids == {"sig-b"}


# =========================================================================
# Convenience helpers
# =========================================================================

class TestConvenienceHelpers:
    def test_all_satisfied_true(self):
        store = _store_with_constraint_and_signal(
            bound_type="upper", bound_value=500.0,
        )
        results = evaluate_all_constraints(store, {"sig-001": 300.0})
        assert all_satisfied(results) is True

    def test_all_satisfied_false(self):
        store = _store_with_constraint_and_signal(
            bound_type="upper", bound_value=500.0,
        )
        results = evaluate_all_constraints(store, {"sig-001": 600.0})
        assert all_satisfied(results) is False

    def test_all_satisfied_empty(self):
        assert all_satisfied([]) is True

    def test_violations_returns_only_failures(self):
        store = OntologyStore()
        store.add_entity(_make_signal())
        store.add_entity(_make_constraint(
            cid="c-lower", bound_type="lower", bound_value=10.0,
        ))
        store.add_entity(_make_constraint(
            cid="c-upper", bound_type="upper", bound_value=100.0,
        ))
        store.add_relationship("sig-001", "bounded_by", "c-lower")
        store.add_relationship("sig-001", "bounded_by", "c-upper")

        results = evaluate_all_constraints(store, {"sig-001": 200.0})
        v = violations(results)
        assert len(v) == 1
        assert v[0].constraint_id == "c-upper"


# =========================================================================
# results_to_evidence
# =========================================================================

class TestResultsToEvidence:
    def test_produces_derivation_evidence(self):
        c = _make_constraint(bound_type="upper", bound_value=500.0, unit="Hz")
        r = evaluate_constraint(c, "sig-001", 300.0)
        ev = results_to_evidence([r])
        assert len(ev) == 1
        assert ev[0]["type"] == "derivation"
        assert ev[0]["source"] == "c-001"
        assert "satisfied" in ev[0]["summary"]
        assert ev[0]["value"] == pytest.approx(300.0)
        assert ev[0]["unit"] == "Hz"

    def test_violated_shows_VIOLATED(self):
        c = _make_constraint(bound_type="upper", bound_value=500.0)
        r = evaluate_constraint(c, "sig-001", 600.0)
        ev = results_to_evidence([r])
        assert "VIOLATED" in ev[0]["summary"]

    def test_empty_input(self):
        assert results_to_evidence([]) == []
