"""
Public GridWise sample-case integration tests.

This test file is driven by:
    tests/data/public_sample_cases.json

It intentionally does NOT require the returned hourly schedule to match the
reference schedule byte-for-byte. The challenge specification allows any
valid schedule with equivalent optimal cost.

Run:
    pytest tests/test_public_cases.py -v
"""

from pathlib import Path
import json
import math

import pytest
from fastapi.testclient import TestClient

from app.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_FILE = PROJECT_ROOT / "tests" / "data" / "live_test_data.json"

with SAMPLE_FILE.open("r", encoding="utf-8") as f:
    SAMPLE_DATA = json.load(f)

CASES = SAMPLE_DATA["cases"]

client = TestClient(app)


def _close(a: float, b: float, tol: float = 0.01) -> bool:
    return math.isclose(float(a), float(b), abs_tol=tol)


def _directive_semantics(entry: dict) -> tuple:
    """
    Ignore the free-text explanation because the public specification says
    explanation wording does not need to match byte-for-byte.
    """
    return (
        entry["note_index"],
        entry["applies"],
        entry["directive_type"],
        entry["structured_adjustment"],
    )


@pytest.mark.parametrize(
    "case",
    CASES,
    ids=[case["id"] for case in CASES],
)
def test_public_case_end_to_end(case):
    """
    Send each official public sample input through the real FastAPI pipeline
    and validate the returned response against the public reference semantics.
    """
    response = client.post(
        "/optimize-energy",
        json=case["input"],
    )

    assert response.status_code == 200, (
        f"{case['id']} failed with HTTP {response.status_code}: "
        f"{response.text}"
    )

    result = response.json()
    expected = case["expected_output"]

    # -------------------------
    # Top-level response
    # -------------------------
    assert result["scenario_id"] == case["input"]["scenario_id"]
    assert result["scenario_id"] == expected["scenario_id"]

    required_fields = {
        "scenario_id",
        "directive_interpretation",
        "hourly_plan",
        "total_grid_kwh",
        "total_cost_bdt",
        "peak_grid_kwh",
        "plan_summary",
    }
    assert required_fields.issubset(result.keys())

    # -------------------------
    # Directive interpretation
    # -------------------------
    actual_directives = result["directive_interpretation"]
    expected_directives = expected["directive_interpretation"]

    assert len(actual_directives) == len(case["input"]["operator_notes"])
    assert len(actual_directives) == len(expected_directives)

    actual_semantics = [
        _directive_semantics(d)
        for d in actual_directives
    ]
    expected_semantics = [
        _directive_semantics(d)
        for d in expected_directives
    ]

    assert actual_semantics == expected_semantics

    # -------------------------
    # Hourly plan shape
    # -------------------------
    plan = result["hourly_plan"]

    assert len(plan) == 24
    assert [row["hour"] for row in plan] == list(range(24))

    for row in plan:
        assert row["battery_action"] in {
            "charge",
            "discharge",
            "idle",
        }

        assert row["grid_kwh"] >= -0.01
        assert row["solar_used_kwh"] >= -0.01
        assert row["battery_kwh"] >= -0.01
        assert math.isfinite(float(row["grid_kwh"]))
        assert math.isfinite(float(row["solar_used_kwh"]))
        assert math.isfinite(float(row["battery_kwh"]))
        assert math.isfinite(float(row["battery_energy_after_kwh"]))

        if row["battery_action"] == "idle":
            assert _close(row["battery_kwh"], 0.0)

    # -------------------------
    # The returned aggregates
    # must agree with the returned plan.
    # -------------------------
    inputs_by_hour = {
        row["hour"]: row
        for row in case["input"]["hours"]
    }

    calculated_grid = sum(
        row["grid_kwh"]
        for row in plan
    )

    calculated_cost = sum(
        row["grid_kwh"] * inputs_by_hour[row["hour"]]["tariff_bdt_per_kwh"]
        for row in plan
    )

    calculated_peak = max(
        row["grid_kwh"]
        for row in plan
    )

    assert _close(
        result["total_grid_kwh"],
        calculated_grid,
    )

    assert _close(
        result["total_cost_bdt"],
        calculated_cost,
    )

    assert _close(
        result["peak_grid_kwh"],
        calculated_peak,
    )
