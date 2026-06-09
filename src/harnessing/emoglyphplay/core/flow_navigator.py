"""FlowNavigator — Flow State Navigation Engine.

Formula: Flow = 0.74 ≤ (Challenge/Skill) ≤ 1.34, personality-modulated

Detects and navigates the user's flow state based on the challenge-skill
ratio, modulated by personality vectors. Suggests adjustments to keep
the user in the optimal flow channel.
"""

from __future__ import annotations


class FlowNavigator:
    """FlowNavigator — Flow State Navigation Engine.

    Uses the challenge-skill ratio (C/S) to determine the user's current
    state relative to the flow channel (0.74 ≤ C/S ≤ 1.34), with
    personality-based modulation for individual differences.

    Args:
        personality_vector: Optional personality dimensions for flow modulation.
    """

    FLOW_LOWER = 0.74
    FLOW_UPPER = 1.34

    def __init__(self, personality_vector: dict | None = None) -> None:
        self.personality_vector = personality_vector or {}

    def detect_flow_state(self, user_signals: dict) -> dict:
        """Detect the current flow state from user behavioral signals.

        Args:
            user_signals: Dictionary with keys like 'challenge', 'skill',
                'engagement', 'frustration', etc.

        Returns:
            Dictionary with keys: state, ratio, in_flow, suggestion.
        """
        challenge = float(user_signals.get("challenge", 0.5))
        skill = float(user_signals.get("skill", 0.5))
        ratio = challenge / max(skill, 0.01)

        zone = self.compute_flow_zone(challenge, skill)
        return {
            "state": zone["state"],
            "ratio": round(ratio, 3),
            "in_flow": zone["in_flow"],
            "suggestion": zone["suggestion"],
        }

    def compute_flow_zone(self, challenge: float, skill: float) -> dict:
        """Compute the flow zone classification for a challenge-skill pair.

        Args:
            challenge: Challenge level (0.0 to 1.0+).
            skill: Skill level (0.0 to 1.0+).

        Returns:
            Dictionary with keys: state, ratio, in_flow, suggestion.
        """
        ratio = challenge / max(skill, 0.01)

        # Apply personality modulation
        modulation = self.personality_vector.get("flow_tolerance", 1.0)
        lower = self.FLOW_LOWER * modulation
        upper = self.FLOW_UPPER * modulation

        if ratio < lower:
            state = "boredom"
            in_flow = False
            suggestion = "Increase challenge or decrease skill support to enter flow."
        elif ratio > upper:
            state = "anxiety"
            in_flow = False
            suggestion = "Decrease challenge or increase skill support to enter flow."
        else:
            state = "flow"
            in_flow = True
            suggestion = "You are in the flow zone. Maintain current balance."

        return {
            "state": state,
            "ratio": round(ratio, 3),
            "in_flow": in_flow,
            "suggestion": suggestion,
        }

    def suggest_adjustment(self, current_state: dict) -> dict:
        """Suggest an adjustment to move toward the flow zone.

        Args:
            current_state: Dictionary with 'challenge', 'skill', and optionally
                other signal keys.

        Returns:
            Dictionary with keys: adjustment_type, target_challenge, target_skill,
                rationale.
        """
        challenge = float(current_state.get("challenge", 0.5))
        skill = float(current_state.get("skill", 0.5))
        ratio = challenge / max(skill, 0.01)

        if ratio < self.FLOW_LOWER:
            target_ratio = (self.FLOW_LOWER + self.FLOW_UPPER) / 2
            target_challenge = skill * target_ratio
            return {
                "adjustment_type": "increase_challenge",
                "target_challenge": round(target_challenge, 3),
                "target_skill": round(skill, 3),
                "rationale": f"Current ratio {ratio:.2f} is below flow zone. "
                f"Increase challenge to ~{target_challenge:.2f}.",
            }
        elif ratio > self.FLOW_UPPER:
            target_ratio = (self.FLOW_LOWER + self.FLOW_UPPER) / 2
            target_skill = challenge / target_ratio
            return {
                "adjustment_type": "increase_skill_support",
                "target_challenge": round(challenge, 3),
                "target_skill": round(target_skill, 3),
                "rationale": f"Current ratio {ratio:.2f} is above flow zone. "
                f"Increase skill support to ~{target_skill:.2f}.",
            }
        else:
            return {
                "adjustment_type": "maintain",
                "target_challenge": round(challenge, 3),
                "target_skill": round(skill, 3),
                "rationale": f"Current ratio {ratio:.2f} is in the flow zone. Maintain.",
            }

    def update_personality(self, personality_vector: dict) -> None:
        """Update the personality vector for flow modulation.

        Args:
            personality_vector: New personality dimensions to merge.
        """
        self.personality_vector.update(personality_vector)
