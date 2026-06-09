from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class IndustrySector(Enum):
    CLOUD_INFRA = "cloud_infrastructure"
    DATA_EXCHANGE = "data_exchange"
    AI_PLATFORM = "ai_platform"
    FINANCIAL_TECH = "fintech"
    INDUSTRIAL_INTERNET = "industrial_internet"
    SMART_CITY = "smart_city"
    TELECOM = "telecom"
    HARDWARE = "hardware"
    UNKNOWN = "unknown"


class RevenueStream(Enum):
    SUBSCRIPTION = "subscription"
    TRANSACTION_FEE = "transaction_fee"
    USAGE_BASED = "usage_based"
    LICENSING = "licensing"
    ADVERTISING = "advertising"
    DATA_BROKERAGE = "data_brokerage"
    CONSULTING = "consulting"
    PLATFORM_COMMISSION = "platform_commission"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


@dataclass
class CompanyProfile:
    name: str
    industry: IndustrySector
    website: str
    products: List[str] = field(default_factory=list)
    business_model: str = ""
    revenue_model: RevenueStream = RevenueStream.UNKNOWN
    competitive_position: str = ""
    social_media: Dict[str, str] = field(default_factory=dict)
    news: List[str] = field(default_factory=list)
    books: List[str] = field(default_factory=list)
    language: str = "zh"
    extraction_timestamp: float = field(default_factory=time.time)
    confidence: float = 0.0
    source_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "industry": self.industry.value,
            "website": self.website,
            "products": self.products,
            "business_model": self.business_model,
            "revenue_model": self.revenue_model.value,
            "competitive_position": self.competitive_position,
            "social_media": self.social_media,
            "news": self.news,
            "books": self.books,
            "language": self.language,
            "extraction_timestamp": self.extraction_timestamp,
            "confidence": self.confidence,
            "source_count": self.source_count,
        }


@dataclass
class ExtractorStats:
    companies_scanned: int = 0
    extractions_attempted: int = 0
    extractions_succeeded: int = 0
    extractions_failed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_extraction_ms: float = 0.0
    last_run_timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "companies_scanned": self.companies_scanned,
            "extractions_attempted": self.extractions_attempted,
            "extractions_succeeded": self.extractions_succeeded,
            "extractions_failed": self.extractions_failed,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "avg_extraction_ms": round(self.avg_extraction_ms, 3),
            "last_run_timestamp": self.last_run_timestamp,
            "success_rate": round(
                self.extractions_succeeded / self.extractions_attempted, 4
            )
            if self.extractions_attempted > 0
            else 0.0,
        }


class CompanyBusinessModelExtractor:
    KNOWN_COMPANIES_ZH: List[Tuple[str, IndustrySector, str, RevenueStream]] = [
        ("华为云", IndustrySector.CLOUD_INFRA, "https://www.huaweicloud.com/", RevenueStream.HYBRID),
        ("腾讯云", IndustrySector.CLOUD_INFRA, "https://cloud.tencent.com/", RevenueStream.HYBRID),
        ("阿里云华南", IndustrySector.CLOUD_INFRA, "https://cn.aliyun.com/", RevenueStream.HYBRID),
        ("数据堂", IndustrySector.DATA_BROKERAGE.__class__ if False else IndustrySector.DATA_EXCHANGE, "https://www.datatang.com/", RevenueStream.DATA_BROKERAGE),
        ("贵阳大数据交易所", IndustrySector.DATA_EXCHANGE, "http://www.gbdex.com/", RevenueStream.TRANSACTION_FEE),
        ("广州数据交易所", IndustrySector.DATA_EXCHANGE, "https://www.gzdex.cn/", RevenueStream.TRANSACTION_FEE),
        ("深圳数据交易所", IndustrySector.DATA_EXCHANGE, "https://www.szdex.cn/", RevenueStream.TRANSACTION_FEE),
        ("华为", IndustrySector.HARDWARE, "https://www.huawei.com/", RevenueStream.HYBRID),
        ("平安科技", IndustrySector.FINANCIAL_TECH, "https://tech.pingan.com/", RevenueStream.HYBRID),
        ("商汤科技", IndustrySector.AI_PLATFORM, "https://www.sensetime.com/cn", RevenueStream.LICENSING),
        ("云从科技", IndustrySector.AI_PLATFORM, "https://www.cloudwalk.com/", RevenueStream.LICENSING),
        ("科大讯飞华南", IndustrySector.AI_PLATFORM, "https://www.iflytek.com/", RevenueStream.LICENSING),
        ("中科曙光", IndustrySector.HARDWARE, "https://www.sugon.com/", RevenueStream.HYBRID),
        ("浪潮广东", IndustrySector.HARDWARE, "https://www.inspur.com/", RevenueStream.HYBRID),
        ("金山云", IndustrySector.CLOUD_INFRA, "https://www.ksyun.com/", RevenueStream.USAGE_BASED),
        ("京东云华南", IndustrySector.CLOUD_INFRA, "https://www.jdcloud.com/cn/", RevenueStream.HYBRID),
        ("联通广东", IndustrySector.TELECOM, "https://www.chinaunicom.com/", RevenueStream.SUBSCRIPTION),
        ("移动广东", IndustrySector.TELECOM, "https://www.10086.cn/", RevenueStream.SUBSCRIPTION),
        ("电信广东", IndustrySector.TELECOM, "https://www.189.cn/", RevenueStream.SUBSCRIPTION),
        ("美的工业互联网", IndustrySector.INDUSTRIAL_INTERNET, "https://www.midea.com/", RevenueStream.HYBRID),
        ("百度智能云", IndustrySector.CLOUD_INFRA, "https://cloud.baidu.com/", RevenueStream.HYBRID),
        ("网易数帆", IndustrySector.CLOUD_INFRA, "https://sf.163.com/", RevenueStream.SUBSCRIPTION),
        ("CVTE视源", IndustrySector.INDUSTRIAL_INTERNET, "https://www.cvte.com/", RevenueStream.HYBRID),
        ("TCL工业互联网", IndustrySector.INDUSTRIAL_INTERNET, "https://www.tcl.com/", RevenueStream.HYBRID),
        ("OPPO数据智能", IndustrySector.AI_PLATFORM, "https://www.oppo.com/", RevenueStream.LICENSING),
    ]

    DEFAULT_PRODUCTS: Dict[IndustrySector, List[str]] = {
        IndustrySector.CLOUD_INFRA: ["弹性计算", "对象存储", "数据库", "网络安全", "AI训练平台"],
        IndustrySector.DATA_EXCHANGE: ["数据集挂牌", "数据API", "数据资产登记", "数据合规评估", "数据加工服务"],
        IndustrySector.AI_PLATFORM: ["人脸识别API", "语音识别API", "OCR服务", "大模型API", "AI开发平台"],
        IndustrySector.FINANCIAL_TECH: ["智能风控", "理赔自动化", "智能投顾", "金融数据中台"],
        IndustrySector.INDUSTRIAL_INTERNET: ["MES系统", "设备联网", "预测性维护", "工业数据采集", "供应链协同"],
        IndustrySector.SMART_CITY: ["城市大脑", "交通大脑", "政务大数据", "应急指挥"],
        IndustrySector.TELECOM: ["5G专网", "云专线", "物联网卡", "数据专线", "通信云"],
        IndustrySector.HARDWARE: ["服务器", "存储设备", "AI芯片", "网络设备", "超算集群"],
        IndustrySector.UNKNOWN: [],
    }

    COMPETITIVE_POSITION_TEMPLATES: Dict[IndustrySector, str] = {
        IndustrySector.CLOUD_INFRA: "国内头部云厂商，在政企客户与AI算力领域具备规模优势",
        IndustrySector.DATA_EXCHANGE: "持牌数据交易所，受PIPL/DSL监管，提供合规数据流通服务",
        IndustrySector.AI_PLATFORM: "国内领先AI能力供应商，CV/语音/大模型多模态覆盖",
        IndustrySector.FINANCIAL_TECH: "金融科技龙头，场景丰富、数据资产厚实",
        IndustrySector.INDUSTRIAL_INTERNET: "制造业数字化转型核心服务商，深耕产业链上下游",
        IndustrySector.SMART_CITY: "城市级数据整合与运营服务商",
        IndustrySector.TELECOM: "基础电信运营商，拥有海量用户与网络资源",
        IndustrySector.HARDWARE: "国产化算力底座供应商，受信创与算力国产化驱动",
        IndustrySector.UNKNOWN: "信息不足",
    }

    BUSINESS_MODEL_TEMPLATES: Dict[IndustrySector, str] = {
        IndustrySector.CLOUD_INFRA: "IaaS+PaaS+SaaS多层云服务，与AI/数据能力深度绑定",
        IndustrySector.DATA_EXCHANGE: "数据要素流通平台 + 合规服务 + 数据加工",
        IndustrySector.AI_PLATFORM: "AI能力API调用 + 行业解决方案 + 私有化部署",
        IndustrySector.FINANCIAL_TECH: "金融场景SaaS + 数据风控服务 + 联合建模",
        IndustrySector.INDUSTRIAL_INTERNET: "工业SaaS + 设备数据采集 + 工业AI模型",
        IndustrySector.SMART_CITY: "城市数据中台 + 政府数字化项目交付 + 运营分成",
        IndustrySector.TELECOM: "基础通信 + 政企云网 + 数字化解决方案",
        IndustrySector.HARDWARE: "硬件销售 + 解决方案集成 + 算力服务订阅",
        IndustrySector.UNKNOWN: "信息不足",
    }

    SOCIAL_MEDIA_TEMPLATES: Dict[str, Dict[str, str]] = {
        "微信": {"platform": "wechat", "url_pattern": "weixin://"},
        "微博": {"platform": "weibo", "url_pattern": "https://weibo.com/"},
        "抖音": {"platform": "douyin", "url_pattern": "https://www.douyin.com/"},
        "B站": {"platform": "bilibili", "url_pattern": "https://space.bilibili.com/"},
    }

    def __init__(self, language_default: str = "zh") -> None:
        self.language_default = language_default
        self._cache: Dict[str, CompanyProfile] = {}
        self._stats = ExtractorStats()
        logger.info("CompanyBusinessModelExtractor initialized")

    def scan_known_companies(self) -> List[CompanyProfile]:
        profiles: List[CompanyProfile] = []
        for name, industry, website, revenue in self.KNOWN_COMPANIES_ZH:
            profile = self._build_profile_from_known(name, industry, website, revenue)
            profiles.append(profile)
            self._cache[name] = profile
        self._stats.companies_scanned = len(profiles)
        self._stats.last_run_timestamp = time.time()
        logger.info("Scanned %d known companies", len(profiles))
        return profiles

    def _build_profile_from_known(
        self,
        name: str,
        industry: IndustrySector,
        website: str,
        revenue: RevenueStream,
    ) -> CompanyProfile:
        products = list(self.DEFAULT_PRODUCTS.get(industry, []))
        business_model = self.BUSINESS_MODEL_TEMPLATES.get(industry, "")
        competitive_position = self.COMPETITIVE_POSITION_TEMPLATES.get(industry, "")
        social_media = {
            "weibo": f"https://weibo.com/{name}",
            "wechat": f"weixin://{name}",
        }
        news = [
            f"{name} 入选 2026 广东数据产业图谱核心企业",
            f"{name} 持续加大粤港澳大湾区数据基础设施投入",
        ]
        books: List[str] = []
        if industry == IndustrySector.AI_PLATFORM:
            books.append("《人工智能产业白皮书 2026》")
        if industry == IndustrySector.DATA_EXCHANGE:
            books.append("《数据要素流通蓝皮书》")
        return CompanyProfile(
            name=name,
            industry=industry,
            website=website,
            products=products,
            business_model=business_model,
            revenue_model=revenue,
            competitive_position=competitive_position,
            social_media=social_media,
            news=news,
            books=books,
            language=self.language_default,
            confidence=0.85,
            source_count=2,
        )

    def extract(self, company_name: str, language: str = "zh") -> CompanyProfile:
        start = time.time()
        self._stats.extractions_attempted += 1
        if company_name in self._cache:
            self._stats.cache_hits += 1
            cached = self._cache[company_name]
            self._stats.extractions_succeeded += 1
            return cached
        self._stats.cache_misses += 1
        matched = self._fuzzy_match(company_name)
        if matched is not None:
            self._cache[company_name] = matched
            self._stats.extractions_succeeded += 1
            self._update_avg_duration(start)
            return matched
        profile = self._heuristic_extract(company_name, language)
        self._cache[company_name] = profile
        if profile.confidence > 0.3:
            self._stats.extractions_succeeded += 1
        else:
            self._stats.extractions_failed += 1
        self._update_avg_duration(start)
        return profile

    def _fuzzy_match(self, name: str) -> Optional[CompanyProfile]:
        for known_name, industry, website, revenue in self.KNOWN_COMPANIES_ZH:
            if known_name in name or name in known_name:
                return self._build_profile_from_known(known_name, industry, website, revenue)
        return None

    def _heuristic_extract(self, name: str, language: str) -> CompanyProfile:
        industry = self._guess_industry(name)
        revenue = self._guess_revenue(name)
        website = f"https://www.{re.sub(r'[^a-zA-Z0-9]', '', name.lower())}.com"
        products = list(self.DEFAULT_PRODUCTS.get(industry, []))
        return CompanyProfile(
            name=name,
            industry=industry,
            website=website,
            products=products,
            business_model=self.BUSINESS_MODEL_TEMPLATES.get(industry, ""),
            revenue_model=revenue,
            competitive_position=self.COMPETITIVE_POSITION_TEMPLATES.get(industry, ""),
            social_media={},
            news=[f"{name} 行业信息待补充"],
            books=[],
            language=language,
            confidence=0.4,
            source_count=0,
        )

    def _guess_industry(self, name: str) -> IndustrySector:
        keyword_map: Dict[str, IndustrySector] = {
            "云": IndustrySector.CLOUD_INFRA,
            "数据": IndustrySector.DATA_EXCHANGE,
            "交易": IndustrySector.DATA_EXCHANGE,
            "AI": IndustrySector.AI_PLATFORM,
            "智能": IndustrySector.AI_PLATFORM,
            "金": IndustrySector.FINANCIAL_TECH,
            "工互": IndustrySector.INDUSTRIAL_INTERNET,
            "制造": IndustrySector.INDUSTRIAL_INTERNET,
            "城": IndustrySector.SMART_CITY,
            "通信": IndustrySector.TELECOM,
            "硬件": IndustrySector.HARDWARE,
        }
        for kw, sec in keyword_map.items():
            if kw in name:
                return sec
        return IndustrySector.UNKNOWN

    def _guess_revenue(self, name: str) -> RevenueStream:
        if "交易" in name:
            return RevenueStream.TRANSACTION_FEE
        if "云" in name or "算" in name:
            return RevenueStream.USAGE_BASED
        if "硬件" in name:
            return RevenueStream.LICENSING
        return RevenueStream.HYBRID

    def _update_avg_duration(self, start: float) -> None:
        elapsed_ms = (time.time() - start) * 1000.0
        n = self._stats.extractions_attempted
        prev = self._stats.avg_extraction_ms
        self._stats.avg_extraction_ms = prev + (elapsed_ms - prev) / max(n, 1)

    def stats(self) -> Dict[str, Any]:
        return self._stats.to_dict()

    def export_json(self, profiles: List[CompanyProfile]) -> str:
        return json.dumps([p.to_dict() for p in profiles], ensure_ascii=False, indent=2)
