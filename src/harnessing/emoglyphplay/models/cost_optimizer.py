"""CostOptimizer — Token cost optimization and budget tracking.

Optimizes AI model spending through cost analysis, budget allocation,
and usage tracking across models and time periods.
"""

from __future__ import annotations


class CostOptimizer:
    """CostOptimizer — Token cost optimization and budget tracking.

    Tracks spending across models, allocates budgets, and provides
    cost optimization recommendations.

    Args:
        daily_budget: Maximum daily spending budget in USD.
        monthly_budget: Maximum monthly spending budget in USD.
    """

    def __init__(
        self,
        daily_budget: float = 10.0,
        monthly_budget: float = 200.0,
    ) -> None:
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget
        self._spending: dict[str, float] = {}
        self._model_usage: dict[str, dict[str, float]] = {}

    def record_usage(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cost_per_1k_input: float,
        cost_per_1k_output: float,
    ) -> dict:
        """Record a model usage event and calculate cost.

        Args:
            model_id: The model identifier.
            input_tokens: Number of input tokens used.
            output_tokens: Number of output tokens generated.
            cost_per_1k_input: Cost per 1K input tokens.
            cost_per_1k_output: Cost per 1K output tokens.

        Returns:
            Dictionary with keys: model_id, input_cost, output_cost, total_cost.
        """
        input_cost = (input_tokens / 1000.0) * cost_per_1k_input
        output_cost = (output_tokens / 1000.0) * cost_per_1k_output
        total_cost = input_cost + output_cost

        self._spending[model_id] = self._spending.get(model_id, 0.0) + total_cost
        if model_id not in self._model_usage:
            self._model_usage[model_id] = {"tokens": 0, "cost": 0.0}
        self._model_usage[model_id]["tokens"] += input_tokens + output_tokens
        self._model_usage[model_id]["cost"] += total_cost

        return {
            "model_id": model_id,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(total_cost, 6),
        }

    def check_budget(self, estimated_cost: float) -> dict:
        """Check if an estimated cost fits within the budget.

        Args:
            estimated_cost: The estimated cost for a planned operation.

        Returns:
            Dictionary with keys: within_budget, remaining_daily, remaining_monthly.
        """
        total_spent = sum(self._spending.values())
        remaining_daily = max(0.0, self.daily_budget - total_spent)
        remaining_monthly = max(0.0, self.monthly_budget - total_spent)

        return {
            "within_budget": estimated_cost <= remaining_daily,
            "remaining_daily": round(remaining_daily, 4),
            "remaining_monthly": round(remaining_monthly, 4),
        }

    def get_spending_report(self) -> dict:
        """Get a spending report across all models.

        Returns:
            Dictionary with keys: total_spent, by_model, budget_status.
        """
        total_spent = sum(self._spending.values())
        return {
            "total_spent": round(total_spent, 4),
            "by_model": {k: round(v, 4) for k, v in self._spending.items()},
            "budget_status": {
                "daily_budget": self.daily_budget,
                "monthly_budget": self.monthly_budget,
                "daily_remaining": round(max(0.0, self.daily_budget - total_spent), 4),
                "monthly_remaining": round(max(0.0, self.monthly_budget - total_spent), 4),
            },
        }

    def suggest_optimization(self) -> list[dict]:
        """Suggest cost optimization strategies based on usage patterns.

        Returns:
            List of suggestion dictionaries with keys: type, description,
            estimated_savings_percent.
        """
        suggestions: list[dict] = []
        total_spent = sum(self._spending.values())

        if total_spent > self.daily_budget * 0.8:
            suggestions.append({
                "type": "budget_alert",
                "description": "Spending is above 80% of daily budget. Consider routing to cheaper models.",
                "estimated_savings_percent": 20,
            })

        for model_id, usage in self._model_usage.items():
            if "large" in model_id and usage["cost"] > total_spent * 0.5:
                suggestions.append({
                    "type": "model_downgrade",
                    "description": (
                        f"Model '{model_id}' accounts for "
                        f"{usage['cost']/max(total_spent,0.01)*100:.0f}% of cost. "
                        f"Consider using a medium model for simpler tasks."
                    ),
                    "estimated_savings_percent": 30,
                })

        if not suggestions:
            suggestions.append({
                "type": "optimal",
                "description": "Current spending pattern looks efficient.",
                "estimated_savings_percent": 0,
            })

        return suggestions
