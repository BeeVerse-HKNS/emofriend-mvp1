"""
SkillDiscovery — 1M+ 技能市场深度研究引擎

深度研究西方和中国开源技能市场，发现新技能并评估价值。

研究范围：
  - GitHub Actions (~50K)
  - VS Code Extensions (~50K)
  - npm CLI tools (~100K)
  - PyPI Python tools (~50K)
  - Hugging Face models/spaces (~500K)
  - Docker Hub (~100K)
  - 飞书/钉钉/微信开放平台 (~100K)
  - 百度千帆/阿里云百炼 (~10K)
  - Coze (扣子) 技能市场 (~50K)
  - Dify 插件市场 (~10K)

发现公式：
  Skill_Value = (Relevance × Quality) + (Popularity × 0.3) - (Complexity × 0.2)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .domain_map import DomainMap, DomainEntry


# ── 技能市场定义 ───────────────────────────────────────────────────

@dataclass
class SkillMarket:
    """一个技能市场的定义。"""

    name: str
    estimated_count: int
    region: str  # "western" | "china" | "global"
    api_available: bool
    priority: str  # "P1" | "P2" | "P3"
    description: str = ""


SKILL_MARKETS: dict[str, SkillMarket] = {
    "github_actions": SkillMarket(
        name="GitHub Actions",
        estimated_count=50000,
        region="global",
        api_available=True,
        priority="P1",
        description="CI/CD 自动化工作流",
    ),
    "vscode_extensions": SkillMarket(
        name="VS Code Extensions",
        estimated_count=50000,
        region="global",
        api_available=True,
        priority="P1",
        description="代码编辑器扩展",
    ),
    "npm_cli": SkillMarket(
        name="npm CLI Tools",
        estimated_count=100000,
        region="global",
        api_available=True,
        priority="P2",
        description="Node.js 命令行工具",
    ),
    "pypi": SkillMarket(
        name="PyPI Python Tools",
        estimated_count=50000,
        region="global",
        api_available=True,
        priority="P1",
        description="Python 包和工具",
    ),
    "huggingface": SkillMarket(
        name="Hugging Face",
        estimated_count=500000,
        region="global",
        api_available=True,
        priority="P2",
        description="AI 模型和 Spaces",
    ),
    "dockerhub": SkillMarket(
        name="Docker Hub",
        estimated_count=100000,
        region="global",
        api_available=True,
        priority="P3",
        description="容器镜像",
    ),
    "feishu": SkillMarket(
        name="飞书",
        estimated_count=12000,
        region="china",
        api_available=False,
        priority="P1",
        description="飞书开放平台插件和应用",
    ),
    "dingtalk": SkillMarket(
        name="钉钉",
        estimated_count=15000,
        region="china",
        api_available=False,
        priority="P1",
        description="钉钉开放平台插件和应用",
    ),
    "wechat": SkillMarket(
        name="微信小程序",
        estimated_count=50000,
        region="china",
        api_available=False,
        priority="P1",
        description="微信小程序开发工具和框架",
    ),
    "baidu_qianfan": SkillMarket(
        name="百度千帆",
        estimated_count=5000,
        region="china",
        api_available=False,
        priority="P1",
        description="百度千帆 AI 平台技能",
    ),
    "aliyun_bailian": SkillMarket(
        name="阿里云百炼",
        estimated_count=5000,
        region="china",
        api_available=False,
        priority="P1",
        description="阿里云百炼 AI 平台技能",
    ),
    "feishu_dingtalk_wechat": SkillMarket(
        name="飞书/钉钉/微信开放平台",
        estimated_count=100000,
        region="china",
        api_available=False,
        priority="P1",
        description="中国办公和社交平台插件",
    ),
    "baidu_qianfan_aliyun": SkillMarket(
        name="百度千帆/阿里云百炼",
        estimated_count=10000,
        region="china",
        api_available=False,
        priority="P1",
        description="中国 AI 平台技能",
    ),
    "coze": SkillMarket(
        name="Coze (扣子)",
        estimated_count=18000,
        region="china",
        api_available=False,
        priority="P1",
        description="字节跳动 AI Bot 技能市场",
    ),
    "dify": SkillMarket(
        name="Dify",
        estimated_count=12000,
        region="global",
        api_available=False,
        priority="P2",
        description="LLM 应用开发平台插件",
    ),
}

TOTAL_ESTIMATED_SKILLS = sum(m.estimated_count for m in SKILL_MARKETS.values())


# ── 已发现技能 ─────────────────────────────────────────────────────

@dataclass
class DiscoveredSkill:
    """一个从市场发现的技能。"""

    name: str
    market: str
    description: str = ""
    category: str = ""
    domain: str = ""
    relevance: float = 0.5
    quality: float = 0.5
    popularity: float = 0.5
    complexity: float = 0.5
    skill_value: float = 0.0
    region: str = "global"
    url: str = ""
    discovered_at: str = ""

    def compute_value(self) -> float:
        """计算技能价值：Skill_Value = (Relevance × Quality) + (Popularity × 0.3) - (Complexity × 0.2)"""
        self.skill_value = round(
            (self.relevance * self.quality) + (self.popularity * 0.3) - (self.complexity * 0.2),
            4,
        )
        return self.skill_value


# ── 预置的高价值技能（从 TRAE 已有技能 + 市场研究） ────────────────

_PRESET_DISCOVERED_SKILLS: list[dict[str, Any]] = [
    # 中国社交媒体
    {"name": "baoyu-post-to-weibo", "market": "trae", "category": "social_media_china",
     "description": "发布微博内容和头条文章", "domain": "social_media_china",
     "relevance": 0.9, "quality": 0.8, "popularity": 0.7, "complexity": 0.3, "region": "china"},
    {"name": "baoyu-post-to-x", "market": "trae", "category": "social_media_global",
     "description": "发布 X/Twitter 内容和文章", "domain": "social_media_china",
     "relevance": 0.8, "quality": 0.8, "popularity": 0.8, "complexity": 0.3, "region": "global"},
    {"name": "baoyu-xhs-images", "market": "trae", "category": "social_media_china",
     "description": "小红书风格图片卡片生成", "domain": "social_media_china",
     "relevance": 0.9, "quality": 0.8, "popularity": 0.8, "complexity": 0.4, "region": "china"},
    {"name": "baoyu-wechat-summary", "market": "trae", "category": "social_media_china",
     "description": "微信群聊精华总结", "domain": "social_media_china",
     "relevance": 0.8, "quality": 0.7, "popularity": 0.7, "complexity": 0.4, "region": "china"},
    {"name": "baoyu-post-to-wechat", "market": "trae", "category": "social_media_china",
     "description": "发布微信公众号文章", "domain": "social_media_china",
     "relevance": 0.9, "quality": 0.8, "popularity": 0.8, "complexity": 0.4, "region": "china"},
    {"name": "baoyu-youtube-transcript", "market": "trae", "category": "content_analysis",
     "description": "YouTube 视频字幕下载", "domain": "research",
     "relevance": 0.7, "quality": 0.8, "popularity": 0.7, "complexity": 0.3, "region": "global"},
    {"name": "baoyu-url-to-markdown", "market": "trae", "category": "research",
     "description": "URL 转 Markdown", "domain": "research",
     "relevance": 0.8, "quality": 0.8, "popularity": 0.7, "complexity": 0.3, "region": "global"},
    {"name": "baoyu-image-gen", "market": "trae", "category": "content_creation",
     "description": "AI 图片生成（多后端）", "domain": "content_creation",
     "relevance": 0.9, "quality": 0.9, "popularity": 0.9, "complexity": 0.5, "region": "global"},
    {"name": "baoyu-cover-image", "market": "trae", "category": "content_creation",
     "description": "文章封面图生成", "domain": "content_creation",
     "relevance": 0.8, "quality": 0.8, "popularity": 0.7, "complexity": 0.4, "region": "global"},
    {"name": "baoyu-compress-image", "market": "trae", "category": "content_creation",
     "description": "图片压缩（WebP/PNG）", "domain": "content_creation",
     "relevance": 0.6, "quality": 0.7, "popularity": 0.6, "complexity": 0.2, "region": "global"},
    {"name": "baoyu-translate", "market": "trae", "category": "localization",
     "description": "文章翻译（多模式）", "domain": "research",
     "relevance": 0.8, "quality": 0.9, "popularity": 0.8, "complexity": 0.4, "region": "global"},
    {"name": "baoyu-diagram", "market": "trae", "category": "visualization",
     "description": "SVG 图表生成", "domain": "data_analysis",
     "relevance": 0.8, "quality": 0.8, "popularity": 0.7, "complexity": 0.4, "region": "global"},
    {"name": "baoyu-infographic", "market": "trae", "category": "visualization",
     "description": "信息图生成", "domain": "data_analysis",
     "relevance": 0.7, "quality": 0.8, "popularity": 0.6, "complexity": 0.5, "region": "global"},
    {"name": "baoyu-slide-deck", "market": "trae", "category": "presentation",
     "description": "幻灯片图片生成", "domain": "documentation",
     "relevance": 0.7, "quality": 0.7, "popularity": 0.6, "complexity": 0.4, "region": "global"},
    {"name": "baoyu-comic", "market": "trae", "category": "content_creation",
     "description": "知识漫画创作", "domain": "content_creation",
     "relevance": 0.7, "quality": 0.8, "popularity": 0.5, "complexity": 0.5, "region": "global"},
    {"name": "baoyu-article-illustrator", "market": "trae", "category": "content_creation",
     "description": "文章配图生成", "domain": "content_creation",
     "relevance": 0.7, "quality": 0.7, "popularity": 0.5, "complexity": 0.4, "region": "global"},
    {"name": "baoyu-format-markdown", "market": "trae", "category": "documentation",
     "description": "Markdown 格式化", "domain": "documentation",
     "relevance": 0.6, "quality": 0.7, "popularity": 0.6, "complexity": 0.2, "region": "global"},
    {"name": "baoyu-markdown-to-html", "market": "trae", "category": "documentation",
     "description": "Markdown 转 HTML（微信兼容）", "domain": "documentation",
     "relevance": 0.7, "quality": 0.8, "popularity": 0.7, "complexity": 0.4, "region": "china"},
    {"name": "baoyu-danger-x-to-markdown", "market": "trae", "category": "social_media_global",
     "description": "X/Twitter 转 Markdown", "domain": "research",
     "relevance": 0.6, "quality": 0.7, "popularity": 0.5, "complexity": 0.4, "region": "global"},
    {"name": "baoyu-electron-extract", "market": "trae", "category": "reverse_engineering",
     "description": "Electron 应用资源提取", "domain": "devops",
     "relevance": 0.5, "quality": 0.7, "popularity": 0.4, "complexity": 0.5, "region": "global"},
    # PM / Strategy skills
    {"name": "acquisition-channel-advisor", "market": "trae", "category": "pm_strategy",
     "description": "获客渠道评估", "domain": "research",
     "relevance": 0.6, "quality": 0.8, "popularity": 0.5, "complexity": 0.4, "region": "global"},
    {"name": "consulting-analysis", "market": "trae", "category": "pm_strategy",
     "description": "咨询级研究报告", "domain": "research",
     "relevance": 0.8, "quality": 0.9, "popularity": 0.7, "complexity": 0.5, "region": "global"},
    {"name": "company-research", "market": "trae", "category": "pm_strategy",
     "description": "公司研究简报", "domain": "research",
     "relevance": 0.7, "quality": 0.8, "popularity": 0.6, "complexity": 0.4, "region": "global"},
    {"name": "customer-journey-map", "market": "trae", "category": "pm_strategy",
     "description": "客户旅程地图", "domain": "research",
     "relevance": 0.6, "quality": 0.8, "popularity": 0.5, "complexity": 0.4, "region": "global"},
    {"name": "jobs-to-be-done", "market": "trae", "category": "pm_strategy",
     "description": "JTBD 需求分析", "domain": "research",
     "relevance": 0.6, "quality": 0.8, "popularity": 0.5, "complexity": 0.4, "region": "global"},
    {"name": "positioning-statement", "market": "trae", "category": "pm_strategy",
     "description": "定位声明", "domain": "research",
     "relevance": 0.6, "quality": 0.8, "popularity": 0.5, "complexity": 0.3, "region": "global"},
    {"name": "prd-development", "market": "trae", "category": "pm_strategy",
     "description": "PRD 产品需求文档", "domain": "documentation",
     "relevance": 0.7, "quality": 0.9, "popularity": 0.7, "complexity": 0.5, "region": "global"},
    {"name": "roadmap-planning", "market": "trae", "category": "pm_strategy",
     "description": "路线图规划", "domain": "documentation",
     "relevance": 0.7, "quality": 0.8, "popularity": 0.6, "complexity": 0.5, "region": "global"},
    {"name": "user-story", "market": "trae", "category": "pm_strategy",
     "description": "用户故事创建", "domain": "documentation",
     "relevance": 0.7, "quality": 0.8, "popularity": 0.6, "complexity": 0.3, "region": "global"},
    {"name": "user-story-mapping", "market": "trae", "category": "pm_strategy",
     "description": "用户故事地图", "domain": "documentation",
     "relevance": 0.6, "quality": 0.8, "popularity": 0.5, "complexity": 0.4, "region": "global"},
    # Finance / SaaS
    {"name": "saas-revenue-growth-metrics", "market": "trae", "category": "finance",
     "description": "SaaS 收入增长指标", "domain": "data_analysis",
     "relevance": 0.6, "quality": 0.8, "popularity": 0.5, "complexity": 0.4, "region": "global"},
    {"name": "saas-economics-efficiency-metrics", "market": "trae", "category": "finance",
     "description": "SaaS 经济效率指标", "domain": "data_analysis",
     "relevance": 0.6, "quality": 0.8, "popularity": 0.5, "complexity": 0.4, "region": "global"},
    {"name": "business-health-diagnostic", "market": "trae", "category": "finance",
     "description": "商业健康诊断", "domain": "data_analysis",
     "relevance": 0.6, "quality": 0.8, "popularity": 0.5, "complexity": 0.4, "region": "global"},
    {"name": "tam-sam-som-calculator", "market": "trae", "category": "finance",
     "description": "TAM/SAM/SOM 市场规模计算", "domain": "data_analysis",
     "relevance": 0.6, "quality": 0.8, "popularity": 0.5, "complexity": 0.4, "region": "global"},
    # Web dev
    {"name": "web-dev", "market": "trae", "category": "web_development",
     "description": "Web 应用开发", "domain": "design_ui",
     "relevance": 0.7, "quality": 0.9, "popularity": 0.8, "complexity": 0.6, "region": "global"},
    {"name": "webapp-testing", "market": "trae", "category": "testing",
     "description": "Web 应用测试（Playwright）", "domain": "testing",
     "relevance": 0.8, "quality": 0.8, "popularity": 0.7, "complexity": 0.5, "region": "global"},
    {"name": "canvas-design", "market": "trae", "category": "design",
     "description": "视觉设计（PNG/PDF）", "domain": "content_creation",
     "relevance": 0.7, "quality": 0.8, "popularity": 0.6, "complexity": 0.5, "region": "global"},
    {"name": "slides", "market": "trae", "category": "presentation",
     "description": "PowerPoint 幻灯片生成", "domain": "documentation",
     "relevance": 0.7, "quality": 0.8, "popularity": 0.7, "complexity": 0.5, "region": "global"},
    # Notion / Obsidian
    {"name": "notion-cli", "market": "trae", "category": "knowledge_mgmt",
     "description": "Notion API 交互", "domain": "knowledge_mgmt",
     "relevance": 0.6, "quality": 0.8, "popularity": 0.6, "complexity": 0.4, "region": "global"},
    {"name": "obsidian-cli", "market": "trae", "category": "knowledge_mgmt",
     "description": "Obsidian Vault 交互", "domain": "knowledge_mgmt",
     "relevance": 0.6, "quality": 0.8, "popularity": 0.5, "complexity": 0.4, "region": "global"},
    # AI / ML
    {"name": "ai-shaped-readiness-advisor", "market": "trae", "category": "ai_strategy",
     "description": "AI 成熟度评估", "domain": "research",
     "relevance": 0.6, "quality": 0.8, "popularity": 0.5, "complexity": 0.4, "region": "global"},
    {"name": "recommendation-canvas", "market": "trae", "category": "ai_strategy",
     "description": "AI 产品推荐画布", "domain": "research",
     "relevance": 0.6, "quality": 0.8, "popularity": 0.5, "complexity": 0.4, "region": "global"},
    {"name": "context-engineering-advisor", "market": "trae", "category": "ai_strategy",
     "description": "上下文工程诊断", "domain": "research",
     "relevance": 0.7, "quality": 0.8, "popularity": 0.6, "complexity": 0.5, "region": "global"},
    # DevOps / Infra
    {"name": "redis-development", "market": "trae", "category": "database",
     "description": "Redis 性能优化", "domain": "data_analysis",
     "relevance": 0.7, "quality": 0.9, "popularity": 0.7, "complexity": 0.5, "region": "global"},
    {"name": "mcp-builder", "market": "trae", "category": "integration",
     "description": "MCP 服务器创建", "domain": "devops",
     "relevance": 0.7, "quality": 0.8, "popularity": 0.6, "complexity": 0.5, "region": "global"},
    # Payment
    {"name": "alipay-payment-integration", "market": "trae", "category": "payment",
     "description": "支付宝支付集成", "domain": "payment_china",
     "relevance": 0.9, "quality": 0.9, "popularity": 0.8, "complexity": 0.6, "region": "china"},
    {"name": "douyinpay-payment-integration", "market": "trae", "category": "payment",
     "description": "抖音支付集成", "domain": "payment_china",
     "relevance": 0.8, "quality": 0.8, "popularity": 0.7, "complexity": 0.6, "region": "china"},

    # Western Markets — GitHub Actions
    {"name": "gha-checkout", "market": "github_actions", "category": "ci_cd",
     "description": "GitHub Actions checkout action — clone repository for CI/CD workflows", "domain": "devops",
     "relevance": 0.9, "quality": 0.95, "popularity": 0.95, "complexity": 0.2, "region": "global"},
    {"name": "gha-cache", "market": "github_actions", "category": "ci_cd",
     "description": "GitHub Actions cache action — manage workflow caching for faster builds", "domain": "devops",
     "relevance": 0.8, "quality": 0.9, "popularity": 0.85, "complexity": 0.3, "region": "global"},
    {"name": "gha-setup-node", "market": "github_actions", "category": "ci_cd",
     "description": "Setup Node.js environment in GitHub Actions workflows", "domain": "devops",
     "relevance": 0.7, "quality": 0.9, "popularity": 0.8, "complexity": 0.2, "region": "global"},
    {"name": "gha-setup-python", "market": "github_actions", "category": "ci_cd",
     "description": "Setup Python environment in GitHub Actions workflows", "domain": "devops",
     "relevance": 0.8, "quality": 0.9, "popularity": 0.8, "complexity": 0.2, "region": "global"},
    {"name": "gha-docker-build-push", "market": "github_actions", "category": "ci_cd",
     "description": "Build and push Docker images in GitHub Actions", "domain": "devops",
     "relevance": 0.8, "quality": 0.85, "popularity": 0.75, "complexity": 0.4, "region": "global"},

    # VS Code Extensions
    {"name": "vsc-copilot", "market": "vscode_extensions", "category": "ai_ml",
     "description": "GitHub Copilot — AI pair programmer for VS Code", "domain": "devops",
     "relevance": 0.9, "quality": 0.9, "popularity": 0.95, "complexity": 0.3, "region": "global"},
    {"name": "vsc-prettier", "market": "vscode_extensions", "category": "code_quality",
     "description": "Prettier — opinionated code formatter for VS Code", "domain": "devops",
     "relevance": 0.7, "quality": 0.9, "popularity": 0.9, "complexity": 0.2, "region": "global"},
    {"name": "vsc-eslint", "market": "vscode_extensions", "category": "code_quality",
     "description": "ESLint — JavaScript/TypeScript linter for VS Code", "domain": "devops",
     "relevance": 0.7, "quality": 0.9, "popularity": 0.85, "complexity": 0.3, "region": "global"},
    {"name": "vsc-gitlens", "market": "vscode_extensions", "category": "productivity",
     "description": "GitLens — Git supercharged with blame, history, and repository insights", "domain": "devops",
     "relevance": 0.7, "quality": 0.85, "popularity": 0.8, "complexity": 0.3, "region": "global"},
    {"name": "vsc-python", "market": "vscode_extensions", "category": "developer_tools",
     "description": "Python extension — IntelliSense, linting, debugging for VS Code", "domain": "data_analysis",
     "relevance": 0.8, "quality": 0.9, "popularity": 0.9, "complexity": 0.3, "region": "global"},

    # PyPI Python Tools
    {"name": "pypi-fastapi", "market": "pypi", "category": "web_framework",
     "description": "FastAPI — modern high-performance Python web framework", "domain": "devops",
     "relevance": 0.8, "quality": 0.95, "popularity": 0.9, "complexity": 0.4, "region": "global"},
    {"name": "pypi-streamlit", "market": "pypi", "category": "web_framework",
     "description": "Streamlit — build data apps in Python quickly", "domain": "data_analysis",
     "relevance": 0.9, "quality": 0.85, "popularity": 0.85, "complexity": 0.3, "region": "global"},
    {"name": "pypi-pandas", "market": "pypi", "category": "data_science",
     "description": "Pandas — data analysis and manipulation library", "domain": "data_analysis",
     "relevance": 0.85, "quality": 0.95, "popularity": 0.95, "complexity": 0.4, "region": "global"},
    {"name": "pypi-pytest", "market": "pypi", "category": "testing",
     "description": "Pytest — Python testing framework with simple assertions", "domain": "testing",
     "relevance": 0.85, "quality": 0.9, "popularity": 0.9, "complexity": 0.3, "region": "global"},
    {"name": "pypi-langchain", "market": "pypi", "category": "ai_ml",
     "description": "LangChain — build LLM-powered applications and agents", "domain": "research",
     "relevance": 0.85, "quality": 0.8, "popularity": 0.85, "complexity": 0.6, "region": "global"},

    # Hugging Face Models
    {"name": "hf-stable-diffusion", "market": "huggingface", "category": "ai_ml",
     "description": "Stable Diffusion — text-to-image generation model", "domain": "content_creation",
     "relevance": 0.85, "quality": 0.85, "popularity": 0.9, "complexity": 0.6, "region": "global"},
    {"name": "hf-llama", "market": "huggingface", "category": "ai_ml",
     "description": "LLaMA — Meta's open large language model", "domain": "research",
     "relevance": 0.8, "quality": 0.85, "popularity": 0.85, "complexity": 0.7, "region": "global"},
    {"name": "hf-whisper", "market": "huggingface", "category": "ai_ml",
     "description": "Whisper — OpenAI's speech recognition model", "domain": "content_creation",
     "relevance": 0.7, "quality": 0.9, "popularity": 0.8, "complexity": 0.5, "region": "global"},
    {"name": "hf-bert", "market": "huggingface", "category": "ai_ml",
     "description": "BERT — bidirectional encoder for NLP tasks", "domain": "data_analysis",
     "relevance": 0.7, "quality": 0.9, "popularity": 0.8, "complexity": 0.6, "region": "global"},
    {"name": "hf-deepseek", "market": "huggingface", "category": "ai_ml",
     "description": "DeepSeek — open-source LLM with strong reasoning", "domain": "research",
     "relevance": 0.8, "quality": 0.85, "popularity": 0.8, "complexity": 0.7, "region": "global"},

    # China Markets — 飞书
    {"name": "feishu-aily", "market": "feishu", "category": "ai_ml",
     "description": "飞书Aily — AI智能伙伴，企业级AI助手", "domain": "research",
     "relevance": 0.8, "quality": 0.8, "popularity": 0.7, "complexity": 0.5, "region": "china"},
    {"name": "feishu-mcp", "market": "feishu", "category": "developer_tools",
     "description": "飞书MCP — 连接飞书核心能力与AI工具", "domain": "devops",
     "relevance": 0.85, "quality": 0.8, "popularity": 0.7, "complexity": 0.5, "region": "china"},
    {"name": "feishu-bitable", "market": "feishu", "category": "data_analysis",
     "description": "飞书多维表格 — 多维数据表格，支持自动化流程", "domain": "data_analysis",
     "relevance": 0.7, "quality": 0.8, "popularity": 0.7, "complexity": 0.4, "region": "china"},

    # 钉钉
    {"name": "dingtalk-yida", "market": "dingtalk", "category": "developer_tools",
     "description": "钉钉宜搭 — 阿里云低代码平台", "domain": "design_ui",
     "relevance": 0.7, "quality": 0.8, "popularity": 0.7, "complexity": 0.4, "region": "china"},
    {"name": "dingtalk-ai", "market": "dingtalk", "category": "ai_ml",
     "description": "钉钉AI — 内置AI助手，支持CLI化改造", "domain": "research",
     "relevance": 0.75, "quality": 0.75, "popularity": 0.7, "complexity": 0.5, "region": "china"},

    # 微信小程序
    {"name": "wechat-devtools", "market": "wechat", "category": "developer_tools",
     "description": "微信开发者工具 — 官方小程序IDE", "domain": "design_ui",
     "relevance": 0.85, "quality": 0.85, "popularity": 0.85, "complexity": 0.4, "region": "china"},
    {"name": "taro-framework", "market": "wechat", "category": "developer_tools",
     "description": "Taro — 京东开源跨端小程序开发框架", "domain": "design_ui",
     "relevance": 0.8, "quality": 0.85, "popularity": 0.75, "complexity": 0.5, "region": "china"},
    {"name": "uni-app-framework", "market": "wechat", "category": "developer_tools",
     "description": "uni-app — DCloud跨平台开发框架", "domain": "design_ui",
     "relevance": 0.8, "quality": 0.8, "popularity": 0.8, "complexity": 0.5, "region": "china"},
    {"name": "wechat-cloudbase", "market": "wechat", "category": "developer_tools",
     "description": "微信云开发 — Serverless后端平台", "domain": "devops",
     "relevance": 0.75, "quality": 0.8, "popularity": 0.7, "complexity": 0.5, "region": "china"},

    # 百度千帆/阿里云百炼
    {"name": "qianfan-agent-builder", "market": "baidu_qianfan", "category": "ai_ml",
     "description": "百度千帆AgentBuilder — 低代码智能体创建平台", "domain": "research",
     "relevance": 0.8, "quality": 0.8, "popularity": 0.7, "complexity": 0.5, "region": "china"},
    {"name": "bailian-mcp-hub", "market": "aliyun_bailian", "category": "ai_ml",
     "description": "阿里云百炼MCP广场 — 50+款MCP服务", "domain": "devops",
     "relevance": 0.85, "quality": 0.8, "popularity": 0.7, "complexity": 0.5, "region": "china"},
    {"name": "qianfan-rag", "market": "baidu_qianfan", "category": "ai_ml",
     "description": "千帆RAG知识问答 — 基于RAG框架的知识库问答", "domain": "research",
     "relevance": 0.8, "quality": 0.8, "popularity": 0.65, "complexity": 0.5, "region": "china"},

    # Coze (扣子)
    {"name": "coze-bing-search", "market": "coze", "category": "developer_tools",
     "description": "Coze必应搜索插件 — 搜索天气、汇率、时事", "domain": "research",
     "relevance": 0.7, "quality": 0.75, "popularity": 0.7, "complexity": 0.3, "region": "china"},
    {"name": "coze-doubao-image", "market": "coze", "category": "ai_ml",
     "description": "Coze豆包图像生成 — 字节AI图像生成", "domain": "content_creation",
     "relevance": 0.8, "quality": 0.8, "popularity": 0.75, "complexity": 0.4, "region": "china"},
    {"name": "coze-code-runner", "market": "coze", "category": "developer_tools",
     "description": "Coze代码执行器 — 运行Python代码", "domain": "data_analysis",
     "relevance": 0.75, "quality": 0.75, "popularity": 0.7, "complexity": 0.4, "region": "china"},
    {"name": "coze-tianyancha", "market": "coze", "category": "data_analysis",
     "description": "Coze天眼查 — 企业搜索与信息查询", "domain": "research",
     "relevance": 0.7, "quality": 0.75, "popularity": 0.6, "complexity": 0.3, "region": "china"},

    # Dify
    {"name": "dify-tavily", "market": "dify", "category": "developer_tools",
     "description": "Dify Tavily — AI原生搜索引擎 (232K+安装)", "domain": "research",
     "relevance": 0.8, "quality": 0.85, "popularity": 0.8, "complexity": 0.4, "region": "global"},
    {"name": "dify-deepseek", "market": "dify", "category": "ai_ml",
     "description": "Dify DeepSeek — DeepSeek大模型插件 (956K+安装)", "domain": "research",
     "relevance": 0.85, "quality": 0.85, "popularity": 0.85, "complexity": 0.5, "region": "china"},
    {"name": "dify-tongyi", "market": "dify", "category": "ai_ml",
     "description": "Dify通义千问 — 阿里通义千问大模型 (1M+安装)", "domain": "research",
     "relevance": 0.85, "quality": 0.85, "popularity": 0.85, "complexity": 0.5, "region": "china"},
    {"name": "dify-alipay", "market": "dify", "category": "payment",
     "description": "Dify支付宝插件 — 支付宝支付工具 (3.6K+安装)", "domain": "payment_china",
     "relevance": 0.9, "quality": 0.8, "popularity": 0.5, "complexity": 0.5, "region": "china"},
    {"name": "dify-firecrawl", "market": "dify", "category": "developer_tools",
     "description": "Dify Firecrawl — Web爬虫工具 (152K+安装)", "domain": "research",
     "relevance": 0.75, "quality": 0.85, "popularity": 0.75, "complexity": 0.4, "region": "global"},
    {"name": "dify-bilibili-search", "market": "dify", "category": "social_media",
     "description": "Dify B站搜索 — B站视频搜索工具", "domain": "social_media_china",
     "relevance": 0.75, "quality": 0.7, "popularity": 0.5, "complexity": 0.3, "region": "china"},
    {"name": "dify-paddleocr", "market": "dify", "category": "ai_ml",
     "description": "Dify PaddleOCR — 百度飞桨OCR插件 (18K+安装)", "domain": "data_analysis",
     "relevance": 0.7, "quality": 0.85, "popularity": 0.6, "complexity": 0.5, "region": "china"},

    # Book-Based Thinking Framework Skills
    {"name": "triz-contradiction-solver", "market": "invented", "category": "thinking_framework",
     "description": "TRIZ矛盾解决器 — 识别技术/物理矛盾，映射到39x39矛盾矩阵，推荐发明原理", "domain": "research",
     "relevance": 0.85, "quality": 0.8, "popularity": 0.55, "complexity": 0.75, "region": "global"},
    {"name": "triz-inventive-principles", "market": "invented", "category": "thinking_framework",
     "description": "TRIZ 40发明原理 — 系统化应用40个发明原理生成解决方案", "domain": "research",
     "relevance": 0.8, "quality": 0.75, "popularity": 0.5, "complexity": 0.7, "region": "global"},
    {"name": "triz-ideal-final-result", "market": "invented", "category": "thinking_framework",
     "description": "TRIZ理想最终结果 — 定义IFR，从零复杂度目标反向求解", "domain": "research",
     "relevance": 0.75, "quality": 0.78, "popularity": 0.45, "complexity": 0.65, "region": "global"},
    {"name": "design-thinking-empathy-mapper", "market": "invented", "category": "thinking_framework",
     "description": "设计思维同理心映射 — 结构化用户研究，生成同理心图和用户旅程", "domain": "research",
     "relevance": 0.9, "quality": 0.85, "popularity": 0.8, "complexity": 0.55, "region": "global"},
    {"name": "design-thinking-ideation-engine", "market": "invented", "category": "thinking_framework",
     "description": "设计思维创意引擎 — HMW、SCAMPER、最差创意等多技法创意生成", "domain": "research",
     "relevance": 0.85, "quality": 0.82, "popularity": 0.75, "complexity": 0.5, "region": "global"},
    {"name": "design-thinking-prototype-test", "market": "invented", "category": "thinking_framework",
     "description": "设计思维原型测试 — 快速原型规划和用户测试循环", "domain": "testing",
     "relevance": 0.85, "quality": 0.8, "popularity": 0.7, "complexity": 0.5, "region": "global"},
    {"name": "lean-startup-mvp-designer", "market": "invented", "category": "thinking_framework",
     "description": "精益创业MVP设计器 — 定义风险假设，设计最小验证实验", "domain": "research",
     "relevance": 0.9, "quality": 0.85, "popularity": 0.85, "complexity": 0.45, "region": "global"},
    {"name": "lean-startup-validation-loop", "market": "invented", "category": "thinking_framework",
     "description": "精益创业验证循环 — Build-Measure-Learn全流程，区分虚荣指标", "domain": "research",
     "relevance": 0.88, "quality": 0.83, "popularity": 0.8, "complexity": 0.55, "region": "global"},
    {"name": "first-principles-decomposer", "market": "invented", "category": "thinking_framework",
     "description": "第一性原理分解器 — 将复杂问题分解为不可约基本真理", "domain": "research",
     "relevance": 0.85, "quality": 0.82, "popularity": 0.8, "complexity": 0.6, "region": "global"},
    {"name": "first-principles-rebuilder", "market": "invented", "category": "thinking_framework",
     "description": "第一性原理重建器 — 从基本真理向上重建新颖解决方案", "domain": "research",
     "relevance": 0.82, "quality": 0.78, "popularity": 0.7, "complexity": 0.65, "region": "global"},
    {"name": "systems-thinking-leverage-finder", "market": "invented", "category": "thinking_framework",
     "description": "系统思维杠杆点发现 — 映射存量/流量/反馈环，识别12个杠杆点", "domain": "research",
     "relevance": 0.82, "quality": 0.8, "popularity": 0.55, "complexity": 0.75, "region": "global"},
    {"name": "systems-thinking-causal-loop-mapper", "market": "invented", "category": "thinking_framework",
     "description": "系统思维因果环映射 — 构建因果环图，发现隐藏动态和二阶效应", "domain": "data_analysis",
     "relevance": 0.8, "quality": 0.78, "popularity": 0.5, "complexity": 0.7, "region": "global"},
    {"name": "six-hats-decision-review", "market": "invented", "category": "thinking_framework",
     "description": "六顶思考帽决策评审 — 从6个视角系统审查决策，减少认知偏差", "domain": "research",
     "relevance": 0.85, "quality": 0.82, "popularity": 0.7, "complexity": 0.45, "region": "global"},
    {"name": "six-hats-facilitator", "market": "invented", "category": "thinking_framework",
     "description": "六顶思考帽引导器 — 按最优顺序排列帽子，引导结构化思维会议", "domain": "research",
     "relevance": 0.8, "quality": 0.78, "popularity": 0.6, "complexity": 0.5, "region": "global"},
    {"name": "scamper-idea-generator", "market": "invented", "category": "thinking_framework",
     "description": "SCAMPER创意生成器 — 7维度系统化生成创意变体和改进", "domain": "research",
     "relevance": 0.82, "quality": 0.8, "popularity": 0.65, "complexity": 0.4, "region": "global"},
    {"name": "scamper-feature-remixer", "market": "invented", "category": "thinking_framework",
     "description": "SCAMPER功能精简器 — 聚焦消除和重排，对抗功能膨胀", "domain": "research",
     "relevance": 0.78, "quality": 0.75, "popularity": 0.55, "complexity": 0.45, "region": "global"},
]


# ── SkillDiscovery ─────────────────────────────────────────────────

class SkillDiscovery:
    """1M+ 技能市场深度研究引擎。"""

    def __init__(
        self,
        domain_map: DomainMap | None = None,
        cache_path: str | Path | None = None,
    ) -> None:
        self.domain_map = domain_map or DomainMap()
        self._cache_path = Path(cache_path) if cache_path else None
        self._discovered: list[DiscoveredSkill] = []
        self._load_preset_skills()

    def _load_preset_skills(self) -> None:
        """加载预置的高价值技能。"""
        for skill_data in _PRESET_DISCOVERED_SKILLS:
            skill = DiscoveredSkill(
                name=skill_data["name"],
                market=skill_data["market"],
                description=skill_data.get("description", ""),
                category=skill_data.get("category", ""),
                domain=skill_data.get("domain", ""),
                relevance=skill_data.get("relevance", 0.5),
                quality=skill_data.get("quality", 0.5),
                popularity=skill_data.get("popularity", 0.5),
                complexity=skill_data.get("complexity", 0.5),
                region=skill_data.get("region", "global"),
                discovered_at=datetime.utcnow().isoformat(),
            )
            skill.compute_value()
            self._discovered.append(skill)

    def discover_all(
        self, query: str = "", limit: int = 100
    ) -> list[DiscoveredSkill]:
        """搜索所有已发现的技能。"""
        results = self._discovered

        if query:
            query_lower = query.lower()
            results = [
                s for s in results
                if query_lower in s.name.lower()
                or query_lower in s.description.lower()
                or query_lower in s.category.lower()
                or query_lower in s.domain.lower()
            ]

        # 按技能价值排序
        results.sort(key=lambda s: s.skill_value, reverse=True)
        return results[:limit]

    def discover_by_domain(self, domain: str) -> list[DiscoveredSkill]:
        """按领域搜索技能。"""
        return [
            s for s in self._discovered
            if s.domain == domain
        ]

    def discover_by_region(self, region: str) -> list[DiscoveredSkill]:
        """按地区搜索技能。"""
        return [
            s for s in self._discovered
            if s.region == region or s.region == "global"
        ]

    def evaluate_skill(self, skill_data: dict[str, Any]) -> DiscoveredSkill:
        """用公式评估技能价值。"""
        skill = DiscoveredSkill(
            name=skill_data.get("name", "unknown"),
            market=skill_data.get("market", "unknown"),
            description=skill_data.get("description", ""),
            category=skill_data.get("category", ""),
            domain=skill_data.get("domain", ""),
            relevance=skill_data.get("relevance", 0.5),
            quality=skill_data.get("quality", 0.5),
            popularity=skill_data.get("popularity", 0.5),
            complexity=skill_data.get("complexity", 0.5),
            region=skill_data.get("region", "global"),
            discovered_at=datetime.utcnow().isoformat(),
        )
        skill.compute_value()
        return skill

    def add_discovered_skill(self, skill: DiscoveredSkill) -> None:
        """添加一个发现的技能。"""
        # 避免重复
        if not any(s.name == skill.name for s in self._discovered):
            self._discovered.append(skill)

    def categorize_skill(self, skill: DiscoveredSkill) -> str:
        """自动分类技能到领域。"""
        # 先检查是否已有领域
        if skill.domain and skill.domain in self.domain_map.all_domains():
            return skill.domain

        # 根据描述和类别推断领域
        text = f"{skill.name} {skill.description} {skill.category}".lower()

        best_domain = ""
        best_score = 0.0

        for domain_name in self.domain_map.all_domains():
            signals = self.domain_map.get_context_signals(domain_name)
            score = sum(1 for s in signals if s.lower() in text)
            if score > best_score:
                best_score = score
                best_domain = domain_name

        if best_domain:
            skill.domain = best_domain
            return best_domain

        # 默认分类
        skill.domain = "research"
        return "research"

    def get_high_value_skills(self, threshold: float = 0.6) -> list[DiscoveredSkill]:
        """获取高价值技能（超过阈值的）。"""
        return [s for s in self._discovered if s.skill_value >= threshold]

    def get_market_stats(self) -> dict[str, dict[str, Any]]:
        """获取市场统计。"""
        stats: dict[str, dict[str, Any]] = {}
        for market_name, market in SKILL_MARKETS.items():
            market_skills = [s for s in self._discovered if s.market == market_name]
            stats[market_name] = {
                "name": market.name,
                "estimated_count": market.estimated_count,
                "discovered_count": len(market_skills),
                "region": market.region,
                "priority": market.priority,
            }
        return stats

    def total_discovered(self) -> int:
        """返回已发现的技能总数。"""
        return len(self._discovered)

    def generate_research_summary(self) -> dict[str, Any]:
        """生成研究摘要。"""
        high_value = self.get_high_value_skills()
        china_skills = self.discover_by_region("china")
        global_skills = self.discover_by_region("global")

        return {
            "total_discovered": self.total_discovered(),
            "total_estimated": TOTAL_ESTIMATED_SKILLS,
            "high_value_count": len(high_value),
            "china_skills_count": len(china_skills),
            "global_skills_count": len(global_skills),
            "markets": self.get_market_stats(),
            "top_skills": [
                {"name": s.name, "value": s.skill_value, "domain": s.domain}
                for s in high_value[:20]
            ],
        }
