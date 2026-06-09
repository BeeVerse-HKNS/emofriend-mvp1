from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .company_business_model_extractor import CompanyProfile, IndustrySector, RevenueStream

logger = logging.getLogger(__name__)


class ProposalCategory(Enum):
    DATA_BROKER = "data_brokerage"
    INDUSTRY_AI = "industry_ai_assistant"
    COMPLIANCE_AUDIT = "compliance_audit"
    EXCHANGE_OPERATOR = "data_exchange_operator"
    CROSS_BORDER_FLOW = "cross_border_data_flow"
    CLEANROOM = "data_cleanroom"
    DATASPACE = "industrial_dataspace"
    COMPUTE_BROKER = "compute_broker"
    AGENT_MARKETPLACE = "agent_marketplace"
    SYNTHETIC_DATA = "synthetic_data_factory"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class BusinessProposal:
    id: str
    title: str
    category: ProposalCategory
    target_customer: str
    value_proposition: str
    revenue_model: str
    competitive_moat: str
    mvp_scope: List[str]
    regulatory_considerations: List[str]
    source_companies: List[str] = field(default_factory=list)
    confidence: float = 0.0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    novelty_score: float = 0.0
    formula: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category.value,
            "target_customer": self.target_customer,
            "value_proposition": self.value_proposition,
            "revenue_model": self.revenue_model,
            "competitive_moat": self.competitive_moat,
            "mvp_scope": self.mvp_scope,
            "regulatory_considerations": self.regulatory_considerations,
            "source_companies": self.source_companies,
            "confidence": self.confidence,
            "risk_level": self.risk_level.value,
            "novelty_score": self.novelty_score,
            "formula": self.formula,
            "timestamp": self.timestamp,
        }


@dataclass
class SynthesizerStats:
    proposals_generated: int = 0
    synthesis_runs: int = 0
    avg_proposals_per_run: float = 0.0
    avg_novelty_score: float = 0.0
    last_run_timestamp: float = 0.0
    source_companies_processed: int = 0
    formula_invocations: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposals_generated": self.proposals_generated,
            "synthesis_runs": self.synthesis_runs,
            "avg_proposals_per_run": round(self.avg_proposals_per_run, 3),
            "avg_novelty_score": round(self.avg_novelty_score, 3),
            "last_run_timestamp": self.last_run_timestamp,
            "source_companies_processed": self.source_companies_processed,
            "formula_invocations": dict(self.formula_invocations),
        }


class NewBusinessModelSynthesizer:
    BASE_FORMULAS: List[Tuple[str, ProposalCategory, str, RiskLevel, float]] = [
        (
            "F1: D + B + C",
            ProposalCategory.DATA_BROKER,
            "Data Broker for SMEs — 通用行业数据集标准化分发 + 合规包",
            RiskLevel.LOW,
            0.62,
        ),
        (
            "F2: I * A + R",
            ProposalCategory.INDUSTRY_AI,
            "Industry-specific AI Assistant — 行业知识 + 私域数据 + 模型微调",
            RiskLevel.MEDIUM,
            0.74,
        ),
        (
            "F3: G * S + K^H",
            ProposalCategory.COMPLIANCE_AUDIT,
            "Data Compliance Audit Service — PIPL/DSL自动化合规扫描 + 整改",
            RiskLevel.MEDIUM,
            0.78,
        ),
        (
            "F4: E * T + D^C",
            ProposalCategory.EXCHANGE_OPERATOR,
            "Vertical Data Exchange Operator — 单一行业数据交易运营",
            RiskLevel.MEDIUM,
            0.69,
        ),
        (
            "F5: X + E * (K+C)",
            ProposalCategory.CROSS_BORDER_FLOW,
            "Cross-Border Data Flow Bridge — 标准合同 + 跨境通道 + 法律服务",
            RiskLevel.HIGH,
            0.85,
        ),
        (
            "F6: D ⊕ M + P",
            ProposalCategory.CLEANROOM,
            "Data Cleanroom Platform — 数据不动模型动 + 联邦学习",
            RiskLevel.MEDIUM,
            0.81,
        ),
        (
            "F7: I^C + M * S",
            ProposalCategory.DATASPACE,
            "Industrial Dataspace Operator — 工业数据空间 + 设备孪生",
            RiskLevel.MEDIUM,
            0.73,
        ),
        (
            "F8: C^H + T * R",
            ProposalCategory.COMPUTE_BROKER,
            "Compute Broker for AI Startups — 算力调度 + 国产芯片适配",
            RiskLevel.MEDIUM,
            0.71,
        ),
        (
            "F9: A * M + G/S",
            ProposalCategory.AGENT_MARKETPLACE,
            "Vertical Agent Marketplace — 行业Agent上架 + 调用计费",
            RiskLevel.MEDIUM,
            0.77,
        ),
        (
            "F10: S * K + G/A",
            ProposalCategory.SYNTHETIC_DATA,
            "Synthetic Data Factory — 行业合成数据 + 隐私保护 + 模型训练",
            RiskLevel.LOW,
            0.79,
        ),
    ]

    MVP_SCOPE_TEMPLATES: Dict[ProposalCategory, List[str]] = {
        ProposalCategory.DATA_BROKER: [
            "数据商品化模板",
            "API计费系统",
            "合规包生成器",
            "买家自助门户",
        ],
        ProposalCategory.INDUSTRY_AI: [
            "行业知识库",
            "私域向量库",
            "Agent编排框架",
            "微信小程序入口",
        ],
        ProposalCategory.COMPLIANCE_AUDIT: [
            "PIPL/DSL扫描器",
            "数据资产清单自动生成",
            "合规报告PDF",
            "整改跟踪看板",
        ],
        ProposalCategory.EXCHANGE_OPERATOR: [
            "数据登记系统",
            "智能合约撮合",
            "清算结算",
            "数据出境通道",
        ],
        ProposalCategory.CROSS_BORDER_FLOW: [
            "SCC标准合同",
            "出境评估",
            "可信通道(TLS+审计)",
            "法律服务对接",
        ],
        ProposalCategory.CLEANROOM: [
            "多方安全计算节点",
            "联邦学习任务调度",
            "审计日志",
            "结果水印",
        ],
        ProposalCategory.DATASPACE: [
            "工业设备数据接入",
            "数据空间ID注册",
            "使用控制策略",
            "计费与清算",
        ],
        ProposalCategory.COMPUTE_BROKER: [
            "国产芯片资源池",
            "调度器",
            "成本优化器",
            "开发者门户",
        ],
        ProposalCategory.AGENT_MARKETPLACE: [
            "Agent上架审核",
            "调用计费",
            "评价系统",
            "分发SDK",
        ],
        ProposalCategory.SYNTHETIC_DATA: [
            "行业数据生成器",
            "差分隐私引擎",
            "质量评估",
            "API服务",
        ],
    }

    REGULATORY_TEMPLATES: Dict[ProposalCategory, List[str]] = {
        ProposalCategory.DATA_BROKER: ["数据来源合法性", "个人信息告知"],
        ProposalCategory.INDUSTRY_AI: ["行业数据合规", "模型备案"],
        ProposalCategory.COMPLIANCE_AUDIT: ["律师事务所合作", "审计资质"],
        ProposalCategory.EXCHANGE_OPERATOR: ["数据交易所牌照", "反垄断"],
        ProposalCategory.CROSS_BORDER_FLOW: ["数据出境安全评估", "SCC合同"],
        ProposalCategory.CLEANROOM: ["数据不出域证明", "密码评估"],
        ProposalCategory.DATASPACE: ["工业数据分类分级", "使用权控制"],
        ProposalCategory.COMPUTE_BROKER: ["算力国产化合规", "能耗双控"],
        ProposalCategory.AGENT_MARKETPLACE: ["算法备案", "内容审核"],
        ProposalCategory.SYNTHETIC_DATA: ["合成数据标识", "防深度伪造"],
    }

    TARGET_CUSTOMER_TEMPLATES: Dict[ProposalCategory, str] = {
        ProposalCategory.DATA_BROKER: "中小制造企业、零售连锁、本地服务商",
        ProposalCategory.INDUSTRY_AI: "垂直行业SMB（餐饮/物流/医美/教培）",
        ProposalCategory.COMPLIANCE_AUDIT: "上市公司、金融机构、跨国企业中国子公司",
        ProposalCategory.EXCHANGE_OPERATOR: "产业链核心企业（汽车、能源、装备）",
        ProposalCategory.CROSS_BORDER_FLOW: "外贸企业、跨境电商、跨境制造",
        ProposalCategory.CLEANROOM: "金融联合风控、医疗联合研究、零售联合营销",
        ProposalCategory.DATASPACE: "电子制造、汽车零部件、家电",
        ProposalCategory.COMPUTE_BROKER: "AI初创团队、高校实验室",
        ProposalCategory.AGENT_MARKETPLACE: "企业IT部门、SI集成商",
        ProposalCategory.SYNTHETIC_DATA: "数据短缺行业的算法团队",
    }

    MOAT_TEMPLATES: Dict[ProposalCategory, str] = {
        ProposalCategory.DATA_BROKER: "本地化数据源 + 合规包 + 渠道分销",
        ProposalCategory.INDUSTRY_AI: "行业Know-How + 私域数据壁垒",
        ProposalCategory.COMPLIANCE_AUDIT: "持牌律所合作 + 自动化工具 + 报告体系",
        ProposalCategory.EXCHANGE_OPERATOR: "牌照壁垒 + 撮合网络效应",
        ProposalCategory.CROSS_BORDER_FLOW: "HK↔南沙双边通道 + 法律+技术复合能力",
        ProposalCategory.CLEANROOM: "密码学工程能力 + 跨方接入",
        ProposalCategory.DATASPACE: "工业协议接入 + ID注册中心",
        ProposalCategory.COMPUTE_BROKER: "国产芯片适配 + 价格优势",
        ProposalCategory.AGENT_MARKETPLACE: "Agent质量审核 + 流量分发",
        ProposalCategory.SYNTHETIC_DATA: "差分隐私核心算法 + 行业模板",
    }

    REVENUE_TEMPLATES: Dict[ProposalCategory, str] = {
        ProposalCategory.DATA_BROKER: "数据商品GMV抽佣5-15% + 订阅费",
        ProposalCategory.INDUSTRY_AI: "按调用量计费 + 私有化部署License",
        ProposalCategory.COMPLIANCE_AUDIT: "项目制审计费 + SaaS订阅",
        ProposalCategory.EXCHANGE_OPERATOR: "交易手续费 + 增值服务费",
        ProposalCategory.CROSS_BORDER_FLOW: "通道使用费 + 增值法律服务",
        ProposalCategory.CLEANROOM: "任务调度费 + 结果分成",
        ProposalCategory.DATASPACE: "接入费 + 使用费 + 数据增值",
        ProposalCategory.COMPUTE_BROKER: "算力时费 + 调度服务费",
        ProposalCategory.AGENT_MARKETPLACE: "分发佣金 + 广告位",
        ProposalCategory.SYNTHETIC_DATA: "数据集订阅 + 定制化服务",
    }

    EXISTING_PROJECTS: List[str] = [
        "Harnessing Master Agent",
        "BeeVerse Ollama",
        "Linkedin Builder",
        "Agent Project",
        "Knowledge Base Engine",
    ]

    def __init__(self, seed: Optional[int] = None) -> None:
        self._seed = seed if seed is not None else int(time.time()) % 100000
        self._stats = SynthesizerStats()
        self._generated: List[BusinessProposal] = []
        logger.info("NewBusinessModelSynthesizer initialized (seed=%d)", self._seed)

    def synthesize(
        self,
        companies: List[CompanyProfile],
        num_proposals: int = 3,
    ) -> List[BusinessProposal]:
        self._stats.synthesis_runs += 1
        self._stats.source_companies_processed += len(companies)
        existing_categories = self._detect_existing_categories(companies)
        candidates: List[BusinessProposal] = []
        for formula, category, title, risk, novelty in self.BASE_FORMULAS:
            if category in existing_categories and num_proposals <= len(self.BASE_FORMULAS) // 2:
                continue
            proposal = self._build_proposal(formula, category, title, risk, novelty, companies)
            candidates.append(proposal)
            self._stats.formula_invocations[formula] = (
                self._stats.formula_invocations.get(formula, 0) + 1
            )
        candidates.sort(key=lambda p: p.novelty_score, reverse=True)
        chosen = candidates[:max(1, num_proposals)]
        self._generated.extend(chosen)
        self._stats.proposals_generated += len(chosen)
        self._update_averages(chosen)
        self._stats.last_run_timestamp = time.time()
        logger.info("Synthesized %d proposals (run %d)", len(chosen), self._stats.synthesis_runs)
        return chosen

    def _detect_existing_categories(self, companies: List[CompanyProfile]) -> List[ProposalCategory]:
        cat: List[ProposalCategory] = []
        sector_set = {c.industry for c in companies}
        if IndustrySector.DATA_EXCHANGE in sector_set:
            cat.append(ProposalCategory.EXCHANGE_OPERATOR)
        if IndustrySector.AI_PLATFORM in sector_set:
            cat.append(ProposalCategory.INDUSTRY_AI)
        if IndustrySector.CLOUD_INFRA in sector_set:
            cat.append(ProposalCategory.COMPUTE_BROKER)
        if IndustrySector.FINANCIAL_TECH in sector_set:
            cat.append(ProposalCategory.CLEANROOM)
        return cat

    def _build_proposal(
        self,
        formula: str,
        category: ProposalCategory,
        title: str,
        risk: RiskLevel,
        novelty: float,
        companies: List[CompanyProfile],
    ) -> BusinessProposal:
        source_names = [c.name for c in companies[:5]]
        return BusinessProposal(
            id=f"PROP-{uuid.uuid4().hex[:8]}",
            title=title,
            category=category,
            target_customer=self.TARGET_CUSTOMER_TEMPLATES[category],
            value_proposition=self._generate_value_prop(category, companies),
            revenue_model=self.REVENUE_TEMPLATES[category],
            competitive_moat=self.MOAT_TEMPLATES[category],
            mvp_scope=list(self.MVP_SCOPE_TEMPLATES[category]),
            regulatory_considerations=list(self.REGULATORY_TEMPLATES[category]),
            source_companies=source_names,
            confidence=0.7,
            risk_level=risk,
            novelty_score=novelty,
            formula=formula,
        )

    def _generate_value_prop(
        self, category: ProposalCategory, companies: List[CompanyProfile]
    ) -> str:
        anchors = [c.name for c in companies[:3]]
        anchor_str = "、".join(anchors) if anchors else "本地数据生态"
        templates: Dict[ProposalCategory, str] = {
            ProposalCategory.DATA_BROKER: f"以{anchor_str}为锚，构建广东本地SMB数据流通网络，把价格打到中小商户可承受水位",
            ProposalCategory.INDUSTRY_AI: f"基于{anchor_str}的行业Know-How，提供开箱即用垂直行业Agent",
            ProposalCategory.COMPLIANCE_AUDIT: f"对接{anchor_str}的合规体系，提供PIPL/DSL一站式审计SaaS",
            ProposalCategory.EXCHANGE_OPERATOR: f"在{anchor_str}所在产业链上运营垂直数据交易所",
            ProposalCategory.CROSS_BORDER_FLOW: f"利用{anchor_str}的HK/南沙双边资源，提供低成本跨境数据通道",
            ProposalCategory.CLEANROOM: f"联动{anchor_str}的算力与数据资源，提供数据不出域的联合建模服务",
            ProposalCategory.DATASPACE: f"在{anchor_str}等制造业场景落地工业数据空间，使用控制+计费",
            ProposalCategory.COMPUTE_BROKER: f"整合{anchor_str}等云厂商国产算力池，提供低价AI算力调度",
            ProposalCategory.AGENT_MARKETPLACE: f"依托{anchor_str}生态构建垂直Agent市场，按调用分成",
            ProposalCategory.SYNTHETIC_DATA: f"基于{anchor_str}的模型能力提供行业合成数据，规避数据获取难题",
        }
        return templates[category]

    def _update_averages(self, chosen: List[BusinessProposal]) -> None:
        n = self._stats.synthesis_runs
        prev_p = self._stats.avg_proposals_per_run
        prev_n = self._stats.avg_novelty_score
        if chosen:
            self._stats.avg_proposals_per_run = prev_p + (len(chosen) - prev_p) / n
            avg_novelty = sum(p.novelty_score for p in chosen) / len(chosen)
            self._stats.avg_novelty_score = prev_n + (avg_novelty - prev_n) / n

    def explain_novelty(self, proposal: BusinessProposal) -> str:
        conflicts = []
        title_lower = proposal.title.lower()
        for proj in self.EXISTING_PROJECTS:
            if proj.lower().split()[0] in title_lower:
                conflicts.append(proj)
        if not conflicts:
            return f"与现有项目（{', '.join(self.EXISTING_PROJECTS)}）不重叠，方向独立"
        return f"与 {', '.join(conflicts)} 存在主题重叠，需要差异化定位"

    def stats(self) -> Dict[str, Any]:
        return self._stats.to_dict()

    def export_json(self, proposals: Optional[List[BusinessProposal]] = None) -> str:
        proposals = proposals if proposals is not None else self._generated
        return json.dumps([p.to_dict() for p in proposals], ensure_ascii=False, indent=2)
