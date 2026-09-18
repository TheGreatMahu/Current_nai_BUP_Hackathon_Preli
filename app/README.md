# Application Layer

The `app/` package contains the HTTP service boundary, validation schemas, and natural-language directive interpretation components.

## Modules

### `main.py`

Creates the FastAPI application, registers the health and optimization routers, and defines controlled error handlers.

### `schemas.py`

Defines the request and response models. Validation is strict by design:

- exactly 24 unique hours from 0 to 23;
- one to three non-empty operator notes;
- finite, non-negative numeric values;
- battery initial energy between minimum and capacity;
- stable directive and battery-action enums.

### `api/health.py`

Provides the service health endpoint.

### `api/optimize.py`

Provides `POST /optimize-energy`. The current handler contains a demonstration implementation that uses solar directly and leaves the battery idle. The intended production handler should connect the LLM interpreter and `app.optimizer.pipeline.run_optimization_pipeline`.

### `llm/llm_interpreter.py`

Builds the structured interpretation prompt, calls Groq, parses JSON, retries failures, and invokes guardrails.

### `llm/guardrails.py`

Performs deterministic validation of every model response before it can influence the optimizer.

## Integration Boundary

The intended API integration is:

```text
OptimizeRequest
  -> interpret_notes(operator_notes, battery_info)
  -> run_optimization_pipeline(request_dict, interpretations)
  -> OptimizeResponse
```

Keep the LLM call outside the mathematical optimizer. This makes the scheduling engine testable with fixed directive dictionaries and avoids allowing unvalidated model output to become solver constraints.
