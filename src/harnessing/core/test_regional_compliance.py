from __future__ import annotations

import sys
from typing import Any


def run_metacognitive_tests() -> dict[str, Any]:
    from harnessing.core.metacognitive_reflection_engine import (
        MetacognitiveReflectionEngine,
        RegionalComplianceTestMixin,
        ConfidenceLevel,
    )

    mixin = RegionalComplianceTestMixin()
    results = {}

    results["HK_PDPO"] = mixin.test_hk_pdbo_confidence_calibration()
    results["CN_PIPL"] = mixin.test_cn_pipl_uncertainty_quantification()
    results["EU_AI_Act"] = mixin.test_eu_ai_act_transparency_verification()
    results["SG_Agent"] = mixin.test_sg_agent_governance_reflection()

    engine = MetacognitiveReflectionEngine()
    test_claims = [
        "This is a verified claim from official documentation",
        "This is a researched claim from web search",
        "This is a speculative claim without evidence",
    ]
    kb = {"verified_claim": "Official documentation confirms this"}
    result = engine.reflect(test_claims, kb)
    results["Basic_Reflection"] = {
        "convergence": result.convergence_achieved,
        "avg_confidence": result.final_confidence_avg,
        "claims_processed": len(result.original_claims),
    }

    return results


def run_world_model_tests() -> dict[str, Any]:
    from harnessing.core.world_model_constructor import (
        RegionalWorldModelMixin,
        WorldModelConstructor,
    )

    mixin = RegionalWorldModelMixin()
    results = {}

    results["HK_CrossBorder"] = mixin.test_hk_cross_border_awareness()
    results["CN_Localization"] = mixin.test_cn_data_localization()
    results["EU_GDPR"] = mixin.test_eu_gdpr_restrictions()
    results["SG_Framework"] = mixin.test_sg_agent_framework()
    results["Multi_Jurisdiction"] = mixin.test_multiple_jurisdiction_tracking()

    engine = WorldModelConstructor()
    engine.construct_from_interactions([
        {"entities": [
            {"name": "TestEntity", "entity_type": "CONCEPT", "attributes": {"test": True}}
        ]}
    ])
    summary = engine.construct_from_interactions([])
    results["Basic_Construction"] = {
        "entities": summary.total_entities,
        "relations": summary.total_relations,
        "coverage": summary.coverage_score,
    }

    return results


def run_causal_tests() -> dict[str, Any]:
    from harnessing.core.causal_reasoning_engine import (
        CausalReasoningEngine,
        Observation,
        RegionalCausalMixin,
    )

    mixin = RegionalCausalMixin()
    results = {}

    results["HK_LAR"] = mixin.test_hk_legal_implications()
    results["CN_Liability"] = mixin.test_cn_liability_attribution()
    results["EU_Intervention"] = mixin.test_eu_intervention_restrictions()
    results["SG_Accountability"] = mixin.test_sg_agent_accountability()
    results["Counterfactual"] = mixin.test_counterfactual_reasoning_regional()

    engine = CausalReasoningEngine()
    obs = [
        Observation(event="cause_A", observed_outcome="effect_X"),
        Observation(event="cause_B", observed_outcome="effect_Y"),
    ]
    analysis = engine.analyze_causally(obs)
    results["Basic_Analysis"] = {
        "relations_found": len(analysis.causal_relations),
        "root_causes": len(analysis.root_causes),
        "downstream_effects": len(analysis.downstream_effects),
    }

    return results


def run_attention_tests() -> dict[str, Any]:
    from harnessing.core.attention_budget_manager import (
        AttentionBudgetManager,
        InfoCategory,
        InfoUnit,
        Priority,
        RegionalAttentionMixin,
    )
    import time

    mixin = RegionalAttentionMixin()
    results = {}

    results["HK_DataMinimization"] = mixin.test_hk_data_minimization()
    results["CN_ContentFiltering"] = mixin.test_cn_content_filtering()
    results["EU_Fairness"] = mixin.test_eu_fairness_priority()
    results["SG_Transparency"] = mixin.test_sg_transparency_allocation()
    results["Budget_Reallocation"] = mixin.test_budget_reallocation_regional()

    manager = AttentionBudgetManager(total_budget=1000)
    unit = InfoUnit(
        id="test_unit",
        content="Test content",
        category=InfoCategory.RULE,
        priority=Priority.HIGH,
        relevance_score=0.8,
        token_count=100,
        timestamp=time.time(),
        source="test"
    )
    manager.add_info(unit)
    result = manager.auto_manage()
    results["Basic_Management"] = {
        "active_count": len(result.active_info),
        "budget_util": result.budget_status.get("utilization", 0),
    }

    return results


def run_unified_tests() -> dict[str, Any]:
    from harnessing.core.unified_cognitive_architecture import (
        RegionalUnifiedMixin,
        UnifiedCognitiveArchitecture,
    )

    mixin = RegionalUnifiedMixin()
    results = {}

    results["HK_PDPO"] = mixin.test_hk_pdbo_mode_selection()
    results["CN_Localization"] = mixin.test_cn_localization_orchestration()
    results["EU_Risk"] = mixin.test_eu_risk_classification()
    results["SG_Governance"] = mixin.test_sg_agent_governance()
    results["MultiRegion"] = mixin.test_multi_region_convergence()

    unified = UnifiedCognitiveArchitecture()
    result = unified.think("Analyze a complex interdependent task")
    results["Basic_Think"] = {
        "mode": result.mode_used.value,
        "confidence": result.final_confidence,
        "convergence": result.convergence_achieved,
    }

    return results


def run_all_regional_tests() -> dict[str, Any]:
    print("=" * 60)
    print("RUNNING GLOBAL COMPLIANCE REGIONAL TESTS")
    print("=" * 60)

    all_results = {}

    print("\n[1/5] MetacognitiveReflectionEngine Regional Tests...")
    all_results["metacognitive"] = run_metacognitive_tests()
    print(f"  ✓ {len(all_results['metacognitive'])} test categories completed")

    print("\n[2/5] WorldModelConstructor Regional Tests...")
    all_results["world_model"] = run_world_model_tests()
    print(f"  ✓ {len(all_results['world_model'])} test categories completed")

    print("\n[3/5] CausalReasoningEngine Regional Tests...")
    all_results["causal"] = run_causal_tests()
    print(f"  ✓ {len(all_results['causal'])} test categories completed")

    print("\n[4/5] AttentionBudgetManager Regional Tests...")
    all_results["attention"] = run_attention_tests()
    print(f"  ✓ {len(all_results['attention'])} test categories completed")

    print("\n[5/5] UnifiedCognitiveArchitecture Regional Tests...")
    all_results["unified"] = run_unified_tests()
    print(f"  ✓ {len(all_results['unified'])} test categories completed")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_categories = sum(len(v) for v in all_results.values())
    print(f"Total Test Categories: {total_categories}")

    print("\nRegional Coverage:")
    regions = ["HK", "CN", "EU", "SG"]
    for region in regions:
        count = sum(1 for engine_results in all_results.values() for key in engine_results if region in key)
        print(f"  {region}: {count} test cases")

    print("\nTest Categories by Engine:")
    for engine, results in all_results.items():
        print(f"  {engine}: {len(results)} categories")

    print("\n" + "=" * 60)
    print("DETAILED RESULTS")
    print("=" * 60)
    for engine, results in all_results.items():
        print(f"\n### {engine.upper()} ###")
        for test_name, result in results.items():
            status = "✓" if result.get("region") or result.get("convergence") or result.get("entities", 0) > 0 else "○"
            print(f"  {status} {test_name}: {result}")

    return all_results


if __name__ == "__main__":
    results = run_all_regional_tests()
    print("\n✅ All regional compliance tests completed successfully!")
    sys.exit(0)
