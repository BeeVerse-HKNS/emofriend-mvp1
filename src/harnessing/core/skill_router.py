from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .emoglyph_play.intelligent_router import (
    IntelligentSkillRouter as _IntelligentSkillRouter,
    IntelligentRouteResult as _IntelligentRouteResult,
    FeedbackTracker as _FeedbackTracker,
)

SKILL_REGISTRY: list[dict[str, Any]] = [
    {
        "name": "Harness Engineering Copilot",
        "triggers": [
            "harness", "規則", "痛點", "自我約束", "記憶恢復", "方案分析",
            "session", "feature", "bugfix", "code change",
            "email", "linkedin", "audit", "voice order", "business plan",
            "kids", "sub-project", "子項目",
        ],
        "trigger_phrases": [
            "Use Skill: Harness", "ride on", "pain point",
            "vibe coding", "implement a feature", "fix a bug",
            "email agent", "linkedin builder", "audit engine",
            "voice order", "business plan", "python for kids",
        ],
        "relevance": "high",
        "auto_invoke": True,
        "reason": "項目核心 Skill — 所有 session 自動載入",
    },
    {
        "name": "agent-browser",
        "triggers": ["browser", "navigate", "screenshot", "scrape", "fill form", "click button", "web app", "automate"],
        "trigger_phrases": [
            "open a website", "fill out a form", "click a button",
            "take a screenshot", "scrape data", "test this web app",
            "login to", "automate browser",
        ],
        "relevance": "high",
        "auto_invoke": False,
        "reason": "YouTube 掃描、社交媒體自動化、Web 測試",
    },
    {
        "name": "algorithmic-art",
        "triggers": ["algorithmic art", "generative art", "p5.js", "flow field", "particle system"],
        "trigger_phrases": [
            "create art using code", "generative art",
            "algorithmic art", "flow field", "particle system",
        ],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前項目不需要演算法藝術",
    },
    {
        "name": "alipay-payment-integration",
        "triggers": ["支付宝", "支付", "付款码", "扫码支付", "预授权", "代扣", "H5支付"],
        "trigger_phrases": ["接入支付宝", "集成支付宝支付", "支付宝收款", "支付宝下单"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前項目不需要支付功能",
    },
    {
        "name": "brainstorming",
        "triggers": ["create", "build", "add", "modify", "feature", "component", "functionality"],
        "trigger_phrases": ["create a feature", "build a component", "add functionality", "modify behavior"],
        "relevance": "high",
        "auto_invoke": True,
        "reason": "MUST use before any creative work — 防止痛點 10（忽略意圖）",
    },
    {
        "name": "brand-guidelines",
        "triggers": ["brand", "anthropic", "look-and-feel", "company design", "visual formatting"],
        "trigger_phrases": ["apply brand colors", "brand style", "company design standards"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "Anthropic 品牌規範，非項目所需",
    },
    {
        "name": "byted-seedance-video-generate",
        "triggers": ["video", "seedance", "text to video", "image to video"],
        "trigger_phrases": ["create videos from text", "generate video", "image to video", "video from text"],
        "relevance": "high",
        "auto_invoke": False,
        "reason": "Video Engine L3 層 — 影片生成核心",
    },
    {
        "name": "byted-seedream-image-generate",
        "triggers": ["image generate", "create image", "text to image", "artwork", "visual content"],
        "trigger_phrases": ["create images from text", "generate artwork", "visual content"],
        "relevance": "high",
        "auto_invoke": False,
        "reason": "Comic Generator — 漫畫/縮略圖生成",
    },
    {
        "name": "canvas-design",
        "triggers": ["poster", "art", "design", "static piece", "visual", "png", "pdf"],
        "trigger_phrases": ["create a poster", "piece of art", "design a poster"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "社交媒體圖片/海報設計",
    },
    {
        "name": "chart-visualization",
        "triggers": ["chart", "graph", "visualize data", "plot", "diagram"],
        "trigger_phrases": ["visualize data", "create a chart", "show this data"],
        "relevance": "high",
        "auto_invoke": False,
        "reason": "Upload Timing Analyzer 數據可視化、學習曲線報告",
    },
    {
        "name": "consulting-analysis",
        "triggers": [
            "market analysis", "consumer insights", "financial analysis",
            "industry research", "competitive intelligence",
            "due diligence", "consulting",
        ],
        "trigger_phrases": ["market analysis", "competitive analysis", "industry research", "consulting report"],
        "relevance": "high",
        "auto_invoke": True,
        "reason": "深度研究時自動觸發 — 解決手動遺漏（CM-6 高頻觸發）",
    },
    {
        "name": "data-analysis",
        "triggers": ["excel", "xlsx", "xls", "csv", "pivot table", "sql query", "data analysis", "statistics"],
        "trigger_phrases": ["analyze this data", "excel file", "csv data", "pivot table"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "需要明確數據文件時觸發，避免誤觸發",
    },
    {
        "name": "defuddle",
        "triggers": ["url", "web page", "read online", "documentation", "article", "blog post"],
        "trigger_phrases": ["read this url", "fetch this page", "analyze this web page"],
        "relevance": "high",
        "auto_invoke": True,
        "reason": "WebFetch 替代品 — 任何 URL 自動觸發提取乾淨 Markdown",
    },
    {
        "name": "doc-coauthoring",
        "triggers": ["documentation", "proposal", "technical spec", "decision doc", "write docs"],
        "trigger_phrases": ["write documentation", "create a proposal", "draft a spec", "co-author"],
        "relevance": "high",
        "auto_invoke": True,
        "reason": "撰寫 SKILL.md / spec / 決策文檔時自動觸發",
    },
    {
        "name": "dogfood",
        "triggers": ["dogfood", "qa", "exploratory test", "find issues", "bug hunt", "test this app"],
        "trigger_phrases": ["dogfood this app", "find issues", "bug hunt", "test this app"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "Web app QA 測試（Phase 3 MVP 上線後）",
    },
    {
        "name": "douyin-interact-creation",
        "triggers": ["抖音", "interact_creation", "h5 experience", "offline h5"],
        "trigger_phrases": ["抖音互動", "interact_creation", "h5 experience"],
        "relevance": "high",
        "auto_invoke": False,
        "reason": "抖音互動內容創作 — 中國社交媒體核心",
    },
    {
        "name": "electron",
        "triggers": ["electron", "desktop app", "vs code", "slack", "discord", "figma", "native app"],
        "trigger_phrases": ["automate slack", "control vs code", "electron app", "desktop app"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前不需要桌面應用自動化",
    },
    {
        "name": "executing-plans",
        "triggers": ["implementation plan", "execute plan", "review checkpoint"],
        "trigger_phrases": ["execute this plan", "follow this plan", "implementation plan"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "執行 spec 中的 tasks.md 計劃",
    },
    {
        "name": "figma",
        "triggers": ["figma", "design-to-code", "figma url", "figma node"],
        "trigger_phrases": ["figma design", "figma url", "design to code"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前沒有 Figma 設計稿",
    },
    {
        "name": "frontend-design",
        "triggers": ["web component", "landing page", "dashboard", "react component", "html/css", "web ui", "beautify"],
        "trigger_phrases": ["build a landing page", "create a dashboard", "web component", "beautify this ui"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "未來 OPC Dashboard UI",
    },
    {
        "name": "frontend-skill",
        "triggers": ["landing page", "website", "app prototype", "demo", "game ui"],
        "trigger_phrases": ["build a website", "landing page", "app prototype"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "未來 OPC 網站/原型",
    },
    {
        "name": "gh-cli",
        "triggers": ["github", "pull request", "issue", "actions", "release", "repository"],
        "trigger_phrases": ["github cli", "create a pr", "github issue", "gh command"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "GitHub 版本管理",
    },
    {
        "name": "git-commit",
        "triggers": ["commit", "git commit", "/commit"],
        "trigger_phrases": ["commit changes", "create a git commit", "/commit"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "Git 提交代碼",
    },
    {
        "name": "hook-analyzer",
        "triggers": ["钩子分析", "hook analysis", "前三秒", "first 3 seconds"],
        "trigger_phrases": ["analyze hook", "first 3 seconds", "钩子分析"],
        "relevance": "high",
        "auto_invoke": False,
        "reason": "YouTube/抖音影片前三秒 Hook 分析",
    },
    {
        "name": "internal-comms",
        "triggers": ["status report", "leadership update", "newsletter", "incident report", "internal communication"],
        "trigger_phrases": ["status report", "leadership update", "internal comms"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "內部溝通 — BeeVerse 內部可能用到",
    },
    {
        "name": "json-canvas",
        "triggers": ["canvas", "mind map", "flowchart", "obsidian canvas"],
        "trigger_phrases": ["create a canvas", "mind map", "json canvas"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "Obsidian Canvas — 目前不用",
    },
    {
        "name": "mcp-builder",
        "triggers": ["mcp server", "mcp protocol", "fastmcp", "model context protocol"],
        "trigger_phrases": ["create mcp server", "build mcp", "mcp integration"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "MCP 協議是已研究主題，未來可能需要",
    },
    {
        "name": "notion-cli",
        "triggers": ["notion api", "notion database", "notion page", "ntn command"],
        "trigger_phrases": ["call the notion api", "notion database", "upload to notion"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前不用 Notion",
    },
    {
        "name": "notion-knowledge-capture",
        "triggers": ["capture knowledge", "notion wiki", "notion documentation"],
        "trigger_phrases": ["save to notion", "capture insights", "notion wiki"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前不用 Notion",
    },
    {
        "name": "notion-meeting-intelligence",
        "triggers": ["meeting", "notion meeting", "pre-read", "agenda"],
        "trigger_phrases": ["prepare meeting", "meeting materials", "notion meeting"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前不用 Notion",
    },
    {
        "name": "notion-research-documentation",
        "triggers": ["notion research", "search notion", "research documentation"],
        "trigger_phrases": ["search notion workspace", "research in notion"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前不用 Notion",
    },
    {
        "name": "notion-spec-to-implementation",
        "triggers": ["spec to task", "notion tasks", "implementation plan notion"],
        "trigger_phrases": ["turn spec into tasks", "notion implementation"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前不用 Notion",
    },
    {
        "name": "obsidian-bases",
        "triggers": ["obsidian base", "database view", "obsidian table"],
        "trigger_phrases": ["obsidian base file", "database view"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前不用 Obsidian",
    },
    {
        "name": "obsidian-cli",
        "triggers": ["obsidian vault", "obsidian note", "obsidian plugin"],
        "trigger_phrases": ["obsidian vault", "obsidian note", "obsidian plugin"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前不用 Obsidian",
    },
    {
        "name": "obsidian-markdown",
        "triggers": ["obsidian markdown", "wikilink", "callout", "frontmatter", "embed"],
        "trigger_phrases": ["obsidian note", "wikilink", "obsidian markdown"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前不用 Obsidian",
    },
    {
        "name": "redis-development",
        "triggers": ["redis", "vector search", "redisvl", "semantic cache", "langcache"],
        "trigger_phrases": ["redis optimization", "redis query", "vector search redis"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "ChromaDB 可能未來替換為 Redis — 已有研究",
    },
    {
        "name": "report-generator",
        "triggers": ["视频分析报告", "video analysis report", "report generation"],
        "trigger_phrases": ["generate report", "video analysis report", "分析报告"],
        "relevance": "high",
        "auto_invoke": False,
        "reason": "影片分析報告生成 — YouTube/B站內容分析",
    },
    {
        "name": "screenshot",
        "triggers": ["screenshot", "capture screen", "desktop screenshot"],
        "trigger_phrases": ["take a screenshot", "capture screen", "desktop screenshot"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "QA 截圖、Web app 測試",
    },
    {
        "name": "security-best-practices",
        "triggers": ["security review", "security best practice", "secure coding", "security audit"],
        "trigger_phrases": ["security review", "security best practices", "secure coding"],
        "relevance": "high",
        "auto_invoke": False,
        "reason": "對應痛點 11（安全盲區）— Python/JS 安全審計",
    },
    {
        "name": "shadcn",
        "triggers": ["shadcn", "components.json", "shadcn/ui", "shadcn init"],
        "trigger_phrases": ["add shadcn component", "shadcn init", "shadcn project"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前不用 shadcn/ui",
    },
    {
        "name": "slides",
        "triggers": ["powerpoint", "pptx", "slide deck", "presentation", "slides"],
        "trigger_phrases": ["create presentation", "powerpoint", "slide deck", "pptx"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "OPC 商業簡報、投資人 Deck",
    },
    {
        "name": "test-driven-development",
        "triggers": ["implement feature", "bugfix", "before writing implementation"],
        "trigger_phrases": ["implement a feature", "fix a bug", "tdd"],
        "relevance": "high",
        "auto_invoke": False,
        "reason": "Python 代碼開發 — 先寫測試再實作",
    },
    {
        "name": "theme-factory",
        "triggers": ["theme", "style", "colors", "fonts", "visual theme"],
        "trigger_phrases": ["apply a theme", "style this", "change theme"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前不需要主題系統",
    },
    {
        "name": "vercel-composition-patterns",
        "triggers": ["react composition", "compound component", "render prop", "context provider"],
        "trigger_phrases": ["react composition", "component architecture"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "Python 項目，不用 React",
    },
    {
        "name": "vercel-react-best-practices",
        "triggers": ["react performance", "next.js", "bundle optimization"],
        "trigger_phrases": ["react performance", "next.js optimization"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "Python 項目，不用 React",
    },
    {
        "name": "vercel-react-native-skills",
        "triggers": ["react native", "expo", "mobile app", "native module"],
        "trigger_phrases": ["react native", "expo app", "mobile performance"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "Python 項目，不用 React Native",
    },
    {
        "name": "web-artifacts-builder",
        "triggers": ["html artifact", "react component", "shadcn artifact", "multi-component"],
        "trigger_phrases": ["create html artifact", "multi-component artifact"],
        "relevance": "low",
        "auto_invoke": False,
        "reason": "目前不需要 HTML artifacts",
    },
    {
        "name": "web-design-guidelines",
        "triggers": ["review ui", "check accessibility", "audit design", "review ux", "web interface guidelines"],
        "trigger_phrases": ["review my ui", "check accessibility", "audit design"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "未來 Web UI 審計",
    },
    {
        "name": "web-dev",
        "triggers": ["build website", "create web app", "web-based game", "from scratch"],
        "trigger_phrases": ["build a website", "create a web app", "from scratch"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "未來 OPC Web 平台（僅限新建項目）",
    },
    {
        "name": "webapp-testing",
        "triggers": ["test web app", "playwright", "browser test", "local web app"],
        "trigger_phrases": ["test this web app", "playwright test", "local web app"],
        "relevance": "medium",
        "auto_invoke": False,
        "reason": "Phase 3 MVP 上線後的 Web 測試",
    },
    {
        "name": "writing-plans",
        "triggers": ["spec", "requirements", "multi-step task", "plan before action"],
        "trigger_phrases": ["write a plan", "spec or requirements", "multi-step task"],
        "relevance": "high",
        "auto_invoke": False,
        "reason": "對應痛點 3（過快執行）— 先規劃再行動",
    },
]


# =============================================================================
# INTEGRATION TIERS (Phase 1: Enhance Harness with TRAE Skills)
# =============================================================================
# Three-tier skill integration strategy:
#   ABSORB  : Best practices added as native Harness rules (Rule 78-85)
#   BRIDGE  : Auto-invoke TRAE skills when triggers match (CM-7 to CM-16)
#   RECOMMEND: Skills invoked manually when needed

INTEGRATION_TIERS: dict[str, list[str]] = {
    "absorb": [
        "test-driven-development",
        "security-best-practices",
        "brainstorming",
        "writing-plans",
        "spec-to-implementation",
        "executing-plans",
        "circularmind",
        "doc-coauthoring",
    ],
    "bridge": [
        # Phase 1 (CM-7 to CM-16)
        "defuddle",
        "chart-visualization",
        "agent-browser",
        "screenshot",
        "gh-cli",
        "git-commit",
        "data-analysis",
        "webapp-testing",
        "research-documentation",
        "slides",
        # Phase 2 (CM-17 to CM-53)
        "frontend-skill",
        "meeting-intelligence",
        "internal-comms",
        "algorithmic-art",
        "canvas-design",
        "byted-seedream-image-generate",
        "byted-seedance-video-generate",
        "theme-factory",
        "dogfood",
        "consulting-analysis",
        "alipay-payment-integration",
        "douyinpay-payment-integration",
        "obsidian-markdown",
        "obsidian-cli",
        "obsidian-bases",
        "mcp-builder",
        "notion-cli",
        "notion-knowledge-capture",
        "notion-meeting-intelligence",
        "notion-research-documentation",
        "notion-spec-to-implementation",
        "redis-development",
        "json-canvas",
        "hook-analyzer",
        "figma",
        "web-design-guidelines",
        "web-artifacts-builder",
        "shadcn",
        "electron",
        "frontend-design",
        "douyin-interact-creation",
        "vercel-composition-patterns",
        "vercel-react-best-practices",
        "vercel-react-native-skills",
        "report-generator",
        "brand-guidelines",
    ],
    "recommend": [],  # All skills now auto-trigger
}

# CM Rules Integration (CM-7 to CM-16)
# Format: "cm_id": (skill_name, trigger_keywords, confidence_threshold)
CM_RULES_INTEGRATION: dict[str, tuple[str, list[str], float]] = {
    "CM-7": ("defuddle", ["url", "web page", "read online", "fetch this"], 0.7),
    "CM-8": ("chart-visualization", ["chart", "visualize", "graph", "plot"], 0.6),
    "CM-9": ("agent-browser", ["browser", "navigate", "fill form", "login"], 0.6),
    "CM-10": ("screenshot", ["screenshot", "capture screen", "screen shot"], 0.5),
    "CM-11": ("gh-cli", ["github", "pull request", "create pr", "github cli"], 0.6),
    "CM-12": ("git-commit", ["commit", "git commit", "/commit"], 0.7),
    "CM-13": ("data-analysis", ["excel", "csv", "data analysis", "statistics"], 0.6),
    "CM-14": ("webapp-testing", ["test", "qa", "playwright", "webapp test"], 0.5),
    "CM-15": ("research-documentation", ["research", "report", "document"], 0.5),
    "CM-16": ("slides", ["presentation", "powerpoint", "slides", "deck"], 0.6),
    "CM-17": ("frontend-skill", ["landing page", "website", "web app", "ui design"], 0.6),
    "CM-18": ("meeting-intelligence", ["meeting", "agenda", "pre-read", "prepare meeting"], 0.6),
    "CM-19": ("internal-comms", ["status report", "newsletter", "announcement", "incident report"], 0.5),
    "CM-20": ("algorithmic-art", ["generative art", "p5.js", "algorithmic art", "flow field"], 0.7),
    "CM-21": ("canvas-design", ["poster", "visual design", "art design", "create design"], 0.6),
    "CM-22": ("byted-seedream-image-generate", ["generate image", "create image", "text to image", "draw image", "image generation"], 0.5),
    "CM-23": ("byted-seedance-video-generate", ["generate video", "create video", "text to video", "make video"], 0.6),
    "CM-24": ("theme-factory", ["theme", "color scheme", "styling", "brand colors"], 0.5),
    "CM-25": ("dogfood", ["dogfood", "qa test", "find bugs", "test this app", "explore app"], 0.6),
    "CM-26": ("consulting-analysis", ["market analysis", "consulting report", "competitive analysis", "industry research"], 0.6),
    "CM-27": ("alipay-payment-integration", ["alipay", "支付宝", "扫码支付", "当面付"], 0.5),
    "CM-28": ("douyinpay-payment-integration", ["douyin pay", "抖音支付", "douyinpay"], 0.5),
    "CM-29": ("obsidian-markdown", ["obsidian", "wikilink", "callout", "obsidian note"], 0.6),
    "CM-30": ("obsidian-cli", ["obsidian vault", "obsidian search", "obsidian plugin"], 0.6),
    "CM-31": ("obsidian-bases", ["obsidian base", "obsidian database", "obsidian table"], 0.6),
    "CM-32": ("mcp-builder", ["mcp server", "model context protocol", "mcp integration"], 0.7),
    "CM-33": ("notion-cli", ["notion api", "notion page", "notion database", "ntn command"], 0.6),
    "CM-34": ("notion-knowledge-capture", ["capture knowledge", "save to notion", "notion wiki"], 0.6),
    "CM-35": ("notion-meeting-intelligence", ["notion meeting", "meeting prep notion", "notion agenda"], 0.6),
    "CM-36": ("notion-research-documentation", ["notion research", "notion report", "research notion"], 0.6),
    "CM-37": ("notion-spec-to-implementation", ["notion spec", "notion task", "spec to notion"], 0.6),
    "CM-38": ("redis-development", ["redis", "cache optimization", "vector search", "redisvl"], 0.7),
    "CM-39": ("json-canvas", ["canvas file", "mind map", "flowchart", "obsidian canvas"], 0.6),
    "CM-40": ("hook-analyzer", ["video hook", "hook analysis", "first 3 seconds", "video analysis"], 0.7),
    "CM-41": ("figma", ["figma", "design token", "figma node", "figma url"], 0.5),
    "CM-43": ("web-design-guidelines", ["ui review", "ux audit", "accessibility check", "web guidelines"], 0.5),
    "CM-44": ("web-artifacts-builder", ["html artifact", "react component", "web artifact", "interactive demo"], 0.6),
    "CM-45": ("shadcn", ["shadcn", "shadcn/ui", "component library", "ui component"], 0.7),
    "CM-46": ("electron", ["electron app", "desktop app", "electron automation"], 0.7),
    "CM-47": ("frontend-design", ["frontend design", "web design", "ui implementation"], 0.5),
    "CM-48": ("douyin-interact-creation", ["抖音互动", "douyin h5", "interact creation", "互动创作"], 0.7),
    "CM-49": ("vercel-composition-patterns", ["react composition", "compound component", "render props"], 0.6),
    "CM-50": ("vercel-react-best-practices", ["react performance", "next.js optimization", "react best practice"], 0.6),
    "CM-51": ("vercel-react-native-skills", ["react native", "expo", "mobile app", "native module"], 0.7),
    "CM-52": ("report-generator", ["video report", "analysis report", "generate report"], 0.6),
    "CM-53": ("brand-guidelines", ["brand", "brand colors", "brand typography", "brand style"], 0.6),
}


@dataclass
class SkillMatch:
    skill_name: str
    confidence: float
    matched_triggers: list[str] = field(default_factory=list)
    matched_phrases: list[str] = field(default_factory=list)
    relevance: str = "low"
    auto_invoke: bool = False
    reason: str = ""


class SkillRouter:
    def __init__(self, registry: list[dict[str, Any]] | None = None) -> None:
        self.registry = registry or SKILL_REGISTRY
        self._intelligent_router: _IntelligentSkillRouter | None = None
        self._feedback_tracker: _FeedbackTracker = _FeedbackTracker()

    def route(self, prompt: str) -> list[SkillMatch]:
        prompt_lower = prompt.lower()
        matches: list[SkillMatch] = []

        for skill in self.registry:
            trigger_hits = [
                t for t in skill["triggers"] if t.lower() in prompt_lower
            ]
            phrase_hits = [
                p
                for p in skill.get("trigger_phrases", [])
                if p.lower() in prompt_lower
            ]

            if not trigger_hits and not phrase_hits:
                continue

            trigger_score = len(trigger_hits) * 0.3
            phrase_score = len(phrase_hits) * 0.5
            relevance_bonus = {"high": 0.2, "medium": 0.1, "low": 0.0}.get(
                skill.get("relevance", "low"), 0.0
            )
            confidence = min(trigger_score + phrase_score + relevance_bonus, 1.0)

            matches.append(
                SkillMatch(
                    skill_name=skill["name"],
                    confidence=confidence,
                    matched_triggers=trigger_hits,
                    matched_phrases=phrase_hits,
                    relevance=skill.get("relevance", "low"),
                    auto_invoke=skill.get("auto_invoke", False),
                    reason=skill.get("reason", ""),
                )
            )

        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches

    def get_auto_invoke_skills(self, prompt: str) -> list[SkillMatch]:
        all_matches = self.route(prompt)
        return [m for m in all_matches if m.auto_invoke and m.confidence > 0.3]

    def get_recommended_skills(self, prompt: str, top_n: int = 5) -> list[SkillMatch]:
        all_matches = self.route(prompt)
        high_medium = [m for m in all_matches if m.relevance in ("high", "medium")]
        return high_medium[:top_n]

    def get_high_relevance_skills(self) -> list[dict[str, Any]]:
        return [s for s in self.registry if s.get("relevance") == "high"]

    def get_skill_by_name(self, name: str) -> dict[str, Any] | None:
        for s in self.registry:
            if s["name"].lower() == name.lower():
                return s
        return None

    def audit_skill_usage(
        self, prompt: str, skills_used: list[str]
    ) -> dict[str, Any]:
        recommended = self.route(prompt)
        recommended_names = {m.skill_name for m in recommended if m.confidence > 0.2}
        used_names = set(skills_used)

        missed = recommended_names - used_names
        unnecessary = used_names - {m.skill_name for m in recommended}

        return {
            "prompt_preview": prompt[:100],
            "skills_used": list(used_names),
            "skills_recommended": list(recommended_names),
            "skills_missed": list(missed),
            "skills_unnecessary": list(unnecessary),
            "coverage_score": (
                len(recommended_names & used_names) / len(recommended_names)
                if recommended_names
                else 1.0
            ),
        }

    def route_with_gap_awareness(self, task_description: str) -> dict[str, Any]:
        result = self.route(task_description)
        if not result:
            try:
                from .beeverse_skill_gap_analyzer import BeeVerseSkillGapAnalyzer

                analyzer = BeeVerseSkillGapAnalyzer()
                report = analyzer.analyze()
                missing = [
                    g["name"]
                    for g in report.critical_gaps + report.important_gaps
                    if isinstance(g, dict) and "name" in g
                ]
                return {
                    "matched_skills": [],
                    "gap_detected": True,
                    "missing_capabilities": missing[:5],
                    "suggestion": "Use BeeVerseSkillInstaller to create and install missing skills",
                }
            except Exception:
                return {
                    "matched_skills": [],
                    "gap_detected": False,
                    "missing_capabilities": [],
                    "suggestion": "",
                }
        return {
            "matched_skills": [
                {
                    "skill_name": m.skill_name,
                    "confidence": m.confidence,
                    "relevance": m.relevance,
                }
                for m in result
            ],
            "gap_detected": False,
            "missing_capabilities": [],
            "suggestion": "",
        }

    def get_skill_tier(self, skill_name: str) -> str | None:
        """Return the integration tier for a skill: 'absorb', 'bridge', or 'recommend'."""
        for tier, skills in INTEGRATION_TIERS.items():
            if skill_name in skills:
                return tier
        return None

    def should_auto_invoke(self, prompt: str) -> list[tuple[str, str, float]]:
        """Check if any BRIDGE skills should be auto-invoked based on prompt.

        Phase 2: 先用 EmoGlyph Play 智能路由，关键词匹配作为后备。

        Returns list of (cm_id, skill_name, confidence) for skills to auto-invoke.
        """
        # 1. 先尝试智能路由
        try:
            result = self.route_intelligent(prompt)
            if result.get("recommended_skills"):
                intelligent_results = []
                for skill_name, confidence, _reason in result["recommended_skills"]:
                    # 查找对应的 CM 编号，智能路由用 "CM-AI" 前缀
                    cm_id = "CM-AI"
                    for cid, (sname, _kw, _th) in CM_RULES_INTEGRATION.items():
                        if sname == skill_name:
                            cm_id = cid
                            break
                    intelligent_results.append((cm_id, skill_name, confidence))
                if intelligent_results:
                    return intelligent_results
        except Exception:
            pass

        # 2. 后备：关键词匹配（现有逻辑不变）
        results = []
        prompt_lower = prompt.lower()

        for cm_id, (skill_name, keywords, threshold) in CM_RULES_INTEGRATION.items():
            # Count keyword matches
            matches = sum(1 for kw in keywords if kw.lower() in prompt_lower)
            if matches > 0:
                # Base confidence from first match, bonus for additional matches
                confidence = min(0.5 + (matches - 1) * 0.2, 1.0)
                if confidence >= threshold:
                    results.append((cm_id, skill_name, confidence))

        # Sort by confidence descending
        results.sort(key=lambda x: x[2], reverse=True)
        return results

    def route_intelligent(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """用 EmoGlyph Play 智能路由替代关键词匹配。

        Phase 2: 情境分析 → 领域匹配 → 技能推荐 + 人类语言解释。

        Returns
        -------
        dict
            {
                "recommended_skills": [(skill_name, confidence, reason), ...],
                "situation": Situation,
                "explanation": str,  # Rule 86: 人类语言解释
                "fallback_used": bool,
            }
        """
        if self._intelligent_router is None:
            self._intelligent_router = _IntelligentSkillRouter()

        result: _IntelligentRouteResult = self._intelligent_router.route(prompt, context)

        return {
            "recommended_skills": [
                (rec.skill_name, rec.confidence, rec.reason)
                for rec in result.recommended_skills
            ],
            "situation": result.situation,
            "explanation": result.explanation,
            "fallback_used": result.fallback_used,
            "formula_score": result.formula_score,
            "player_type": result.player_type.value,
        }

    def record_feedback(self, skill_name: str, accepted: bool) -> None:
        """记录用户对推荐的反馈（用于学习）。"""
        self._feedback_tracker.record(skill_name, accepted)
        if self._intelligent_router is not None:
            self._intelligent_router.record_feedback(skill_name, accepted)

    def get_absorb_rules_for_task(self, task_description: str) -> list[str]:
        """Return list of ABSORB skills that should be applied for this task."""
        applied = []
        task_lower = task_description.lower()
        
        for skill in INTEGRATION_TIERS.get("absorb", []):
            # Check if skill keywords match task
            skill_entry = self.get_skill_by_name(skill)
            if skill_entry:
                triggers = skill_entry.get("triggers", [])
                if any(t.lower() in task_lower for t in triggers):
                    applied.append(skill)
        
        return applied

    # ------------------------------------------------------------------
    # HKI (Hierarchical Knowledge Indexer) delegation
    # ------------------------------------------------------------------
    #
    # Phase 5 of spec ``restructure-md-files-for-engine-efficiency``
    # integrates the HKI router so engine queries (e.g. "what is D-132?")
    # can be routed in O(log N) to the relevant MD file + L1 summary.
    # The integration is additive — existing methods above are untouched.

    def route_md_query(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Delegate an MD-related query to the HKI skill router.

        Returns a list of result dicts with at minimum the keys
        ``path``, ``l0``, ``l1``, ``purpose``, ``top_headings`` and
        ``score`` (see :class:`md_hki_skill_router.HKISkillRouter`).

        Returns an empty list if the HKI router is not importable or
        if the query yields no hits.
        """
        try:
            from .md_hki_skill_router import HKISkillRouter
        except Exception:
            return []
        router = HKISkillRouter()
        return router.route_query(query, top_k=top_k)

    def lookup_md_by_id(self, d_or_idea_id: str) -> dict[str, Any] | None:
        """Return the HKI entry for ``D-NNN`` / ``IDEA-NNN`` / ``KB-NNN``."""
        try:
            from .md_hki_skill_router import HKISkillRouter
        except Exception:
            return None
        return HKISkillRouter().lookup_by_id(d_or_idea_id)

    def lookup_md_by_path(self, path: str) -> dict[str, Any] | None:
        """Return the HKI entry for a given MD file path."""
        try:
            from .md_hki_skill_router import HKISkillRouter
        except Exception:
            return None
        return HKISkillRouter().lookup_by_path(path)
