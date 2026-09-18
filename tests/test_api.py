import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)
CASES = json.loads((Path(__file__).parent / "data" / "public_sample_cases.json").read_text())["cases"]
BASE = CASES[0]["input"]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_public_samples_validate(case):
    r = client.post("/optimize-energy", json=case["input"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == set(case["expected_output"])
    assert body["scenario_id"] == case["input"]["scenario_id"]
    assert len(body["hourly_plan"]) == 24
    assert [e["note_index"] for e in body["directive_interpretation"]] == list(
        range(len(case["input"]["operator_notes"]))
    )


def mutate(fn):
    d = copy.deepcopy(BASE)
    fn(d)
    return d


BAD = {
    "missing_scenario_id": lambda d: d.pop("scenario_id"),
    "blank_scenario_id": lambda d: d.update(scenario_id="  "),
    "no_notes": lambda d: d.update(operator_notes=[]),
    "four_notes": lambda d: d.update(operator_notes=["a", "b", "c", "d"]),
    "blank_note": lambda d: d.update(operator_notes=["ok", "   "]),
    "non_string_note": lambda d: d.update(operator_notes=[5]),
    "23_hours": lambda d: d["hours"].pop(),
    "25_hours": lambda d: d["hours"].append(dict(d["hours"][0])),
    "duplicate_hour": lambda d: d["hours"][5].update(hour=4),
    "hour_out_of_range": lambda d: d["hours"][23].update(hour=24),
    "bool_hour": lambda d: d["hours"][1].update(hour=True),
    "negative_demand": lambda d: d["hours"][3].update(demand_kwh=-1),
    "string_solar": lambda d: d["hours"][3].update(solar_kwh="10"),
    "missing_tariff": lambda d: d["hours"][3].pop("tariff_bdt_per_kwh"),
    "missing_battery": lambda d: d.pop("battery"),
    "initial_above_capacity": lambda d: d["battery"].update(initial_energy_kwh=9999),
    "initial_below_min": lambda d: d["battery"].update(initial_energy_kwh=0),
    "min_above_capacity": lambda d: d["battery"].update(minimum_energy_kwh=9999),
    "negative_rate": lambda d: d["battery"].update(max_charge_kwh_per_hour=-5),
    "missing_battery_field": lambda d: d["battery"].pop("capacity_kwh"),
}


@pytest.mark.parametrize("name", BAD)
def test_invalid_requests_400(name):
    r = client.post("/optimize-energy", json=mutate(BAD[name]))
    assert r.status_code == 400, r.text
    assert "errors" in r.json()


@pytest.mark.parametrize("raw", ['{"scenario_id": ', "", "not json", "[]", "null", '{"a": NaN}'])
def test_malformed_body_400(raw):
    r = client.post("/optimize-energy", content=raw, headers={"Content-Type": "application/json"})
    assert r.status_code == 400, r.text


def test_nan_and_inf_rejected():
    raw = json.dumps(BASE).replace('"demand_kwh": 90', '"demand_kwh": NaN', 1)
    r = client.post("/optimize-energy", content=raw, headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    raw = json.dumps(BASE).replace('"demand_kwh": 90', '"demand_kwh": 1e999', 1)
    r = client.post("/optimize-energy", content=raw, headers={"Content-Type": "application/json"})
    assert r.status_code == 400


def test_unshuffled_hours_ok_and_extra_fields_ignored():
    d = copy.deepcopy(BASE)
    d["hours"].reverse()
    d["extra"] = "ignored"
    r = client.post("/optimize-energy", json=d)
    assert r.status_code == 200
    assert [p["hour"] for p in r.json()["hourly_plan"]] == list(range(24))
