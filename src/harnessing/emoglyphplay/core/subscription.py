"""SubscriptionManager — Tier-based Feature Gating.

Manages subscription tiers and their associated resource limits,
providing feature gating and quota tracking for the EmoGlyphPlay platform.
"""

from __future__ import annotations

from enum import Enum


class SubscriptionTier(Enum):
    """Subscription tier levels."""

    FREE = "free"
    MINI = "mini"
    PRO = "pro"
    ENTERPRISE = "enterprise"


TIER_LIMITS: dict[SubscriptionTier, dict[str, int]] = {
    SubscriptionTier.FREE: {
        "token_quota": 100_000,
        "project_limit": 1,
        "parallel_limit": 1,
        "personality_dims": 4,
        "connector_limit": 3,
    },
    SubscriptionTier.MINI: {
        "token_quota": 1_000_000,
        "project_limit": 3,
        "parallel_limit": 3,
        "personality_dims": 9,
        "connector_limit": 10,
    },
    SubscriptionTier.PRO: {
        "token_quota": 10_000_000,
        "project_limit": -1,
        "parallel_limit": 5,
        "personality_dims": 25,
        "connector_limit": -1,
    },
    SubscriptionTier.ENTERPRISE: {
        "token_quota": -1,
        "project_limit": -1,
        "parallel_limit": -1,
        "personality_dims": 25,
        "connector_limit": -1,
    },
}

# Feature availability matrix per tier
_FEATURE_MAP: dict[str, set[SubscriptionTier]] = {
    "parallel_workspaces": {SubscriptionTier.MINI, SubscriptionTier.PRO, SubscriptionTier.ENTERPRISE},
    "custom_personality": {SubscriptionTier.MINI, SubscriptionTier.PRO, SubscriptionTier.ENTERPRISE},
    "east_west_bridge": {SubscriptionTier.PRO, SubscriptionTier.ENTERPRISE},
    "flow_navigator": {SubscriptionTier.PRO, SubscriptionTier.ENTERPRISE},
    "advanced_connectors": {SubscriptionTier.PRO, SubscriptionTier.ENTERPRISE},
    "priority_support": {SubscriptionTier.ENTERPRISE},
    "custom_deploy": {SubscriptionTier.ENTERPRISE},
    "sso": {SubscriptionTier.ENTERPRISE},
}


class SubscriptionManager:
    """SubscriptionManager — Tier-based Feature Gating.

    Manages subscription tiers, feature availability, and resource quotas
    for the EmoGlyphPlay platform.

    Args:
        user_id: Unique identifier for the user.
        tier: The subscription tier level. Defaults to FREE.
    """

    def __init__(self, user_id: str, tier: SubscriptionTier = SubscriptionTier.FREE) -> None:
        self.user_id = user_id
        self.tier = tier
        self._usage: dict[str, int] = {}

    def check_feature(self, feature: str) -> bool:
        """Check whether a feature is available for the current tier.

        Args:
            feature: The feature identifier to check.

        Returns:
            True if the feature is available at the current tier.
        """
        allowed_tiers = _FEATURE_MAP.get(feature)
        if allowed_tiers is None:
            return True  # Unknown features are allowed by default
        return self.tier in allowed_tiers

    def check_quota(self, resource: str, amount: int) -> bool:
        """Check whether a resource usage amount is within quota.

        Args:
            resource: The resource identifier (e.g., 'token_quota', 'project_limit').
            amount: The requested amount.

        Returns:
            True if the amount is within the allowed quota.
        """
        limits = TIER_LIMITS[self.tier]
        limit = limits.get(resource, -1)
        if limit == -1:
            return True  # Unlimited
        current = self._usage.get(resource, 0)
        return current + amount <= limit

    def consume(self, resource: str, amount: int) -> bool:
        """Consume a resource amount if within quota.

        Args:
            resource: The resource identifier.
            amount: The amount to consume.

        Returns:
            True if the consumption was successful, False if quota exceeded.
        """
        if not self.check_quota(resource, amount):
            return False
        self._usage[resource] = self._usage.get(resource, 0) + amount
        return True

    def get_usage(self) -> dict:
        """Get current resource usage and limits.

        Returns:
            Dictionary with keys per resource: used, limit, remaining.
        """
        limits = TIER_LIMITS[self.tier]
        result: dict[str, dict[str, int]] = {}
        for resource, limit in limits.items():
            used = self._usage.get(resource, 0)
            remaining = -1 if limit == -1 else max(0, limit - used)
            result[resource] = {"used": used, "limit": limit, "remaining": remaining}
        return result

    def upgrade(self, new_tier: SubscriptionTier) -> bool:
        """Upgrade the subscription to a new tier.

        Args:
            new_tier: The target subscription tier.

        Returns:
            True if the upgrade was applied. Downgrades return False.
        """
        tier_order = [
            SubscriptionTier.FREE,
            SubscriptionTier.MINI,
            SubscriptionTier.PRO,
            SubscriptionTier.ENTERPRISE,
        ]
        if tier_order.index(new_tier) <= tier_order.index(self.tier):
            return False  # Not an upgrade
        self.tier = new_tier
        return True
