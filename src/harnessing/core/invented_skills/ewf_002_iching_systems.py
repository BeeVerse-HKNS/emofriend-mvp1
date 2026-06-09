from __future__ import annotations

import math
import structlog
from dataclasses import dataclass, field
from typing import Any

from .base_engine import BaseInventionEngine
from .base_invention_engine import ConfidenceLevel, InventionResult

logger = structlog.get_logger()

HEXAGRAM_NAMES: dict[int, str] = {
    1: "Qian/Creative",
    2: "Kun/Receptive",
    3: "Zhun/Difficulty",
    4: "Meng/Youthful Folly",
    5: "Xu/Waiting",
    6: "Song/Conflict",
    7: "Shi/Army",
    8: "Bi/Holding Together",
    9: "Hexagram_9",
    10: "Hexagram_10",
    11: "Hexagram_11",
    12: "Hexagram_12",
    13: "Hexagram_13",
    14: "Hexagram_14",
    15: "Hexagram_15",
    16: "Hexagram_16",
    17: "Hexagram_17",
    18: "Hexagram_18",
    19: "Hexagram_19",
    20: "Hexagram_20",
    21: "Hexagram_21",
    22: "Hexagram_22",
    23: "Hexagram_23",
    24: "Hexagram_24",
    25: "Hexagram_25",
    26: "Hexagram_26",
    27: "Hexagram_27",
    28: "Hexagram_28",
    29: "Hexagram_29",
    30: "Hexagram_30",
    31: "Hexagram_31",
    32: "Hexagram_32",
    33: "Hexagram_33",
    34: "Hexagram_34",
    35: "Hexagram_35",
    36: "Hexagram_36",
    37: "Hexagram_37",
    38: "Hexagram_38",
    39: "Hexagram_39",
    40: "Hexagram_40",
    41: "Hexagram_41",
    42: "Hexagram_42",
    43: "Hexagram_43",
    44: "Hexagram_44",
    45: "Hexagram_45",
    46: "Hexagram_46",
    47: "Hexagram_47",
    48: "Hexagram_48",
    49: "Hexagram_49",
    50: "Hexagram_50",
    51: "Hexagram_51",
    52: "Hexagram_52",
    53: "Hexagram_53",
    54: "Hexagram_54",
    55: "Hexagram_55",
    56: "Hexagram_56",
    57: "Hexagram_57",
    58: "Hexagram_58",
    59: "Hexagram_59",
    60: "Hexagram_60",
    61: "Hexagram_61",
    62: "Hexagram_62",
    63: "Hexagram_63",
    64: "Hexagram_64",
}

HEXAGRAM_NATURES: dict[int, str] = {
    1: "Creative",
    2: "Receptive",
    3: "Difficulty",
    4: "Youthful Folly",
    5: "Waiting",
    6: "Conflict",
    7: "Army",
    8: "Holding Together",
}


@dataclass
class HexagramState:
    number: int
    binary: list[int]
    name: str
    nature: str


@dataclass
class TransitionPrediction:
    target_hexagram: HexagramState
    probability: float
    lead_time: float
    transition_type: str


class HexagramEncoder:
    def encode(self, hexagram_number: int) -> list[int]:
        if hexagram_number < 1 or hexagram_number > 64:
            logger.warning("invalid_hexagram_number", number=hexagram_number)
            hexagram_number = max(1, min(64, hexagram_number))
        index = hexagram_number - 1
        binary = []
        for bit_pos in range(5, -1, -1):
            binary.append((index >> bit_pos) & 1)
        return binary

    def decode(self, binary: list[int]) -> int:
        if len(binary) != 6:
            logger.warning("invalid_binary_length", length=len(binary))
            return 1
        number = 0
        for bit in binary:
            number = (number << 1) | (bit & 1)
        return number + 1


class SystemStateClassifier:
    _DIMENSION_KEYS: list[str] = [
        "growth",
        "stability",
        "complexity",
        "momentum",
        "cohesion",
        "openness",
    ]

    def __init__(self, encoder: HexagramEncoder | None = None) -> None:
        self._encoder = encoder or HexagramEncoder()

    def classify(self, metrics: dict[str, float]) -> HexagramState:
        binary: list[int] = []
        for key in self._DIMENSION_KEYS:
            value = metrics.get(key, 0.5)
            binary.append(1 if value >= 0.5 else 0)
        number = self._encoder.decode(binary)
        name = HEXAGRAM_NAMES.get(number, f"Hexagram_{number}")
        nature = HEXAGRAM_NATURES.get(number, "Unknown")
        return HexagramState(number=number, binary=binary, name=name, nature=nature)


class ChangingLineTransitionOperator:
    def __init__(self, encoder: HexagramEncoder | None = None) -> None:
        self._encoder = encoder or HexagramEncoder()

    def transition(self, current_state: HexagramState, changing_lines: list[int]) -> HexagramState:
        new_binary = list(current_state.binary)
        for line_index in changing_lines:
            if 0 <= line_index < 6:
                new_binary[line_index] = 1 - new_binary[line_index]
        new_number = self._encoder.decode(new_binary)
        name = HEXAGRAM_NAMES.get(new_number, f"Hexagram_{new_number}")
        nature = HEXAGRAM_NATURES.get(new_number, "Unknown")
        return HexagramState(number=new_number, binary=new_binary, name=name, nature=nature)


class PhaseTransitionPredictor:
    _TRANSITION_TYPES: list[str] = [
        "gradual_evolution",
        "sudden_transformation",
        "cyclic_return",
        "divergent_branching",
    ]

    def __init__(
        self,
        encoder: HexagramEncoder | None = None,
        transition_op: ChangingLineTransitionOperator | None = None,
    ) -> None:
        self._encoder = encoder or HexagramEncoder()
        self._transition_op = transition_op or ChangingLineTransitionOperator(self._encoder)

    def predict(self, current_state: HexagramState, dynamics: dict[str, Any]) -> TransitionPrediction:
        instability = dynamics.get("instability", 0.5)
        velocity = dynamics.get("velocity", 0.5)
        changing_lines = self._identify_changing_lines(current_state, dynamics)
        target_state = self._transition_op.transition(current_state, changing_lines)
        probability = self._compute_transition_probability(current_state, target_state, dynamics)
        lead_time = self._compute_lead_time(instability, velocity)
        transition_type = self._classify_transition_type(changing_lines, instability)
        return TransitionPrediction(
            target_hexagram=target_state,
            probability=probability,
            lead_time=lead_time,
            transition_type=transition_type,
        )

    def _identify_changing_lines(self, state: HexagramState, dynamics: dict[str, Any]) -> list[int]:
        changing: list[int] = []
        instability = dynamics.get("instability", 0.5)
        dimension_instability = dynamics.get("dimension_instability", {})
        for i in range(6):
            dim_instability = dimension_instability.get(str(i), instability)
            threshold = 1.0 - instability
            if dim_instability > threshold:
                changing.append(i)
        if not changing and instability > 0.6:
            most_unstable = 5
            max_dim = 0.0
            for i in range(6):
                dim_val = dimension_instability.get(str(i), 0.0)
                if dim_val > max_dim:
                    max_dim = dim_val
                    most_unstable = i
            changing.append(most_unstable)
        return changing

    def _compute_transition_probability(
        self,
        current: HexagramState,
        target: HexagramState,
        dynamics: dict[str, Any],
    ) -> float:
        instability = dynamics.get("instability", 0.5)
        hamming = sum(1 for a, b in zip(current.binary, target.binary) if a != b)
        distance_factor = math.exp(-hamming * 0.5)
        probability = instability * distance_factor
        return max(0.0, min(1.0, probability))

    def _compute_lead_time(self, instability: float, velocity: float) -> float:
        if velocity <= 0.0:
            return float("inf")
        effective_velocity = velocity * (0.5 + instability * 0.5)
        if effective_velocity <= 0.0:
            return float("inf")
        return 1.0 / effective_velocity

    def _classify_transition_type(self, changing_lines: list[int], instability: float) -> str:
        num_changing = len(changing_lines)
        if num_changing == 0:
            return self._TRANSITION_TYPES[2]
        if num_changing >= 4:
            return self._TRANSITION_TYPES[1]
        if instability > 0.8:
            return self._TRANSITION_TYPES[3]
        return self._TRANSITION_TYPES[0]


class IChingSystemsThinking(BaseInventionEngine):
    name = "IChingSystemsThinking"
    invention_id = "EWF-002"
    operator = "log(Yang ⊗ Yin) + ∇(network_flow)"
    formula = "log(Yang ⊗ Yin) + ∇(network_flow) → classify(hexagram) → predict(transition)"
    category = "EWF"
    description = "Classify system states into 64 hexagram archetypes and predict phase transitions"

    def __init__(self) -> None:
        self._encoder = HexagramEncoder()
        self._classifier = SystemStateClassifier(self._encoder)
        self._transition_op = ChangingLineTransitionOperator(self._encoder)
        self._predictor = PhaseTransitionPredictor(self._encoder, self._transition_op)

    def execute(self, context: dict[str, Any]) -> InventionResult:
        try:
            system_metrics = context.get("system_metrics")
            if not system_metrics:
                logger.warning("no_system_metrics_provided", invention_id=self.invention_id)
                return InventionResult(
                    output={"state": "empty", "message": "No system_metrics provided"},
                    confidence=ConfidenceLevel.UNCERTAIN,
                    invention_id=self.invention_id,
                )

            current_state = self._classifier.classify(system_metrics)

            changing_lines = self._identify_unstable_dimensions(system_metrics)

            dynamics = context.get("dynamics", {
                "instability": self._compute_instability(system_metrics),
                "velocity": system_metrics.get("momentum", 0.5),
                "dimension_instability": {
                    str(i): 1.0 - abs(system_metrics.get(k, 0.5) - 0.5) * 2
                    for i, k in enumerate(SystemStateClassifier._DIMENSION_KEYS)
                },
            })

            prediction = self._predictor.predict(current_state, dynamics)

            yang_count = sum(current_state.binary)
            yin_count = 6 - yang_count
            yang_yin_tensor = yang_count * yin_count
            log_yang_yin = math.log1p(yang_yin_tensor) if yang_yin_tensor >= 0 else 0.0

            result_output = {
                "state": "classified",
                "current_hexagram": {
                    "number": current_state.number,
                    "binary": current_state.binary,
                    "name": current_state.name,
                    "nature": current_state.nature,
                    "yang_lines": yang_count,
                    "yin_lines": yin_count,
                },
                "changing_lines": changing_lines,
                "prediction": {
                    "target_hexagram": {
                        "number": prediction.target_hexagram.number,
                        "binary": prediction.target_hexagram.binary,
                        "name": prediction.target_hexagram.name,
                        "nature": prediction.target_hexagram.nature,
                    },
                    "probability": prediction.probability,
                    "lead_time": prediction.lead_time,
                    "transition_type": prediction.transition_type,
                },
                "formula_components": {
                    "log_yang_yin": log_yang_yin,
                    "yang_yin_tensor": yang_yin_tensor,
                    "network_flow_gradient": dynamics.get("instability", 0.0),
                },
            }

            confidence = ConfidenceLevel.INFERRED
            if prediction.probability > 0.7:
                confidence = ConfidenceLevel.RESEARCHED
            if prediction.probability > 0.9 and len(changing_lines) <= 2:
                confidence = ConfidenceLevel.VERIFIED

            logger.info(
                "iching_systems_thinking_classified",
                invention_id=self.invention_id,
                hexagram=current_state.number,
                hexagram_name=current_state.name,
                target_hexagram=prediction.target_hexagram.number,
                probability=prediction.probability,
            )

            return InventionResult(
                output=result_output,
                confidence=confidence,
                synergy_detected=self.get_synergy_partners(),
                metadata={
                    "formula": self.formula,
                    "operator": self.operator,
                    "category": self.category,
                },
                invention_id=self.invention_id,
            )

        except Exception as exc:
            logger.error("iching_systems_thinking_failed", invention_id=self.invention_id, error=str(exc))
            return InventionResult(
                output={"state": "error", "error": str(exc)},
                confidence=ConfidenceLevel.UNCERTAIN,
                invention_id=self.invention_id,
            )

    def validate(self, result: InventionResult) -> bool:
        if not result.output:
            return False
        if result.confidence == ConfidenceLevel.UNCERTAIN:
            return False
        state = result.output.get("state")
        if state != "classified":
            return False
        current = result.output.get("current_hexagram", {})
        if not current.get("number"):
            return False
        number = current["number"]
        if number < 1 or number > 64:
            return False
        binary = current.get("binary", [])
        if len(binary) != 6:
            return False
        if not all(b in (0, 1) for b in binary):
            return False
        prediction = result.output.get("prediction", {})
        prob = prediction.get("probability", 0.0)
        if prob < 0.0 or prob > 1.0:
            return False
        return True

    def get_synergy_partners(self) -> list[str]:
        return ["EWF-005", "EWF-001", "SCI-005"]

    def _identify_unstable_dimensions(self, metrics: dict[str, float]) -> list[int]:
        unstable: list[int] = []
        for i, key in enumerate(SystemStateClassifier._DIMENSION_KEYS):
            value = metrics.get(key, 0.5)
            if abs(value - 0.5) < 0.2:
                unstable.append(i)
        return unstable

    def _compute_instability(self, metrics: dict[str, float]) -> float:
        values = [metrics.get(k, 0.5) for k in SystemStateClassifier._DIMENSION_KEYS]
        if not values:
            return 0.5
        variance = sum((v - 0.5) ** 2 for v in values) / len(values)
        return min(1.0, variance * 4.0)
