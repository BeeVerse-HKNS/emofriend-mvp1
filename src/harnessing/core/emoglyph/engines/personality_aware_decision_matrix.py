"""
Personality-Aware Decision Matrix — 人格感知決策矩陣
Enhances the 8 Agent Mode decision matrix with personality-informed mode selection.
Formula: Mode_Selection = f(complexity, risk, personality_profile)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


class AgentMode(Enum):
    SOLO = "solo"
    PIPELINE = "pipeline"
    PARALLEL = "parallel"
    QUORUM = "quorum"
    SUPERVISOR = "supervisor"
    ITERATIVE = "iterative"
    EVENT_DRIVEN = "event_driven"
    HYBRID = "hybrid"


@dataclass
class ModeRecommendation:
    """Recommendation for agent mode with personality reasoning"""
    mode: AgentMode
    confidence: float
    personality_alignment: float  # How well the mode aligns with personality
    conflict: bool  # Whether personality preference conflicts with optimal mode
    conflict_description: str = ""
    reasoning: str = ""


# DISC type → Agent mode preference mapping
DISC_MODE_PREFERENCES = {
    "D": {  # Dominance — prefers fast, decisive modes
        "preferred": [AgentMode.SOLO, AgentMode.QUORUM],
        "avoided": [AgentMode.ITERATIVE, AgentMode.SUPERVISOR],
        "reasoning": "High D prefers decisive, results-oriented modes",
    },
    "I": {  # Influence — prefers collaborative, creative modes
        "preferred": [AgentMode.ITERATIVE, AgentMode.PARALLEL],
        "avoided": [AgentMode.SOLO, AgentMode.PIPELINE],
        "reasoning": "High I prefers collaborative, engaging modes",
    },
    "S": {  # Steadiness — prefers structured, supportive modes
        "preferred": [AgentMode.PIPELINE, AgentMode.SUPERVISOR],
        "avoided": [AgentMode.QUORUM, AgentMode.SOLO],
        "reasoning": "High S prefers structured, predictable modes",
    },
    "C": {  # Conscientiousness — prefers quality-focused, analytical modes
        "preferred": [AgentMode.SUPERVISOR, AgentMode.QUORUM],
        "avoided": [AgentMode.SOLO, AgentMode.EVENT_DRIVEN],
        "reasoning": "High C prefers quality-assured, evidence-based modes",
    },
}


class PersonalityAwareDecisionMatrix:
    """Enhanced decision matrix with personality-informed mode selection"""

    def __init__(self, disc_profile: Optional[Dict[str, float]] = None):
        self.disc_profile = disc_profile or {"D": 0.5, "I": 0.5, "S": 0.5, "C": 0.5}

    def get_primary_disc(self) -> str:
        """Get primary DISC dimension"""
        return max(self.disc_profile, key=self.disc_profile.get)

    def recommend_mode(self, complexity: float, risk: float,
                        urgency: float = 0.5) -> ModeRecommendation:
        """
        Recommend agent mode based on task characteristics and personality.

        Args:
            complexity: 0.0-1.0, task complexity
            risk: 0.0-1.0, risk level
            urgency: 0.0-1.0, urgency level
        """
        # Step 1: Determine optimal mode from task characteristics (standard logic)
        optimal_mode = self._task_based_mode(complexity, risk, urgency)

        # Step 2: Check personality alignment
        primary_disc = self.get_primary_disc()
        preferences = DISC_MODE_PREFERENCES[primary_disc]

        personality_alignment = 1.0
        conflict = False
        conflict_description = ""

        if optimal_mode in preferences["preferred"]:
            personality_alignment = 1.0
        elif optimal_mode in preferences["avoided"]:
            personality_alignment = 0.4
            conflict = True
            conflict_description = (
                f"High {primary_disc} personality prefers {', '.join(m.value for m in preferences['preferred'])} "
                f"but task characteristics suggest {optimal_mode.value}. "
                f"User should decide: follow personality preference or optimal mode."
            )
        else:
            personality_alignment = 0.7  # Neutral alignment

        # Step 3: Calculate confidence
        confidence = 0.5 + (personality_alignment * 0.3) + (0.2 if not conflict else 0.0)

        return ModeRecommendation(
            mode=optimal_mode,
            confidence=min(1.0, confidence),
            personality_alignment=personality_alignment,
            conflict=conflict,
            conflict_description=conflict_description,
            reasoning=preferences["reasoning"],
        )

    def _task_based_mode(self, complexity: float, risk: float,
                          urgency: float) -> AgentMode:
        """Standard task-based mode selection (existing logic)"""
        if complexity < 0.3:
            return AgentMode.SOLO
        elif complexity < 0.6:
            if urgency > 0.7:
                return AgentMode.PIPELINE
            else:
                return AgentMode.PARALLEL
        else:  # High complexity
            if risk > 0.7:
                return AgentMode.QUORUM
            elif risk > 0.4:
                return AgentMode.SUPERVISOR
            else:
                return AgentMode.HYBRID

    def get_personality_alternative(self, recommendation: ModeRecommendation) -> Optional[AgentMode]:
        """Get the personality-preferred alternative mode if there's a conflict"""
        if not recommendation.conflict:
            return None

        primary_disc = self.get_primary_disc()
        preferences = DISC_MODE_PREFERENCES[primary_disc]

        # Return the first preferred mode that's reasonable for the task
        return preferences["preferred"][0] if preferences["preferred"] else None
