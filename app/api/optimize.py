"""POST /optimize-energy endpoint."""

from fastapi import APIRouter

from app.schemas import OptimizeRequest, OptimizeResponse
from app.llm.llm_interpreter import interpret_notes
from app.optimizer.pipeline import run_optimization_pipeline

router = APIRouter()


@router.post("/optimize-energy", response_model=OptimizeResponse)
def optimize_energy(req: OptimizeRequest) -> OptimizeResponse:

    # 1. LLM interprets operator notes
    directive_interpretations = interpret_notes(
        req.operator_notes,
        battery_info=req.battery.model_dump(),
    )

    # 2. Pass the original scenario + LLM result into the optimizer pipeline
    response_body = run_optimization_pipeline(
        request_body=req.model_dump(),
        directive_interpretations=directive_interpretations,
    )

    # 3. Validate/serialize according to the FastAPI response schema
    return OptimizeResponse.model_validate(response_body)