"""
Personality Vector Engine (PVE) — 統一人格向量引擎
Formula: PV = ⊕(DISC₄, OCEAN₅, MBTI₈, VAK₃, Eastern₅) ^ Ξ

Combines 5 personality models into a unified computational representation
that modulates all 5 EmoGlyph layers simultaneously.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import math


class DISCType(Enum):
    DOMINANCE = "D"
    INFLUENCE = "I"
    STEADINESS = "S"
    CONSCIENTIOUSNESS = "C"


class CailloisPlayType(Enum):
    AGON = "agon"        # Competition
    ALEA = "alea"        # Chance
    MIMICRY = "mimicry"  # Simulation
    ILINX = "ilinx"      # Vertigo


class FlowZone(Enum):
    BOREDOM = "boredom"       # skill > challenge
    FLOW = "flow"             # challenge/skill in [0.74, 1.34]
    ANXIETY = "anxiety"       # challenge > skill


class VAKChannel(Enum):
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"


class MBTIFunction(Enum):
    NI = "ni"  # Introverted Intuition
    NE = "ne"  # Extraverted Intuition
    SI = "si"  # Introverted Sensing
    SE = "se"  # Extraverted Sensing
    TI = "ti"  # Introverted Thinking
    TE = "te"  # Extraverted Thinking
    FI = "fi"  # Introverted Feeling
    FE = "fe"  # Extraverted Feeling


class FiveElement(Enum):
    WOOD = "wood"    # 木 - Growth, expansion
    FIRE = "fire"    # 火 - Passion, expression
    EARTH = "earth"  # 土 - Stability, nurturing
    METAL = "metal"  # 金 - Precision, structure
    WATER = "water"  # 水 - Wisdom, depth


@dataclass
class DISCProfile:
    """DISC behavioral profile — 4 dimensions [0.0-1.0]"""
    dominance: float = 0.5
    influence: float = 0.5
    steadiness: float = 0.5
    conscientiousness: float = 0.5

    def to_vector(self) -> List[float]:
        return [self.dominance, self.influence, self.steadiness, self.conscientiousness]

    def primary_type(self) -> DISCType:
        values = {
            DISCType.DOMINANCE: self.dominance,
            DISCType.INFLUENCE: self.influence,
            DISCType.STEADINESS: self.steadiness,
            DISCType.CONSCIENTIOUSNESS: self.conscientiousness,
        }
        return max(values, key=values.get)


@dataclass
class OCEANProfile:
    """Big 5 / OCEAN trait profile — 5 dimensions [0.0-1.0]"""
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5

    def to_vector(self) -> List[float]:
        return [self.openness, self.conscientiousness, self.extraversion,
                self.agreeableness, self.neuroticism]


@dataclass
class MBTIProfile:
    """MBTI cognitive function profile — 8 function weights [0.0-1.0]"""
    ni: float = 0.5
    ne: float = 0.5
    si: float = 0.5
    se: float = 0.5
    ti: float = 0.5
    te: float = 0.5
    fi: float = 0.5
    fe: float = 0.5

    def to_vector(self) -> List[float]:
        return [self.ni, self.ne, self.si, self.se, self.ti, self.te, self.fi, self.fe]

    def dominant_function(self) -> MBTIFunction:
        values = {MBTIFunction.NI: self.ni, MBTIFunction.NE: self.ne,
                  MBTIFunction.SI: self.si, MBTIFunction.SE: self.se,
                  MBTIFunction.TI: self.ti, MBTIFunction.TE: self.te,
                  MBTIFunction.FI: self.fi, MBTIFunction.FE: self.fe}
        return max(values, key=values.get)


@dataclass
class VAKProfile:
    """NLP Representational System profile — 3 channels [0.0-1.0]"""
    visual: float = 0.4
    auditory: float = 0.3
    kinesthetic: float = 0.3

    def to_vector(self) -> List[float]:
        return [self.visual, self.auditory, self.kinesthetic]

    def primary_channel(self) -> VAKChannel:
        values = {VAKChannel.VISUAL: self.visual, VAKChannel.AUDITORY: self.auditory,
                  VAKChannel.KINESTHETIC: self.kinesthetic}
        return max(values, key=values.get)


@dataclass
class EasternProfile:
    """Eastern personality profile — Five Elements [0.0-1.0]"""
    wood: float = 0.2    # 木 - Growth ↔ Openness
    fire: float = 0.2    # 火 - Passion ↔ Extraversion
    earth: float = 0.2   # 土 - Nurturing ↔ Agreeableness
    metal: float = 0.2   # 金 - Precision ↔ Conscientiousness
    water: float = 0.2   # 水 - Wisdom ↔ (inverse Neuroticism + Openness)

    def to_vector(self) -> List[float]:
        return [self.wood, self.fire, self.earth, self.metal, self.water]

    def primary_element(self) -> FiveElement:
        values = {FiveElement.WOOD: self.wood, FiveElement.FIRE: self.fire,
                  FiveElement.EARTH: self.earth, FiveElement.METAL: self.metal,
                  FiveElement.WATER: self.water}
        return max(values, key=values.get)


@dataclass
class PersonalityVector:
    """
    Unified Personality Vector — 統一人格向量
    Formula: PV = ⊕(DISC₄, OCEAN₅, MBTI₈, VAK₃, Eastern₅) ^ Ξ

    Combines all personality models into a single computational representation.
    """
    disc: DISCProfile = field(default_factory=DISCProfile)
    ocean: OCEANProfile = field(default_factory=OCEANProfile)
    mbti: MBTIProfile = field(default_factory=MBTIProfile)
    vak: VAKProfile = field(default_factory=VAKProfile)
    eastern: EasternProfile = field(default_factory=EasternProfile)
    confidence: float = 0.1  # Low confidence for default profile
    observation_count: int = 0

    def to_full_vector(self) -> List[float]:
        """Return the complete 25-dimensional personality vector"""
        return (self.disc.to_vector() + self.ocean.to_vector() +
                self.mbti.to_vector() + self.vak.to_vector() +
                self.eastern.to_vector())

    def superposition(self) -> float:
        """⊕ Superposition — compute the overall personality coherence"""
        vec = self.to_full_vector()
        mean = sum(vec) / len(vec)
        variance = sum((v - mean) ** 2 for v in vec) / len(vec)
        # High coherence = low variance (personality is consistent)
        # Low coherence = high variance (personality is diverse)
        return 1.0 - min(variance * 4, 1.0)  # Scale variance to [0,1]

    def emergence_detected(self) -> bool:
        """Ξ Emergence — detect if personality patterns produce emergent properties"""
        coherence = self.superposition()
        # Emergence occurs when personality is both coherent AND has strong dimensions
        strong_dims = sum(1 for v in self.to_full_vector() if v > 0.7)
        return coherence > 0.6 and strong_dims >= 3

    def flow_channel_width(self) -> Tuple[float, float]:
        """
        Calculate personality-modulated Flow channel bounds.
        Returns (lower_bound, upper_bound) for challenge/skill ratio.

        Base Flow channel: [0.74, 1.34]
        - High Openness → wider channel
        - High Neuroticism → narrower channel
        - High Conscientiousness → shifted toward challenge
        """
        base_lower = 0.74
        base_upper = 1.34

        # Openness widens the channel
        openness_modifier = (self.ocean.openness - 0.5) * 0.4  # -0.2 to +0.2

        # Neuroticism narrows the channel
        neuroticism_modifier = (self.ocean.neuroticism - 0.5) * 0.3  # -0.15 to +0.15

        # Conscientiousness shifts toward challenge
        conscientiousness_shift = (self.ocean.conscientiousness - 0.5) * 0.2

        lower = base_lower - openness_modifier + neuroticism_modifier + conscientiousness_shift
        upper = base_upper + openness_modifier - neuroticism_modifier + conscientiousness_shift

        # Ensure reasonable bounds
        lower = max(0.3, min(lower, 1.0))
        upper = max(1.0, min(upper, 2.0))

        return (round(lower, 2), round(upper, 2))

    def autotelic_index(self) -> float:
        """
        Calculate autotelic personality index.
        Based on: curiosity + persistence + low_self_centeredness + intrinsic_motivation
        Approximated from available personality dimensions.
        """
        curiosity = self.ocean.openness  # Openness ≈ curiosity
        persistence = self.ocean.conscientiousness  # Conscientiousness ≈ persistence
        low_self_centeredness = self.ocean.agreeableness  # Agreeableness ≈ other-oriented
        intrinsic_motivation = self.disc.influence * 0.3 + self.ocean.openness * 0.7  # Blend

        return (curiosity + persistence + low_self_centeredness + intrinsic_motivation) / 4

    def update_from_observation(self, signal_type: str, values: Dict[str, float],
                                 learning_rate: float = 0.1):
        """
        Update personality profile using exponential moving average.
        Formula: Profile(t+1) = Profile(t) + α(observation - Profile(t))
        """
        self.observation_count += 1

        if signal_type == "disc":
            for key, value in values.items():
                if hasattr(self.disc, key):
                    current = getattr(self.disc, key)
                    setattr(self.disc, key, current + learning_rate * (value - current))

        elif signal_type == "ocean":
            for key, value in values.items():
                if hasattr(self.ocean, key):
                    current = getattr(self.ocean, key)
                    setattr(self.ocean, key, current + learning_rate * (value - current))

        elif signal_type == "mbti":
            for key, value in values.items():
                if hasattr(self.mbti, key):
                    current = getattr(self.mbti, key)
                    setattr(self.mbti, key, current + learning_rate * (value - current))

        elif signal_type == "vak":
            for key, value in values.items():
                if hasattr(self.vak, key):
                    current = getattr(self.vak, key)
                    setattr(self.vak, key, current + learning_rate * (value - current))

        elif signal_type == "eastern":
            for key, value in values.items():
                if hasattr(self.eastern, key):
                    current = getattr(self.eastern, key)
                    setattr(self.eastern, key, current + learning_rate * (value - current))

        # Increase confidence with more observations (capped at 1.0)
        self.confidence = min(1.0, 0.1 + self.observation_count * 0.05)

    def get_layer_modifiers(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate Big 5 trait modifiers for each EmoGlyph layer.
        Formula: Layer' = Layer × (1 + Σ(trait × weight))

        Returns dict of {layer_name: {trait: weight_modifier}}
        """
        return {
            "pulse": {
                "openness": self.ocean.openness * 0.3,      # O amplifies SEEKING/PLAY
                "neuroticism": self.ocean.neuroticism * 0.4, # N amplifies FEAR/PANIC
                "extraversion": self.ocean.extraversion * 0.2, # E amplifies positive pulses
            },
            "current": {
                "extraversion": self.ocean.extraversion * 0.3,  # E increases social routing
                "openness": self.ocean.openness * 0.2,          # O increases exploration routing
                "conscientiousness": self.ocean.conscientiousness * 0.2, # C increases structure
            },
            "construct": {
                "conscientiousness": self.ocean.conscientiousness * 0.4, # C increases plan rigor
                "openness": self.ocean.openness * 0.3,                   # O increases alternatives
                "agreeableness": self.ocean.agreeableness * 0.1,         # A includes stakeholder impact
            },
            "enactive": {
                "neuroticism": self.ocean.neuroticism * 0.3,     # N increases Fast Reaction
                "conscientiousness": self.ocean.conscientiousness * 0.2, # C increases quality checks
                "extraversion": self.ocean.extraversion * 0.2,   # E increases collaborative action
            },
            "resonance": {
                "agreeableness": self.ocean.agreeableness * 0.3,       # A increases user satisfaction weight
                "conscientiousness": self.ocean.conscientiousness * 0.3, # C increases quality thresholds
                "neuroticism": self.ocean.neuroticism * 0.2,           # N increases anxiety about quality
            },
        }


# Cross-model mapping functions

def disc_to_ocean(disc: DISCProfile) -> Dict[str, float]:
    """Map DISC profile to approximate Big 5 scores"""
    return {
        "openness": 0.3 + disc.dominance * 0.3 + disc.influence * 0.2,
        "conscientiousness": 0.3 + disc.conscientiousness * 0.4 + disc.dominance * 0.1,
        "extraversion": 0.2 + disc.influence * 0.4 + disc.dominance * 0.2,
        "agreeableness": 0.2 + disc.steadiness * 0.4 + disc.influence * 0.1,
        "neuroticism": 0.5 - disc.steadiness * 0.2 - disc.conscientiousness * 0.1,
    }


def ocean_to_eastern(ocean: OCEANProfile) -> Dict[str, float]:
    """Map Big 5 profile to Five Elements"""
    return {
        "wood": ocean.openness * 0.6 + (1 - ocean.neuroticism) * 0.2 + ocean.extraversion * 0.2,
        "fire": ocean.extraversion * 0.5 + ocean.openness * 0.3 + ocean.agreeableness * 0.2,
        "earth": ocean.agreeableness * 0.5 + ocean.conscientiousness * 0.3 + (1 - ocean.neuroticism) * 0.2,
        "metal": ocean.conscientiousness * 0.6 + (1 - ocean.openness) * 0.2 + ocean.agreeableness * 0.2,
        "water": (1 - ocean.neuroticism) * 0.4 + ocean.openness * 0.3 + ocean.conscientiousness * 0.3,
    }


def detect_disc_from_text(text: str) -> Dict[str, float]:
    """Detect DISC profile from user language patterns"""
    text_lower = text.lower()

    d_keywords = ["directly", "bottom line", "results", "decide", "now", "urgent", "immediately",
                  "直接", "結果", "決定", "緊急", "立刻", "馬上"]
    i_keywords = ["exciting", "great", "feel", "together", "share", "fun", "enthusiastic",
                  "興奮", "太好了", "一起", "分享", "有趣"]
    s_keywords = ["step by step", "careful", "stable", "support", "patient", "reliable",
                  "一步一步", "小心", "穩定", "支持", "耐心", "可靠"]
    c_keywords = ["analyze", "data", "evidence", "precise", "accurate", "quality", "detail",
                  "分析", "數據", "證據", "精確", "準確", "質量", "細節"]

    scores = {"dominance": 0.3, "influence": 0.3, "steadiness": 0.3, "conscientiousness": 0.3}

    for kw in d_keywords:
        if kw in text_lower:
            scores["dominance"] += 0.15
    for kw in i_keywords:
        if kw in text_lower:
            scores["influence"] += 0.15
    for kw in s_keywords:
        if kw in text_lower:
            scores["steadiness"] += 0.15
    for kw in c_keywords:
        if kw in text_lower:
            scores["conscientiousness"] += 0.15

    # Cap at 1.0
    for key in scores:
        scores[key] = min(1.0, scores[key])

    return scores


def detect_vak_from_text(text: str) -> Dict[str, float]:
    """Detect VAK representational preference from user language"""
    text_lower = text.lower()

    v_keywords = ["see", "look", "picture", "imagine", "visualize", "clear", "perspective",
                  "show", "diagram", "chart", "看到", "想像", "圖", "顯示"]
    a_keywords = ["hear", "sound", "resonate", "listen", "discuss", "explain", "tell",
                  "speak", "say", "聽", "聲音", "討論", "解釋"]
    k_keywords = ["feel", "grasp", "touch", "handle", "walk through", "solid", "concrete",
                  "hands-on", "experience", "感覺", "掌握", "具體", "實際"]

    scores = {"visual": 0.33, "auditory": 0.33, "kinesthetic": 0.33}

    for kw in v_keywords:
        if kw in text_lower:
            scores["visual"] += 0.1
    for kw in a_keywords:
        if kw in text_lower:
            scores["auditory"] += 0.1
    for kw in k_keywords:
        if kw in text_lower:
            scores["kinesthetic"] += 0.1

    # Normalize to sum to 1.0
    total = sum(scores.values())
    if total > 0:
        for key in scores:
            scores[key] = scores[key] / total

    return scores


def create_personality_vector_from_text(text: str) -> PersonalityVector:
    """Create a PersonalityVector from text input by detecting all models"""
    disc_scores = detect_disc_from_text(text)
    vak_scores = detect_vak_from_text(text)

    disc = DISCProfile(**disc_scores)
    ocean_map = disc_to_ocean(disc)
    ocean = OCEANProfile(**ocean_map)
    eastern_map = ocean_to_eastern(ocean)
    eastern = EasternProfile(**eastern_map)
    vak = VAKProfile(**vak_scores)
    mbti = MBTIProfile()  # Default; MBTI requires more interaction history

    return PersonalityVector(
        disc=disc, ocean=ocean, mbti=mbti, vak=vak, eastern=eastern,
        confidence=0.3, observation_count=1
    )
