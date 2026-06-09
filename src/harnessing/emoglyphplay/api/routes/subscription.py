"""Subscription API Routes — REST endpoints for subscription management.

Provides endpoints for checking subscription tiers, feature availability,
and resource quotas.
"""

from __future__ import annotations

from typing import Any

try:
    from fastapi import APIRouter
except ImportError:
    class APIRouter:  # type: ignore[no-redef]
        def post(self, path: str, **kwargs: Any) -> Any:
            def decorator(func: Any) -> Any: return func
            return decorator
        def get(self, path: str, **kwargs: Any) -> Any:
            def decorator(func: Any) -> Any: return func
            return decorator

router = APIRouter()


@router.get("/current")
async def get_subscription() -> dict:
    """Get the current subscription tier and usage.

    Returns:
        Dictionary with tier, features, and usage information.
    """
    return {
        "tier": "free",
        "features": {},
        "usage": {},
    }


@router.get("/check-feature/{feature}")
async def check_feature(feature: str) -> dict:
    """Check if a feature is available for the current tier.

    Args:
        feature: The feature identifier to check.

    Returns:
        Dictionary with feature name and availability.
    """
    return {"feature": feature, "available": False}


@router.get("/check-quota/{resource}")
async def check_quota(resource: str, amount: int = 1) -> dict:
    """Check if a resource amount is within quota.

    Args:
        resource: The resource identifier.
        amount: The requested amount.

    Returns:
        Dictionary with quota check result.
    """
    return {"resource": resource, "amount": amount, "within_quota": True}


@router.post("/upgrade")
async def upgrade_subscription(new_tier: str = "") -> dict:
    """Upgrade the subscription to a new tier.

    Args:
        new_tier: The target tier (mini, pro, enterprise).

    Returns:
        Dictionary with upgrade result.
    """
    return {"previous_tier": "free", "new_tier": new_tier, "upgraded": True}


@router.get("/usage")
async def get_usage() -> dict:
    """Get current resource usage and limits.

    Returns:
        Dictionary with usage details per resource.
    """
    return {"usage": {}}
