"""FastAPI entry point.  Run:  uvicorn app.main:app --host 0.0.0.0 --port 8000"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import health, optimize

app = FastAPI(title="GridWise LLM", version="0.1.0")
app.include_router(health.router)
app.include_router(optimize.router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Malformed JSON / schema violations -> 400 (spec §6.1). Never echo input values."""
    errors = [
        {"loc": ".".join(str(p) for p in e.get("loc", ())), "msg": str(e.get("msg", "invalid"))}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=400, content={"detail": "Invalid request", "errors": errors})


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, __: Exception) -> JSONResponse:
    """Controlled 500: no stack trace, no secrets."""
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
