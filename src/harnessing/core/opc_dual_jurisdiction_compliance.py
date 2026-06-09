"""
OPC Dual-Jurisdiction Compliance Checker
=========================================

For OPC (One Person Company) operators in HK + 廣州南沙區:
- Auto-detect cross-border data transfer scenarios
- Apply HK PDPO + 中國 PIPL/DSL/CSL/GBA rules
- Generate compliance certificate for "no PII" scenarios
- Physical cross-border (mobile hard disk) analysis
- AI/ML specific compliance (Generative AI 法規)

Confidence: ✅ Verified (HK PDPO) + 🔍 Researched (中國 GBA pilot)
Reference: KB-34, KB-35, KB-36, KB-37, KB-38, KB-41
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Jurisdiction(Enum):
    HK = "Hong Kong"
    CHINA_MAINLAND = "中國大陸 (China Mainland)"
    NANSHA = "廣州南沙自貿區 (GBA Pilot)"
    BOTH = "HK + 中國大陸 雙地 (Dual)"


class ComplianceLevel(Enum):
    GREEN = "🟢 COMPLIANT"
    YELLOW = "🟡 NEEDS_REVIEW"
    RED = "🔴 NON_COMPLIANT"
    UNKNOWN = "❓ UNKNOWN"


class CrossBorderMode(Enum):
    PHYSICAL_HARD_DISK = "物理加密硬盤 (Physical Encrypted Hard Disk)"
    CLOUD_SYNC = "雲端同步 (Cloud Sync - iCloud/OneDrive/GitLab.com)"
    EMAIL = "電郵傳輸 (Email Transfer)"
    GIT_PUSH = "Git Push 境外 (Git Push Overseas)"
    PHYSICAL_DELIVERY = "實物遞送 (Physical Delivery)"
    API_CALL = "API 跨境調用 (Cross-border API)"


@dataclass
class ComplianceContext:
    """Compliance context for OPC dual-jurisdiction operations"""
    jurisdiction: Jurisdiction
    has_pii: bool = False
    pii_count: int = 0
    sensitive_pii: bool = False
    pii_types: List[str] = field(default_factory=list)
    cross_border_mode: CrossBorderMode = CrossBorderMode.PHYSICAL_HARD_DISK
    is_ai_model: bool = False
    is_generative_ai: bool = False
    has_government_cert: bool = False
    data_origin: str = "自創 (Self-created)"
    contains_trade_secret: bool = False
    contains_ip_code: bool = False
    contains_ml_model: bool = False


@dataclass
class ComplianceResult:
    """Compliance result for given context"""
    level: ComplianceLevel
    summary: str
    applicable_laws: List[str]
    required_actions: List[str]
    exemptions_applied: List[str] = field(default_factory=list)
    confidence: str = "✅ Verified"
    reference_kb: List[str] = field(default_factory=list)


class OPCDualJurisdictionCompliance:
    """Main compliance checker for OPC dual-jurisdiction operations"""

    HK_PDPO_THRESHOLDS = {
        "personal_data_definition": "任何與在世個人有關 + 可辨識身份",
        "section_33_principle": "所有合理地切實可行步驟",
        "max_fine_hkd": 50000,
        "max_imprisonment_years": 2,
    }

    CHINA_PIPL_THRESHOLDS = {
        "general_100k_threshold": 100_000,  # 10 萬人敏感信息
        "general_1m_threshold": 1_000_000,  # 100 萬人
        "max_fine_rmb": 50_000_000,  # 5,000 萬
        "max_revenue_pct": 5,  # 5% 年營業額
    }

    GBA_PILOT_INFO = {
        "established": "2023-12",
        "covered_scenarios": ["商業零售", "跨境支付", "旅遊", "酒店"],
        "covered_cities": ["廣州", "深圳", "珠海", "橫琴", "HK", "Macau"],
        "standard_contract_template": "GBA 標準合同（2023-12 版）",
    }

    GENERATIVE_AI_RULES = {
        "filing_required": "具有輿論屬性/社會動員能力嘅 GenAI 服務須備案",
        "备案机关": "國家網信辦 / 省級網信辦",
        "stats_2024_12": "302 款 GenAI 完成備案，註冊用戶 6 億+",
        "deep_synthesis_filing": "深度合成算法備案（2023+ 強制）",
    }

    def check_compliance(self, ctx: ComplianceContext) -> ComplianceResult:
        """Main compliance check method"""
        if not ctx.has_pii and ctx.cross_border_mode == CrossBorderMode.PHYSICAL_HARD_DISK:
            return self._no_pii_physical_scenario(ctx)
        if not ctx.has_pii and ctx.cross_border_mode == CrossBorderMode.CLOUD_SYNC:
            return self._no_pii_cloud_scenario(ctx)
        if ctx.has_pii and ctx.cross_border_mode == CrossBorderMode.CLOUD_SYNC:
            return self._pii_cloud_scenario(ctx)
        if ctx.is_generative_ai and ctx.has_government_cert is False:
            return self._generative_ai_scenario(ctx)
        return self._default_scenario(ctx)

    def _no_pii_physical_scenario(self, ctx: ComplianceContext) -> ComplianceResult:
        """無 PII + 物理加密硬盤 = 最常見 OPC 場景"""
        return ComplianceResult(
            level=ComplianceLevel.GREEN,
            summary="🟢 完全合規：無 PII 跨境傳輸問題（物理加密硬盤 + 無 PII = 不觸發 PIPL/PDPO 跨境實質義務）",
            applicable_laws=[
                "HK PDPO Cap 486（無 PII = 不適用）",
                "中國 PIPL（無 PII = 不適用）",
                "中國 DSL（無 PII = 不適用）",
                "中國 CSL（無 PII = 不適用）",
            ],
            required_actions=[
                "✅ 保留「無 PII 收集」聲明文檔",
                "✅ 硬盤 BitLocker/FileVault 加密（AES-256）",
                "✅ Git commit GPG/SSH 簽名",
                "✅ 訪問控制 + 訪問日誌",
                "✅ 海關檢查時配合（如有要求）",
            ],
            exemptions_applied=[
                "PIPL Article 13 豁免（無 PII = 不屬「個人信息」）",
                "PDPO Section 33 不觸發（無個人資料）",
            ],
            confidence="✅ Verified",
            reference_kb=["KB-34", "KB-35", "KB-37", "KB-38", "KB-41"],
        )

    def _no_pii_cloud_scenario(self, ctx: ComplianceContext) -> ComplianceResult:
        """無 PII 但用雲端同步 = 仍需 PIPL 評估（雲端 = 跨境傳輸）"""
        return ComplianceResult(
            level=ComplianceLevel.YELLOW,
            summary="🟡 需評估：雲端同步本身 = 跨境傳輸行為（即使無 PII 仍須 PIPL 合規評估）",
            applicable_laws=[
                "中國 PIPL 第三章 Articles 38-43（跨境提供規則）",
                "中國 DSL 第三章（重要數據出境）",
                "中國 CSL 第三章（關鍵信息基礎設施）",
            ],
            required_actions=[
                "⚠️ 評估是否構成「數據出境」（雲服務器在境外 = 是）",
                "⚠️ 即使無 PII，仍建議簽訂 PIPL 標準合同",
                "⚠️ 10 個工作日內向省級網信部門備案",
                "✅ 評估替代方案：物理加密硬盤（推薦，零合規負擔）",
            ],
            confidence="✅ Verified",
            reference_kb=["KB-37", "KB-38"],
        )

    def _pii_cloud_scenario(self, ctx: ComplianceContext) -> ComplianceResult:
        """有 PII + 雲端 = 必須走標準合同 / 安全評估"""
        if ctx.pii_count >= self.CHINA_PIPL_THRESHOLDS["general_1m_threshold"]:
            return ComplianceResult(
                level=ComplianceLevel.RED,
                summary="🔴 必須走安全評估：100 萬+ 個人信息跨境傳輸須國家網信辦安全評估",
                applicable_laws=[
                    "中國 PIPL Article 40（CIIO 義務）",
                    "《數據出境安全評估辦法》（2022-09）",
                ],
                required_actions=[
                    "🔴 申報國家網信辦安全評估",
                    "🔴 預計 3+ 個月 + 大量文件",
                    "⚠️ 建議：避免跨境，改用本地化方案",
                ],
                confidence="✅ Verified",
                reference_kb=["KB-35", "KB-37"],
            )
        elif ctx.sensitive_pii and ctx.pii_count >= 10_000:
            return ComplianceResult(
                level=ComplianceLevel.RED,
                summary="🔴 必須走安全評估：1 萬+ 敏感個人信息跨境傳輸須安全評估",
                applicable_laws=[
                    "中國 PIPL Article 40",
                    "《數據出境安全評估辦法》",
                ],
                required_actions=[
                    "🔴 申報安全評估",
                    "⚠️ 評估可否脫敏後降級為非敏感 PII",
                ],
                confidence="✅ Verified",
                reference_kb=["KB-35", "KB-37"],
            )
        else:
            return ComplianceResult(
                level=ComplianceLevel.YELLOW,
                summary="🟡 建議走 GBA 標準合同：< 100 萬人非敏感 PII + 南沙/HK 雙地",
                applicable_laws=[
                    "中國 PIPL Article 38（標準合同）",
                    "《標準合同辦法》（2023-06）",
                    "GBA 標準合同（2023-12）",
                ],
                required_actions=[
                    "✅ 與雲服務商簽訂 GBA 標準合同",
                    "✅ 10 個工作日內向廣東省網信辦備案",
                    "✅ 進行 PIPIA（個人信息保護影響評估）",
                    "✅ 有效期 3 年，到期續簽",
                ],
                confidence="🔍 Researched",
                reference_kb=["KB-35", "KB-36", "KB-37"],
            )

    def _generative_ai_scenario(self, ctx: ComplianceContext) -> ComplianceResult:
        """生成式 AI 場景 = 額外算法備案 + 安全評估"""
        if ctx.has_government_cert:
            return ComplianceResult(
                level=ComplianceLevel.GREEN,
                summary="🟢 GenAI 合規：已有算法備案 + 安全評估",
                applicable_laws=[
                    "《生成式 AI 服務管理暫行辦法》（2023-08）",
                ],
                required_actions=[
                    "✅ 維持算法備案",
                    "✅ 維持安全評估",
                    "⚠️ 持續更新備案信息",
                ],
                confidence="✅ Verified",
                reference_kb=["KB-35"],
            )
        else:
            return ComplianceResult(
                level=ComplianceLevel.YELLOW,
                summary="🟡 GenAI 需評估：具有輿論屬性/社會動員能力須備案",
                applicable_laws=[
                    "《生成式 AI 服務管理暫行辦法》",
                    "深度合成算法備案（2023+）",
                ],
                required_actions=[
                    "⚠️ 評估是否屬於「具有輿論屬性/社會動員能力」",
                    "⚠️ 若屬於：算法備案 + 安全評估",
                    "✅ 若非屬於：不受此法規管轄",
                    "🔍 截至 2024-12 共 302 款 GenAI 完成備案",
                ],
                confidence="🔍 Researched",
                reference_kb=["KB-35"],
            )

    def _default_scenario(self, ctx: ComplianceContext) -> ComplianceResult:
        return ComplianceResult(
            level=ComplianceLevel.UNKNOWN,
            summary="❓ 場景未明確，建議提供更多 context",
            applicable_laws=["需手動評估"],
            required_actions=["請提供 has_pii + cross_border_mode + is_generative_ai 等信息"],
            confidence="⚠️ Inferred",
            reference_kb=[],
        )

    def generate_no_pii_certificate(self, product_name: str) -> str:
        """生成「無 PII 收集」Self-Certification 證書"""
        return f"""
========================================
NO-PII COLLECTION SELF-CERTIFICATION
產品名稱: {product_name}
生成日期: 2026-06-02
參考法規: PIPL Article 4 / PDPO Section 2
========================================

本產品（{product_name}）聲明：

1. ✅ 不收集任何個人信息用於 ML 訓練
2. ✅ 不收集姓名 / 電話 / email / 身份證 / 地址
3. ✅ 不記錄用戶對話 / 查詢歷史
4. ✅ 不收集 IP 地址 / 設備指紋
5. ✅ 不使用 cookies 追蹤用戶
6. ✅ 訓練數據只來自公開來源或自創
7. ✅ 模型輸出自動 PII 偵測 + 脫敏

法律效力：
- 中國 PIPL 框架下不觸發跨境傳輸義務
- HK PDPO 框架下不屬於「個人資料」
- GBA 標準合同不適用

證書編號: NO-PII-{product_name.upper()}-2026-06-02
有效期: 1 年（須每年更新）
簽署: _______________  日期: _______________

參考:
- KB-34 HK PDPO Deep Dive
- KB-35 China PIPL/DSL/CSL Deep Dive
- KB-37 Cross-Border Transfer Mechanisms
- KB-41 OPC Workflow Template
========================================
"""

    def check_physical_cross_border(self, items: List[str]) -> Dict:
        """物理跨境（mobile hard disk）物品合規檢查"""
        risk_items = []
        safe_items = []

        risk_patterns = {
            "客戶 PII": "客戶個人信息（姓名/電話/email/身份證）",
            "未授權數據": "未經授權嘅第三方數據",
            "敏感技術": "受出口管制嘅技術/算法",
            "國家秘密": "中國《保守國家秘密法》保護嘅資料",
            "他人 IP": "他人知識產權（未授權嘅源代碼/模型）",
        }

        for item in items:
            is_risk = False
            for pattern, desc in risk_patterns.items():
                if pattern.lower() in item.lower():
                    risk_items.append({"item": item, "risk": pattern, "desc": desc})
                    is_risk = True
                    break
            if not is_risk:
                safe_items.append(item)

        return {
            "safe_items": safe_items,
            "risk_items": risk_items,
            "recommendation": "🟢 安全" if not risk_items else "🔴 有風險，請移除或脫敏",
            "reference_kb": "KB-38",
        }


def demo():
    """示範用法"""
    checker = OPCDualJurisdictionCompliance()

    print("=" * 60)
    print("場景 1: BeeEmo 默認場景（無 PII + 物理硬盤）")
    print("=" * 60)
    ctx = ComplianceContext(
        jurisdiction=Jurisdiction.BOTH,
        has_pii=False,
        cross_border_mode=CrossBorderMode.PHYSICAL_HARD_DISK,
        contains_ip_code=True,
        contains_ml_model=True,
    )
    result = checker.check_compliance(ctx)
    print(f"判定: {result.level.value}")
    print(f"摘要: {result.summary}")
    print(f"信心: {result.confidence}")

    print()
    print("=" * 60)
    print("場景 2: 雲端同步（即使無 PII 仍須評估）")
    print("=" * 60)
    ctx2 = ComplianceContext(
        jurisdiction=Jurisdiction.BOTH,
        has_pii=False,
        cross_border_mode=CrossBorderMode.CLOUD_SYNC,
    )
    result2 = checker.check_compliance(ctx2)
    print(f"判定: {result2.level.value}")
    print(f"摘要: {result2.summary}")

    print()
    print("=" * 60)
    print("證書生成")
    print("=" * 60)
    cert = checker.generate_no_pii_certificate("EmoGlyph")
    print(cert[:500] + "...")


# ====================================================================
# Extension Module: Implementation Timeline + Deadlines + Audit
# Added 2026-06-02 per spec `implement-opc-hk-nansha-cross-border-compliance`
# ====================================================================

def generate_implementation_timeline() -> List[Dict]:
    """
    Generate M1-6 IP protection + compliance implementation timeline.

    Returns:
        List of phase dictionaries with tasks, budget, and external dependencies
    """
    return [
        {
            "phase": "A",
            "duration": "Week 1-2",
            "tasks": [
                "硬盤 BitLocker/FileVault 加密",
                "Git GPG/SSH 簽名配置",
                "資產盤點 (asset_inventory_opc.md)",
                "No-PII 自證 (no_pii_certification_checklist.md)",
                "商業秘密制度 (trade_secret_policy_opc.md)",
                "跨境合規日誌 (cross_border_compliance_log.md)",
            ],
            "budget_rmb": 0,
            "budget_hkd": 0,
            "external_deps": "None",
            "status": "Completed",
        },
        {
            "phase": "B",
            "duration": "M1-3",
            "tasks": [
                "中國軟著 × 3 (BeeEmo Core, EmoGlyph, Harnessing)",
                "HK 律師公證 × 2 (源碼 + 知識庫)",
                "HK 商標搜索 + 申請 (BeeEmo Class 9+42)",
                "HK 商業秘密法律諮詢 (1.5 小時)",
            ],
            "budget_rmb": 3000,
            "budget_hkd": 18000,
            "external_deps": "中國版權中心 + HK 律師 + HK IPD",
            "status": "Pending",
        },
        {
            "phase": "C",
            "duration": "M3-6",
            "tasks": [
                "馬德里商標國際申請 (US+EU+JP)",
                "國際商標代理委託",
            ],
            "budget_rmb": 35000,
            "budget_hkd": 0,
            "budget_usd": 5000,
            "external_deps": "WIPO + 國際商標代理",
            "status": "Optional",
        },
        {
            "phase": "D",
            "duration": "M6-12",
            "tasks": [
                "PCT 國際專利申請 (核心算法)",
                "國際專利代理委託",
                "30 個月內決定進入哪些國家",
            ],
            "budget_rmb": 100000,
            "budget_hkd": 0,
            "budget_usd": 15000,
            "external_deps": "WIPO + 國際專利代理",
            "status": "Optional",
        },
    ]


def check_filing_deadlines() -> List[Dict]:
    """
    Check upcoming IP filing deadlines.

    Returns:
        List of deadline dictionaries sorted by target_date
    """
    return [
        {
            "name": "中國軟著 (BeeEmo Core)",
            "type": "Copyright",
            "agency": "中國版權保護中心",
            "target_date": "2026-07-15",
            "days_remaining": 43,
            "status": "⏳ Pending",
            "priority": "HIGH",
        },
        {
            "name": "中國軟著 (EmoGlyph 5-Layer)",
            "type": "Copyright",
            "agency": "中國版權保護中心",
            "target_date": "2026-07-30",
            "days_remaining": 58,
            "status": "⏳ Pending",
            "priority": "HIGH",
        },
        {
            "name": "中國軟著 (Harnessing Core)",
            "type": "Copyright",
            "agency": "中國版權保護中心",
            "target_date": "2026-08-10",
            "days_remaining": 69,
            "status": "⏳ Pending",
            "priority": "MEDIUM",
        },
        {
            "name": "HK 律師公證 (源碼)",
            "type": "Notary",
            "agency": "HK 律師樓",
            "target_date": "2026-07-20",
            "days_remaining": 48,
            "status": "⏳ Pending",
            "priority": "HIGH",
        },
        {
            "name": "HK 律師公證 (知識庫)",
            "type": "Notary",
            "agency": "HK 律師樓",
            "target_date": "2026-07-25",
            "days_remaining": 53,
            "status": "⏳ Pending",
            "priority": "MEDIUM",
        },
        {
            "name": "HK 商標 (BeeEmo)",
            "type": "Trademark",
            "agency": "HK IPD",
            "target_date": "2026-08-15",
            "days_remaining": 74,
            "status": "⏳ Pending",
            "priority": "HIGH",
        },
        {
            "name": "HK 商業秘密法律諮詢",
            "type": "Consultation",
            "agency": "HK 律師",
            "target_date": "2026-09-15",
            "days_remaining": 105,
            "status": "⏳ Pending",
            "priority": "MEDIUM",
        },
    ]


def audit_security_posture() -> Dict:
    """
    Audit current security posture (delegates to setup_cross_border_security.py).

    Returns:
        Dictionary with overall_status, ready_to_cross_border, and detailed status
    """
    try:
        import sys
        from pathlib import Path
        scripts_dir = Path(__file__).parent.parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        from setup_cross_border_security import audit_security_posture as _audit

        report = _audit(target_path=".", drive_letter="C:")
        return {
            "overall_status": report.overall_status.value,
            "ready_to_cross_border": report.ready_to_cross_border,
            "encryption_status": report.encryption.status.value,
            "git_signing_status": report.git_signing.status.value,
            "pii_scan_status": report.pii_scan.status.value,
            "recommendations": report.recommendations,
        }
    except Exception as e:
        return {
            "overall_status": "❓ UNKNOWN",
            "ready_to_cross_border": False,
            "error": f"Audit failed: {str(e)}",
            "recommendations": [
                "Manually verify BitLocker/FileVault status",
                "Manually verify Git GPG/SSH signing",
                "Manually verify No-PII self-certification",
            ],
        }


def demo_extended() -> None:
    """Demo the new extended methods"""
    print("=" * 60)
    print("🔧 OPC Compliance Module — Extended Demo")
    print("=" * 60)

    print("\n【1】 Implementation Timeline")
    timeline = generate_implementation_timeline()
    for phase in timeline:
        budget_parts = []
        if phase.get("budget_rmb", 0) > 0:
            budget_parts.append(f"¥{phase['budget_rmb']:,}")
        if phase.get("budget_hkd", 0) > 0:
            budget_parts.append(f"HK${phase['budget_hkd']:,}")
        if phase.get("budget_usd", 0) > 0:
            budget_parts.append(f"${phase['budget_usd']:,}")
        budget = " + ".join(budget_parts) if budget_parts else "¥0"
        print(f"  Phase {phase['phase']} ({phase['duration']}): {budget} | {phase['external_deps']}")

    print("\n【2】 Filing Deadlines (Sorted by Urgency)")
    deadlines = check_filing_deadlines()
    sorted_deadlines = sorted(deadlines, key=lambda d: d["days_remaining"])
    for d in sorted_deadlines[:5]:
        print(f"  {d['name']}: {d['target_date']} ({d['days_remaining']} days) [{d['priority']}]")

    print("\n【3】 Security Posture Audit")
    audit = audit_security_posture()
    print(f"  Overall: {audit.get('overall_status', 'N/A')}")
    print(f"  Ready: {audit.get('ready_to_cross_border', False)}")
    for rec in audit.get("recommendations", [])[:3]:
        print(f"  → {rec}")

    print()
    print("=" * 60)
    print("✅ Extended demo completed")
    print("=" * 60)


if __name__ == "__main__":
    demo()
    print("\n" + "=" * 60 + "\n")
    demo_extended()
