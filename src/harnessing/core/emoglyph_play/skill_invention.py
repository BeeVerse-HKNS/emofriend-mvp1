"""
SkillInvention — Formula Thinking 新技能发明引擎

分析技能缺口，用公式思维发明新技能。

发明公式：
  New_Skill = (Gap × Demand) + (Innovation²) - (Complexity)

缺口检测：
  - 扫描 DomainMap，找出没有技能覆盖的领域
  - 分析用户 prompt 历史，找出频繁出现但无技能匹配的场景
  - 对比西方和中国市场，找出地域性缺口
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .domain_map import DomainMap, DomainEntry
from .skill_discovery import DiscoveredSkill, SkillDiscovery


# ── 缺口定义 ───────────────────────────────────────────────────────

@dataclass
class SkillGap:
    """一个技能缺口。"""

    domain: str
    description: str = ""
    gap_score: float = 0.0      # 0-1，缺口大小
    demand_score: float = 0.0   # 0-1，需求强度
    innovation_score: float = 0.0  # 0-1，创新潜力
    complexity_score: float = 0.0  # 0-1，实现复杂度
    invention_score: float = 0.0   # 最终发明分数
    region: str = "any"
    suggested_skills: list[str] = field(default_factory=list)


# ── 已知缺口模板 ───────────────────────────────────────────────────

_KNOWN_GAPS: list[dict[str, Any]] = [
    {
        "domain": "payment_global",
        "description": "全球支付场景缺少 Stripe/PayPal 集成技能",
        "gap_score": 0.9,
        "demand_score": 0.7,
        "innovation_score": 0.5,
        "complexity_score": 0.6,
        "region": "global",
        "suggested_skills": ["stripe-payment-integration", "paypal-payment-integration"],
    },
    {
        "domain": "social_media_china",
        "description": "缺少微博发布、小红书图片生成、B站内容管理技能",
        "gap_score": 0.7,
        "demand_score": 0.9,
        "innovation_score": 0.7,
        "complexity_score": 0.4,
        "region": "china",
        "suggested_skills": ["weibo-content-manager", "xiaohongshu-image-generator", "bilibili-content-manager"],
    },
    {
        "domain": "localization",
        "description": "缺少多语言本地化技能（中英互译、文化适配）",
        "gap_score": 0.6,
        "demand_score": 0.8,
        "innovation_score": 0.6,
        "complexity_score": 0.5,
        "region": "any",
        "suggested_skills": ["i18n-localization-engine", "cultural-adaptation-engine"],
    },
    {
        "domain": "compliance",
        "description": "缺少合规检查技能（中国刑法303、香港Cap 148、PIPL）",
        "gap_score": 0.8,
        "demand_score": 0.9,
        "innovation_score": 0.8,
        "complexity_score": 0.7,
        "region": "china",
        "suggested_skills": ["china-compliance-checker", "hongkong-compliance-checker", "pipl-privacy-auditor"],
    },
    {
        "domain": "monitoring",
        "description": "缺少应用监控和告警技能",
        "gap_score": 0.5,
        "demand_score": 0.6,
        "innovation_score": 0.4,
        "complexity_score": 0.5,
        "region": "any",
        "suggested_skills": ["app-monitoring-dashboard", "alert-manager"],
    },
    {
        "domain": "email_automation",
        "description": "缺少邮件自动化技能（发送、模板、调度）",
        "gap_score": 0.6,
        "demand_score": 0.7,
        "innovation_score": 0.5,
        "complexity_score": 0.4,
        "region": "any",
        "suggested_skills": ["email-automation-engine", "email-template-manager"],
    },
    {
        "domain": "data_pipeline",
        "description": "缺少数据管道技能（ETL、数据清洗、数据同步）",
        "gap_score": 0.5,
        "demand_score": 0.6,
        "innovation_score": 0.5,
        "complexity_score": 0.6,
        "region": "any",
        "suggested_skills": ["etl-pipeline-builder", "data-sync-engine"],
    },
    {
        "domain": "mobile_development",
        "description": "缺少移动端开发技能（React Native、Flutter、小程序）",
        "gap_score": 0.7,
        "demand_score": 0.8,
        "innovation_score": 0.6,
        "complexity_score": 0.7,
        "region": "china",
        "suggested_skills": ["wechat-miniprogram-builder", "react-native-builder"],
    },
    {
        "domain": "seo_marketing",
        "description": "缺少 SEO 和营销技能（关键词分析、内容优化）",
        "gap_score": 0.5,
        "demand_score": 0.7,
        "innovation_score": 0.5,
        "complexity_score": 0.4,
        "region": "any",
        "suggested_skills": ["seo-analyzer", "content-optimizer"],
    },
    {
        "domain": "ai_agent_orchestration",
        "description": "缺少 AI Agent 编排技能（多 Agent 协调、任务分配）",
        "gap_score": 0.8,
        "demand_score": 0.9,
        "innovation_score": 0.9,
        "complexity_score": 0.8,
        "region": "any",
        "suggested_skills": ["multi-agent-orchestrator", "agent-task-delegator"],
    },
]


# ── SkillInvention ─────────────────────────────────────────────────

class SkillInvention:
    """Formula Thinking 新技能发明引擎。"""

    def __init__(
        self,
        domain_map: DomainMap | None = None,
        skill_discovery: SkillDiscovery | None = None,
    ) -> None:
        self.domain_map = domain_map or DomainMap()
        self.discovery = skill_discovery or SkillDiscovery(self.domain_map)
        self._invented: list[SkillGap] = []

    def detect_gaps(self) -> list[SkillGap]:
        """检测技能缺口。

        检测方式：
        1. 扫描 DomainMap，找出没有技能覆盖的领域
        2. 对比已知缺口模板
        3. 对比西方和中国市场，找出地域性缺口
        """
        gaps: list[SkillGap] = []

        # 1. 检查 DomainMap 中技能为空的领域
        for domain_name in self.domain_map.all_domains():
            entry = self.domain_map.domain_info(domain_name)
            if entry and len(entry.skills) == 0:
                gap = SkillGap(
                    domain=domain_name,
                    description=f"领域 {domain_name} 没有任何技能覆盖",
                    gap_score=1.0,
                    demand_score=0.7,
                    innovation_score=0.6,
                    complexity_score=0.5,
                    region=entry.geo,
                )
                gap.invention_score = self._calculate_invention_score(gap)
                gaps.append(gap)

        # 2. 检查已知缺口模板
        for gap_data in _KNOWN_GAPS:
            # 检查该领域的技能是否已被发现
            domain_skills = self.domain_map.get_skills_for_domain(gap_data["domain"])
            discovered_names = {s.name for s in self.discovery.discover_all()}

            # 检查建议技能是否已存在
            missing_skills = [
                s for s in gap_data["suggested_skills"]
                if s not in discovered_names and s not in domain_skills
            ]

            if missing_skills:
                gap = SkillGap(
                    domain=gap_data["domain"],
                    description=gap_data["description"],
                    gap_score=gap_data["gap_score"],
                    demand_score=gap_data["demand_score"],
                    innovation_score=gap_data["innovation_score"],
                    complexity_score=gap_data["complexity_score"],
                    region=gap_data["region"],
                    suggested_skills=missing_skills,
                )
                gap.invention_score = self._calculate_invention_score(gap)
                gaps.append(gap)

        # 3. 地域性缺口检测
        china_domains = [d for d in self.domain_map.all_domains()
                         if self.domain_map.domain_info(d) and self.domain_map.domain_info(d).geo == "china"]
        for domain_name in china_domains:
            skills = self.domain_map.get_skills_for_domain(domain_name)
            if len(skills) < 3:
                gap = SkillGap(
                    domain=domain_name,
                    description=f"中国领域 {domain_name} 技能不足（仅 {len(skills)} 个）",
                    gap_score=0.7,
                    demand_score=0.8,
                    innovation_score=0.7,
                    complexity_score=0.5,
                    region="china",
                )
                gap.invention_score = self._calculate_invention_score(gap)
                # 避免重复
                if not any(g.domain == gap.domain and g.description == gap.description for g in gaps):
                    gaps.append(gap)

        # 按发明分数排序
        gaps.sort(key=lambda g: g.invention_score, reverse=True)
        self._invented = gaps
        return gaps

    def invent_skill(self, gap: SkillGap) -> DiscoveredSkill:
        """根据缺口发明新技能。"""
        # 取第一个建议技能名，或自动生成
        if gap.suggested_skills:
            skill_name = gap.suggested_skills[0]
        else:
            skill_name = f"{gap.domain}-auto-skill"

        skill = DiscoveredSkill(
            name=skill_name,
            market="invented",
            description=gap.description,
            category=gap.domain,
            domain=gap.domain,
            relevance=gap.demand_score,
            quality=0.7,  # 新发明的技能默认质量
            popularity=0.5,  # 新发明，流行度未知
            complexity=gap.complexity_score,
            region=gap.region,
            discovered_at=datetime.utcnow().isoformat(),
        )
        skill.compute_value()
        return skill

    def batch_invent(self, min_invention_score: float = 0.5) -> list[DiscoveredSkill]:
        """批量发明新技能。"""
        if not self._invented:
            self.detect_gaps()

        invented_skills: list[DiscoveredSkill] = []
        for gap in self._invented:
            if gap.invention_score >= min_invention_score:
                for suggested in gap.suggested_skills:
                    skill = DiscoveredSkill(
                        name=suggested,
                        market="invented",
                        description=gap.description,
                        category=gap.domain,
                        domain=gap.domain,
                        relevance=gap.demand_score,
                        quality=0.7,
                        popularity=0.5,
                        complexity=gap.complexity_score,
                        region=gap.region,
                        discovered_at=datetime.utcnow().isoformat(),
                    )
                    skill.compute_value()
                    invented_skills.append(skill)

        return invented_skills

    def _calculate_invention_score(self, gap: SkillGap) -> float:
        """计算发明分数：New_Skill = (Gap × Demand) + (Innovation²) - (Complexity)"""
        score = (gap.gap_score * gap.demand_score) + (gap.innovation_score ** 2) - gap.complexity_score
        return round(min(max(score, 0.0), 2.0), 4)

    def get_invention_summary(self) -> dict[str, Any]:
        """获取发明摘要。"""
        if not self._invented:
            self.detect_gaps()

        return {
            "total_gaps": len(self._invented),
            "high_priority_gaps": len([g for g in self._invented if g.invention_score >= 0.7]),
            "china_gaps": len([g for g in self._invented if g.region == "china"]),
            "global_gaps": len([g for g in self._invented if g.region in ("global", "any")]),
            "top_gaps": [
                {
                    "domain": g.domain,
                    "invention_score": g.invention_score,
                    "suggested_skills": g.suggested_skills[:3],
                }
                for g in self._invented[:10]
            ],
        }
