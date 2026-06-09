"""Ethics Guard — Ethical Boundary Engine.

Core Principle: Ethical_Violations = 0

Ensures all Dark strategies remain within ethical boundaries.
The Ethics Guard is ALWAYS active, even in Dark mode — it prevents
unethical action while allowing strategic awareness.

Three Guard Levels:
    1. Hard Boundary — Never cross (illegal, harmful, deceptive)
    2. Soft Boundary — Warn before crossing (manipulative, exploitative)
    3. Advisory — Recommend best practice (transparent, constructive)
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ViolationSeverity(Enum):
    """Severity levels for ethical violations."""

    NONE = "none"
    ADVISORY = "advisory"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"


class ViolationCategory(Enum):
    """Categories of ethical violations."""

    DECEPTION = "deception"           # Intentional lying or misleading
    MANIPULATION = "manipulation"     # Exploiting psychological vulnerabilities
    HARM = "harm"                     # Causing physical/financial/emotional harm
    ILLEGAL = "illegal"               # Violating laws or regulations
    PRIVACY = "privacy"               # Violating privacy or data rights
    EXPLOITATION = "exploitation"     # Taking unfair advantage
    DISCRIMINATION = "discrimination" # Unfair treatment based on protected characteristics
    NONE = "none"                     # No violation


class EthicsCheckResult:
    """Result of an ethics check."""

    def __init__(
        self,
        is_ethical: bool,
        severity: ViolationSeverity,
        category: ViolationCategory,
        message: str,
        suggestions: list[str] | None = None,
    ) -> None:
        self.is_ethical = is_ethical
        self.severity = severity
        self.category = category
        self.message = message
        self.suggestions = suggestions or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_ethical": self.is_ethical,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "suggestions": self.suggestions,
        }


# Hard boundary patterns — NEVER allowed
_HARD_BOUNDARY_PATTERNS: list[dict[str, str]] = [
    {
        "pattern": "hack",
        "category": "illegal",
        "message": "Hacking is illegal and unethical.",
    },
    {
        "pattern": "steal",
        "category": "illegal",
        "message": "Stealing is illegal and unethical.",
    },
    {
        "pattern": "fraud",
        "category": "illegal",
        "message": "Fraud is illegal and unethical.",
    },
    {
        "pattern": "exploit vulnerability",
        "category": "harm",
        "message": "Exploiting vulnerabilities for harm is unethical.",
    },
    {
        "pattern": "discriminate",
        "category": "discrimination",
        "message": "Discrimination is unethical and often illegal.",
    },
    {
        "pattern": "sell personal data",
        "category": "privacy",
        "message": "Selling personal data without consent violates privacy.",
    },
    {
        "pattern": "gambling",
        "category": "illegal",
        "message": "Gambling is restricted in China (刑法第303条).",
    },
]

# Soft boundary patterns — WARN before proceeding
_SOFT_BOUNDARY_PATTERNS: list[dict[str, str]] = [
    {
        "pattern": "manipulate",
        "category": "manipulation",
        "message": "This may be manipulative. Consider transparent alternatives.",
    },
    {
        "pattern": "deceive",
        "category": "deception",
        "message": "Deception erodes trust. Consider honest communication.",
    },
    {
        "pattern": "hide information",
        "category": "deception",
        "message": "Withholding information may be unethical in this context.",
    },
    {
        "pattern": "pressure",
        "category": "exploitation",
        "message": "Applying pressure may be exploitative. Ensure voluntary consent.",
    },
]

# Advisory patterns — recommend best practice
_ADVISORY_PATTERNS: list[dict[str, str]] = [
    {
        "pattern": "compete",
        "category": "none",
        "message": "Competition is healthy when fair. Ensure level playing field.",
    },
    {
        "pattern": "negotiate",
        "category": "none",
        "message": "Negotiation is ethical when both parties benefit. Seek win-win.",
    },
]


class EthicsGuard:
    """Ethics Guard — Ethical Boundary Engine.

    Enforces ethical boundaries on all strategies and actions.
    The guard is ALWAYS active — even in Dark mode, it prevents
    unethical action while allowing strategic awareness.

    Core principle: "知暗行明" means knowing the dark, but ACTING in the light.
    Dark strategies are for AWARENESS and DEFENSE, never for offensive unethical action.

    Args:
        jurisdiction: Legal jurisdiction for compliance ("china", "hk", "international").
    """

    # Jurisdiction-specific rules
    _JURISDICTION_RULES: dict[str, dict[str, Any]] = {
        "china": {
            "extra_hard_patterns": [
                {
                    "pattern": "赌博",
                    "category": "illegal",
                    "message": "中国刑法第303条：赌博相关活动违法。",
                },
                {
                    "pattern": "赌博",
                    "category": "illegal",
                    "message": "China Criminal Law Art. 303: Gambling activities are illegal.",
                },
            ],
            "regulatory_framework": "PIPL + 网安法 + 数安法",
        },
        "hk": {
            "extra_hard_patterns": [
                {"pattern": "gambling unlicensed", "category": "illegal",
                 "message": "Hong Kong Cap. 148: Unlicensed gambling is illegal."},
            ],
            "regulatory_framework": "PDPO + Cap. 148",
        },
        "international": {
            "extra_hard_patterns": [],
            "regulatory_framework": "GDPR + local laws",
        },
    }

    def __init__(self, jurisdiction: str = "international") -> None:
        self.jurisdiction = jurisdiction
        self._violation_log: list[EthicsCheckResult] = []

    def check(self, action: str, context: dict[str, Any] | None = None) -> EthicsCheckResult:
        """Check an action against ethical boundaries.

        Args:
            action: The action or strategy description to check.
            context: Optional context for jurisdiction-aware checking.

        Returns:
            EthicsCheckResult with severity, category, and suggestions.
        """
        action_lower = action.lower()

        # Check hard boundaries (FATAL)
        for pattern_def in _HARD_BOUNDARY_PATTERNS:
            if pattern_def["pattern"] in action_lower:
                result = EthicsCheckResult(
                    is_ethical=False,
                    severity=ViolationSeverity.FATAL,
                    category=ViolationCategory(pattern_def["category"]),
                    message=pattern_def["message"],
                    suggestions=["This action is not allowed under any circumstances."],
                )
                self._violation_log.append(result)
                return result

        # Check jurisdiction-specific hard boundaries
        jurisdiction_rules = self._JURISDICTION_RULES.get(self.jurisdiction, {})
        for pattern_def in jurisdiction_rules.get("extra_hard_patterns", []):
            if pattern_def["pattern"] in action_lower:
                result = EthicsCheckResult(
                    is_ethical=False,
                    severity=ViolationSeverity.FATAL,
                    category=ViolationCategory(pattern_def["category"]),
                    message=pattern_def["message"],
                    suggestions=["This action violates local regulations."],
                )
                self._violation_log.append(result)
                return result

        # Check soft boundaries (WARNING)
        for pattern_def in _SOFT_BOUNDARY_PATTERNS:
            if pattern_def["pattern"] in action_lower:
                result = EthicsCheckResult(
                    is_ethical=True,
                    severity=ViolationSeverity.WARNING,
                    category=ViolationCategory(pattern_def["category"]),
                    message=pattern_def["message"],
                    suggestions=[
                        "Consider using a transparent alternative.",
                        "Ensure all parties are fully informed.",
                        "Review the LightDarkBalance principle: 知暗行明.",
                    ],
                )
                self._violation_log.append(result)
                return result

        # Check advisory patterns
        for pattern_def in _ADVISORY_PATTERNS:
            if pattern_def["pattern"] in action_lower:
                result = EthicsCheckResult(
                    is_ethical=True,
                    severity=ViolationSeverity.ADVISORY,
                    category=ViolationCategory.NONE,
                    message=pattern_def["message"],
                )
                self._violation_log.append(result)
                return result

        # No violations found
        return EthicsCheckResult(
            is_ethical=True,
            severity=ViolationSeverity.NONE,
            category=ViolationCategory.NONE,
            message="Action passes ethical review.",
        )

    def check_strategy(self, strategy_dict: dict[str, Any]) -> EthicsCheckResult:
        """Check a strategy dictionary against ethical boundaries.

        Args:
            strategy_dict: Strategy dictionary with 'name', 'description', etc.

        Returns:
            EthicsCheckResult for the strategy.
        """
        name = strategy_dict.get("name", "")
        description = strategy_dict.get("description", "")
        combined = f"{name} {description}"
        return self.check(combined)

    def get_violation_log(self) -> list[dict[str, Any]]:
        """Get the log of all ethics checks performed.

        Returns:
            List of EthicsCheckResult dictionaries.
        """
        return [r.to_dict() for r in self._violation_log]

    def clear_log(self) -> None:
        """Clear the violation log."""
        self._violation_log.clear()

    @property
    def violation_count(self) -> int:
        """Number of violations logged."""
        return len(self._violation_log)

    @property
    def fatal_count(self) -> int:
        """Number of fatal violations logged."""
        return sum(1 for v in self._violation_log if v.severity == ViolationSeverity.FATAL)
