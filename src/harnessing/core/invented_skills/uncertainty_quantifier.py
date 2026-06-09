from __future__ import annotations

import math
import structlog
from dataclasses import dataclass, field
from typing import Any

logger = structlog.get_logger()


@dataclass
class UncertaintyInterval:
    lower_bound: float
    upper_bound: float
    confidence_level: float

    @property
    def width(self) -> float:
        return self.upper_bound - self.lower_bound

    @property
    def midpoint(self) -> float:
        return (self.lower_bound + self.upper_bound) / 2


@dataclass
class ConfidenceScore:
    value: float
    source: str
    calibration_factor: float = 1.0

    @property
    def calibrated_value(self) -> float:
        return min(1.0, max(0.0, self.value * self.calibration_factor))


class EpistemicUncertainty:
    def __init__(self):
        self._model_uncertainty_weight = 0.4
        self._data_uncertainty_weight = 0.3
        self._structural_uncertainty_weight = 0.3

    def estimate(self, predictions: list[float], model_confidence: float = 0.8) -> float:
        if not predictions:
            return 1.0
        variance = self._calculate_variance(predictions)
        model_uncertainty = 1.0 - model_confidence
        data_uncertainty = min(1.0, variance * 2)
        structural_uncertainty = 0.1 if len(predictions) > 3 else 0.3
        epistemic = (
            self._model_uncertainty_weight * model_uncertainty +
            self._data_uncertainty_weight * data_uncertainty +
            self._structural_uncertainty_weight * structural_uncertainty
        )
        return min(1.0, epistemic)

    def _calculate_variance(self, values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return variance


class AleatoricUncertainty:
    def __init__(self):
        self._noise_threshold = 0.1
        self._inherent_variability_weight = 0.5

    def estimate(self, observations: list[float], noise_level: float = 0.1) -> float:
        if not observations:
            return 0.5
        noise_uncertainty = min(1.0, noise_level * 2)
        variability = self._estimate_variability(observations)
        aleatoric = (
            (1 - self._inherent_variability_weight) * noise_uncertainty +
            self._inherent_variability_weight * variability
        )
        return min(1.0, aleatoric)

    def _estimate_variability(self, observations: list[float]) -> float:
        if len(observations) < 2:
            return 0.5
        diffs = [abs(observations[i] - observations[i-1]) for i in range(1, len(observations))]
        if not diffs:
            return 0.0
        avg_diff = sum(diffs) / len(diffs)
        return min(1.0, avg_diff)


class ConfidenceCalibrator:
    def __init__(self):
        self._calibration_history: list[tuple[float, bool]] = []
        self._min_samples_for_calibration = 10

    def calibrate(self, raw_confidence: float, outcome: bool | None = None) -> ConfidenceScore:
        if outcome is not None:
            self._calibration_history.append((raw_confidence, outcome))
        calibration_factor = self._compute_calibration_factor()
        return ConfidenceScore(
            value=raw_confidence,
            source="calibrator",
            calibration_factor=calibration_factor
        )

    def _compute_calibration_factor(self) -> float:
        if len(self._calibration_history) < self._min_samples_for_calibration:
            return 1.0
        bins: dict[str, list[bool]] = {}
        for conf, outcome in self._calibration_history:
            bin_key = f"{int(conf * 10) / 10:.1f}"
            if bin_key not in bins:
                bins[bin_key] = []
            bins[bin_key].append(outcome)
        total_error = 0.0
        count = 0
        for bin_key, outcomes in bins.items():
            expected = float(bin_key)
            actual = sum(outcomes) / len(outcomes)
            total_error += abs(expected - actual)
            count += 1
        if count == 0:
            return 1.0
        avg_error = total_error / count
        return 1.0 / (1.0 + avg_error)

    def get_calibration_status(self) -> dict[str, Any]:
        return {
            "samples": len(self._calibration_history),
            "min_required": self._min_samples_for_calibration,
            "is_calibrated": len(self._calibration_history) >= self._min_samples_for_calibration
        }


class UncertaintyEstimator:
    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        self.epistemic = EpistemicUncertainty()
        self.aleatoric = AleatoricUncertainty()

    def estimate_total(self, predictions: list[float], observations: list[float] | None = None) -> dict[str, float]:
        epistemic = self.epistemic.estimate(predictions)
        aleatoric = self.aleatoric.estimate(observations or predictions)
        total = math.sqrt(epistemic ** 2 + aleatoric ** 2)
        return {
            "epistemic": epistemic,
            "aleatoric": aleatoric,
            "total": min(1.0, total)
        }

    def compute_interval(self, estimate: float, total_uncertainty: float) -> UncertaintyInterval:
        z_score = 1.96 if self.confidence_level == 0.95 else 2.576 if self.confidence_level == 0.99 else 1.645
        margin = z_score * total_uncertainty
        return UncertaintyInterval(
            lower_bound=max(0.0, estimate - margin),
            upper_bound=min(1.0, estimate + margin),
            confidence_level=self.confidence_level
        )


class UncertaintyQuantifier:
    def __init__(self, confidence_level: float = 0.95) -> None:
        self._formula = "R ^ P + log(S)"
        self._capability = "uncertainty_quantifier"
        self._id = "INV-006"
        self.calibrator = ConfidenceCalibrator()
        self.estimator = UncertaintyEstimator(confidence_level)

    def analyze(
        self,
        predictions: list[float],
        observations: list[float] | None = None,
        model_confidence: float = 0.8,
        noise_level: float = 0.1
    ) -> dict[str, Any]:
        try:
            uncertainty = self.estimator.estimate_total(predictions, observations)
            mean_prediction = sum(predictions) / len(predictions) if predictions else 0.5
            interval = self.estimator.compute_interval(mean_prediction, uncertainty["total"])
            confidence = self.calibrator.calibrate(1.0 - uncertainty["total"])
            result = {
                "uncertainty": uncertainty,
                "confidence_interval": {
                    "lower": interval.lower_bound,
                    "upper": interval.upper_bound,
                    "width": interval.width,
                    "confidence_level": interval.confidence_level
                },
                "calibrated_confidence": confidence.calibrated_value,
                "mean_prediction": mean_prediction,
                "calibration_status": self.calibrator.get_calibration_status()
            }
            logger.info(
                "uncertainty_quantifier_success",
                capability=self._capability,
                total_uncertainty=uncertainty["total"]
            )
            return {"status": "success", "capability": self._capability, "result": result, "formula": self._formula}
        except Exception as exc:
            logger.error("uncertainty_quantifier_failed", capability=self._capability, error=str(exc))
            return {"status": "error", "capability": self._capability, "error": str(exc)}

    def execute(
        self,
        predictions: list[float],
        observations: list[float] | None = None,
        model_confidence: float = 0.8,
        noise_level: float = 0.1
    ) -> dict[str, Any]:
        return self.analyze(predictions, observations, model_confidence, noise_level)

    def update_calibration(self, raw_confidence: float, outcome: bool) -> ConfidenceScore:
        return self.calibrator.calibrate(raw_confidence, outcome)


if __name__ == "__main__":
    quantifier = UncertaintyQuantifier()
    test_predictions = [0.7, 0.72, 0.68, 0.71, 0.69]
    test_observations = [0.65, 0.70, 0.68, 0.72, 0.67]
    result = quantifier.analyze(test_predictions, test_observations)
    print(f"Status: {result['status']}")
    print(f"Total uncertainty: {result['result']['uncertainty']['total']:.4f}")
    print(f"Epistemic: {result['result']['uncertainty']['epistemic']:.4f}")
    print(f"Aleatoric: {result['result']['uncertainty']['aleatoric']:.4f}")
    print(f"Confidence interval: [{result['result']['confidence_interval']['lower']:.4f}, {result['result']['confidence_interval']['upper']:.4f}]")
    print(f"Calibrated confidence: {result['result']['calibrated_confidence']:.4f}")
    assert result["status"] == "success"
    assert 0.0 <= result["result"]["uncertainty"]["total"] <= 1.0
    assert result["result"]["confidence_interval"]["lower"] <= result["result"]["confidence_interval"]["upper"]
    print("All tests passed!")
