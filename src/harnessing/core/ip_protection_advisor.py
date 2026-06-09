"""
IP Protection Advisor
======================

Recommend dual-jurisdiction IP protection strategies for OPC operators in
HK + 廣州南沙區. Based on KB-39 + KB-40, covering:

- 6 strategies: A (軟著+公證) / B (商業秘密) / C (PCT 專利) /
                D (Open Source+商標) / E (Public+Prior Art) / F (Private+Mirror)
- Dependency analysis (互依性) — Rule 50 跨域協同
- Short/medium/long term roadmap
- ML model 7-dimension specific protection

Confidence: ✅ Verified (法規) + 🔍 Researched (市場策略)
Reference: KB-39, KB-40
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ProtectionStrategy(Enum):
    A_SOFTWARE_COPYRIGHT = "A_中國軟著+HK律師公證"
    B_TRADE_SECRET = "B_雙邊商業秘密（零外部依賴）"
    C_PCT_PATENT = "C_PCT國際專利"
    D_OPEN_SOURCE_TRADEMARK = "D_Open Source+商標"
    E_PUBLIC_PRIOR_ART = "E_GitHub Public+Prior Art"
    F_PRIVATE_MIRROR = "F_GitLab Private+Mirror"


class AssetType(Enum):
    SOURCE_CODE = "源代碼 (Source Code)"
    ML_MODEL_WEIGHTS = "ML 模型權重 (.pt/.bin)"
    ML_TRAINING_DATA = "訓練數據集"
    API_DEPLOYMENT = "API/部署代碼"
    BRAND_NAME = "品牌名稱 (EmoGlyph/BeeEmo)"
    TRAINING_METHOD = "微調方法/算法"


class Timeline(Enum):
    SHORT = "短期 (30 天內)"
    MEDIUM = "中期 (60-90 天)"
    LONG = "長期 (180+ 天)"


@dataclass
class IPCoverage:
    """IP protection coverage analysis"""
    strategy: ProtectionStrategy
    covered_assets: List[AssetType]
    jurisdictions: List[str]
    estimated_cost_rmb: int
    timeline_days: int
    protection_strength: str
    pros: List[str]
    cons: List[str]
    confidence: str
    reference: str


@dataclass
class RecommendationInput:
    """Input for IP protection recommendation"""
    target_assets: List[AssetType]
    has_novel_algorithm: bool = False
    is_open_source_intent: bool = False
    target_markets: List[str] = field(default_factory=lambda: ["HK", "中國"])
    budget_rmb: int = 50_000
    is_opc: bool = True


@dataclass
class RecommendationResult:
    """Recommendation output"""
    must_have: List[IPCoverage]
    strongly_recommended: List[IPCoverage]
    optional: List[IPCoverage]
    total_cost_rmb: int
    timeline_summary: Dict[str, List[str]]
    ml_model_protection: Dict[AssetType, List[ProtectionStrategy]]


class IPProtectionAdvisor:
    """Main IP protection advisor"""

    def get_strategy_coverage(self, strategy: ProtectionStrategy) -> IPCoverage:
        """Get detailed coverage info for each strategy"""
        coverage_map = {
            ProtectionStrategy.A_SOFTWARE_COPYRIGHT: IPCoverage(
                strategy=strategy,
                covered_assets=[AssetType.SOURCE_CODE, AssetType.API_DEPLOYMENT],
                jurisdictions=["中國", "HK"],
                estimated_cost_rmb=5000,
                timeline_days=45,
                protection_strength="🟢 高",
                pros=["成本低", "覆蓋兩地", "雙重舉證", "永久保護"],
                cons=["需時 30-60 天", "中國軟著須公開 60 頁源碼"],
                confidence="✅ Verified",
                reference="KB-39 § 2.1-2.3",
            ),
            ProtectionStrategy.B_TRADE_SECRET: IPCoverage(
                strategy=strategy,
                covered_assets=[
                    AssetType.SOURCE_CODE,
                    AssetType.ML_MODEL_WEIGHTS,
                    AssetType.ML_TRAINING_DATA,
                    AssetType.TRAINING_METHOD,
                ],
                jurisdictions=["中國", "HK", "國際"],
                estimated_cost_rmb=5000,
                timeline_days=1,
                protection_strength="🟡 中",
                pros=[
                    "零成本（技術措施）",
                    "立即生效",
                    "保護範圍廣",
                    "兩地通用",
                    "無公開",
                ],
                cons=["需舉證「合理保密措施」", "內部洩密難防", "需完整保密體系"],
                confidence="✅ Verified",
                reference="KB-39 § 3.1-3.3 + KB-40 § 1.B",
            ),
            ProtectionStrategy.C_PCT_PATENT: IPCoverage(
                strategy=strategy,
                covered_assets=[AssetType.TRAINING_METHOD, AssetType.SOURCE_CODE],
                jurisdictions=["中國", "HK", "美國（指定國）"],
                estimated_cost_rmb=50_000,
                timeline_days=900,
                protection_strength="🟢 最高",
                pros=["保護力度最高", "排他權", "可商業化（授權+轉讓+訴訟）"],
                cons=["成本高 ¥30,000+", "需時 2-3 年", "需新穎性", "會公開技術"],
                confidence="✅ Verified",
                reference="KB-39 § 5.1 + KB-40 § 1.C",
            ),
            ProtectionStrategy.D_OPEN_SOURCE_TRADEMARK: IPCoverage(
                strategy=strategy,
                covered_assets=[AssetType.SOURCE_CODE, AssetType.BRAND_NAME],
                jurisdictions=["中國", "HK", "國際（馬德里）"],
                estimated_cost_rmb=8000,
                timeline_days=270,
                protection_strength="🟡 中",
                pros=["建立社區", "品牌曝光", "防止搶註"],
                cons=["放棄代碼商業化", "商標維護成本", "License 須明確"],
                confidence="🔍 Researched",
                reference="KB-40 § 1.D",
            ),
            ProtectionStrategy.E_PUBLIC_PRIOR_ART: IPCoverage(
                strategy=strategy,
                covered_assets=[AssetType.SOURCE_CODE],
                jurisdictions=["全球（公知技術）"],
                estimated_cost_rmb=0,
                timeline_days=1,
                protection_strength="🟡 中",
                pros=["Prior Art 對抗專利流氓", "社區建設", "建立聲譽", "零成本"],
                cons=["放棄代碼商業化", "公開後難收回"],
                confidence="🔍 Researched",
                reference="KB-40 § 1.E",
            ),
            ProtectionStrategy.F_PRIVATE_MIRROR: IPCoverage(
                strategy=strategy,
                covered_assets=[AssetType.SOURCE_CODE, AssetType.ML_TRAINING_DATA],
                jurisdictions=["HK", "中國"],
                estimated_cost_rmb=3000,
                timeline_days=1,
                protection_strength="🟡 中",
                pros=["兩地異地備份", "私有代碼", "GitLab 訪問控制"],
                cons=["需 VPS 維護", "同步延遲"],
                confidence="🔍 Researched",
                reference="KB-40 § 1.F",
            ),
        }
        return coverage_map[strategy]

    def recommend(self, input_data: RecommendationInput) -> RecommendationResult:
        """Generate IP protection recommendation"""
        must_have = []
        strongly_recommended = []
        optional = []

        b_strategy = self.get_strategy_coverage(ProtectionStrategy.B_TRADE_SECRET)
        must_have.append(b_strategy)

        f_strategy = self.get_strategy_coverage(ProtectionStrategy.F_PRIVATE_MIRROR)
        if input_data.is_opc:
            strongly_recommended.append(f_strategy)
        else:
            must_have.append(f_strategy)

        if AssetType.SOURCE_CODE in input_data.target_assets:
            a_strategy = self.get_strategy_coverage(ProtectionStrategy.A_SOFTWARE_COPYRIGHT)
            strongly_recommended.append(a_strategy)

        if AssetType.BRAND_NAME in input_data.target_assets:
            d_strategy = self.get_strategy_coverage(
                ProtectionStrategy.D_OPEN_SOURCE_TRADEMARK
            )
            strongly_recommended.append(d_strategy)

        if input_data.has_novel_algorithm:
            c_strategy = self.get_strategy_coverage(ProtectionStrategy.C_PCT_PATENT)
            optional.append(c_strategy)

        if input_data.is_open_source_intent:
            e_strategy = self.get_strategy_coverage(ProtectionStrategy.E_PUBLIC_PRIOR_ART)
            optional.append(e_strategy)

        total_cost = sum(s.estimated_cost_rmb for s in must_have + strongly_recommended + optional)

        timeline_summary = {
            Timeline.SHORT.value: [
                f"✅ 策略 B 商業秘密（{b_strategy.estimated_cost_rmb} 元）",
                f"✅ 策略 F Private Mirror（{f_strategy.estimated_cost_rmb} 元）",
            ],
            Timeline.MEDIUM.value: [
                "✅ 策略 A 中國軟著 + HK 律師公證（~5,000 元）",
                "✅ 策略 D 中國商標 + HK 商標（~8,000 元）",
            ],
            Timeline.LONG.value: [
                "🔧 可選：策略 C PCT 專利（核心算法，~50,000 元）",
                "🔧 可選：馬德里商標（國際擴展）",
            ],
        }

        ml_model_protection = {
            AssetType.SOURCE_CODE: [
                ProtectionStrategy.A_SOFTWARE_COPYRIGHT,
                ProtectionStrategy.B_TRADE_SECRET,
            ],
            AssetType.ML_MODEL_WEIGHTS: [
                ProtectionStrategy.B_TRADE_SECRET,
            ],
            AssetType.ML_TRAINING_DATA: [
                ProtectionStrategy.B_TRADE_SECRET,
                ProtectionStrategy.F_PRIVATE_MIRROR,
            ],
            AssetType.API_DEPLOYMENT: [
                ProtectionStrategy.A_SOFTWARE_COPYRIGHT,
            ],
            AssetType.BRAND_NAME: [
                ProtectionStrategy.D_OPEN_SOURCE_TRADEMARK,
            ],
            AssetType.TRAINING_METHOD: [
                ProtectionStrategy.C_PCT_PATENT,
                ProtectionStrategy.B_TRADE_SECRET,
            ],
        }

        return RecommendationResult(
            must_have=must_have,
            strongly_recommended=strongly_recommended,
            optional=optional,
            total_cost_rmb=total_cost,
            timeline_summary=timeline_summary,
            ml_model_protection=ml_model_protection,
        )

    def check_dependency(
        self, strategy1: ProtectionStrategy, strategy2: ProtectionStrategy
    ) -> str:
        """檢查兩個策略嘅互依性"""
        complementary = [
            (ProtectionStrategy.A_SOFTWARE_COPYRIGHT, ProtectionStrategy.B_TRADE_SECRET),
            (ProtectionStrategy.B_TRADE_SECRET, ProtectionStrategy.C_PCT_PATENT),
            (ProtectionStrategy.A_SOFTWARE_COPYRIGHT, ProtectionStrategy.C_PCT_PATENT),
            (ProtectionStrategy.B_TRADE_SECRET, ProtectionStrategy.F_PRIVATE_MIRROR),
        ]
        conflicting = [
            (ProtectionStrategy.B_TRADE_SECRET, ProtectionStrategy.D_OPEN_SOURCE_TRADEMARK),
            (ProtectionStrategy.B_TRADE_SECRET, ProtectionStrategy.E_PUBLIC_PRIOR_ART),
            (ProtectionStrategy.D_OPEN_SOURCE_TRADEMARK, ProtectionStrategy.E_PUBLIC_PRIOR_ART),
        ]

        s = {strategy1, strategy2}
        for pair in complementary:
            if set(pair) == s:
                return "🟢 互補 (Complementary) - 推薦同時採用"
        for pair in conflicting:
            if set(pair) == s:
                return "⚠️ 衝突 (Conflicting) - 唔建議同時採用"
        return "🟡 並行 (Parallel) - 可同時採用但無明顯協同"


def demo():
    """示範用法"""
    advisor = IPProtectionAdvisor()

    print("=" * 60)
    print("BeeEmo 場景 IP 保護推薦")
    print("=" * 60)
    input_data = RecommendationInput(
        target_assets=[
            AssetType.SOURCE_CODE,
            AssetType.ML_MODEL_WEIGHTS,
            AssetType.BRAND_NAME,
        ],
        has_novel_algorithm=False,
        is_open_source_intent=True,
        target_markets=["HK", "中國", "亞洲"],
        budget_rmb=30_000,
        is_opc=True,
    )
    result = advisor.recommend(input_data)

    print(f"\n[必選] ({len(result.must_have)} 個)")
    for s in result.must_have:
        print(f"  - {s.strategy.value}: ~{s.estimated_cost_rmb} 元 ({s.protection_strength})")

    print(f"\n[強選] ({len(result.strongly_recommended)} 個)")
    for s in result.strongly_recommended:
        print(f"  - {s.strategy.value}: ~{s.estimated_cost_rmb} 元 ({s.protection_strength})")

    print(f"\n[可選] ({len(result.optional)} 個)")
    for s in result.optional:
        print(f"  - {s.strategy.value}: ~{s.estimated_cost_rmb} 元 ({s.protection_strength})")

    print(f"\n[總預估成本] ~{result.total_cost_rmb} 元")

    print("\n" + "=" * 60)
    print("ML 模型 7 維度保護對照")
    print("=" * 60)
    for asset, strategies in result.ml_model_protection.items():
        print(f"  {asset.value}: {[s.value.split('_')[0] for s in strategies]}")

    print("\n" + "=" * 60)
    print("互依性檢查")
    print("=" * 60)
    pairs_to_check = [
        (ProtectionStrategy.A_SOFTWARE_COPYRIGHT, ProtectionStrategy.B_TRADE_SECRET),
        (ProtectionStrategy.B_TRADE_SECRET, ProtectionStrategy.D_OPEN_SOURCE_TRADEMARK),
        (ProtectionStrategy.C_PCT_PATENT, ProtectionStrategy.B_TRADE_SECRET),
    ]
    for s1, s2 in pairs_to_check:
        print(f"  {s1.value} + {s2.value.split('_')[0]}...: {advisor.check_dependency(s1, s2)}")


# ====================================================================
# Extension Module: Filing Progress + Cost Estimation + ICS Calendar
# Added 2026-06-02 per spec `implement-opc-hk-nansha-cross-border-compliance`
# ====================================================================

def track_filing_progress() -> List[Dict]:
    """
    Track progress of all IP filings for BeeEmo OPC.

    Returns:
        List of filing progress dictionaries
    """
    return [
        {
            "id": "FIL-001",
            "name": "中國軟著 (BeeEmo Core)",
            "type": "Copyright",
            "agency": "中國版權保護中心",
            "start_date": "2026-07-15",
            "target_date": "2026-09-15",
            "estimated_completion": "2026-09-15",
            "progress_percent": 0,
            "current_step": "未開始",
            "next_step": "準備 60 頁源代碼",
            "blocker": "無",
            "status": "⏳ Pending",
        },
        {
            "id": "FIL-002",
            "name": "中國軟著 (EmoGlyph 5-Layer)",
            "type": "Copyright",
            "agency": "中國版權保護中心",
            "start_date": "2026-07-30",
            "target_date": "2026-09-30",
            "estimated_completion": "2026-09-30",
            "progress_percent": 0,
            "current_step": "未開始",
            "next_step": "準備 60 頁源代碼",
            "blocker": "無",
            "status": "⏳ Pending",
        },
        {
            "id": "FIL-003",
            "name": "中國軟著 (Harnessing Core)",
            "type": "Copyright",
            "agency": "中國版權保護中心",
            "start_date": "2026-08-10",
            "target_date": "2026-10-10",
            "estimated_completion": "2026-10-10",
            "progress_percent": 0,
            "current_step": "未開始",
            "next_step": "準備 60 頁源代碼",
            "blocker": "無",
            "status": "⏳ Pending",
        },
        {
            "id": "FIL-004",
            "name": "HK 律師公證 (源碼)",
            "type": "Notary",
            "agency": "HK 律師樓",
            "start_date": "2026-07-20",
            "target_date": "2026-07-20",
            "estimated_completion": "2026-07-27",
            "progress_percent": 0,
            "current_step": "未開始",
            "next_step": "揀選律師樓",
            "blocker": "無",
            "status": "⏳ Pending",
        },
        {
            "id": "FIL-005",
            "name": "HK 律師公證 (知識庫)",
            "type": "Notary",
            "agency": "HK 律師樓",
            "start_date": "2026-07-25",
            "target_date": "2026-07-25",
            "estimated_completion": "2026-08-01",
            "progress_percent": 0,
            "current_step": "未開始",
            "next_step": "揀選律師樓",
            "blocker": "無",
            "status": "⏳ Pending",
        },
        {
            "id": "FIL-006",
            "name": "HK 商標 (BeeEmo)",
            "type": "Trademark",
            "agency": "HK IPD",
            "start_date": "2026-08-15",
            "target_date": "2026-08-15",
            "estimated_completion": "2027-02-15",
            "progress_percent": 0,
            "current_step": "未開始",
            "next_step": "商標搜索",
            "blocker": "無",
            "status": "⏳ Pending",
        },
        {
            "id": "FIL-007",
            "name": "馬德里商標 (BeeEmo US+EU+JP)",
            "type": "Trademark (Intl)",
            "agency": "WIPO + 各國",
            "start_date": "2026-10-15",
            "target_date": "2027-10-15",
            "estimated_completion": "2027-10-15",
            "progress_percent": 0,
            "current_step": "未開始",
            "next_step": "取得基礎商標 (HK/China)",
            "blocker": "依賴 FIL-006",
            "status": "⏳ Optional",
        },
        {
            "id": "FIL-008",
            "name": "PCT 專利 (Emotion Inference)",
            "type": "Patent (Intl)",
            "agency": "WIPO + 各國",
            "start_date": "2026-12-15",
            "target_date": "2028-12-15",
            "estimated_completion": "2028-12-15",
            "progress_percent": 0,
            "current_step": "未開始",
            "next_step": "專利檢索",
            "blocker": "無",
            "status": "⏳ Optional",
        },
    ]


def estimate_total_cost(months: int = 12) -> Dict:
    """
    Estimate total IP filing cost over the next N months.

    Args:
        months: Number of months to estimate (default 12)

    Returns:
        Dictionary with cost breakdown by category and currency
    """
    return {
        "period_months": months,
        "categories": {
            "phase_a_immediate": {
                "description": "Phase A: 立即技術安全措施 (Week 1-2)",
                "cost_rmb": 0,
                "cost_hkd": 0,
                "cost_usd": 0,
                "external_deps": "None",
            },
            "phase_b_ip_registration": {
                "description": "Phase B: IP 登記 (M1-3)",
                "cost_rmb": 3000,
                "cost_hkd": 18000,
                "cost_usd": 0,
                "breakdown": {
                    "中國軟著 × 3 (自主)": {"rmb": 0, "hkd": 0, "usd": 0},
                    "HK 律師公證 × 2": {"rmb": 0, "hkd": 8000, "usd": 0},
                    "HK 商標 (Class 9+42)": {"rmb": 0, "hkd": 3000, "usd": 0},
                    "HK 律師商標代理 (可選)": {"rmb": 0, "hkd": 3000, "usd": 0},
                    "HK 商業秘密法律諮詢": {"rmb": 0, "hkd": 4000, "usd": 0},
                    "雜費 / 郵寄": {"rmb": 3000, "hkd": 0, "usd": 0},
                },
                "external_deps": "中國版權中心 + HK 律師 + HK IPD",
            },
            "phase_c_madrid_trademark": {
                "description": "Phase C: 馬德里商標 (M3-6, 可選)",
                "cost_rmb": 0,
                "cost_hkd": 0,
                "cost_usd": 5000,
                "breakdown": {
                    "WIPO 國際階段": {"rmb": 0, "hkd": 0, "usd": 1053},
                    "國家階段 (US+EU+JP)": {"rmb": 0, "hkd": 0, "usd": 4000},
                },
                "external_deps": "WIPO + 國際商標代理",
            },
            "phase_d_pct_patent": {
                "description": "Phase D: PCT 國際專利 (M6-12, 可選)",
                "cost_rmb": 0,
                "cost_hkd": 0,
                "cost_usd": 15000,
                "breakdown": {
                    "國際階段 (WIPO)": {"rmb": 0, "hkd": 0, "usd": 2500},
                    "國家階段 (1 國)": {"rmb": 0, "hkd": 0, "usd": 12500},
                },
                "external_deps": "WIPO + 國際專利代理",
            },
        },
        "totals": {
            "rmb": 3000,
            "hkd": 18000,
            "usd": 20000,
            "rmb_equivalent": 145000,  # 3000 + 18000*0.92 + 20000*7.0 ≈ 145,000
        },
        "scenarios": {
            "conservative": {
                "description": "只做 Phase A + B (推薦 OPC 規模)",
                "cost_rmb": 3000,
                "cost_hkd": 18000,
                "cost_usd": 0,
                "rmb_equivalent": 19560,
            },
            "moderate": {
                "description": "Phase A + B + C (含馬德里商標)",
                "cost_rmb": 3000,
                "cost_hkd": 18000,
                "cost_usd": 5000,
                "rmb_equivalent": 54560,
            },
            "complete": {
                "description": "Phase A + B + C + D (含 PCT 專利)",
                "cost_rmb": 3000,
                "cost_hkd": 18000,
                "cost_usd": 20000,
                "rmb_equivalent": 164560,
            },
        },
    }


def generate_filing_calendar(months: int = 12) -> str:
    """
    Generate ICS (iCalendar) format file content for IP filing deadlines.

    Args:
        months: Number of months to include in calendar

    Returns:
        ICS format string ready to save as .ics file
    """
    filings = track_filing_progress()

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//BeeEmo OPC//IP Filing Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for filing in filings:
        if filing["status"] == "⏳ Optional" and months < 6:
            continue
        target_date = filing["target_date"].replace("-", "")
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"UID:{filing['id']}@beeemo-opc.com",
            f"DTSTAMP:20260602T000000Z",
            f"DTSTART;VALUE=DATE:{target_date}",
            f"SUMMARY:{filing['name']} (Due)",
            f"DESCRIPTION:Type: {filing['type']}\\nAgency: {filing['agency']}\\n"
            f"Status: {filing['status']}\\nNext Step: {filing['next_step']}",
            f"LOCATION:{filing['agency']}",
            "PRIORITY:5",
            "STATUS:NEEDS-ACTION",
            "END:VEVENT",
        ])

    ics_lines.append("END:VCALENDAR")
    return "\r\n".join(ics_lines) + "\r\n"


def generate_m1_m6_action_items(month: str) -> dict:
    """
    Generate action items for a given month in the M1-M6 IP filing roadmap.

    Args:
        month: Month identifier like "M1", "M2", etc.

    Returns:
        Dict with keys: "month", "tasks", "budget", "dependencies"
    """
    roadmap = {
        "M1": {
            "month": "M1",
            "tasks": [
                {"name": "中國軟著申請 (3產品)", "products": ["BeeEmo Core", "EmoGlyph 5-Layer", "Harnessing Core"], "action": "提交中國版權保護中心軟著登記"},
            ],
            "budget": {"cny": 1100, "hkd": 0},
            "dependencies": [],
        },
        "M2": {
            "month": "M2",
            "tasks": [
                {"name": "HK 律師公證", "products": ["源碼", "知識庫"], "action": "揀選 HK 律師樓辦理源碼及知識庫公證"},
            ],
            "budget": {"cny": 0, "hkd": 9000},
            "dependencies": ["M1"],
        },
        "M3": {
            "month": "M3",
            "tasks": [
                {"name": "HK 商標提交", "products": ["BeeEmo"], "action": "向 HK IPD 提交商標申請 (Class 9+42)"},
                {"name": "軟著取得", "products": ["BeeEmo Core", "EmoGlyph 5-Layer", "Harnessing Core"], "action": "確認中國軟著登記證書"},
                {"name": "馬德里決策", "products": ["BeeEmo"], "action": "決定是否申請馬德里國際商標 (US+EU+JP)"},
            ],
            "budget": {"cny": 0, "hkd": 3300},
            "dependencies": ["M1", "M2"],
        },
        "M4": {
            "month": "M4",
            "tasks": [
                {"name": "馬德里商標申請 (可選)", "products": ["BeeEmo"], "action": "通過 WIPO 提交馬德里國際商標申請"},
            ],
            "budget": {"cny": 0, "hkd": 25000},
            "dependencies": ["M3"],
        },
        "M5": {
            "month": "M5",
            "tasks": [
                {"name": "馬德里跟進 (可選)", "products": ["BeeEmo"], "action": "跟進馬德里商標國際階段審查進度"},
            ],
            "budget": {"cny": 0, "hkd": 0},
            "dependencies": ["M4"],
        },
        "M6": {
            "month": "M6",
            "tasks": [
                {"name": "PCT 國際專利 (可選)", "products": ["Emotion Inference"], "action": "通過 WIPO 提交 PCT 國際專利申請"},
            ],
            "budget": {"cny": 0, "hkd": 70000},
            "dependencies": ["M3"],
        },
    }
    return roadmap.get(month, {"month": month, "tasks": [], "budget": {}, "dependencies": []})


def demo_extended() -> None:
    """Demo the new extended methods"""
    print("=" * 60)
    print("🔧 IP Protection Advisor — Extended Demo")
    print("=" * 60)

    print("\n【1】 Filing Progress")
    progress = track_filing_progress()
    for p in progress[:5]:
        print(f"  {p['id']}: {p['name']} | {p['status']} ({p['progress_percent']}%)")

    print("\n【2】 Cost Estimation (12 months)")
    cost = estimate_total_cost(months=12)
    print(f"  Conservative: ¥{cost['scenarios']['conservative']['rmb_equivalent']:,}")
    print(f"  Moderate:     ¥{cost['scenarios']['moderate']['rmb_equivalent']:,}")
    print(f"  Complete:     ¥{cost['scenarios']['complete']['rmb_equivalent']:,}")

    print("\n【3】 Filing Calendar (ICS format, first 5 events)")
    ics = generate_filing_calendar(months=12)
    ics_events = [l for l in ics.split("\r\n") if l.startswith("SUMMARY:")][:5]
    for event in ics_events:
        print(f"  {event}")

    print("\n" + "=" * 60)
    print("✅ Extended demo completed")
    print("=" * 60)


if __name__ == "__main__":
    demo()
    print("\n" + "=" * 60 + "\n")
    demo_extended()
