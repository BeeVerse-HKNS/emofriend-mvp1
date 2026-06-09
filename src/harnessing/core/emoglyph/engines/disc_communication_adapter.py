"""
DISC Communication Style Adapter — DISC 溝通風格適配器
Adapts AI's communication style based on user's DISC profile.
Formula: Encode_Style = DISC_profile × (tone, pace, detail, structure)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class DISCStyle(Enum):
    D = "dominance"
    I = "influence"
    S = "steadiness"
    C = "conscientiousness"


@dataclass
class CommunicationStyle:
    """Communication style parameters for Encode stage"""
    tone: str = "neutral"           # direct/enthusiastic/supportive/analytical
    pace: str = "moderate"          # fast/moderate/slow
    detail_level: str = "moderate"  # minimal/moderate/extensive
    structure: str = "balanced"     # results-first/narrative/step-by-step/evidence-based
    greeting: str = ""              # Style-specific greeting
    closing: str = ""               # Style-specific closing
    decision_format: str = "options"  # options/recommendation/consensus/analysis


# Pre-defined DISC communication styles
DISC_STYLES = {
    DISCStyle.D: CommunicationStyle(
        tone="direct",
        pace="fast",
        detail_level="minimal",
        structure="results-first",
        greeting="",
        closing="Let me know your decision.",
        decision_format="options",
    ),
    DISCStyle.I: CommunicationStyle(
        tone="enthusiastic",
        pace="fast",
        detail_level="moderate",
        structure="narrative",
        greeting="Great news! ",
        closing="Excited to hear your thoughts!",
        decision_format="recommendation",
    ),
    DISCStyle.S: CommunicationStyle(
        tone="supportive",
        pace="slow",
        detail_level="extensive",
        structure="step-by-step",
        greeting="Let me help you with this. ",
        closing="Take your time — I'm here to help.",
        decision_format="consensus",
    ),
    DISCStyle.C: CommunicationStyle(
        tone="analytical",
        pace="slow",
        detail_level="extensive",
        structure="evidence-based",
        greeting="",
        closing="Please review the analysis above.",
        decision_format="analysis",
    ),
}


class DISCCommunicationAdapter:
    """Adapts communication style based on DISC profile"""

    def __init__(self, disc_profile: Optional[Dict[str, float]] = None):
        self.disc_profile = disc_profile or {"dominance": 0.5, "influence": 0.5,
                                              "steadiness": 0.5, "conscientiousness": 0.5}

    def get_primary_style(self) -> DISCStyle:
        """Get the primary DISC style"""
        style_map = {
            DISCStyle.D: self.disc_profile.get("dominance", 0.5),
            DISCStyle.I: self.disc_profile.get("influence", 0.5),
            DISCStyle.S: self.disc_profile.get("steadiness", 0.5),
            DISCStyle.C: self.disc_profile.get("conscientiousness", 0.5),
        }
        return max(style_map, key=style_map.get)

    def get_communication_style(self) -> CommunicationStyle:
        """Get the communication style for the current DISC profile"""
        primary = self.get_primary_style()
        base_style = DISC_STYLES[primary]

        # Blend styles based on secondary dimensions
        secondary_max = max(
            (s for s in DISCStyle if s != primary),
            key=lambda s: self.disc_profile.get(s.value, 0.5)
        )
        secondary_weight = self.disc_profile.get(secondary_max.value, 0.5) * 0.3

        # If secondary dimension is strong enough, blend
        if secondary_weight > 0.15:
            secondary_style = DISC_STYLES[secondary_max]
            # Simple blending: use primary tone but add secondary characteristics
            blended = CommunicationStyle(
                tone=base_style.tone,
                pace=base_style.pace,
                detail_level=secondary_style.detail_level if secondary_weight > 0.2 else base_style.detail_level,
                structure=base_style.structure,
                greeting=base_style.greeting,
                closing=base_style.closing,
                decision_format=base_style.decision_format,
            )
            return blended

        return base_style

    def format_output(self, content: str, style: Optional[CommunicationStyle] = None) -> str:
        """Format output content according to DISC communication style"""
        if style is None:
            style = self.get_communication_style()

        parts = []

        # Add greeting
        if style.greeting:
            parts.append(style.greeting)

        # Structure content based on style
        if style.structure == "results-first":
            # D-style: Lead with conclusion, then details
            lines = content.split('\n')
            if len(lines) > 2:
                parts.append(lines[0])  # Conclusion first
                parts.append("")
                parts.append("**Details:**")
                parts.extend(lines[1:])
            else:
                parts.append(content)

        elif style.structure == "narrative":
            # I-style: Wrap in engaging narrative
            parts.append(content)

        elif style.structure == "step-by-step":
            # S-style: Add numbered steps
            lines = content.split('\n')
            step_lines = []
            step_num = 1
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and not stripped.startswith('-'):
                    step_lines.append(f"{step_num}. {stripped}")
                    step_num += 1
                else:
                    step_lines.append(line)
            parts.extend(step_lines)

        elif style.structure == "evidence-based":
            # C-style: Add evidence markers
            parts.append(content)

        else:
            parts.append(content)

        # Add closing
        if style.closing:
            parts.append("")
            parts.append(style.closing)

        return '\n'.join(parts)

    def format_decision_point(self, options: List[str], style: Optional[CommunicationStyle] = None) -> str:
        """Format a decision point according to DISC style"""
        if style is None:
            style = self.get_communication_style()

        if style.decision_format == "options":
            # D-style: Quick options
            return "⚠️ **Decision needed:**\n" + '\n'.join(f"  {chr(65+i)}. {opt}" for i, opt in enumerate(options))

        elif style.decision_format == "recommendation":
            # I-style: Enthusiastic recommendation
            return f"💡 **I recommend:** {options[0]}\n\nOther options: " + ', '.join(options[1:])

        elif style.decision_format == "consensus":
            # S-style: Collaborative decision
            return "🤝 **Let's decide together:**\n" + '\n'.join(f"  - {opt}" for opt in options) + "\n\nWhich feels right to you?"

        else:  # analysis
            # C-style: Detailed analysis
            result = "📊 **Decision analysis:**\n\n"
            for i, opt in enumerate(options):
                result += f"Option {chr(65+i)}: {opt}\n"
                result += f"  - Pros: [to be analyzed]\n"
                result += f"  - Cons: [to be analyzed]\n\n"
            return result
