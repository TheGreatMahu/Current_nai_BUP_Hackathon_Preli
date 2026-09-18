# GridWise

## LLM-Assisted Energy Optimization for Smart Campuses

GridWise turns operational instructions written in natural language into a validated, cost-aware 24-hour energy schedule. It combines an LLM directive interpreter with deterministic guardrails and a linear-programming optimizer for solar utilization, battery dispatch, grid purchasing, and operational constraints.

This project was built for the **BUP CSE Fest 2026 Hackathon - Online Preliminary**. The design is intentionally hybrid: language models interpret intent, while deterministic validation and mathematical optimization decide what is physically and operationally feasible.

## Why GridWise

Campus energy operations change throughout the day. A facilities operator may write:

> Keep at least 120 kWh in reserve from 6 PM until 9 PM.

GridWise translates that instruction into a machine-checkable constraint, optimizes the schedule against hourly tariffs, and returns an auditable plan with the exact directive interpretation, hourly actions, total grid usage, cost, and peak import.

### Core strengths

- **Natural-language operations:** supports plain-language operator notes.
- **Deterministic safety boundary:** LLM output is validated before it can affect optimization.
- **Constraint-aware scheduling:** respects demand, solar, battery capacity, charge/discharge rates, reserves, and grid caps.
- **Cost optimization:** minimizes total grid electricity cost across a 24-hour horizon.
- **Replay validation:** independently replays the generated plan against the same rules before returning it.
- **Judge-friendly output:** returns a stable, machine-checkable response contract.

## System Overview

```text
+--------------------------+
| Operator or campus system|
+------------+-------------+
			 |
			 v
+--------------------------+
| FastAPI endpoint         |
+------------+-------------+
			 |
			 v
+--------------------------+
| Pydantic request         |
| validation               |
+------------+-------------+
			 |
			 v
+--------------------------+
| LLM directive            |
| interpreter              |
+------------+-------------+
			 |
			 v
+--------------------------+
| Deterministic            |
| guardrails               |
+------------+-------------+
			 |
			 v
+--------------------------+
| Directive application    |
| layer                    |
+------------+-------------+
			 |
			 v
+--------------------------+
| PuLP/CBC optimizer       |
+------------+-------------+
			 |
			 v
+--------------------------+
| Independent replay       |
| validator                |
+------------+-------------+
			 |
			 v
+--------------------------+
| Recalculate totals       |
+------------+-------------+
			 |
			 v
+--------------------------+
| Auditable optimization   |
| response                 |
+--------------------------+
```

The repository currently contains both the public API implementation and the completed optimization pipeline. The API endpoint is still wired to a demonstration implementation that keeps the battery idle; the production pipeline is implemented in `app/optimizer/pipeline.py` and is documented as the intended integration path. See [Architecture](docs/ARCHITECTURE.md#implementation-status).

## Repository Guide

| Area                                 | Responsibility                                      | Documentation                              |
| ------------------------------------ | --------------------------------------------------- | ------------------------------------------ |
| `app/main.py`                        | FastAPI application and error handling              | [API module guide](app/README.md)          |
| `app/schemas.py`                     | Strict request and response models                  | [API contract](docs/API.md)                |
| `app/api/`                           | HTTP route handlers                                 | [API module guide](app/README.md)          |
| `app/llm/`                           | LLM interpretation and output guardrails            | [Architecture](docs/ARCHITECTURE.md)       |
| `app/optimizer/directive_applier.py` | Converts directives into hourly constraints         | [Optimizer guide](app/optimizer/README.md) |
| `app/optimizer/optimizer.py`         | LP model, solver, replay validation, totals         | [Optimizer guide](app/optimizer/README.md) |
| `app/optimizer/pipeline.py`          | End-to-end deterministic optimization orchestration | [Architecture](docs/ARCHITECTURE.md)       |
| `tests/`                             | API validation and public contract tests            | [Development guide](docs/DEVELOPMENT.md)   |

## Quick Start

### 1. Create an environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The LLM and LP modules additionally require the packages used by their imports (`groq`, `python-dotenv`, and `pulp`) and a configured `GROQ_API_KEY` when those paths are executed. The current public API tests exercise the FastAPI contract without making an external LLM call.

### 2. Start the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Useful endpoints:

- `GET http://localhost:8000/health`
- `POST http://localhost:8000/optimize-energy`
- Interactive OpenAPI documentation: `http://localhost:8000/docs`

### 3. Run tests

```bash
python -m pytest -q
```

## API At A Glance

`POST /optimize-energy` accepts:

- one `scenario_id`;
- one to three non-empty `operator_notes`;
- exactly 24 hourly demand, solar, and tariff records;
- battery capacity, initial state, reserve, and rate limits.

The response contains:

- one structured interpretation per operator note;
- 24 hourly schedule entries;
- total grid energy;
- total cost in BDT;
- peak hourly grid import;
- a human-readable plan summary.

See the complete field-by-field contract and example in [docs/API.md](docs/API.md).

## Directive Language

The interpreter supports six directive types:

| Directive                 | Effect                                                                          |
| ------------------------- | ------------------------------------------------------------------------------- |
| `solar_reduction`         | Reduces usable solar during selected hours. `factor` is the fraction remaining. |
| `minimum_battery_reserve` | Raises the minimum battery energy during selected hours.                        |
| `no_charge_window`        | Prevents battery charging during selected hours.                                |
| `no_discharge_window`     | Prevents battery discharging during selected hours.                             |
| `max_grid_window`         | Caps grid import during selected hours.                                         |
| `no_op`                   | Marks a note as irrelevant to today's energy schedule.                          |

Time windows are start-inclusive and end-exclusive. For example, 1 PM to 3 PM maps to `[13, 14]`.

## Optimization Model

For each hour $h$, GridWise solves for grid energy $G_h$, solar used $S_h$, battery charge $C_h$, battery discharge $D_h$, and battery energy after the hour $E_h$.

The model minimizes:

$$
\min \sum_{h=0}^{23} G_h \times tariff_h
$$

Subject to the hourly energy balance:

$$
G_h + S_h + D_h = demand_h + C_h
$$

and battery transition:

$$
E_h = E_{h-1} + C_h - D_h
$$

The schedule also enforces battery bounds, hourly charge/discharge limits, directive-derived constraints, and end-of-day neutrality:

$$
E_{23} = E_{initial}
$$

The full model and validation rules are explained in [app/optimizer/README.md](app/optimizer/README.md).

## Quality And Safety Design

GridWise does not trust raw model output. The guardrail layer requires the exact number of note interpretations, preserves note order, restricts directive types, validates hour windows, and checks directive-specific numeric fields. The optimizer then produces a schedule that is independently replayed before totals are calculated from the returned hourly plan.

This separation gives the project a defensible architecture:

```text
Probabilistic interpretation -> deterministic validation -> deterministic optimization -> deterministic replay
```

## Documentation

- [Architecture and data flow](docs/ARCHITECTURE.md)
- [API contract and examples](docs/API.md)
- [Development and testing](docs/DEVELOPMENT.md)
- [Application module guide](app/README.md)
- [Optimizer module guide](app/optimizer/README.md)

## Project Status

The API validation layer, response contract, directive guardrails, directive application layer, LP optimizer, replay validator, and public sample case materials are present in the repository.

The remaining integration step is to connect `app/api/optimize.py` to the LLM interpreter and `app/optimizer/pipeline.py`. Until that wiring is completed, the live endpoint returns the documented demo schedule with direct solar usage and an idle battery. This status is intentionally visible so evaluators and contributors can distinguish the stable contract from the integration work.

## License

No license file is currently included. Add the team or event-approved license before distributing the project outside the hackathon submission.
