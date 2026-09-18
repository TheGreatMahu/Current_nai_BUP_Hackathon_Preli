"""Pydantic models: request validation + response contract (Problem Statement §07, §10)."""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Strict numbers: JSON ints/floats accepted; strings, bools, NaN, Infinity rejected.
NonNegFloat = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
StrictStr = Annotated[str, Field(strict=True)]

DirectiveType = Literal[
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
]
BatteryAction = Literal["charge", "discharge", "idle"]


# --------------------------------------------------------------------------- #
# Request
# --------------------------------------------------------------------------- #
class HourEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hour: Annotated[int, Field(strict=True, ge=0, le=23)]
    demand_kwh: NonNegFloat
    solar_kwh: NonNegFloat
    tariff_bdt_per_kwh: NonNegFloat


class Battery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    capacity_kwh: NonNegFloat
    initial_energy_kwh: NonNegFloat
    minimum_energy_kwh: NonNegFloat
    max_charge_kwh_per_hour: NonNegFloat
    max_discharge_kwh_per_hour: NonNegFloat

    @model_validator(mode="after")
    def _check_bounds(self) -> "Battery":
        if self.minimum_energy_kwh > self.capacity_kwh:
            raise ValueError("battery.minimum_energy_kwh must not exceed capacity_kwh")
        if not (self.minimum_energy_kwh <= self.initial_energy_kwh <= self.capacity_kwh):
            raise ValueError(
                "battery.initial_energy_kwh must be between minimum_energy_kwh and capacity_kwh"
            )
        return self


class OptimizeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scenario_id: StrictStr = Field(min_length=1)
    operator_notes: Annotated[List[StrictStr], Field(min_length=1, max_length=3)]
    hours: Annotated[List[HourEntry], Field(min_length=24, max_length=24)]
    battery: Battery

    @model_validator(mode="after")
    def _check_fields(self) -> "OptimizeRequest":
        if not self.scenario_id.strip():
            raise ValueError("scenario_id must not be blank")
        if any(not n.strip() for n in self.operator_notes):
            raise ValueError("operator_notes must contain non-empty strings")
        if sorted(h.hour for h in self.hours) != list(range(24)):
            raise ValueError("hours must contain each hour 0..23 exactly once")
        self.hours = sorted(self.hours, key=lambda h: h.hour)
        return self


# --------------------------------------------------------------------------- #
# Response
# --------------------------------------------------------------------------- #
class DirectiveInterpretation(BaseModel):
    note_index: int
    applies: bool
    directive_type: DirectiveType
    structured_adjustment: Optional[Dict[str, Any]] = None
    explanation: str


class HourlyPlanEntry(BaseModel):
    hour: int
    grid_kwh: float
    solar_used_kwh: float
    battery_action: BatteryAction
    battery_kwh: float
    battery_energy_after_kwh: float


class OptimizeResponse(BaseModel):
    scenario_id: str
    directive_interpretation: List[DirectiveInterpretation]
    hourly_plan: List[HourlyPlanEntry]
    total_grid_kwh: float
    total_cost_bdt: float
    peak_grid_kwh: float
    plan_summary: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
