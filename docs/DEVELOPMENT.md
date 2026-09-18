# Development Guide

## Environment

GridWise targets Python 3 with FastAPI, Pydantic, Uvicorn, HTTPX, and Pytest. The LP and LLM modules also import PuLP, Groq, and python-dotenv.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For the LLM path, configure the API key outside source control:

```bash
export GROQ_API_KEY="your-key"
```

Never commit `.env` files, API keys, solver logs containing sensitive data, or real campus operational data.

## Run Locally

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000/docs` for the generated OpenAPI UI.

## Test Strategy

The current test suite focuses on the public API contract:

- health endpoint behavior;
- valid public sample requests;
- missing, malformed, duplicated, or out-of-range fields;
- strict number handling, including NaN and infinity rejection;
- shuffled hour input and ignored extra fields.

Run:

```bash
python -m pytest -q
```

The next high-value tests for full integration are:

1. guardrail acceptance and rejection for every directive type;
2. overlapping directive resolution;
3. battery charge/discharge rate limits;
4. end-of-day neutrality;
5. replay rejection of a deliberately invalid schedule;
6. solver behavior under max-grid and reserve constraints;
7. API integration from operator notes through the LP pipeline.

## Code Organization Rules

- Keep Pydantic validation at the API boundary.
- Keep LLM parsing separate from directive application.
- Pass only validated, structured directives into the optimizer.
- Keep solver constraints explicit and independently replayable.
- Recalculate response totals from the returned hourly plan.
- Avoid embedding API keys or model-specific assumptions in optimization code.
- Preserve the public response field names and enum values.

## Working With Public Cases

The public case pack is stored in `tests/data/public_sample_cases.json`. It includes natural-language notes, expected directive semantics, and valid reference schedules. Equivalent optimal schedules are acceptable; a solution does not need to reproduce one exact hourly action sequence.

The standalone `test_public_cases.py` script exercises the LLM interpreter against `app/llm/public_class.json` and compares directive types. It requires the LLM dependencies and a working `GROQ_API_KEY`.

## Pull Request Checklist

- [ ] Request and response contracts remain compatible.
- [ ] New behavior has a focused test.
- [ ] Directive interpretation is deterministic after validation.
- [ ] Solver output passes independent replay validation.
- [ ] No secrets or real operational data are included.
- [ ] Documentation explains new fields, constraints, and failure modes.
