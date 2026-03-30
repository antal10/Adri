"""Constraint evaluator — checks design constraints against measured values.

Given an OntologyStore containing Constraint entities linked via ``bounded_by``
relationships, evaluates whether bounded entities satisfy their constraints.

Constraint properties (from ontology.md):
- bound_type: upper | lower | equality | range
- bound_value: float (single) or [float, float] (range)
- unit: string

The caller provides measured values as a dict mapping entity_id → float.
The evaluator finds all bounded_by relationships, matches them to
measurements, and returns structured pass/fail results with margin.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from adri.ontology_store import OntologyStore


@dataclass
class ConstraintResult:
    """Outcome of evaluating one constraint against one entity's value."""

    constraint_id: str
    entity_id: str
    constraint_name: str
    passed: bool
    bound_type: str
    bound_value: Any  # float or [float, float]
    actual_value: float
    unit: str
    margin: float  # positive → within bounds, negative → violated


def evaluate_constraint(
    constraint: dict[str, Any],
    entity_id: str,
    actual_value: float,
) -> ConstraintResult:
    """Evaluate a single Constraint entity against a measured value.

    Parameters
    ----------
    constraint : dict
        A Constraint entity from the ontology store.  Must have keys
        ``bound_type``, ``bound_value``, and ``unit``.
    entity_id : str
        ID of the entity whose value is being checked.
    actual_value : float
        The measured/computed value to compare against the bound.

    Returns
    -------
    ConstraintResult

    Raises
    ------
    ValueError
        If ``bound_type`` is unrecognised or ``bound_value`` is malformed.
    """
    bound_type = constraint.get("bound_type", "")
    bound_value = constraint.get("bound_value")
    unit = constraint.get("unit", "")
    name = constraint.get("name", constraint.get("id", ""))

    if bound_type == "upper":
        if not isinstance(bound_value, (int, float)):
            raise ValueError(f"upper constraint requires scalar bound_value, got {type(bound_value).__name__}")
        passed = actual_value <= bound_value
        margin = bound_value - actual_value

    elif bound_type == "lower":
        if not isinstance(bound_value, (int, float)):
            raise ValueError(f"lower constraint requires scalar bound_value, got {type(bound_value).__name__}")
        passed = actual_value >= bound_value
        margin = actual_value - bound_value

    elif bound_type == "equality":
        if not isinstance(bound_value, (int, float)):
            raise ValueError(f"equality constraint requires scalar bound_value, got {type(bound_value).__name__}")
        tolerance = constraint.get("tolerance", 0.0)
        diff = abs(actual_value - bound_value)
        passed = diff <= tolerance
        margin = tolerance - diff

    elif bound_type == "range":
        if not (isinstance(bound_value, (list, tuple)) and len(bound_value) == 2):
            raise ValueError(f"range constraint requires [lo, hi] bound_value, got {bound_value!r}")
        lo, hi = float(bound_value[0]), float(bound_value[1])
        if actual_value < lo:
            margin = actual_value - lo
        elif actual_value > hi:
            margin = hi - actual_value
        else:
            margin = min(actual_value - lo, hi - actual_value)
        passed = lo <= actual_value <= hi

    else:
        raise ValueError(f"Unknown bound_type '{bound_type}'.")

    return ConstraintResult(
        constraint_id=constraint["id"],
        entity_id=entity_id,
        constraint_name=name,
        passed=passed,
        bound_type=bound_type,
        bound_value=bound_value,
        actual_value=actual_value,
        unit=unit,
        margin=margin,
    )


def evaluate_all_constraints(
    store: OntologyStore,
    measurements: dict[str, float],
) -> list[ConstraintResult]:
    """Evaluate every bounded_by constraint in the store.

    Walks all Constraint entities, finds incoming ``bounded_by``
    relationships, and evaluates each bound entity whose ID appears
    in *measurements*.  Entities without a measurement are skipped
    silently (they may be evaluated later when data arrives).

    Parameters
    ----------
    store : OntologyStore
        Must contain Constraint entities and ``bounded_by`` relationships.
    measurements : dict[str, float]
        Maps entity_id → measured value for the constrained property.

    Returns
    -------
    list[ConstraintResult]
        One result per (entity, constraint) pair that could be evaluated.
    """
    results: list[ConstraintResult] = []
    for constraint in store.list_by_type("Constraint"):
        cid = constraint["id"]
        for source_id, rel_type, target_id in store.relationships_to(cid):
            if rel_type != "bounded_by":
                continue
            if source_id not in measurements:
                continue
            results.append(
                evaluate_constraint(constraint, source_id, measurements[source_id])
            )
    return results


def all_satisfied(results: list[ConstraintResult]) -> bool:
    """Return True if every constraint result passed."""
    return all(r.passed for r in results)


def violations(results: list[ConstraintResult]) -> list[ConstraintResult]:
    """Return only the violated constraints."""
    return [r for r in results if not r.passed]


def results_to_evidence(results: list[ConstraintResult]) -> list[dict[str, Any]]:
    """Convert constraint results into recommendation-schema evidence items.

    Each result becomes one evidence entry of type ``derivation`` so that
    constraint evaluation feeds directly into the recommendation pipeline.
    """
    evidence: list[dict[str, Any]] = []
    for r in results:
        status = "satisfied" if r.passed else "VIOLATED"
        evidence.append({
            "type": "derivation",
            "source": r.constraint_id,
            "summary": (
                f"Constraint '{r.constraint_name}' "
                f"({r.bound_type} {r.bound_value} {r.unit}): "
                f"actual={r.actual_value:.4g}, margin={r.margin:.4g} — {status}."
            ),
            "value": r.actual_value,
            "unit": r.unit,
        })
    return evidence
