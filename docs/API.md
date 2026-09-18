# GridWise API Contract

## Base URL

When running locally:

```text
http://localhost:8000
```

## Health Check

### `GET /health`

Response:

```json
{
  "status": "ok"
}
```

## Optimize Energy

### `POST /optimize-energy`

Content type:

```text
application/json
```

The request must include exactly 24 unique hourly records covering `0` through `23`. The API sorts valid hourly records by hour before processing.

### Request shape

```json
{
  "scenario_id": "campus-day-001",
  "operator_notes": [
    "Do not charge the battery between 2 PM and 4 PM.",
    "Keep at least 120 kWh in reserve from 6 PM until 9 PM."
  ],
  "hours": [
    {
      "hour": 0,
      "demand_kwh": 90,
      "solar_kwh": 0,
      "tariff_bdt_per_kwh": 6
    }
  ],
  "battery": {
    "capacity_kwh": 500,
    "initial_energy_kwh": 200,
    "minimum_energy_kwh": 50,
    "max_charge_kwh_per_hour": 100,
    "max_discharge_kwh_per_hour": 100
  }
}
```

The `hours` array above is abbreviated for readability; a real request must contain all 24 hours.

### Request fields

| Field                                | Type         | Rules                                      |
| ------------------------------------ | ------------ | ------------------------------------------ |
| `scenario_id`                        | string       | Non-empty and not whitespace-only          |
| `operator_notes`                     | string array | 1 to 3 non-empty strings                   |
| `hours`                              | object array | Exactly 24 records, one for each hour 0-23 |
| `hours[].demand_kwh`                 | number       | Strict, finite, non-negative               |
| `hours[].solar_kwh`                  | number       | Strict, finite, non-negative               |
| `hours[].tariff_bdt_per_kwh`         | number       | Strict, finite, non-negative               |
| `battery.capacity_kwh`               | number       | Strict, finite, non-negative               |
| `battery.initial_energy_kwh`         | number       | Between minimum and capacity               |
| `battery.minimum_energy_kwh`         | number       | Must not exceed capacity                   |
| `battery.max_charge_kwh_per_hour`    | number       | Strict, finite, non-negative               |
| `battery.max_discharge_kwh_per_hour` | number       | Strict, finite, non-negative               |

### Response shape

```json
{
  "scenario_id": "campus-day-001",
  "directive_interpretation": [
    {
      "note_index": 0,
      "applies": true,
      "directive_type": "no_charge_window",
      "structured_adjustment": {
        "hours": [14, 15]
      },
      "explanation": "Charging disabled."
    }
  ],
  "hourly_plan": [
    {
      "hour": 0,
      "grid_kwh": 90,
      "solar_used_kwh": 0,
      "battery_action": "idle",
      "battery_kwh": 0,
      "battery_energy_after_kwh": 200
    }
  ],
  "total_grid_kwh": 0,
  "total_cost_bdt": 0,
  "peak_grid_kwh": 0,
  "plan_summary": "..."
}
```

### Directive response fields

`directive_interpretation` contains exactly one entry per input note, in the same order. Allowed `directive_type` values are:

- `solar_reduction`: `{ "hours": [..], "factor": 0..1 }`
- `minimum_battery_reserve`: `{ "hours": [..], "minimum_energy_kwh": number }`
- `no_charge_window`: `{ "hours": [..] }`
- `no_discharge_window`: `{ "hours": [..] }`
- `max_grid_window`: `{ "hours": [..], "max_grid_kwh": number }`
- `no_op`: `null`

For `no_op`, `applies` must be `false`. For all other directive types, `applies` must be `true`.

### Hourly plan rules

For each hour:

```text
grid_kwh + solar_used_kwh + battery_discharge_kwh
= demand_kwh + battery_charge_kwh
```

`battery_action` is one of `charge`, `discharge`, or `idle`. `battery_kwh` is the amount for that action and must be zero for `idle`. Battery energy must stay within its active minimum and capacity, and hour 23 must end at the initial battery energy.

### Errors

Malformed JSON or schema violations return:

```json
{
  "detail": "Invalid request",
  "errors": [
    {
      "loc": "hours",
      "msg": "..."
    }
  ]
}
```

Unexpected server errors return a generic `500` response without stack traces.
