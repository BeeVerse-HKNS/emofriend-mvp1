"""Strategy API — Strategic Awareness Endpoint.

POST /api/v1/strategy — Generate strategic awareness analysis.
"""

from __future__ import annotations

from typing import Any

try:
    from fastapi import APIRouter
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError("FastAPI is required. Install with: pip install fastapi")

from harnessing.emoglyphplay.core.light_dark_balance import LightDarkBalanceEngine, StrategyMode
from harnessing.emoglyphplay.dark_mapping import EasternDarkMapper, StrategyGenerator, WesternDarkMapper

router = APIRouter()


class StrategyRequest(BaseModel):
    """Request body for the strategy endpoint."""

    situation: str = Field(..., min_length=1, description="Situation or task to analyze.")
    mode: str = Field("balanced", pattern="^(light|balanced|dark)$",
                      description="Strategy disclosure mode.")
    origin: str = Field("all", pattern="^(eastern|western|all)$",
                        description="Strategy tradition origin filter.")
    context_override: dict[str, Any] | None = Field(None, description="Optional context overrides.")


class StrategyResponse(BaseModel):
    """Response body for the strategy endpoint."""

    situation: str
    mode: str
    context: dict[str, Any]
    light_strategies: list[dict[str, Any]]
    dark_strategies: list[dict[str, Any]]
    balance_score: float
    eastern_catalog_count: int
    western_catalog_count: int
    generated_strategies: list[dict[str, Any]]


@router.post("/", response_model=StrategyResponse)
async def generate_strategy(request: StrategyRequest) -> StrategyResponse:
    """Generate strategic awareness analysis.

    Combines LightDarkBalance analysis with Eastern and Western
    strategy catalogs for comprehensive strategic awareness.
    """
    mode_map = {
        "light": StrategyMode.LIGHT,
        "balanced": StrategyMode.BALANCED,
        "dark": StrategyMode.DARK,
    }
    mode = mode_map[request.mode]

    # LightDarkBalance analysis
    engine = LightDarkBalanceEngine()
    result = engine.analyze(request.situation, mode=mode, context_override=request.context_override)

    # Strategy generation
    generator = StrategyGenerator()
    generated = generator.generate(request.situation, context_override=request.context_override)

    # Catalog counts
    eastern = EasternDarkMapper()
    western = WesternDarkMapper()
    eastern_count = len(eastern.get_strategies())
    western_count = len(western.get_strategies())

    return StrategyResponse(
        situation=request.situation,
        mode=request.mode,
        context=result.context_snapshot.to_dict(),
        light_strategies=[s.to_dict() for s in result.light_strategies],
        dark_strategies=[s.to_dict() for s in result.dark_strategies],
        balance_score=result.balance_score,
        eastern_catalog_count=eastern_count,
        western_catalog_count=western_count,
        generated_strategies=[s.to_dict() for s in generated],
    )
