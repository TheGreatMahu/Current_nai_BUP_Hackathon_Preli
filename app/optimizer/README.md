# Optimizer Layer

The `app/optimizer/` package converts validated operator directives into hourly constraints, solves the energy schedule, validates the resulting plan, and calculates response totals.

## Pipeline

```text
request_body + directive_interpretations
        |
        v
build_optimizer_inputs()
        |
        +--> ScenarioInput
        +--> ParsedDirective[]
        +--> DerivedConstraints
                         |
                         v
                   solve_schedule()
                         |
                         v
                   replay_validate()
                         |
                         v
                   recalculate_totals()
```

## `directive_applier.py`

`ScenarioInput` stores the 24-hour demand, solar, tariff, and battery parameters. `ParsedDirective` stores one validated directive. `DerivedConstraints` contains the five hourly arrays consumed by the solver:

- `effective_solar`;
- `active_min_battery`;
- `charge_allowed`;
- `discharge_allowed`;
- `grid_max`.

`apply_directives` starts from unconstrained defaults and applies only directives where `applies` is true. Overlapping constraints resolve using the most restrictive value.

## `optimizer.py`

The solver uses PuLP with CBC. For every hour it creates:

- `G`: grid energy;
- `S`: solar energy used;
- `C`: battery charge;
- `D`: battery discharge;
- `E`: battery energy after the hour.

The objective is total grid cost:

```text
minimize sum(G[h] * tariff[h])
```

The model enforces energy balance, battery state transitions, bounds, directive restrictions, and final battery neutrality. The result is rounded into the public response format.

## Replay Validation

`replay_validate` is intentionally independent from the solver model. It checks the serialized hourly plan that will be returned to the caller, including the effects of rounding. It rejects invalid hour counts, negative quantities, solar overuse, grid-cap violations, rate violations, forbidden actions, energy-balance errors, battery-state errors, reserve violations, and end-of-day imbalance.

## `pipeline.py`

`run_optimization_pipeline` is the orchestration entry point. It accepts raw request data, validated directive interpretations, and an optional solver time limit with a default of 15 seconds. It refuses infeasible solver statuses and refuses any plan that fails replay validation.

## Practical Notes

- The optimizer is deterministic for fixed inputs and solver configuration.
- Battery charge/discharge variables are continuous.
- The current model relies on cost minimization to avoid simultaneous charge and discharge; binary action variables can be introduced later if a strict operational guarantee is required.
- The API currently does not invoke this pipeline; see the root README and [architecture documentation](../../docs/ARCHITECTURE.md#implementation-status).
