"""
Pipeline: directive_applier → optimizer → replay validation → response
======================================================================
This module connects the Directive Application Layer with the Math Optimizer
and produces the final API response body.

Usage from your API handler:
    from pipeline import run_optimization_pipeline
    response_body = run_optimization_pipeline(request_json, llm_interpretations)
"""

from __future__ import annotations

from app.optimizer.directive_applier import (
    ScenarioInput,
    ParsedDirective,
    build_optimizer_inputs,
)

from app.optimizer.optimizer import (
    solve_schedule,
    replay_validate,
    recalculate_totals,
)


def run_optimization_pipeline(
    request_body: dict,
    directive_interpretations: list[dict],
    time_limit_seconds: int = 15,
) -> dict:
    """
    Full pipeline: parse → apply directives → solve LP → validate → format response.

    Args:
        request_body: The raw POST /optimize-energy JSON body.
        directive_interpretations: List of validated directive dicts from
                                   the LLM guardrail layer.
        time_limit_seconds: Max solver time.

    Returns:
        A dict matching the exact response schema required by the problem statement.

    Raises:
        ValueError: If the solver fails or replay validation finds errors.
    """

    # ── Step 1: Parse input + apply directives ──
    scenario, parsed_directives, derived = build_optimizer_inputs(
        request_body, directive_interpretations
    )

    # ── Step 2: Solve the LP ──
    result = solve_schedule(scenario, derived, time_limit_seconds)

    if result.status not in ("Optimal", "Feasible"):
        raise ValueError(
            f"Optimizer returned status '{result.status}'. "
            f"No feasible schedule found. Check directive combinations."
        )

    # ── Step 3: Replay validation (mirrors the judge) ──
    validation_errors = replay_validate(scenario, derived, result.hourly_plan)

    if validation_errors:
        error_details = "; ".join(str(e) for e in validation_errors)
        raise ValueError(
            f"Replay validation failed with {len(validation_errors)} error(s): {error_details}"
        )

    # ── Step 4: Recalculate totals from hourly_plan (as the judge does) ──
    total_grid, total_cost, peak_grid = recalculate_totals(
        result.hourly_plan, scenario.tariff
    )

    # ── Step 5: Build response ──
    # Build the plan_summary
    plan_summary = _generate_plan_summary(
        scenario, parsed_directives, total_grid, total_cost, peak_grid
    )

    response = {
        "scenario_id": scenario.scenario_id,
        "directive_interpretation": directive_interpretations,
        "hourly_plan": result.hourly_plan,
        "total_grid_kwh": total_grid,
        "total_cost_bdt": total_cost,
        "peak_grid_kwh": peak_grid,
        "plan_summary": plan_summary,
    }

    return response


def _generate_plan_summary(
    scenario: ScenarioInput,
    directives: list[ParsedDirective],
    total_grid: float,
    total_cost: float,
    peak_grid: float,
) -> str:
    """Generate a human-readable plan_summary string."""
    applied = [d for d in directives if d.applies and d.directive_type != "no_op"]
    ignored = [d for d in directives if d.directive_type == "no_op"]

    parts = []

    if applied:
        directive_names = [d.directive_type.replace("_", " ") for d in applied]
        parts.append(f"Applied {len(applied)} directive(s): {', '.join(directive_names)}.")

    if ignored:
        parts.append(f"Ignored {len(ignored)} irrelevant note(s).")

    parts.append(
        f"Total grid: {total_grid} kWh, cost: {total_cost} BDT, peak: {peak_grid} kWh."
    )

    parts.append(
        "Battery is charged during low-tariff hours and discharged during peak-tariff hours "
        "while respecting all operator directives and returning to initial energy level."
    )

    return " ".join(parts)
