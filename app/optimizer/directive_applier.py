"""
Directive Application Layer
===========================
Takes validated LLM directive interpretations and builds the derived parameter
arrays that the optimizer consumes.

This module is the bridge between the LLM guardrail output and the LP solver.
It does NOT call the LLM — it only processes already-validated structured directives.

Derived parameter arrays produced (all length-24):
  - effective_solar[h]       : solar available after solar_reduction
  - active_min_battery[h]    : battery floor (max of base minimum and any reserve directive)
  - charge_allowed[h]        : 1 if charging permitted, 0 if blocked by no_charge_window
  - discharge_allowed[h]     : 1 if discharging permitted, 0 if blocked by no_discharge_window
  - grid_max[h]              : upper bound on grid import (inf unless max_grid_window applies)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional


# ─────────────────────────────────────────────
#  Data classes for typed directive structures
# ─────────────────────────────────────────────

@dataclass
class SolarReduction:
    hours: list[int]
    factor: float  # usable fraction remaining (0.2 means 80% reduction)


@dataclass
class MinimumBatteryReserve:
    hours: list[int]
    minimum_energy_kwh: float


@dataclass
class NoChargeWindow:
    hours: list[int]


@dataclass
class NoDischargeWindow:
    hours: list[int]


@dataclass
class MaxGridWindow:
    hours: list[int]
    max_grid_kwh: float


@dataclass
class ParsedDirective:
    """One fully validated directive from the LLM guardrail layer."""
    note_index: int
    applies: bool
    directive_type: str  # one of the 6 enum values
    structured_adjustment: Optional[
        SolarReduction | MinimumBatteryReserve |
        NoChargeWindow | NoDischargeWindow | MaxGridWindow
    ]
    explanation: str


# ─────────────────────────────────────────────
#  Scenario input data class
# ─────────────────────────────────────────────

@dataclass
class ScenarioInput:
    """All input parameters extracted from the POST request."""
    scenario_id: str
    # Hourly arrays — all length 24
    demand: list[float]       # demand_kwh per hour
    solar: list[float]        # solar_kwh per hour (raw forecast)
    tariff: list[float]       # tariff_bdt_per_kwh per hour
    # Battery parameters
    capacity_kwh: float       # B_max
    initial_energy_kwh: float # B_init
    minimum_energy_kwh: float # B_min
    max_charge_kwh_per_hour: float   # C_max
    max_discharge_kwh_per_hour: float # D_max

    @classmethod
    def from_request(cls, body: dict) -> "ScenarioInput":
        """Parse a POST /optimize-energy JSON body into a ScenarioInput."""
        hours_data = sorted(body["hours"], key=lambda h: h["hour"])
        bat = body["battery"]
        return cls(
            scenario_id=body["scenario_id"],
            demand=[h["demand_kwh"] for h in hours_data],
            solar=[h["solar_kwh"] for h in hours_data],
            tariff=[h["tariff_bdt_per_kwh"] for h in hours_data],
            capacity_kwh=bat["capacity_kwh"],
            initial_energy_kwh=bat["initial_energy_kwh"],
            minimum_energy_kwh=bat["minimum_energy_kwh"],
            max_charge_kwh_per_hour=bat["max_charge_kwh_per_hour"],
            max_discharge_kwh_per_hour=bat["max_discharge_kwh_per_hour"],
        )


# ─────────────────────────────────────────────
#  Derived constraint arrays (optimizer input)
# ─────────────────────────────────────────────

@dataclass
class DerivedConstraints:
    """
    The complete set of hourly constraint arrays that the optimizer needs.
    Produced by applying all validated directives onto the raw scenario.
    """
    effective_solar: list[float]        # length 24
    active_min_battery: list[float]     # length 24
    charge_allowed: list[int]           # length 24, values 0 or 1
    discharge_allowed: list[int]        # length 24, values 0 or 1
    grid_max: list[float]              # length 24, can be math.inf


# ─────────────────────────────────────────────
#  Directive parser (dict → typed dataclass)
# ─────────────────────────────────────────────

def parse_directive(raw: dict) -> ParsedDirective:
    """
    Convert one validated directive_interpretation dict from the guardrail
    layer into a typed ParsedDirective.
    """
    dtype = raw["directive_type"]
    adj_raw = raw.get("structured_adjustment")
    adjustment = None

    if dtype == "solar_reduction" and adj_raw is not None:
        adjustment = SolarReduction(
            hours=adj_raw["hours"],
            factor=adj_raw["factor"],
        )
    elif dtype == "minimum_battery_reserve" and adj_raw is not None:
        adjustment = MinimumBatteryReserve(
            hours=adj_raw["hours"],
            minimum_energy_kwh=adj_raw["minimum_energy_kwh"],
        )
    elif dtype == "no_charge_window" and adj_raw is not None:
        adjustment = NoChargeWindow(hours=adj_raw["hours"])
    elif dtype == "no_discharge_window" and adj_raw is not None:
        adjustment = NoDischargeWindow(hours=adj_raw["hours"])
    elif dtype == "max_grid_window" and adj_raw is not None:
        adjustment = MaxGridWindow(
            hours=adj_raw["hours"],
            max_grid_kwh=adj_raw["max_grid_kwh"],
        )
    elif dtype == "no_op":
        adjustment = None  # explicitly null
    # else: unknown type — should have been caught by guardrails

    return ParsedDirective(
        note_index=raw["note_index"],
        applies=raw["applies"],
        directive_type=dtype,
        structured_adjustment=adjustment,
        explanation=raw.get("explanation", ""),
    )


# ─────────────────────────────────────────────
#  Core: apply directives → DerivedConstraints
# ─────────────────────────────────────────────

def apply_directives(
    scenario: ScenarioInput,
    directives: list[ParsedDirective],
) -> DerivedConstraints:
    """
    Apply all validated directives to produce the derived constraint arrays
    that feed into the LP optimizer.

    This function handles overlapping directives on the same hour correctly:
      - Multiple solar_reduction on the same hour: uses the MINIMUM factor
        (most restrictive).
      - Multiple minimum_battery_reserve on the same hour: uses the MAXIMUM
        reserve (most restrictive).
      - Multiple no_charge / no_discharge on the same hour: still blocked.
      - Multiple max_grid_window on the same hour: uses the MINIMUM cap
        (most restrictive).
    """
    H = 24

    # ── 1. Start with defaults ──
    effective_solar = list(scenario.solar)  # copy of raw forecast
    active_min_battery = [scenario.minimum_energy_kwh] * H
    charge_allowed = [1] * H
    discharge_allowed = [1] * H
    grid_max = [math.inf] * H

    # ── 2. Walk every applicable directive ──
    for d in directives:
        if not d.applies or d.directive_type == "no_op":
            continue

        adj = d.structured_adjustment
        if adj is None:
            continue  # safety — shouldn't happen after guardrails

        if isinstance(adj, SolarReduction):
            for h in adj.hours:
                # effective_solar = raw_solar * factor
                reduced = scenario.solar[h] * adj.factor
                # If multiple reductions overlap, keep the MORE restrictive one
                effective_solar[h] = min(effective_solar[h], reduced)

        elif isinstance(adj, MinimumBatteryReserve):
            for h in adj.hours:
                # Raise floor to max(base_min, directive_reserve)
                active_min_battery[h] = max(
                    active_min_battery[h],
                    adj.minimum_energy_kwh,
                )

        elif isinstance(adj, NoChargeWindow):
            for h in adj.hours:
                charge_allowed[h] = 0

        elif isinstance(adj, NoDischargeWindow):
            for h in adj.hours:
                discharge_allowed[h] = 0

        elif isinstance(adj, MaxGridWindow):
            for h in adj.hours:
                grid_max[h] = min(grid_max[h], adj.max_grid_kwh)

    return DerivedConstraints(
        effective_solar=effective_solar,
        active_min_battery=active_min_battery,
        charge_allowed=charge_allowed,
        discharge_allowed=discharge_allowed,
        grid_max=grid_max,
    )


# ─────────────────────────────────────────────
#  Convenience: full pipeline entry point
# ─────────────────────────────────────────────

def build_optimizer_inputs(
    request_body: dict,
    directive_interpretations: list[dict],
) -> tuple[ScenarioInput, list[ParsedDirective], DerivedConstraints]:
    """
    One-call convenience function used by the API handler.

    Args:
        request_body: the raw POST /optimize-energy JSON body
        directive_interpretations: list of dicts from the LLM guardrail layer

    Returns:
        (scenario, parsed_directives, derived_constraints)
    """
    scenario = ScenarioInput.from_request(request_body)
    parsed = [parse_directive(d) for d in directive_interpretations]
    constraints = apply_directives(scenario, parsed)
    return scenario, parsed, constraints
