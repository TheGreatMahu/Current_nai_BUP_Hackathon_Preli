"""POST /optimize-energy — validation is done by Pydantic (OptimizeRequest).

`run_pipeline` is the seam for the rest of the team:
    LLM interpreter -> guardrail validator -> optimizer -> final validator.
Right now it is a DEMO stub: no directives applied, battery idle.
"""
from fastapi import APIRouter

from app.schemas import (
    DirectiveInterpretation,
    HourlyPlanEntry,
    OptimizeRequest,
    OptimizeResponse,
)

router = APIRouter()


def run_pipeline(req: OptimizeRequest) -> OptimizeResponse:
    # TODO(team): replace with llm.interpret(...) -> guardrails -> optimizer.solve(...)
    interpretation = [
        DirectiveInterpretation(
            note_index=i,
            applies=False,
            directive_type="no_op",
            structured_adjustment=None,
            explanation="Demo stub: LLM interpreter not connected yet.",
        )
        for i, _ in enumerate(req.operator_notes)
    ]

    energy = req.battery.initial_energy_kwh
    plan = []
    for h in req.hours:
        solar_used = min(h.solar_kwh, h.demand_kwh)
        plan.append(
            HourlyPlanEntry(
                hour=h.hour,
                grid_kwh=round(h.demand_kwh - solar_used, 6),
                solar_used_kwh=solar_used,
                battery_action="idle",
                battery_kwh=0,
                battery_energy_after_kwh=energy,
            )
        )

    tariff = {h.hour: h.tariff_bdt_per_kwh for h in req.hours}
    return OptimizeResponse(
        scenario_id=req.scenario_id,
        directive_interpretation=interpretation,
        hourly_plan=plan,
        total_grid_kwh=round(sum(p.grid_kwh for p in plan), 6),
        total_cost_bdt=round(sum(p.grid_kwh * tariff[p.hour] for p in plan), 6),
        peak_grid_kwh=max(p.grid_kwh for p in plan),
        plan_summary="Demo plan: solar used directly, battery idle, remainder from grid.",
    )


@router.post("/optimize-energy", response_model=OptimizeResponse)
def optimize_energy(req: OptimizeRequest) -> OptimizeResponse:
    return run_pipeline(req)
