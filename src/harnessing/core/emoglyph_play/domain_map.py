"""
DomainMap — 领域知识地图

把技能按领域分组，不再只按关键词。
每个领域包含：技能列表、上下文信号词、地理环境、是否自动推荐。

这是 EmoGlyph Play 智能路由的基础：
  旧方式：关键词匹配 → "alipay" 才触发 alipay 技能
  新方式：领域匹配 → "在中国收钱" → payment_china 领域 → alipay + douyinpay
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DomainEntry:
    """一个领域的定义。"""

    skills: list[str] = field(default_factory=list)
    context_signals: list[str] = field(default_factory=list)
    geo: str = "any"  # "china" | "global" | "any"
    auto_recommend: bool = True
    description: str = ""


# 领域知识地图 — 10 个核心领域
DOMAIN_MAP: dict[str, DomainEntry] = {
    "payment_china": DomainEntry(
        skills=["alipay-payment-integration", "douyinpay-payment-integration", "dify-alipay"],
        context_signals=["收钱", "支付", "付款", "收款", "中国支付", "扫码", "支付宝", "抖音支付", "当面付", "代扣"],
        geo="china",
        auto_recommend=True,
        description="中国支付场景：支付宝、抖音支付等",
    ),
    "payment_global": DomainEntry(
        skills=[],
        context_signals=["payment", "checkout", "stripe", "paypal", "credit card", "subscription", "billing"],
        geo="global",
        auto_recommend=True,
        description="全球支付场景：Stripe、PayPal 等",
    ),
    "data_analysis": DomainEntry(
        skills=["data-analysis", "chart-visualization", "redis-development", "feishu-bitable", "pypi-streamlit", "pypi-pandas", "vsc-python", "dify-paddleocr"],
        context_signals=["数据", "分析", "报表", "缓存", "慢查询", "可视化", "excel", "csv", "统计", "pivot", "数据库优化"],
        geo="any",
        auto_recommend=True,
        description="数据分析与可视化：Excel、图表、缓存优化",
    ),
    "design_ui": DomainEntry(
        skills=["figma", "frontend-design", "shadcn", "web-design-guidelines", "frontend-skill"],
        context_signals=["设计", "界面", "UI", "美化", "样式", "组件", "landing page", "dashboard", "web ui"],
        geo="any",
        auto_recommend=True,
        description="UI 设计与前端开发：Figma、shadcn、Web UI",
    ),
    "content_creation": DomainEntry(
        skills=["byted-seedream-image-generate", "byted-seedance-video-generate", "canvas-design", "algorithmic-art"],
        context_signals=["生成图片", "生成视频", "创作", "海报", "艺术", "图片生成", "视频生成", "text to image", "text to video"],
        geo="any",
        auto_recommend=True,
        description="内容创作：图片生成、视频生成、海报设计",
    ),
    "social_media_china": DomainEntry(
        skills=["douyin-interact-creation", "hook-analyzer", "report-generator", "dify-bilibili-search"],
        context_signals=["抖音", "短视频", "互动", "钩子", "视频分析", "小红书", "微博", "B站", "社交内容"],
        geo="china",
        auto_recommend=True,
        description="中国社交媒体：抖音互动、视频分析、报告生成",
    ),
    "research": DomainEntry(
        skills=["defuddle", "consulting-analysis", "chart-visualization"],
        context_signals=["研究", "调研", "市场", "竞品", "报告", "url", "网页", "文章", "行业分析", "咨询"],
        geo="any",
        auto_recommend=True,
        description="深度研究：URL 提取、市场分析、咨询报告",
    ),
    "devops": DomainEntry(
        skills=["gh-cli", "git-commit", "mcp-builder"],
        context_signals=["部署", "发布", "版本", "GitHub", "CI/CD", "commit", "pull request", "release", "MCP"],
        geo="any",
        auto_recommend=True,
        description="DevOps：GitHub、Git、MCP 协议",
    ),
    "knowledge_mgmt": DomainEntry(
        skills=["obsidian-markdown", "obsidian-cli", "obsidian-bases", "notion-cli", "notion-knowledge-capture",
                "notion-meeting-intelligence", "notion-research-documentation", "notion-spec-to-implementation"],
        context_signals=["笔记", "知识库", "文档管理", "Notion", "Obsidian", "wiki", "知识捕获"],
        geo="any",
        auto_recommend=False,  # 需要用户明确使用这些工具
        description="知识管理：Obsidian、Notion",
    ),
    "testing": DomainEntry(
        skills=["webapp-testing", "dogfood", "screenshot", "pypi-pytest"],
        context_signals=["测试", "QA", "Bug", "质量", "playwright", "测试网站", "探索性测试"],
        geo="any",
        auto_recommend=True,
        description="测试：Web 测试、QA、截图",
    ),
    "documentation": DomainEntry(
        skills=["doc-coauthoring", "slides"],
        context_signals=["文档", "文档协作", "简报", "PPT", "presentation", "提案", "技术规范"],
        geo="any",
        auto_recommend=True,
        description="文档：协作写作、简报生成",
    ),
    "browser_automation": DomainEntry(
        skills=["agent-browser", "screenshot", "electron"],
        context_signals=["浏览器", "自动化", "截图", "桌面应用", "网页操作", "fill form", "navigate"],
        geo="any",
        auto_recommend=True,
        description="浏览器自动化：网页操作、截图、桌面应用",
    ),
    "ci_cd": DomainEntry(
        skills=["gha-checkout", "gha-cache", "gha-setup-node", "gha-setup-python", "gha-docker-build-push"],
        context_signals=["CI/CD", "GitHub Actions", "workflow", "pipeline", "构建", "部署流水线", "自动化构建"],
        geo="global",
        auto_recommend=True,
        description="CI/CD 自动化：GitHub Actions 工作流",
    ),
    "thinking_frameworks": DomainEntry(
        skills=["triz-contradiction-solver", "triz-inventive-principles", "triz-ideal-final-result",
                "design-thinking-empathy-mapper", "design-thinking-ideation-engine", "design-thinking-prototype-test",
                "lean-startup-mvp-designer", "lean-startup-validation-loop",
                "first-principles-decomposer", "first-principles-rebuilder",
                "systems-thinking-leverage-finder", "systems-thinking-causal-loop-mapper",
                "six-hats-decision-review", "six-hats-facilitator",
                "scamper-idea-generator", "scamper-feature-remixer"],
        context_signals=["思维", "框架", "TRIZ", "设计思维", "精益创业", "第一性原理", "系统思维",
                        "六顶思考帽", "SCAMPER", "创新", "矛盾", "创意", "thinking", "framework",
                        "brainstorm", "problem solving", "decision"],
        geo="any",
        auto_recommend=True,
        description="思维框架：TRIZ、设计思维、精益创业、第一性原理、系统思维、六帽、SCAMPER",
    ),
    "china_ai_platforms": DomainEntry(
        skills=["feishu-aily", "feishu-mcp", "qianfan-agent-builder", "bailian-mcp-hub", "qianfan-rag",
                "coze-bing-search", "coze-doubao-image", "coze-code-runner", "coze-tianyancha",
                "dify-deepseek", "dify-tongyi", "dify-alipay", "dify-tavily", "dify-firecrawl",
                "dify-bilibili-search", "dify-paddleocr"],
        context_signals=["千帆", "百炼", "扣子", "Coze", "Dify", "飞书AI", "豆包", "通义千问",
                        "AI平台", "智能体", "Agent", "MCP广场"],
        geo="china",
        auto_recommend=True,
        description="中国 AI 平台：千帆、百炼、Coze、Dify",
    ),
    "miniprogram_dev": DomainEntry(
        skills=["wechat-devtools", "taro-framework", "uni-app-framework", "wechat-cloudbase",
                "dingtalk-yida", "dingtalk-ai"],
        context_signals=["小程序", "miniprogram", "Taro", "uni-app", "微信开发", "钉钉开发",
                        "跨端开发", "低代码"],
        geo="china",
        auto_recommend=True,
        description="小程序开发：微信、钉钉、跨端框架",
    ),
    "ai_models": DomainEntry(
        skills=["hf-stable-diffusion", "hf-llama", "hf-whisper", "hf-bert", "hf-deepseek",
                "vsc-copilot", "pypi-langchain"],
        context_signals=["AI模型", "大模型", "LLM", "Stable Diffusion", "LLaMA", "Whisper",
                        "DeepSeek", "LangChain", "Copilot", "图像生成", "语音识别"],
        geo="any",
        auto_recommend=True,
        description="AI 模型：LLM、图像生成、语音识别、Agent 框架",
    ),
}


class DomainMap:
    """领域知识地图 — 技能按领域分组，支持情境匹配。"""

    def __init__(self, domain_map: dict[str, DomainEntry] | None = None) -> None:
        self._map = domain_map or DOMAIN_MAP

    def find_domains(
        self, prompt: str, context: dict[str, Any] | None = None
    ) -> list[tuple[str, float]]:
        """根据 prompt 和上下文，返回匹配的领域列表及置信度。

        Returns
        -------
        list[tuple[str, float]]
            [(domain_name, confidence), ...] 按置信度降序排列。
        """
        if context is None:
            context = {}

        prompt_lower = prompt.lower()
        results: list[tuple[str, float]] = []

        for domain_name, entry in self._map.items():
            score = 0.0
            matched_signals = 0

            # 1. 上下文信号匹配
            for signal in entry.context_signals:
                if signal.lower() in prompt_lower:
                    matched_signals += 1

            if matched_signals > 0:
                # 基础分：第一个信号 0.4，每个额外信号 +0.15
                score = min(0.4 + (matched_signals - 1) * 0.15, 0.95)

            # 2. 地理环境加分
            context_geo = context.get("geo", "")
            if context_geo and entry.geo in (context_geo, "any"):
                score += 0.1
            elif context_geo and entry.geo != "any" and entry.geo != context_geo:
                score -= 0.2  # 地理不匹配则降低

            # 3. auto_recommend 加分
            if entry.auto_recommend:
                score += 0.05

            if score > 0.3:
                results.append((domain_name, round(min(score, 1.0), 4)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def get_skills_for_domain(self, domain_name: str) -> list[str]:
        """返回指定领域的所有技能。"""
        entry = self._map.get(domain_name)
        if entry is None:
            return []
        return list(entry.skills)

    def get_context_signals(self, domain_name: str) -> list[str]:
        """返回指定领域的上下文信号词。"""
        entry = self._map.get(domain_name)
        if entry is None:
            return []
        return list(entry.context_signals)

    def get_domain_for_skill(self, skill_name: str) -> str | None:
        """返回技能所属的领域。"""
        for domain_name, entry in self._map.items():
            if skill_name in entry.skills:
                return domain_name
        return None

    def add_skill_to_domain(self, skill_name: str, domain_name: str) -> None:
        """将技能添加到指定领域。"""
        if domain_name not in self._map:
            self._map[domain_name] = DomainEntry()
        if skill_name not in self._map[domain_name].skills:
            self._map[domain_name].skills.append(skill_name)

    def add_domain(self, domain_name: str, entry: DomainEntry) -> None:
        """添加新领域。"""
        self._map[domain_name] = entry

    def all_domains(self) -> list[str]:
        """返回所有领域名称。"""
        return list(self._map.keys())

    def all_skills(self) -> list[str]:
        """返回所有领域中的技能（去重）。"""
        seen: set[str] = set()
        result: list[str] = []
        for entry in self._map.values():
            for skill in entry.skills:
                if skill not in seen:
                    seen.add(skill)
                    result.append(skill)
        return result

    def domain_info(self, domain_name: str) -> DomainEntry | None:
        """返回领域详情。"""
        return self._map.get(domain_name)
