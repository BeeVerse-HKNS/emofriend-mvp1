"""
MBTI Cognitive Function Router — MBTI 認知功能路由器
Uses MBTI's 8 cognitive functions as processing mode selectors.
Formula: Process_Mode = argmax(Ni, Ne, Si, Se, Ti, Te, Fi, Fe | context)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


class CognitiveFunction(Enum):
    NI = "ni"  # Introverted Intuition — Convergent insight
    NE = "ne"  # Extraverted Intuition — Divergent exploration
    SI = "si"  # Introverted Sensing — Detail recall
    SE = "se"  # Extraverted Sensing — Real-time engagement
    TI = "ti"  # Introverted Thinking — Logical precision
    TE = "te"  # Extraverted Thinking — Systematic efficiency
    FI = "fi"  # Introverted Feeling — Value authenticity
    FE = "fe"  # Extraverted Feeling — Social harmony


@dataclass
class ProcessingMode:
    """Processing mode corresponding to a cognitive function"""
    function: CognitiveFunction
    name: str
    description: str
    thinking_modes: List[str]  # Which of the 6 EmoGlyph thinking modes to activate
    flow_entry: str  # How this function enters Flow
    strengths: List[str]
    blind_spots: List[str]


# Define all 8 processing modes
PROCESSING_MODES = {
    CognitiveFunction.NI: ProcessingMode(
        function=CognitiveFunction.NI,
        name="Convergent Insight",
        description="Synthesize patterns, find hidden structure, predict outcomes",
        thinking_modes=["rational", "intuitive", "analytical"],
        flow_entry="Through deep pattern recognition and 'aha' moments",
        strengths=["Pattern synthesis", "Long-term vision", "Strategic insight"],
        blind_spots=["May miss concrete details", "Can be too abstract"],
    ),
    CognitiveFunction.NE: ProcessingMode(
        function=CognitiveFunction.NE,
        name="Divergent Exploration",
        description="Generate many possibilities, brainstorm, explore alternatives",
        thinking_modes=["creative", "rational", "intuitive"],
        flow_entry="Through brainstorming and discovering new connections",
        strengths=["Idea generation", "Alternative perspectives", "Innovation"],
        blind_spots=["May not follow through", "Can be scattered"],
    ),
    CognitiveFunction.SI: ProcessingMode(
        function=CognitiveFunction.SI,
        name="Detail Recall",
        description="Reference past experience, verify against known patterns",
        thinking_modes=["analytical", "practical", "rational"],
        flow_entry="Through methodical review and pattern matching",
        strengths=["Accuracy", "Reliability", "Consistency"],
        blind_spots=["May resist novelty", "Can be too cautious"],
    ),
    CognitiveFunction.SE: ProcessingMode(
        function=CognitiveFunction.SE,
        name="Real-time Engagement",
        description="Focus on immediate data, hands-on testing, live observation",
        thinking_modes=["practical", "intuitive", "creative"],
        flow_entry="Through direct sensory engagement and action",
        strengths=["Adaptability", "Quick response", "Practical skill"],
        blind_spots=["May miss big picture", "Can be impulsive"],
    ),
    CognitiveFunction.TI: ProcessingMode(
        function=CognitiveFunction.TI,
        name="Logical Precision",
        description="Analyze, deduce, find inconsistencies, build internal frameworks",
        thinking_modes=["rational", "analytical"],
        flow_entry="Through deep logical analysis and system building",
        strengths=["Logical rigor", "Systematic understanding", "Precision"],
        blind_spots=["May over-analyze", "Can miss emotional context"],
    ),
    CognitiveFunction.TE: ProcessingMode(
        function=CognitiveFunction.TE,
        name="Systematic Efficiency",
        description="Organize, structure, optimize for output, implement systems",
        thinking_modes=["rational", "practical", "analytical"],
        flow_entry="Through organizing and optimizing systems",
        strengths=["Efficiency", "Execution", "Clear structure"],
        blind_spots=["May overlook people", "Can be too rigid"],
    ),
    CognitiveFunction.FI: ProcessingMode(
        function=CognitiveFunction.FI,
        name="Value Authenticity",
        description="Evaluate against personal values, find meaning, ensure integrity",
        thinking_modes=["emotional", "creative", "intuitive"],
        flow_entry="Through value-aligned meaningful work",
        strengths=["Authenticity", "Empathy", "Moral clarity"],
        blind_spots=["May be subjective", "Can be too idealistic"],
    ),
    CognitiveFunction.FE: ProcessingMode(
        function=CognitiveFunction.FE,
        name="Social Harmony",
        description="Consider impact on others, build consensus, maintain relationships",
        thinking_modes=["emotional", "practical", "creative"],
        flow_entry="Through collaborative and socially meaningful activities",
        strengths=["Diplomacy", "Team building", "Social awareness"],
        blind_spots=["May suppress own needs", "Can be people-pleasing"],
    ),
}

# MBTI type → cognitive function stack (simplified 4-function stack)
MBTI_FUNCTION_STACKS = {
    "INTJ": [CognitiveFunction.NI, CognitiveFunction.TE, CognitiveFunction.FI, CognitiveFunction.SE],
    "INTP": [CognitiveFunction.TI, CognitiveFunction.NE, CognitiveFunction.SI, CognitiveFunction.FE],
    "ENTJ": [CognitiveFunction.TE, CognitiveFunction.NI, CognitiveFunction.SE, CognitiveFunction.FI],
    "ENTP": [CognitiveFunction.NE, CognitiveFunction.TI, CognitiveFunction.FE, CognitiveFunction.SI],
    "INFJ": [CognitiveFunction.NI, CognitiveFunction.FE, CognitiveFunction.TI, CognitiveFunction.SE],
    "INFP": [CognitiveFunction.FI, CognitiveFunction.NE, CognitiveFunction.SI, CognitiveFunction.TE],
    "ENFJ": [CognitiveFunction.FE, CognitiveFunction.NI, CognitiveFunction.SE, CognitiveFunction.TI],
    "ENFP": [CognitiveFunction.NE, CognitiveFunction.FI, CognitiveFunction.TE, CognitiveFunction.SI],
    "ISTJ": [CognitiveFunction.SI, CognitiveFunction.TE, CognitiveFunction.FI, CognitiveFunction.NE],
    "ISFJ": [CognitiveFunction.SI, CognitiveFunction.FE, CognitiveFunction.TI, CognitiveFunction.NE],
    "ESTJ": [CognitiveFunction.TE, CognitiveFunction.SI, CognitiveFunction.NE, CognitiveFunction.FI],
    "ESFJ": [CognitiveFunction.FE, CognitiveFunction.SI, CognitiveFunction.NE, CognitiveFunction.TI],
    "ISTP": [CognitiveFunction.TI, CognitiveFunction.SE, CognitiveFunction.NI, CognitiveFunction.FE],
    "ISFP": [CognitiveFunction.FI, CognitiveFunction.SE, CognitiveFunction.NI, CognitiveFunction.TE],
    "ESTP": [CognitiveFunction.SE, CognitiveFunction.TI, CognitiveFunction.FE, CognitiveFunction.NI],
    "ESFP": [CognitiveFunction.SE, CognitiveFunction.FI, CognitiveFunction.TE, CognitiveFunction.NI],
}


class MBTICognitiveRouter:
    """Routes processing through MBTI cognitive functions"""

    def __init__(self, function_weights: Optional[Dict[str, float]] = None):
        self.function_weights = function_weights or {
            "ni": 0.5, "ne": 0.5, "si": 0.5, "se": 0.5,
            "ti": 0.5, "te": 0.5, "fi": 0.5, "fe": 0.5,
        }

    def get_dominant_function(self) -> CognitiveFunction:
        """Get the dominant cognitive function"""
        return max(CognitiveFunction, key=lambda f: self.function_weights.get(f.value, 0.5))

    def get_processing_mode(self) -> ProcessingMode:
        """Get the primary processing mode based on dominant function"""
        dominant = self.get_dominant_function()
        return PROCESSING_MODES[dominant]

    def get_thinking_modes(self, context: str = "") -> List[str]:
        """Get recommended thinking modes based on cognitive function weights"""
        dominant = self.get_dominant_function()
        mode = PROCESSING_MODES[dominant]
        return mode.thinking_modes

    def detect_function_preference(self, text: str) -> Dict[str, float]:
        """Detect cognitive function preference from text"""
        text_lower = text.lower()

        keywords = {
            CognitiveFunction.NI: ["pattern", "insight", "vision", "predict", "underlying", "big picture",
                                    "模式", "洞察", "願景", "預測", "深層"],
            CognitiveFunction.NE: ["possibility", "what if", "alternative", "brainstorm", "explore", "creative",
                                    "可能", "如果", "替代", "頭腦風暴", "探索"],
            CognitiveFunction.SI: ["experience", "remember", "proven", "reliable", "consistent", "detail",
                                    "經驗", "記住", "已證明", "可靠", "一致"],
            CognitiveFunction.SE: ["now", "immediate", "hands-on", "real-time", "observe", "action",
                                    "現在", "即時", "實際", "觀察", "行動"],
            CognitiveFunction.TI: ["logic", "analyze", "consistent", "framework", "deduce", "principle",
                                    "邏輯", "分析", "一致", "框架", "推導"],
            CognitiveFunction.TE: ["organize", "efficient", "implement", "structure", "optimize", "execute",
                                    "組織", "高效", "實施", "結構", "優化"],
            CognitiveFunction.FI: ["value", "meaning", "authentic", "personal", "integrity", "believe",
                                    "價值", "意義", "真實", "個人", "信念"],
            CognitiveFunction.FE: ["team", "harmony", "consensus", "impact", "others", "collaborate",
                                    "團隊", "和諧", "共識", "影響", "合作"],
        }

        scores = {}
        for func, kws in keywords.items():
            score = sum(0.1 for kw in kws if kw in text_lower)
            scores[func.value] = min(1.0, 0.5 + score)

        return scores

    def get_flow_entry_path(self, mbti_type: Optional[str] = None) -> str:
        """Get the Flow entry path for a given MBTI type"""
        if mbti_type and mbti_type.upper() in MBTI_FUNCTION_STACKS:
            dominant = MBTI_FUNCTION_STACKS[mbti_type.upper()][0]
            return PROCESSING_MODES[dominant].flow_entry

        dominant = self.get_dominant_function()
        return PROCESSING_MODES[dominant].flow_entry
