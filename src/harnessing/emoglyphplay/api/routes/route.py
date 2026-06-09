"""Route API — Intelligent Routing Endpoint.

POST /api/v1/route — Route a task through the intelligent routing engine.
"""

from __future__ import annotations

from typing import Any

try:
    from fastapi import APIRouter
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError("FastAPI is required. Install with: pip install fastapi")

from harnessing.emoglyphplay.core.ethics_guard import EthicsGuard
from harnessing.emoglyphplay.core.light_dark_balance import LightDarkBalanceEngine, StrategyMode
from harnessing.emoglyphplay.core.token_saver import TokenSaver

router = APIRouter()


class RouteRequest(BaseModel):
    """Request body for the route endpoint."""

    task: str = Field(..., min_length=1, description="Task description to route.")
    mode: str = Field("balanced", pattern="^(light|balanced|dark)$",
                      description="Strategy mode: light/balanced/dark.")
    save_tokens: bool = Field(True, description="Enable token optimization.")
    context_override: dict[str, Any] | None = Field(None, description="Optional context overrides.")


class RouteResponse(BaseModel):
    """Response body for the route endpoint."""

    task: str
    mode: str
    light_strategies: list[dict[str, Any]]
    dark_strategies: list[dict[str, Any]]
    balance_score: float
    context: dict[str, Any]
    token_savings: dict[str, Any] | None = None
    ethics_check: dict[str, Any] | None = None


@router.post("/", response_model=RouteResponse)
async def route_task(request: RouteRequest) -> RouteResponse:
    """Route a task through the intelligent routing engine.

    Applies LightDarkBalance analysis, token optimization, and
    ethics checking to provide strategic recommendations.
    """
    # Map mode string to enum
    mode_map = {
        "light": StrategyMode.LIGHT,
        "balanced": StrategyMode.BALANCED,
        "dark": StrategyMode.DARK,
    }
    mode = mode_map[request.mode]

    # Run LightDarkBalance analysis
    engine = LightDarkBalanceEngine()
    result = engine.analyze(request.task, mode=mode, context_override=request.context_override)

    # Token savings estimate
    token_savings = None
    if request.save_tokens:
        saver = TokenSaver()
        token_savings = saver.estimate_savings(len(request.task.split()), "general")

    # Ethics check on all strategies
    ethics_guard = EthicsGuard()
    ethics_violations = []
    for s in result.all_strategies:
        check = ethics_guard.check(f"{s.name} {s.description}")
        if not check.is_ethical:
            ethics_violations.append(check.to_dict())

    ethics_check = {
        "total_strategies": len(result.all_strategies),
        "violations": len(ethics_violations),
        "violation_details": ethics_violations,
    } if ethics_violations else {
        "total_strategies": len(result.all_strategies),
        "violations": 0,
    }

    return RouteResponse(
        task=request.task,
        mode=request.mode,
        light_strategies=[s.to_dict() for s in result.light_strategies],
        dark_strategies=[s.to_dict() for s in result.dark_strategies],
        balance_score=result.balance_score,
        context=result.context_snapshot.to_dict(),
        token_savings=token_savings,
        ethics_check=ethics_check,
    )
