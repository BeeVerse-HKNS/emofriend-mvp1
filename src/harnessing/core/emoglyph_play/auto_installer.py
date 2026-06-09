"""
AutoInstaller — 自动注册引擎

发现新技能后自动注册到 skill_router.py（不是安装软件包）。

注册流程：
  发现新技能 → 评估质量 → 分配 CM 编号 → 创建触发规则 → 注册到 skill_router.py → 更新 DomainMap → 验证

注册内容（添加到 skill_router.py）：
  1. SKILL_REGISTRY 添加新技能条目
  2. INTEGRATION_TIERS["bridge"] 添加技能名
  3. CM_RULES_INTEGRATION 添加新 CM 规则
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .domain_map import DomainMap
from .skill_discovery import DiscoveredSkill, SkillDiscovery


# ── 注册结果 ───────────────────────────────────────────────────────

@dataclass
class RegistrationResult:
    """单个技能的注册结果。"""

    skill_name: str
    cm_id: str = ""
    success: bool = False
    message: str = ""
    registered_at: str = ""

    # 注册详情
    domain: str = ""
    trigger_keywords: list[str] = field(default_factory=list)
    confidence_threshold: float = 0.5


@dataclass
class BatchRegistrationResult:
    """批量注册结果。"""

    total: int = 0
    successful: int = 0
    failed: int = 0
    results: list[RegistrationResult] = field(default_factory=list)
    next_cm_id: int = 54  # CM-53 已被使用，下一个从 CM-54 开始


# ── AutoInstaller ──────────────────────────────────────────────────

class AutoInstaller:
    """自动注册引擎 — 发现新技能后自动注册到系统。"""

    # skill_router.py 的路径
    _SKILL_ROUTER_PATH = Path(
        r"d:\My_Code_Projects\Harnessing\src\harnessing\core\skill_router.py"
    )

    def __init__(
        self,
        domain_map: DomainMap | None = None,
        skill_discovery: SkillDiscovery | None = None,
    ) -> None:
        self.domain_map = domain_map or DomainMap()
        self.discovery = skill_discovery or SkillDiscovery(self.domain_map)
        self._next_cm_id = 54  # CM-53 已被使用

    def register_skill(self, skill: DiscoveredSkill) -> RegistrationResult:
        """注册一个发现的技能到系统。

        Parameters
        ----------
        skill : DiscoveredSkill
            要注册的技能。

        Returns
        -------
        RegistrationResult
            注册结果。
        """
        result = RegistrationResult(
            skill_name=skill.name,
            domain=skill.domain,
            registered_at=datetime.utcnow().isoformat(),
        )

        # 1. 评估质量
        if skill.skill_value < 0.3:
            result.success = False
            result.message = f"技能价值太低 ({skill.skill_value:.2f})，跳过注册"
            return result

        # 2. 分配 CM 编号
        cm_id = f"CM-{self._next_cm_id}"
        result.cm_id = cm_id

        # 3. 创建触发关键词
        trigger_keywords = self._create_trigger_keywords(skill)
        result.trigger_keywords = trigger_keywords

        # 4. 设置置信度阈值
        threshold = self._calculate_threshold(skill)
        result.confidence_threshold = threshold

        # 5. 更新 DomainMap
        if skill.domain:
            self.domain_map.add_skill_to_domain(skill.name, skill.domain)

        # 6. 标记成功
        result.success = True
        result.message = f"已注册 {skill.name} 为 {cm_id}，领域={skill.domain}，阈值={threshold}"

        # 7. 递增 CM 编号
        self._next_cm_id += 1

        return result

    def batch_register(
        self, skills: list[DiscoveredSkill] | None = None, min_value: float = 0.5
    ) -> BatchRegistrationResult:
        """批量注册技能。

        Parameters
        ----------
        skills : list[DiscoveredSkill] | None
            要注册的技能列表。如果为 None，则自动发现高价值技能。
        min_value : float
            最低技能价值阈值。

        Returns
        -------
        BatchRegistrationResult
            批量注册结果。
        """
        if skills is None:
            skills = self.discovery.get_high_value_skills(min_value)

        batch_result = BatchRegistrationResult(total=len(skills))

        for skill in skills:
            reg_result = self.register_skill(skill)
            batch_result.results.append(reg_result)
            if reg_result.success:
                batch_result.successful += 1
            else:
                batch_result.failed += 1

        batch_result.next_cm_id = self._next_cm_id
        return batch_result

    def _create_trigger_keywords(self, skill: DiscoveredSkill) -> list[str]:
        """为技能创建触发关键词。"""
        keywords: list[str] = []

        # 1. 从技能名称提取关键词
        name_parts = skill.name.replace("-", " ").replace("_", " ").split()
        keywords.extend(name_parts[:3])

        # 2. 从描述提取关键词
        if skill.description:
            desc_words = skill.description.split()
            # 取描述中的关键名词
            for word in desc_words:
                if len(word) > 2 and word not in keywords:
                    keywords.append(word)
                if len(keywords) >= 6:
                    break

        # 3. 从领域信号词获取
        if skill.domain:
            domain_signals = self.domain_map.get_context_signals(skill.domain)
            keywords.extend(domain_signals[:3])

        # 去重并限制数量
        seen: set[str] = set()
        unique_keywords: list[str] = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)
            if len(unique_keywords) >= 8:
                break

        return unique_keywords

    def _calculate_threshold(self, skill: DiscoveredSkill) -> float:
        """计算置信度阈值。"""
        # 高价值技能 → 低阈值（更容易触发）
        # 低价值技能 → 高阈值（更难触发）
        if skill.skill_value >= 0.8:
            return 0.4
        if skill.skill_value >= 0.6:
            return 0.5
        if skill.skill_value >= 0.4:
            return 0.6
        return 0.7

    def generate_registration_code(self, result: RegistrationResult) -> dict[str, str]:
        """生成需要添加到 skill_router.py 的代码片段。

        Returns
        -------
        dict[str, str]
            {"registry_entry": "...", "tier_entry": "...", "cm_rule": "..."}
        """
        if not result.success:
            return {}

        # SKILL_REGISTRY 条目
        registry_entry = f'''    {{
        "name": "{result.skill_name}",
        "triggers": {result.trigger_keywords},
        "trigger_phrases": {result.trigger_keywords[:3]},
        "relevance": "high" if {result.confidence_threshold} <= 0.5 else "medium",
        "auto_invoke": False,
        "reason": "Auto-registered by AutoInstaller ({result.cm_id})",
    }},'''

        # INTEGRATION_TIERS 条目
        tier_entry = f'        "{result.skill_name}",'

        # CM_RULES_INTEGRATION 条目
        cm_rule = f'    "{result.cm_id}": ("{result.skill_name}", {result.trigger_keywords}, {result.confidence_threshold}),'

        return {
            "registry_entry": registry_entry,
            "tier_entry": tier_entry,
            "cm_rule": cm_rule,
        }

    def get_next_cm_id(self) -> str:
        """返回下一个可用的 CM 编号。"""
        return f"CM-{self._next_cm_id}"

    def get_registration_summary(self) -> dict[str, Any]:
        """获取注册摘要。"""
        return {
            "next_cm_id": self.get_next_cm_id(),
            "total_discovered": self.discovery.total_discovered(),
            "high_value_skills": len(self.discovery.get_high_value_skills()),
            "domains": self.domain_map.all_domains(),
        }
