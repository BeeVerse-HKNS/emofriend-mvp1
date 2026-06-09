"""
Cross-Cultural Thinking Engine (R-ERR-081)
D-100 Daily Learning Cycle 2026-06-03

整合東方同西方嘅核心思維方法，提供跨文化決策支持。
基於 Hofstede 文化維度 + EWF-001（QuantumZenCognition）+ EWF-005（PratityaCausalReasoning）。

信心等級：🔍 已研究（D-100 Daily Learning）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CultureSphere(str, Enum):
    """文化圈分類"""
    EAST_ASIAN = "EAST_ASIAN"  # 中、日、韓
    WESTERN = "WESTERN"        # 歐美
    SOUTH_ASIAN = "SOUTH_ASIAN"  # 印度
    ISLAMIC = "ISLAMIC"        # 中東
    AFRICAN = "AFRICAN"        # 非洲
    LATIN = "LATIN"            # 拉美


class ThinkingMethod(str, Enum):
    """思維方法類型"""
    # 中國
    SUN_TZU = "SUN_TZU"                    # 孫子兵法
    I_CHING = "I_CHING"                    # 易經
    DAOIST = "DAOIST"                      # 道家
    CONFUCIAN = "CONFUCIAN"                # 儒家
    WANG_YANGMING = "WANG_YANGMING"        # 王陽明心學
    # 西方
    GREEK_LOGIC = "GREEK_LOGIC"            # 古希臘邏輯
    SCIENTIFIC_METHOD = "SCIENTIFIC_METHOD"  # 科學方法
    ENLIGHTENMENT = "ENLIGHTENMENT"        # 啟蒙運動
    DARWINIAN = "DARWINIAN"                # 達爾文進化論
    VIENNA_CIRCLE = "VIENNA_CIRCLE"        # 維也納學派


@dataclass
class ThinkingPrinciple:
    """思維方法嘅單一原則"""
    name: str
    original_phrase: str
    explanation: str
    application_scenarios: list[str]
    limitations: list[str] = field(default_factory=list)


@dataclass
class ThinkingMethodProfile:
    """完整嘅思維方法檔案"""
    method: ThinkingMethod
    culture_sphere: CultureSphere
    core_principles: list[ThinkingPrinciple]
    decision_style: str
    time_orientation: str  # LONG_TERM / SHORT_TERM / PRESENT
    authority_distance: str  # HIGH / MEDIUM / LOW
    use_cases: list[str]


@dataclass
class CrossCulturalComparison:
    """跨文化對比結果"""
    method_a: ThinkingMethod
    method_b: ThinkingMethod
    similarities: list[str]
    differences: list[str]
    complementary_scenarios: list[str]


class CrossCulturalThinkingEngine:
    """跨文化思維整合引擎 — 從文字規則升級為可執行代碼 (R-ERR-081)"""

    def __init__(self) -> None:
        self._profiles: dict[ThinkingMethod, ThinkingMethodProfile] = {}
        self._load_default_profiles()

    def _load_default_profiles(self) -> None:
        """載入預設嘅東西方思維方法"""
        # 中國 - 孫子兵法
        self._profiles[ThinkingMethod.SUN_TZU] = ThinkingMethodProfile(
            method=ThinkingMethod.SUN_TZU,
            culture_sphere=CultureSphere.EAST_ASIAN,
            core_principles=[
                ThinkingPrinciple(
                    name="五事七計",
                    original_phrase="道、天、地、將、法；主孰有道？將孰有能？天地孰得？法令孰行？兵眾孰強？士卒孰練？賞罰孰明？",
                    explanation="從七個維度評估實力對比，系統化分析勝負因素",
                    application_scenarios=["策略規劃", "競爭分析", "資源評估"],
                ),
                ThinkingPrinciple(
                    name="知己知彼",
                    original_phrase="知彼知己，百戰不殆",
                    explanation="深入了解自己同對手嘅能力、意圖、限制",
                    application_scenarios=["SWOT 分析", "對手研究", "自我評估"],
                ),
                ThinkingPrinciple(
                    name="以正合以奇勝",
                    original_phrase="以正合，以奇勝",
                    explanation="正兵當面對決，奇兵出其不意",
                    application_scenarios=["雙軌策略", "A/B 測試", "創新 vs 穩健"],
                ),
            ],
            decision_style="情境式（依時依地依對手）",
            time_orientation="LONG_TERM",
            authority_distance="MEDIUM",
            use_cases=["戰略", "競爭策略", "風險管理"],
        )

        # 中國 - 易經
        self._profiles[ThinkingMethod.I_CHING] = ThinkingMethodProfile(
            method=ThinkingMethod.I_CHING,
            culture_sphere=CultureSphere.EAST_ASIAN,
            core_principles=[
                ThinkingPrinciple(
                    name="陰陽",
                    original_phrase="一陰一陽之謂道",
                    explanation="對立統一，動態平衡",
                    application_scenarios=["衝突解決", "二元分析", "動態平衡"],
                ),
                ThinkingPrinciple(
                    name="三才",
                    original_phrase="天、地、人",
                    explanation="從三個維度分析問題",
                    application_scenarios=["系統思維", "多維度分析", "PESTEL"],
                ),
                ThinkingPrinciple(
                    name="六十四卦",
                    original_phrase="卦有六十四，變有無窮",
                    explanation="系統化分類所有可能嘅狀態同轉化",
                    application_scenarios=["狀態機", "場景規劃", "Case Analysis"],
                ),
            ],
            decision_style="變易式（順應變化）",
            time_orientation="LONG_TERM",
            authority_distance="MEDIUM",
            use_cases=["系統思維", "場景規劃", "動態策略"],
        )

        # 中國 - 道家
        self._profiles[ThinkingMethod.DAOIST] = ThinkingMethodProfile(
            method=ThinkingMethod.DAOIST,
            culture_sphere=CultureSphere.EAST_ASIAN,
            core_principles=[
                ThinkingPrinciple(
                    name="無為而治",
                    original_phrase="無為而無不為",
                    explanation="最小干預，讓系統自然演化",
                    application_scenarios=["去中心化", "自組織", "最小可行"],
                ),
                ThinkingPrinciple(
                    name="道法自然",
                    original_phrase="道法自然",
                    explanation="順應事物本來嘅規律",
                    application_scenarios=["First Principles", "去人為設計"],
                ),
                ThinkingPrinciple(
                    name="上善若水",
                    original_phrase="上善若水，水善利萬物而不爭",
                    explanation="柔軟、靈活、滋養而不對抗",
                    application_scenarios=["柔性策略", "用戶體驗", "適應性架構"],
                ),
            ],
            decision_style="順應式（順勢而為）",
            time_orientation="LONG_TERM",
            authority_distance="LOW",
            use_cases=["去中心化", "自組織", "柔性架構"],
        )

        # 中國 - 儒家
        self._profiles[ThinkingMethod.CONFUCIAN] = ThinkingMethodProfile(
            method=ThinkingMethod.CONFUCIAN,
            culture_sphere=CultureSphere.EAST_ASIAN,
            core_principles=[
                ThinkingPrinciple(
                    name="仁義禮智信",
                    original_phrase="仁、義、禮、智、信",
                    explanation="五常倫理框架，指導人際互動",
                    application_scenarios=["團隊文化", "信任建立", "道德決策"],
                ),
                ThinkingPrinciple(
                    name="格物致知",
                    original_phrase="致知在格物，物格而後知至",
                    explanation="通過研究事物本質嚟獲得知識",
                    application_scenarios=["First Principles", "深度調研", "實證研究"],
                ),
            ],
            decision_style="共識式（先後征求意見再決策）",
            time_orientation="LONG_TERM",
            authority_distance="HIGH",
            use_cases=["團隊管理", "文化建設", "倫理決策"],
        )

        # 中國 - 王陽明心學
        self._profiles[ThinkingMethod.WANG_YANGMING] = ThinkingMethodProfile(
            method=ThinkingMethod.WANG_YANGMING,
            culture_sphere=CultureSphere.EAST_ASIAN,
            core_principles=[
                ThinkingPrinciple(
                    name="知行合一",
                    original_phrase="知是行之始，行是知之成",
                    explanation="知識同實踐必須統一",
                    application_scenarios=["Lean Startup", "MVP", "實踐優先"],
                ),
                ThinkingPrinciple(
                    name="致良知",
                    original_phrase="致良知",
                    explanation="依從內心嘅道德判斷",
                    application_scenarios=["倫理 AI", "用戶同理心", "產品初心"],
                ),
            ],
            decision_style="直覺式 + 實踐式",
            time_orientation="PRESENT",
            authority_distance="LOW",
            use_cases=["產品決策", "倫理設計", "快速迭代"],
        )

        # 西方 - 古希臘邏輯
        self._profiles[ThinkingMethod.GREEK_LOGIC] = ThinkingMethodProfile(
            method=ThinkingMethod.GREEK_LOGIC,
            culture_sphere=CultureSphere.WESTERN,
            core_principles=[
                ThinkingPrinciple(
                    name="三段論",
                    original_phrase="大前提 + 小前提 → 結論",
                    explanation="從已知前提出發推導結論",
                    application_scenarios=["邏輯推理", "代碼證明", "數學證明"],
                ),
                ThinkingPrinciple(
                    name="反詰法",
                    original_phrase="Socratic Method",
                    explanation="通過連續追問逼近真相",
                    application_scenarios=["需求挖掘", "批判思維", "調試"],
                ),
            ],
            decision_style="演繹式（從一般到特殊）",
            time_orientation="PRESENT",
            authority_distance="LOW",
            use_cases=["邏輯推理", "代碼證明", "批判思維"],
        )

        # 西方 - 科學方法
        self._profiles[ThinkingMethod.SCIENTIFIC_METHOD] = ThinkingMethodProfile(
            method=ThinkingMethod.SCIENTIFIC_METHOD,
            culture_sphere=CultureSphere.WESTERN,
            core_principles=[
                ThinkingPrinciple(
                    name="歸納法",
                    original_phrase="Bacon's Induction",
                    explanation="從觀察數據歸納出規律",
                    application_scenarios=["數據分析", "用戶研究", "A/B 測試"],
                ),
                ThinkingPrinciple(
                    name="演繹法",
                    original_phrase="Descartes' Deduction",
                    explanation="從第一原理演繹出推論",
                    application_scenarios=["First Principles", "架構設計", "數學建模"],
                ),
                ThinkingPrinciple(
                    name="可證偽性",
                    original_phrase="Falsifiability",
                    explanation="理論必須能被實驗否證",
                    application_scenarios=["假設驗證", "MVP 測試", "Benchmark"],
                ),
            ],
            decision_style="實證式（用數據驗證）",
            time_orientation="SHORT_TERM",
            authority_distance="LOW",
            use_cases=["研發", "數據決策", "實驗設計"],
        )

        # 西方 - 啟蒙運動
        self._profiles[ThinkingMethod.ENLIGHTENMENT] = ThinkingMethodProfile(
            method=ThinkingMethod.ENLIGHTENMENT,
            culture_sphere=CultureSphere.WESTERN,
            core_principles=[
                ThinkingPrinciple(
                    name="批判哲學",
                    original_phrase="Kant's Critique",
                    explanation="對理性本身嘅界限進行批判",
                    application_scenarios=["AI 倫理", "元認知", "限制識別"],
                ),
                ThinkingPrinciple(
                    name="經驗主義",
                    original_phrase="Locke's Empiricism",
                    explanation="知識來源於經驗",
                    application_scenarios=["用戶研究", "數據驅動", "實證主義"],
                ),
            ],
            decision_style="批判式（質疑假設）",
            time_orientation="PRESENT",
            authority_distance="LOW",
            use_cases=["學術研究", "哲學分析", "元認知"],
        )

        # 西方 - 達爾文進化論
        self._profiles[ThinkingMethod.DARWINIAN] = ThinkingMethodProfile(
            method=ThinkingMethod.DARWINIAN,
            culture_sphere=CultureSphere.WESTERN,
            core_principles=[
                ThinkingPrinciple(
                    name="自然選擇",
                    original_phrase="Natural Selection",
                    explanation="適者生存，唔適者淘汰",
                    application_scenarios=["市場競爭", "產品演進", "A/B 測試"],
                ),
                ThinkingPrinciple(
                    name="適者生存",
                    original_phrase="Survival of the Fittest",
                    explanation="最適應環境嘅個體生存",
                    application_scenarios=["MVP 演化", "市場適應", "技術選型"],
                ),
            ],
            decision_style="演化式（適者生存）",
            time_orientation="LONG_TERM",
            authority_distance="LOW",
            use_cases=["產品演進", "市場策略", "技術演化"],
        )

        # 西方 - 維也納學派
        self._profiles[ThinkingMethod.VIENNA_CIRCLE] = ThinkingMethodProfile(
            method=ThinkingMethod.VIENNA_CIRCLE,
            culture_sphere=CultureSphere.WESTERN,
            core_principles=[
                ThinkingPrinciple(
                    name="可證偽性",
                    original_phrase="Falsifiability Criterion (Popper)",
                    explanation="科學同非科學嘅分界在於能否被證偽",
                    application_scenarios=["假設驗證", "Benchmark", "假說-檢驗"],
                ),
                ThinkingPrinciple(
                    name="奧卡姆剃刀",
                    original_phrase="Occam's Razor",
                    explanation="如無必要，勿增實體",
                    application_scenarios=["YAGNI", "架構簡化", "依賴最小化"],
                ),
                ThinkingPrinciple(
                    name="邏輯實證主義",
                    original_phrase="Logical Positivism",
                    explanation="命題嘅意義在於可被經驗驗證",
                    application_scenarios=["數據驗證", "可測試性", "指標設計"],
                ),
            ],
            decision_style="簡約式（最少假設）",
            time_orientation="SHORT_TERM",
            authority_distance="LOW",
            use_cases=["科學研究", "YAGNI 設計", "指標設計"],
        )

    def get_profile(self, method: ThinkingMethod) -> ThinkingMethodProfile:
        """查詢單一思維方法嘅詳細檔案"""
        return self._profiles[method]

    def recommend_for_scenario(self, scenario: str) -> list[ThinkingMethodProfile]:
        """根據場景推薦適用嘅思維方法"""
        recommendations = []
        for profile in self._profiles.values():
            for use_case in profile.use_cases:
                if scenario.lower() in use_case.lower() or use_case.lower() in scenario.lower():
                    recommendations.append(profile)
                    break
        return recommendations

    def compare(self, method_a: ThinkingMethod, method_b: ThinkingMethod) -> CrossCulturalComparison:
        """跨文化對比兩個思維方法"""
        a = self._profiles[method_a]
        b = self._profiles[method_b]
        return CrossCulturalComparison(
            method_a=method_a,
            method_b=method_b,
            similarities=_find_similarities(a, b),
            differences=_find_differences(a, b),
            complementary_scenarios=_find_complementary(a, b),
        )

    def get_all_eastern_methods(self) -> list[ThinkingMethodProfile]:
        """獲取所有東方思維方法"""
        return [p for p in self._profiles.values() if p.culture_sphere == CultureSphere.EAST_ASIAN]

    def get_all_western_methods(self) -> list[ThinkingMethodProfile]:
        """獲取所有西方思維方法"""
        return [p for p in self._profiles.values() if p.culture_sphere == CultureSphere.WESTERN]

    def suggest_for_user_culture(self, culture: str) -> list[ThinkingMethodProfile]:
        """根據用戶文化背景推薦思維方法"""
        culture_lower = culture.lower()
        if any(k in culture_lower for k in ["中國", "中", "chinese", "hong kong", "台灣", "taiwan"]):
            return self.get_all_eastern_methods()
        return self.get_all_western_methods()


def _find_similarities(a: ThinkingMethodProfile, b: ThinkingMethodProfile) -> list[str]:
    """找兩個方法嘅相似點"""
    sims = []
    if a.time_orientation == b.time_orientation:
        sims.append(f"時間取向相同：{a.time_orientation}")
    if a.authority_distance == b.authority_distance:
        sims.append(f"權力距離相同：{a.authority_distance}")
    common_use_cases = set(a.use_cases) & set(b.use_cases)
    if common_use_cases:
        sims.append(f"共同應用：{', '.join(common_use_cases)}")
    return sims


def _find_differences(a: ThinkingMethodProfile, b: ThinkingMethodProfile) -> list[str]:
    """找兩個方法嘅差異"""
    diffs = []
    if a.time_orientation != b.time_orientation:
        diffs.append(f"時間取向不同：{a.time_orientation} vs {b.time_orientation}")
    if a.authority_distance != b.authority_distance:
        diffs.append(f"權力距離不同：{a.authority_distance} vs {b.authority_distance}")
    if a.culture_sphere != b.culture_sphere:
        diffs.append(f"文化圈不同：{a.culture_sphere.value} vs {b.culture_sphere.value}")
    return diffs


def _find_complementary(a: ThinkingMethodProfile, b: ThinkingMethodProfile) -> list[str]:
    """找兩個方法嘅互補場景"""
    complementary = []
    if a.decision_style != b.decision_style:
        complementary.append(f"互補決策風格：{a.decision_style} + {b.decision_style}")
    if a.time_orientation != b.time_orientation:
        complementary.append("短期+長期平衡")
    return complementary
