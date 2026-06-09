"""
Play State Spectrum Engine — 遊戲狀態頻譜引擎
Replaces binary PLAY pulse with 4D play model:
  Play_Spectrum = f(Play_Type, Play_Intensity, Play_Autonomy, Play_Context)

Play → Flow transition: intensity > 0.7 AND autonomy > 0.6 AND challenge/skill in Flow zone
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


class CailloisPlayType(Enum):
    AGON = "agon"        # Competition — Flow through mastery
    ALEA = "alea"        # Chance — Flow through uncertainty management
    MIMICRY = "mimicry"  # Simulation — Flow through role immersion
    ILINX = "ilinx"      # Vertigo — Flow through boundary pushing


class PlayContext(Enum):
    SOLITARY = "solitary"      # Alone
    PARALLEL = "parallel"      # Side by side, independent
    ASSOCIATIVE = "associative"  # Shared activity, independent goals
    COOPERATIVE = "cooperative"  # Shared goals, collaborative


class FlowZone(Enum):
    BOREDOM = "boredom"
    FLOW = "flow"
    ANXIETY = "anxiety"


@dataclass
class PlaySpectrum:
    """
    Play State Spectrum — 4D play model
    Replaces the binary PLAY pulse (+0.8, +0.5, +0.3) with a richer representation.
    """
    play_type: CailloisPlayType = CailloisPlayType.AGON
    intensity: float = 0.5       # 0.0 (no play) → 1.0 (deep play/Flow)
    autonomy: float = 0.5        # 0.0 (forced play) → 1.0 (autotelic/spontaneous)
    context: PlayContext = PlayContext.SOLITARY

    def is_flow_ready(self, challenge_skill_ratio: float,
                       flow_lower: float = 0.74, flow_upper: float = 1.34) -> bool:
        """
        Detect if Play state is transitioning to Flow state.
        Conditions: intensity > 0.7 AND autonomy > 0.6 AND ratio in Flow zone
        """
        play_conditions = self.intensity > 0.7 and self.autonomy > 0.6
        flow_conditions = flow_lower <= challenge_skill_ratio <= flow_upper
        return play_conditions and flow_conditions

    def to_vad(self) -> Tuple[float, float, float]:
        """Convert PlaySpectrum to VAD vector for Pulse layer compatibility"""
        base_valence = 0.8   # PLAY is positive
        base_arousal = 0.5
        base_dominance = 0.3

        # Intensity modulates arousal
        arousal = base_arousal + (self.intensity - 0.5) * 0.4

        # Autonomy modulates dominance
        dominance = base_dominance + (self.autonomy - 0.5) * 0.4

        # Play type modulates valence
        type_valence = {
            CailloisPlayType.AGON: 0.7,     # Competitive but satisfying
            CailloisPlayType.ALEA: 0.6,     # Exciting but uncertain
            CailloisPlayType.MIMICRY: 0.85, # Immersive and positive
            CailloisPlayType.ILINX: 0.75,   # Thrilling
        }
        valence = type_valence.get(self.play_type, base_valence)

        return (round(valence, 2), round(arousal, 2), round(dominance, 2))


@dataclass
class FlowState:
    """Flow State representation based on Csikszentmihalyi's theory"""
    challenge_skill_ratio: float = 1.0  # Ideal is 0.74-1.34
    zone: FlowZone = FlowZone.FLOW
    duration_seconds: float = 0.0
    personality_modulated: bool = False
    flow_channel_lower: float = 0.74
    flow_channel_upper: float = 1.34

    @classmethod
    def from_ratio(cls, ratio: float, personality_lower: float = 0.74,
                    personality_upper: float = 1.34) -> 'FlowState':
        """Create FlowState from challenge/skill ratio with personality modulation"""
        if ratio < personality_lower:
            zone = FlowZone.BOREDOM
        elif ratio > personality_upper:
            zone = FlowZone.ANXIETY
        else:
            zone = FlowZone.FLOW

        return cls(
            challenge_skill_ratio=ratio,
            zone=zone,
            personality_modulated=(personality_lower != 0.74 or personality_upper != 1.34),
            flow_channel_lower=personality_lower,
            flow_channel_upper=personality_upper,
        )

    def flow_depth(self) -> float:
        """Calculate how deep into Flow the user is (0.0 = edge, 1.0 = deep Flow)"""
        if self.zone != FlowZone.FLOW:
            return 0.0

        # Distance from edges of Flow channel
        channel_width = self.flow_channel_upper - self.flow_channel_lower
        if channel_width == 0:
            return 0.0

        center = (self.flow_channel_lower + self.flow_channel_upper) / 2
        distance_from_center = abs(self.challenge_skill_ratio - center)
        max_distance = channel_width / 2

        return round(1.0 - (distance_from_center / max_distance), 2)

    def maintenance_strategy(self) -> str:
        """Return strategy for maintaining or entering Flow"""
        if self.zone == FlowZone.FLOW:
            return "maintain"  # Keep conditions stable
        elif self.zone == FlowZone.BOREDOM:
            return "increase_challenge"  # Add complexity, constraints, new goals
        else:  # ANXIETY
            return "decrease_challenge"  # Break down tasks, provide scaffolding


class PlayFlowBridge:
    """
    Play-Flow Bridge — 遊戲到心流的橋樑
    Maps how different Play types lead to Flow states.
    Formula: Flow = Play(type, intensity) × Autotelic(personality) × Challenge/Skill
    """

    # Caillois play type → Flow path mapping
    FLOW_PATHS = {
        CailloisPlayType.AGON: "mastery",        # Competition → Flow through skill mastery
        CailloisPlayType.ALEA: "uncertainty",     # Chance → Flow through uncertainty management
        CailloisPlayType.MIMICRY: "immersion",    # Simulation → Flow through role immersion
        CailloisPlayType.ILINX: "boundary",       # Vertigo → Flow through boundary pushing
    }

    # Stuart Brown 8 Player Types → Flow gateway mapping
    PLAYER_FLOW_GATEWAYS = {
        "explorer": {"type": CailloisPlayType.AGON, "gateway": "discovery_novelty"},
        "creator": {"type": CailloisPlayType.MIMICRY, "gateway": "creation_making"},
        "strategist": {"type": CailloisPlayType.AGON, "gateway": "strategic_mastery"},
        "storyteller": {"type": CailloisPlayType.MIMICRY, "gateway": "narrative_immersion"},
        "healer": {"type": CailloisPlayType.AGON, "gateway": "restoring_wholeness"},
        "conductor": {"type": CailloisPlayType.AGON, "gateway": "orchestrating_harmony"},
        "builder": {"type": CailloisPlayType.MIMICRY, "gateway": "constructing_systems"},
        "player": {"type": CailloisPlayType.ILINX, "gateway": "spontaneous_play"},
    }

    def detect_play_type(self, text: str) -> CailloisPlayType:
        """Detect Caillois play type from text"""
        text_lower = text.lower()

        agon_keywords = ["compete", "win", "beat", "challenge", "master", "best",
                         "競爭", "贏", "挑戰", "精通", "最好"]
        alea_keywords = ["chance", "random", "luck", "risk", "uncertain", "surprise",
                         "機會", "隨機", "運氣", "風險", "不確定"]
        mimicry_keywords = ["role", "simulate", "pretend", "story", "imagine", "become",
                            "角色", "模擬", "假裝", "故事", "想像"]
        ilinx_keywords = ["thrill", "edge", "extreme", "push boundary", "danger", "excite",
                          "刺激", "邊緣", "極限", "突破", "興奮"]

        scores = {
            CailloisPlayType.AGON: sum(1 for kw in agon_keywords if kw in text_lower),
            CailloisPlayType.ALEA: sum(1 for kw in alea_keywords if kw in text_lower),
            CailloisPlayType.MIMICRY: sum(1 for kw in mimicry_keywords if kw in text_lower),
            CailloisPlayType.ILINX: sum(1 for kw in ilinx_keywords if kw in text_lower),
        }

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return CailloisPlayType.AGON  # Default

        return best

    def create_play_spectrum(self, text: str, player_type: str = "explorer",
                              intensity: float = 0.5, autonomy: float = 0.5) -> PlaySpectrum:
        """Create a PlaySpectrum from text and player type"""
        play_type = self.detect_play_type(text)

        # Player type influences default play type and autonomy
        if player_type in self.PLAYER_FLOW_GATEWAYS:
            gateway = self.PLAYER_FLOW_GATEWAYS[player_type]
            if intensity == 0.5:  # Only override if not explicitly set
                intensity = 0.6  # Player types have moderate baseline intensity
            if autonomy == 0.5:
                # Autotelic types have higher autonomy
                autotelic_types = ["player", "explorer", "creator"]
                autonomy = 0.7 if player_type in autotelic_types else 0.5

        return PlaySpectrum(
            play_type=play_type,
            intensity=min(1.0, intensity),
            autonomy=min(1.0, autonomy),
            context=PlayContext.COOPERATIVE,  # Default for AI interaction
        )

    def calculate_flow_potential(self, play: PlaySpectrum, autotelic_index: float,
                                  challenge_skill_ratio: float) -> float:
        """
        Calculate Flow potential from Play state, personality, and challenge/skill ratio.
        Formula: Flow = Play(intensity) × Autotelic(personality) × ChannelFit(ratio)
        """
        play_factor = play.intensity * play.autonomy
        autotelic_factor = autotelic_index
        channel_factor = 1.0 if 0.74 <= challenge_skill_ratio <= 1.34 else 0.3

        return round(play_factor * autotelic_factor * channel_factor, 3)


class FlowStateNavigator:
    """
    Flow State Navigator (FSN) — 心流導航器
    Continuously monitors and manages the user's Flow state.
    Formula: Flow = f(challenge/skill) ∈ [0.74, 1.34] | personality_modulated
    """

    def __init__(self, personality_lower: float = 0.74, personality_upper: float = 1.34):
        self.flow_channel_lower = personality_lower
        self.flow_channel_upper = personality_upper
        self.current_state: Optional[FlowState] = None
        self.state_history: List[FlowState] = []

    def assess_flow(self, challenge_level: float, skill_level: float) -> FlowState:
        """Assess current Flow state from challenge and skill levels"""
        if skill_level <= 0:
            skill_level = 0.01  # Prevent division by zero

        ratio = challenge_level / skill_level
        state = FlowState.from_ratio(ratio, self.flow_channel_lower, self.flow_channel_upper)

        self.current_state = state
        self.state_history.append(state)

        return state

    def get_adjustment_recommendation(self) -> Dict[str, any]:
        """Get recommendation for adjusting task to maintain/enter Flow"""
        if self.current_state is None:
            return {"action": "assess", "message": "Need to assess Flow state first"}

        state = self.current_state

        if state.zone == FlowZone.FLOW:
            return {
                "action": "maintain",
                "message": "In Flow zone — maintain current conditions",
                "depth": state.flow_depth(),
                "strategy": "minimize_interruptions",
            }
        elif state.zone == FlowZone.BOREDOM:
            challenge_increase = self.flow_channel_lower * (1.0 / max(state.challenge_skill_ratio, 0.01)) - 1.0
            return {
                "action": "increase_challenge",
                "message": "Boredom zone — increase challenge",
                "suggested_challenge_multiplier": round(1.0 + max(challenge_increase, 0.1), 2),
                "strategies": [
                    "Add time constraints",
                    "Introduce new requirements",
                    "Increase complexity",
                    "Set higher quality bar",
                ],
            }
        else:  # ANXIETY
            challenge_decrease = 1.0 - self.flow_channel_upper / max(state.challenge_skill_ratio, 0.01)
            return {
                "action": "decrease_challenge",
                "message": "Anxiety zone — decrease challenge or increase skill",
                "suggested_challenge_multiplier": round(1.0 - max(challenge_decrease, 0.1), 2),
                "strategies": [
                    "Break task into smaller steps",
                    "Provide scaffolding and examples",
                    "Reduce scope",
                    "Offer guided walkthrough",
                ],
            }

    def update_flow_channel(self, personality_lower: float, personality_upper: float):
        """Update Flow channel bounds based on personality profile"""
        self.flow_channel_lower = personality_lower
        self.flow_channel_upper = personality_upper
