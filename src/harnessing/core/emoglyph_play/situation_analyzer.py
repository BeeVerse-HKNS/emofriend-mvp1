"""
SituationAnalyzer — 情境分析引擎

分析用户的完整情境，不只是关键词匹配。

旧方式（LLM 传统思维）：
  "我要在中国收钱" → 无关键词匹配 → 不推荐任何技能 ❌

新方式（EmoGlyph Play 情境分析）：
  "我要在中国收钱" → geo=china, domain=payment, intent=create
  → 推荐 alipay + douyinpay ✅

分析维度：
  - geo: 地理环境（china / global / any）
  - domain: 任务领域（payment / data / design / ...）
  - intent: 用户意图（create / fix / research / deploy / ...）
  - urgency: 紧急程度（0-1）
  - complexity: 复杂度（0-1）
  - player_type: EmoGlyph Play 玩家类型
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .domain_map import DomainMap
from .lsp_ai_engine import LSPPlayerTypeDetector, PlayerType


# ── 地理环境检测关键词 ──────────────────────────────────────────────

_GEO_CHINA_SIGNALS = [
    # 中文
    "中国", "大陆", "国内", "微信", "支付宝", "抖音", "飞书", "钉钉",
    "小红书", "微博", "B站", "百度", "阿里", "腾讯", "字节",
    "人民币", "CNY", "千帆", "百炼", "扣子", "Coze",
    "收钱", "付款码", "扫码支付", "当面付", "代扣",
    "备案", "ICP", "合规", "刑法303",
    # Pinyin / English
    "alipay", "douyin", "wechat", "weibo", "bilibili",
]

_GEO_GLOBAL_SIGNALS = [
    "stripe", "paypal", "visa", "mastercard", "USD", "EUR",
    "aws", "azure", "gcp", "vercel", "netlify",
    "github", "gitlab", "figma", "notion", "slack",
    "checkout", "subscription", "billing",
]


# ── 意图检测关键词 ──────────────────────────────────────────────────

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "create": [
        "创建", "建立", "新建", "添加", "开发", "实现", "写", "生成",
        "create", "build", "add", "implement", "generate", "make",
    ],
    "fix": [
        "修复", "解决", "调试", "排错", "debug", "fix", "troubleshoot",
        "错误", "bug", "问题", "报错", "崩溃", "慢", "卡",
    ],
    "research": [
        "研究", "调研", "分析", "调查", "了解", "学习",
        "research", "analyze", "investigate", "study", "explore",
    ],
    "deploy": [
        "部署", "发布", "上线", "推送", "deploy", "release", "publish",
        "CI/CD", "Docker", "容器",
    ],
    "design": [
        "设计", "界面", "UI", "UX", "原型", "样式", "美化",
        "design", "prototype", "style", "theme", "layout",
    ],
    "test": [
        "测试", "验证", "QA", "质量", "test", "verify", "validate",
    ],
    "optimize": [
        "优化", "加速", "提升", "改进", "改善",
        "optimize", "improve", "speed up", "enhance", "refactor",
    ],
}


# ── 紧急程度信号 ────────────────────────────────────────────────────

_URGENCY_HIGH = [
    "紧急", "立刻", "马上", "尽快", "urgent", "asap", "immediately",
    "critical", "blocking", "down", "broken", "crash",
]

_URGENCY_LOW = [
    "慢慢", "不急", "有空", "以后", "eventually", "when possible",
    "low priority", "nice to have",
]


# ── Situation 数据类 ───────────────────────────────────────────────

@dataclass
class Situation:
    """用户的完整情境。"""

    geo: str = "any"                # "china" | "global" | "any"
    domain: str = "unknown"         # 任务领域
    domain_confidence: float = 0.0  # 领域匹配置信度
    intent: str = "create"          # 用户意图
    intent_confidence: float = 0.0  # 意图检测置信度
    urgency: float = 0.5            # 紧急程度 0-1
    complexity: float = 0.5         # 复杂度 0-1
    project_context: dict = field(default_factory=dict)
    player_type: PlayerType = PlayerType.EXPLORER
    player_confidence: float = 0.3
    matched_domains: list[tuple[str, float]] = field(default_factory=list)

    def summary(self) -> str:
        """人类语言解释（Rule 86）。"""
        geo_label = {"china": "中国", "global": "国际", "any": "通用"}.get(self.geo, self.geo)
        intent_label = {
            "create": "创建", "fix": "修复", "research": "研究",
            "deploy": "部署", "design": "设计", "test": "测试",
            "optimize": "优化",
        }.get(self.intent, self.intent)
        return (
            f"情境分析：地理={geo_label}，领域={self.domain}，"
            f"意图={intent_label}，玩家类型={self.player_type.value}"
        )


# ── SituationAnalyzer ──────────────────────────────────────────────

class SituationAnalyzer:
    """情境分析引擎 — 分析用户的完整情境。"""

    def __init__(self, domain_map: DomainMap | None = None) -> None:
        self.domain_map = domain_map or DomainMap()

    def analyze(
        self, prompt: str, context: dict[str, Any] | None = None
    ) -> Situation:
        """分析用户的完整情境。

        Parameters
        ----------
        prompt : str
            用户的输入 prompt。
        context : dict | None
            额外上下文（如 geo, project, history 等）。

        Returns
        -------
        Situation
            完整的情境分析结果。
        """
        if context is None:
            context = {}

        # 1. 地理环境检测
        geo = context.get("geo") or self._detect_geo(prompt)

        # 2. 领域检测
        matched_domains = self.domain_map.find_domains(prompt, context)
        domain = "unknown"
        domain_confidence = 0.0
        if matched_domains:
            domain = matched_domains[0][0]
            domain_confidence = matched_domains[0][1]

        # 3. 意图检测
        intent, intent_confidence = self._detect_intent(prompt)

        # 4. 玩家类型检测
        player_type, player_confidence = LSPPlayerTypeDetector.detect(prompt)

        # 5. 紧急程度
        urgency = self._estimate_urgency(prompt)

        # 6. 复杂度
        complexity = self._estimate_complexity(prompt)

        return Situation(
            geo=geo,
            domain=domain,
            domain_confidence=domain_confidence,
            intent=intent,
            intent_confidence=intent_confidence,
            urgency=urgency,
            complexity=complexity,
            project_context=context,
            player_type=player_type,
            player_confidence=player_confidence,
            matched_domains=matched_domains,
        )

    def _detect_geo(self, prompt: str) -> str:
        """检测地理环境。"""
        prompt_lower = prompt.lower()
        china_score = sum(1 for s in _GEO_CHINA_SIGNALS if s.lower() in prompt_lower)
        global_score = sum(1 for s in _GEO_GLOBAL_SIGNALS if s.lower() in prompt_lower)

        if china_score > global_score:
            return "china"
        if global_score > china_score:
            return "global"

        # 默认：检测中文字符比例
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", prompt))
        total_chars = max(len(prompt), 1)
        if chinese_chars / total_chars > 0.3:
            return "china"

        return "any"

    def _detect_intent(self, prompt: str) -> tuple[str, float]:
        """检测用户意图。"""
        prompt_lower = prompt.lower()
        scores: dict[str, float] = {}

        for intent, keywords in _INTENT_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw.lower() in prompt_lower)
            if matches > 0:
                scores[intent] = min(0.4 + matches * 0.15, 1.0)

        if not scores:
            return "create", 0.3  # 默认意图

        best_intent = max(scores, key=lambda k: scores[k])
        return best_intent, scores[best_intent]

    def _estimate_urgency(self, prompt: str) -> float:
        """估算紧急程度。"""
        prompt_lower = prompt.lower()
        for signal in _URGENCY_HIGH:
            if signal.lower() in prompt_lower:
                return 0.9
        for signal in _URGENCY_LOW:
            if signal.lower() in prompt_lower:
                return 0.2
        return 0.5

    def _estimate_complexity(self, prompt: str) -> float:
        """估算任务复杂度。"""
        # 基于提示长度和关键词
        length_factor = min(len(prompt) / 200.0, 0.4)

        complexity_signals = [
            "架构", "系统", "多个", "集成", "全栈", "端到端",
            "architecture", "system", "integration", "full-stack", "end-to-end",
            "微服务", "分布式", "multi-agent",
        ]
        prompt_lower = prompt.lower()
        signal_factor = sum(0.1 for s in complexity_signals if s.lower() in prompt_lower)

        return min(length_factor + signal_factor + 0.3, 1.0)
