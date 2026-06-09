"""
Framework Selector (R-ERR-085)
D-100 Daily Learning Cycle 2026-06-03

根據應用場景自動推薦 AI Agent 框架，遵循：
1. 核心獨立 + 場景借用策略
2. 每個借用嘅框架組件必須有本地 fallback
3. 至少 1 個「零外部依賴」方案優先

5 個應用場景：
1. 快速原型 (RAPID_PROTOTYPE) — < 1 週 / 低預算
2. MVP (MVP) — < 1 月 / 中預算
3. 企業級 (ENTERPRISE) — > 1000 用戶 / 高可用
4. 跨境部署 (CROSS_BORDER) — 中國 + 國際 / 合規要求
5. 邊緣計算 (EDGE) — 資源受限 / 離線運行

信心等級：🔍 已研究（基於 D-100 2026 框架選型對比）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ScenarioType(str, Enum):
    """5 個應用場景"""
    RAPID_PROTOTYPE = "RAPID_PROTOTYPE"  # 快速原型
    MVP = "MVP"  # MVP
    ENTERPRISE = "ENTERPRISE"  # 企業級
    CROSS_BORDER = "CROSS_BORDER"  # 跨境部署
    EDGE = "EDGE"  # 邊緣計算


@dataclass
class FrameworkOption:
    """單一框架方案"""
    name: str
    description: str
    external_dependencies: list[str]  # 外部依賴（API Key / 付費服務）
    local_fallback: bool  # 是否有本地 fallback
    best_for: list[ScenarioType]
    pros: list[str]
    cons: list[str]
    cost: str  # FREE / LOW / MEDIUM / HIGH
    setup_time: str  # < 1 day / 1-3 days / 1 week / 1 month
    confidence: str  # ✅/🔍/⚠️/❌
    rationale: str


@dataclass
class FrameworkRecommendation:
    """框架選型推薦結果"""
    scenario: ScenarioType
    zero_dependency_option: FrameworkOption  # 必含
    additional_options: list[FrameworkOption]  # 至少 2 個額外選項
    rationale: str
    decision_tree_path: list[str] = field(default_factory=list)


class FrameworkSelector:
    """場景化框架選型器 — 從文字規則升級為可執行代碼 (R-ERR-085)"""

    def __init__(self) -> None:
        self._options: list[FrameworkOption] = []
        self._load_default_options()

    def _load_default_options(self) -> None:
        # 零外部依賴方案
        self._options.append(
            FrameworkOption(
                name="BeeVerse + Ollama + 知識庫",
                description="本地 Python 框架 + Ollama 本地 LLM + 知識庫驅動",
                external_dependencies=[],
                local_fallback=True,
                best_for=[ScenarioType.RAPID_PROTOTYPE, ScenarioType.MVP, ScenarioType.EDGE, ScenarioType.CROSS_BORDER],
                pros=[
                    "零外部依賴，完全本地運行",
                    "知識庫驅動，無 Token 限制",
                    "永久免費",
                    "中國可訪問（Ollama 本地）",
                    "支持繁體中文/簡體中文",
                ],
                cons=[
                    "需要本地 GPU 16GB+ VRAM",
                    "模型能力受限於本地 LLM",
                    "企業級監控需自行實作",
                ],
                cost="FREE",
                setup_time="1 week",
                confidence="🔍",
                rationale="符合 Rule 15（零外部依賴優先）+ Rule 32（依賴最小化）",
            )
        )

        # Microsoft agent-framework
        self._options.append(
            FrameworkOption(
                name="Microsoft agent-framework",
                description=".NET + Python 雙語言企業級 Agent 框架",
                external_dependencies=["Azure OpenAI 可選"],
                local_fallback=True,
                best_for=[ScenarioType.ENTERPRISE, ScenarioType.CROSS_BORDER],
                pros=[
                    "企業級監控 + 可觀測性",
                    "雙語言支援（.NET + Python）",
                    "與 Microsoft 生態深度整合",
                    "Workflow + Agent 雙模式",
                ],
                cons=[
                    "需熟悉 .NET 或 Python",
                    "部分企業功能需 Azure 訂閱",
                    "學習曲線較高",
                ],
                cost="MEDIUM",
                setup_time="1 month",
                confidence="🔍",
                rationale="適合企業級（> 1000 用戶）+ 跨境部署（與 Microsoft 全球節點整合）",
            )
        )

        # LangGraph
        self._options.append(
            FrameworkOption(
                name="LangGraph + LangChain",
                description="DAG 風格嘅 Agent 編排框架",
                external_dependencies=["OpenAI API 可選"],
                local_fallback=True,
                best_for=[ScenarioType.MVP, ScenarioType.ENTERPRISE],
                pros=[
                    "成熟嘅 DAG 編排",
                    "豐富嘅生態（LangSmith, LangServe）",
                    "Python 為主，學習曲線中等",
                ],
                cons=[
                    "DAG 設計可能過度複雜",
                    "深度依賴 LangChain 抽象",
                    "中國訪問需注意",
                ],
                cost="LOW",
                setup_time="1-3 days",
                confidence="🔍",
                rationale="適合需要 DAG 編排 + 成熟生態嘅 MVP/企業級",
            )
        )

        # PydanticAI
        self._options.append(
            FrameworkOption(
                name="PydanticAI",
                description="類型安全嘅 Python Agent 框架",
                external_dependencies=["LLM API Key"],
                local_fallback=True,
                best_for=[ScenarioType.MVP, ScenarioType.ENTERPRISE],
                pros=[
                    "類型安全（Pydantic v2 整合）",
                    "FastAPI 風格嘅 DX",
                    "依賴注入 + 結構化輸出",
                ],
                cons=[
                    "生態較新",
                    "需要熟悉 Pydantic v2",
                ],
                cost="LOW",
                setup_time="1 week",
                confidence="🔍",
                rationale="適合重視類型安全 + 結構化輸出嘅項目",
            )
        )

        # AutoGen
        self._options.append(
            FrameworkOption(
                name="AutoGen (Microsoft)",
                description="多 Agent 協作框架",
                external_dependencies=["LLM API Key"],
                local_fallback=True,
                best_for=[ScenarioType.MVP, ScenarioType.ENTERPRISE],
                pros=[
                    "多 Agent 對話模式",
                    "GroupChat 支援",
                    "研究背景強（微軟研究院）",
                ],
                cons=[
                    "代碼生成風格獨特",
                    "調試較困難",
                ],
                cost="LOW",
                setup_time="1-3 days",
                confidence="🔍",
                rationale="適合多 Agent 協作 + GroupChat 場景",
            )
        )

        # CrewAI
        self._options.append(
            FrameworkOption(
                name="CrewAI",
                description="角色扮演 + 任務協作框架",
                external_dependencies=["LLM API Key"],
                local_fallback=True,
                best_for=[ScenarioType.MVP, ScenarioType.RAPID_PROTOTYPE],
                pros=[
                    "角色扮演直觀",
                    "快速搭建 Agent 團隊",
                    "低代碼友好",
                ],
                cons=[
                    "調試困難",
                    "擴展性受限",
                ],
                cost="LOW",
                setup_time="< 1 day",
                confidence="🔍",
                rationale="適合快速搭建多 Agent 團隊嘅 MVP",
            )
        )

        # OpenAI Agents SDK
        self._options.append(
            FrameworkOption(
                name="OpenAI Agents SDK",
                description="OpenAI 官方 Agent SDK",
                external_dependencies=["OpenAI API Key（必須）"],
                local_fallback=False,
                best_for=[ScenarioType.MVP, ScenarioType.ENTERPRISE],
                pros=[
                    "OpenAI 官方支援",
                    "原生 GPT-4o 整合",
                    "輕量級",
                ],
                cons=[
                    "必須用 OpenAI（強綁定）",
                    "中國訪問困難",
                    "違反 Rule 87 互操作性",
                ],
                cost="MEDIUM",
                setup_time="1-3 days",
                confidence="🔍",
                rationale="強綁定 OpenAI，不推薦用於中國或跨平台場景",
            )
        )

        # Smolagents (HuggingFace)
        self._options.append(
            FrameworkOption(
                name="Smolagents (HuggingFace)",
                description="輕量級 HuggingFace Agent 框架",
                external_dependencies=["HF Token 可選"],
                local_fallback=True,
                best_for=[ScenarioType.EDGE, ScenarioType.RAPID_PROTOTYPE],
                pros=[
                    "極輕量（< 1000 行代碼）",
                    "支持本地模型",
                    "HuggingFace 生態",
                ],
                cons=[
                    "生態較新",
                    "企業級功能有限",
                ],
                cost="FREE",
                setup_time="< 1 day",
                confidence="🔍",
                rationale="適合資源受限嘅邊緣計算 + 快速原型",
            )
        )

    def select_for_scenario(self, scenario: ScenarioType, max_options: int = 3) -> FrameworkRecommendation:
        """為場景選擇至少 3 個方案（必含零外部依賴）"""
        # 1. 必含零外部依賴
        zero_dep = next(
            (opt for opt in self._options if not opt.external_dependencies and scenario in opt.best_for),
            self._options[0],  # fallback to BeeVerse
        )

        # 2. 篩選適用於該場景嘅其他選項
        candidates = [
            opt for opt in self._options
            if opt.name != zero_dep.name and scenario in opt.best_for
        ]
        # 3. 排序：本地 fallback 優先 + 成本低優先
        candidates.sort(key=lambda x: (not x.local_fallback, x.cost))
        additional = candidates[: max(0, max_options - 1)]

        # 4. 構建決策路徑
        decision_path = self._build_decision_path(scenario)

        return FrameworkRecommendation(
            scenario=scenario,
            zero_dependency_option=zero_dep,
            additional_options=additional,
            rationale=self._build_rationale(scenario, zero_dep, additional),
            decision_tree_path=decision_path,
        )

    def select_for_requirements(
        self,
        max_users: int = 100,
        budget: str = "FREE",
        timeline_days: int = 7,
        cross_border: bool = False,
        offline: bool = False,
    ) -> FrameworkRecommendation:
        """根據需求自動匹配場景"""
        if offline or budget == "FREE" and max_users < 100:
            scenario = ScenarioType.EDGE if offline else ScenarioType.RAPID_PROTOTYPE
        elif cross_border:
            scenario = ScenarioType.CROSS_BORDER
        elif max_users >= 1000:
            scenario = ScenarioType.ENTERPRISE
        elif timeline_days <= 30:
            scenario = ScenarioType.MVP
        else:
            scenario = ScenarioType.MVP
        return self.select_for_scenario(scenario)

    def get_all_options(self) -> list[FrameworkOption]:
        return list(self._options)

    def _build_decision_path(self, scenario: ScenarioType) -> list[str]:
        path_map = {
            ScenarioType.RAPID_PROTOTYPE: [
                "Q: 是否需要 < 1 週完成？ → 是",
                "Q: 預算是否 < ¥1000？ → 是",
                "→ RAPID_PROTOTYPE 場景",
                "Q: 是否需要本地運行？ → 推薦 BeeVerse",
            ],
            ScenarioType.MVP: [
                "Q: 是否 < 1 月？ → 是",
                "Q: 是否需要 DAG 編排？",
                "→ MVP 場景",
            ],
            ScenarioType.ENTERPRISE: [
                "Q: 用戶數 > 1000？ → 是",
                "Q: 需要企業級監控？ → 是",
                "→ ENTERPRISE 場景",
                "Q: 預算允許 Azure 訂閱？",
            ],
            ScenarioType.CROSS_BORDER: [
                "Q: 部署到中國 + 國際？ → 是",
                "Q: 是否需要 PIPL/GDPR 雙合規？",
                "→ CROSS_BORDER 場景",
            ],
            ScenarioType.EDGE: [
                "Q: 資源受限（< 8GB RAM）？",
                "Q: 是否需要離線運行？",
                "→ EDGE 場景",
            ],
        }
        return path_map.get(scenario, [])

    def _build_rationale(
        self,
        scenario: ScenarioType,
        zero_dep: FrameworkOption,
        additional: list[FrameworkOption],
    ) -> str:
        lines = [f"場景：{scenario.value}"]
        lines.append(f"零外部依賴方案（必含）：{zero_dep.name}")
        lines.append(f"理由：{zero_dep.rationale}")
        for opt in additional:
            lines.append(f"備選：{opt.name} — {opt.rationale}")
        return "\n".join(lines)
