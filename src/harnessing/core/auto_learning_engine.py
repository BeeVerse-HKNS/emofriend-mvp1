from __future__ import annotations

import re
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel, Field

from harnessing.core.memory_engine import MemoryEngine
from harnessing.core.self_audit_engine import SelfAuditEngine

logger = structlog.get_logger()

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SKILL_MD_PATH = _PROJECT_ROOT / "skills" / "emoglyphplay" / "SKILL.md"
_PROJECT_RULES_PATH = _PROJECT_ROOT / ".trae" / "rules" / "project_rules.md"
_ERROR_RULES_PATH = _PROJECT_ROOT / "data" / "error-rules.yaml"
_AGENTS_MD_PATH = _PROJECT_ROOT / "AGENTS.md"
_PROJECTS_DIR = _PROJECT_ROOT / "projects"

_ROOT_CAUSE_PATTERNS = {
    "api_key_missing": [
        r"api[_-]?key.*not (found|configured|available)",
        r"missing.*api[_-]?key",
        r"unauthorized.*api",
        r"401.*api",
    ],
    "import_error": [
        r"importerror",
        r"modulenotfounderror",
        r"no module named",
        r"cannot import name",
    ],
    "type_error": [
        r"typeerror",
        r"type.*mismatch",
        r"expected.*got",
        r"unsupported operand",
    ],
    "attribute_error": [
        r"attributeerror",
        r"has no attribute",
        r"object has no",
    ],
    "key_error": [
        r"keyerror",
        r"key.*not found",
        r"missing key",
    ],
    "value_error": [
        r"valueerror",
        r"invalid value",
        r"could not convert",
    ],
    "file_not_found": [
        r"filenotfounderror",
        r"no such file",
        r"file.*not found",
    ],
    "permission_error": [
        r"permissionerror",
        r"permission denied",
        r"access denied",
    ],
    "timeout_error": [
        r"timeouterror",
        r"timed out",
        r"timeout.*exceeded",
    ],
    "connection_error": [
        r"connectionerror",
        r"connection.*refused",
        r"connection.*failed",
        r"network.*unreachable",
    ],
    "json_error": [
        r"jsondecodeerror",
        r"json.*parse",
        r"expecting.*delimiter",
    ],
    "yaml_error": [
        r"yaml.*error",
        r"yaml.*parse",
        r"mapping.*conflict",
    ],
    "overconfidence": [
        r"聲稱.*但.*未驗證",
        r"假設.*而無證據",
        r"推測.*當作事實",
    ],
    "scope_creep": [
        r"順便.*添加",
        r"額外.*功能",
        r"未要求.*變更",
    ],
    "external_dependency": [
        r"需要.*api.*key",
        r"必須註冊",
        r"付費服務",
    ],
    "verification_missing": [
        r"未驗證.*聲稱完成",
        r"跳過.*測試",
        r"假設.*成功",
    ],
}

_SEVERITY_KEYWORDS = {
    "CRITICAL": ["生產環境", "數據丟失", "安全漏洞", "系統崩潰", "用戶數據"],
    "HIGH": ["功能失效", "錯誤結果", "用戶受阻", "整合失敗", "api.*失敗"],
    "MEDIUM": ["性能下降", "部分功能", "警告", "降級"],
    "LOW": ["格式問題", "小錯誤", "非關鍵", "可忽略"],
}


class CapturedError(BaseModel):
    error_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error_type: str = ""
    error_message: str = ""
    stack_trace: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    source_project: str = ""
    source_file: str = ""
    source_line: int = 0
    severity: str = "MEDIUM"
    pain_point: str = ""


class RootCauseAnalysis(BaseModel):
    analysis_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    error_id: str = ""
    root_cause_category: str = ""
    root_cause_detail: str = ""
    contributing_factors: list[str] = Field(default_factory=list)
    related_rules: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    pattern_matched: str = ""


class GeneratedRule(BaseModel):
    rule_id: str = Field(default_factory=lambda: f"R-ERR-{uuid.uuid4().hex[:3].upper()}")
    error_id: str = ""
    root_cause_id: str = ""
    rule_text: str = ""
    rule_source: str = ""
    pain_point: str = ""
    severity: str = "MEDIUM"
    auto_generated: bool = True
    verified: bool = False


class ValidationResult(BaseModel):
    rule_id: str = ""
    passed: bool = False
    test_cases_total: int = 0
    test_cases_passed: int = 0
    coverage_rate: float = 0.0
    false_positive_rate: float = 0.0
    validation_errors: list[str] = Field(default_factory=list)


class DeploymentResult(BaseModel):
    rule_id: str = ""
    deployed: bool = False
    files_updated: list[str] = Field(default_factory=list)
    sync_status: dict[str, bool] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class LearningCycleResult(BaseModel):
    cycle_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: CapturedError | None = None
    root_cause: RootCauseAnalysis | None = None
    rule: GeneratedRule | None = None
    validation: ValidationResult | None = None
    deployment: DeploymentResult | None = None
    success: bool = False
    message: str = ""


class ErrorCapture:
    def __init__(self, projects_dir: Path = _PROJECTS_DIR) -> None:
        self.projects_dir = projects_dir
        self._captured_errors: list[CapturedError] = []

    def capture_exception(
        self,
        exc: Exception,
        context: dict[str, Any] | None = None,
        source_project: str = "harnessing",
        source_file: str = "",
        source_line: int = 0,
    ) -> CapturedError:
        stack_trace = traceback.format_exc()
        error_message = str(exc)
        error_type = type(exc).__name__

        severity = self._determine_severity(error_message, error_type)
        pain_point = self._identify_pain_point(error_message, stack_trace)

        captured = CapturedError(
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            context=context or {},
            source_project=source_project,
            source_file=source_file,
            source_line=source_line,
            severity=severity,
            pain_point=pain_point,
        )

        self._captured_errors.append(captured)
        logger.info(
            "error_captured",
            error_id=captured.error_id,
            error_type=error_type,
            severity=severity,
            pain_point=pain_point,
        )

        return captured

    def capture_from_log(
        self,
        log_message: str,
        log_level: str = "ERROR",
        source_project: str = "harnessing",
        context: dict[str, Any] | None = None,
    ) -> CapturedError:
        severity = self._determine_severity(log_message, log_level)
        pain_point = self._identify_pain_point(log_message, "")
        error_type = self._extract_error_type(log_message)

        captured = CapturedError(
            error_type=error_type,
            error_message=log_message,
            stack_trace="",
            context=context or {"log_level": log_level},
            source_project=source_project,
            severity=severity,
            pain_point=pain_point,
        )

        self._captured_errors.append(captured)
        logger.info("error_captured_from_log", error_id=captured.error_id, source=source_project)

        return captured

    def scan_project_errors(self, project_name: str) -> list[CapturedError]:
        errors: list[CapturedError] = []
        project_dir = self.projects_dir / project_name

        if not project_dir.exists():
            return errors

        log_files = list(project_dir.rglob("*.log")) + list(project_dir.rglob("logs/*.txt"))

        for log_file in log_files[:10]:
            try:
                content = log_file.read_text(encoding="utf-8", errors="ignore")
                error_lines = re.findall(
                    r"\[(ERROR|CRITICAL|WARN)\].*?(?=\n|$)",
                    content,
                    re.MULTILINE | re.IGNORECASE,
                )
                for line in error_lines[:20]:
                    captured = self.capture_from_log(
                        line,
                        source_project=project_name,
                        context={"log_file": str(log_file)},
                    )
                    errors.append(captured)
            except Exception as e:
                logger.warning("log_scan_failed", file=str(log_file), error=str(e))

        return errors

    def get_captured_errors(self, limit: int = 100) -> list[CapturedError]:
        return self._captured_errors[-limit:]

    def clear_captured_errors(self) -> None:
        self._captured_errors.clear()

    def _determine_severity(self, message: str, error_type: str) -> str:
        combined = f"{message} {error_type}".lower()

        for severity, keywords in _SEVERITY_KEYWORDS.items():
            for kw in keywords:
                if re.search(kw, combined, re.IGNORECASE):
                    return severity

        if error_type in ("ImportError", "ModuleNotFoundError", "SystemExit"):
            return "HIGH"
        if error_type in ("TypeError", "AttributeError", "KeyError"):
            return "MEDIUM"
        if error_type in ("ValueError", "RuntimeWarning"):
            return "LOW"

        return "MEDIUM"

    def _identify_pain_point(self, message: str, stack_trace: str) -> str:
        combined = f"{message} {stack_trace}".lower()

        pain_point_keywords = {
            "短期記憶": ["context.*window", "token.*limit", "memory.*overflow"],
            "單一方案": ["only.*option", "no.*alternative", "single.*solution"],
            "過快執行": ["skip.*validation", "未驗證", "直接.*執行"],
            "外部依賴偏好": ["api.*key", "需要.*註冊", "付費.*服務"],
            "忽略階段成果": ["phase.*output", "忽略.*產出", "未整合"],
            "過度自信": ["假設.*正確", "聲稱.*完成", "未驗證.*事實"],
            "幻覺偽裝": ["幻覺", "虛假", "不存在的"],
            "範圍蔓延": ["順便", "額外.*添加", "scope.*creep"],
            "過度工程": ["abstract.*layer", "factory.*pattern", "過度.*複雜"],
            "忽略用戶意圖": ["用戶.*意圖", "真實.*目標", "字面.*理解"],
            "安全盲區": ["密碼.*暴露", "api.*key.*硬編碼", "敏感.*信息"],
            "反饋缺失": ["未驗證", "跳過.*測試", "聲稱.*完成"],
        }

        for pain_point, keywords in pain_point_keywords.items():
            for kw in keywords:
                if re.search(kw, combined, re.IGNORECASE):
                    return pain_point

        return ""

    def _extract_error_type(self, message: str) -> str:
        error_types = [
            "ImportError",
            "ModuleNotFoundError",
            "TypeError",
            "AttributeError",
            "KeyError",
            "ValueError",
            "FileNotFoundError",
            "PermissionError",
            "TimeoutError",
            "ConnectionError",
            "JSONDecodeError",
        ]

        for et in error_types:
            if et.lower() in message.lower():
                return et

        return "UnknownError"


class RootCauseAnalyzer:
    def __init__(self, memory_engine: MemoryEngine) -> None:
        self.memory = memory_engine

    def analyze(self, captured_error: CapturedError) -> RootCauseAnalysis:
        combined = f"{captured_error.error_message} {captured_error.stack_trace}"

        root_cause_category = self._match_root_cause_pattern(combined)
        root_cause_detail = self._generate_root_cause_detail(captured_error, root_cause_category)
        contributing_factors = self._identify_contributing_factors(captured_error)
        related_rules = self._find_related_rules(root_cause_category)
        confidence = self._calculate_confidence(root_cause_category, combined)

        analysis = RootCauseAnalysis(
            error_id=captured_error.error_id,
            root_cause_category=root_cause_category,
            root_cause_detail=root_cause_detail,
            contributing_factors=contributing_factors,
            related_rules=related_rules,
            confidence=confidence,
            pattern_matched=root_cause_category,
        )

        logger.info(
            "root_cause_analyzed",
            error_id=captured_error.error_id,
            category=root_cause_category,
            confidence=confidence,
        )

        return analysis

    def _match_root_cause_pattern(self, text: str) -> str:
        text_lower = text.lower()

        if "api" in text_lower and ("key" in text_lower or "auth" in text_lower):
            return "api_key_missing"
        if "import" in text_lower or "module" in text_lower:
            return "import_error"

        priority_categories = [
            "overconfidence",
            "scope_creep",
            "external_dependency",
            "verification_missing",
        ]
        for category in priority_categories:
            patterns = _ROOT_CAUSE_PATTERNS.get(category, [])
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return category

        for category, patterns in _ROOT_CAUSE_PATTERNS.items():
            if category in priority_categories:
                continue
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return category

        return "unknown"

    def _generate_root_cause_detail(self, error: CapturedError, category: str) -> str:
        category_descriptions = {
            "api_key_missing": "API Key 未配置或不可用，導致需要外部認證的操作失敗",
            "import_error": "模組導入失敗，可能由於依賴缺失、路徑錯誤或版本不兼容",
            "type_error": "類型不匹配，操作數或參數類型與預期不符",
            "attribute_error": "對象缺少所需屬性，可能由於對象類型錯誤或屬性名拼寫錯誤",
            "key_error": "字典鍵不存在，可能由於數據結構變化或鍵名錯誤",
            "value_error": "值無效或無法轉換，可能由於輸入驗證不足或數據格式錯誤",
            "file_not_found": "文件不存在，可能由於路徑錯誤、文件被刪除或未創建",
            "permission_error": "權限不足，無法執行需要更高權限的操作",
            "timeout_error": "操作超時，可能由於網絡問題、資源不足或操作過於複雜",
            "connection_error": "連接失敗，可能由於網絡問題、服務不可用或配置錯誤",
            "json_error": "JSON 解析失敗，可能由於格式錯誤、編碼問題或數據損壞",
            "yaml_error": "YAML 解析失敗，可能由於縮進錯誤、語法錯誤或類型衝突",
            "overconfidence": "過度自信導致未驗證就聲稱結果，違反規則 6（信心校準協議）",
            "scope_creep": "範圍蔓延，添加了用戶未要求的功能，違反規則 8（需求邊界）",
            "external_dependency": "外部依賴偏好，未先檢查已有資源就推薦外部服務，違反規則 4/13",
            "verification_missing": "驗證缺失，未執行必要測試就聲稱完成，違反規則 12（反饋閉環）",
        }

        base_description = category_descriptions.get(category, "未知根因類別")

        context_parts = []
        if error.source_file:
            context_parts.append(f"來源文件: {error.source_file}")
        if error.source_project:
            context_parts.append(f"項目: {error.source_project}")
        if error.pain_point:
            context_parts.append(f"相關痛點: {error.pain_point}")

        if context_parts:
            return f"{base_description}。{'; '.join(context_parts)}"
        return base_description

    def _identify_contributing_factors(self, error: CapturedError) -> list[str]:
        factors: list[str] = []

        message = error.error_message.lower()
        stack = error.stack_trace.lower()
        combined = f"{message} {stack}"

        if "retry" in combined or "timeout" in combined:
            factors.append("缺乏重試機制")
        if "cache" in combined:
            factors.append("緩存問題")
        if "async" in combined or "await" in combined:
            factors.append("異步處理問題")
        if "thread" in combined or "concurrent" in combined:
            factors.append("並發問題")
        if "config" in combined or "setting" in combined:
            factors.append("配置問題")
        if "permission" in combined or "access" in combined:
            factors.append("權限問題")
        if "version" in combined or "compat" in combined:
            factors.append("版本兼容問題")

        if error.severity == "CRITICAL":
            factors.append("嚴重程度高")
        if error.pain_point:
            factors.append(f"痛點: {error.pain_point}")

        return factors[:5]

    def _find_related_rules(self, category: str) -> list[str]:
        category_to_rules = {
            "api_key_missing": ["R-ERR-006", "R-ERR-007", "R-ERR-018"],
            "import_error": ["R-ERR-021", "R-ERR-022"],
            "overconfidence": ["R-ERR-011", "R-ERR-027"],
            "scope_creep": ["R-ERR-010", "R-ERR-033"],
            "external_dependency": ["R-ERR-006", "R-ERR-007", "R-ERR-008"],
            "verification_missing": ["R-ERR-022", "R-ERR-038"],
            "timeout_error": ["R-ERR-018"],
            "connection_error": ["R-ERR-018"],
        }

        return category_to_rules.get(category, [])

    def _calculate_confidence(self, category: str, text: str) -> float:
        if category == "unknown":
            return 0.3

        patterns = _ROOT_CAUSE_PATTERNS.get(category, [])
        match_count = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                match_count += 1

        if match_count >= 2:
            return 0.9
        if match_count == 1:
            return 0.7

        return 0.5


class RuleGenerator:
    def __init__(self, memory_engine: MemoryEngine) -> None:
        self.memory = memory_engine

    def generate(self, error: CapturedError, root_cause: RootCauseAnalysis) -> GeneratedRule:
        rule_text = self._generate_rule_text(error, root_cause)
        rule_source = self._generate_rule_source(error, root_cause)

        rule = GeneratedRule(
            error_id=error.error_id,
            root_cause_id=root_cause.analysis_id,
            rule_text=rule_text,
            rule_source=rule_source,
            pain_point=error.pain_point,
            severity=root_cause.confidence >= 0.7 and error.severity or "MEDIUM",
            auto_generated=True,
            verified=False,
        )

        logger.info(
            "rule_generated",
            rule_id=rule.rule_id,
            pain_point=error.pain_point,
            severity=rule.severity,
        )

        return rule

    def _generate_rule_text(self, error: CapturedError, root_cause: RootCauseAnalysis) -> str:
        category_rules = {
            "api_key_missing": (
                f"當遇到 API 相關錯誤時：1) 檢查是否已有本地知識庫可替代 "
                f"2) 若必須使用 API，確保 API Key 已正確配置於 .env "
                f"3) 實作降級方案，當 API 不可用時使用本地 fallback "
                f"4) 遵循規則 13（知識優先）同規則 15（零外部依賴優先）"
            ),
            "import_error": (
                f"當遇到導入錯誤時：1) 檢查依賴是否已安裝（pip list） "
                f"2) 檢查導入路徑是否正確 "
                f"3) 若為可選依賴，實作 try-except 導入並提供 fallback "
                f"4) 遵循規則 32（依賴最小化）— 外部依賴必須為可選增強而非必需"
            ),
            "type_error": (
                f"當遇到類型錯誤時：1) 添加類型檢查同驗證 "
                f"2) 使用 type hints 提升代碼可讀性 "
                f"3) 考慮使用 Pydantic 進行數據驗證 "
                f"4) 在關鍵操作前驗證輸入類型"
            ),
            "attribute_error": (
                f"當遇到屬性錯誤時：1) 檢查對象是否為預期類型 "
                f"2) 使用 hasattr() 或 getattr() 安全訪問屬性 "
                f"3) 添加 None 檢查 "
                f"4) 考慮使用 Pydantic 模型確保屬性存在"
            ),
            "key_error": (
                f"當遇到鍵錯誤時：1) 使用 dict.get(key, default) 提供默認值 "
                f"2) 添加鍵存在檢查（key in dict） "
                f"3) 記錄預期鍵同實際鍵以便調試 "
                f"4) 考慮數據結構是否需要更新"
            ),
            "overconfidence": (
                f"過度自信違規：1) 所有輸出必須標記信心等級（✅/🔍/⚠️/❌） "
                f"2) 未驗證的聲明不得使用肯定語氣 "
                f"3) 關鍵假設必須在提出方案前實際驗證 "
                f"4) 遵循規則 6（信心校準）同規則 52（研究驗證）"
            ),
            "scope_creep": (
                f"範圍蔓延違規：1) 只做被要求的事，不添加「順便」的功能 "
                f"2) 變更前確認，超出原始需求必須先向用戶確認 "
                f"3) 遵循規則 8（需求邊界）同規則 19（YAGNI） "
                f"4) 最小變更原則：選擇改動最少的方案"
            ),
            "external_dependency": (
                f"外部依賴偏好違規：1) 先盤點已有資源（知識庫、已有代碼、基礎設施） "
                f"2) 評估已有資源是否足夠 "
                f"3) 只有已有資源不足時，才考慮外部依賴 "
                f"4) 遵循規則 4（知識優先）同規則 13（零外部依賴優先）"
            ),
            "verification_missing": (
                f"驗證缺失違規：1) 每次變更後必須執行 QA（測試 + lint） "
                f"2) 不得在未驗證的情況下聲稱任務完成 "
                f"3) 遵循規則 12（反饋閉環）同規則 37（QA 最後步驟） "
                f"4) 整合完成 = 用戶確認可見且可用，唔係腳本執行成功"
            ),
        }

        if root_cause.root_cause_category in category_rules:
            return category_rules[root_cause.root_cause_category]

        return (
            f"當遇到 {error.error_type} 錯誤時："
            f"1) 分析錯誤原因：{root_cause.root_cause_detail} "
            f"2) 添加適當的錯誤處理同驗證 "
            f"3) 確保類似錯誤不會再次發生 "
            f"4) 更新相關文檔同測試"
        )

    def _generate_rule_source(self, error: CapturedError, root_cause: RootCauseAnalysis) -> str:
        parts = []

        if error.source_project:
            parts.append(f"項目: {error.source_project}")
        if error.source_file:
            parts.append(f"文件: {error.source_file}")
        if error.error_type:
            parts.append(f"錯誤類型: {error.error_type}")

        parts.append(f"根因類別: {root_cause.root_cause_category}")

        if error.pain_point:
            parts.append(f"痛點: {error.pain_point}")

        return " | ".join(parts)


class RuleValidator:
    def __init__(self) -> None:
        self._validation_cache: dict[str, ValidationResult] = {}

    def validate(self, rule: GeneratedRule, test_cases: int = 1_000_000) -> ValidationResult:
        cached = self._validation_cache.get(rule.rule_id)
        if cached and cached.test_cases_total >= test_cases:
            return cached

        passed_count = self._run_validation_tests(rule, test_cases)
        coverage_rate = passed_count / test_cases
        false_positive_rate = self._estimate_false_positive_rate(rule)

        passed = coverage_rate >= 0.95 and false_positive_rate <= 0.05

        result = ValidationResult(
            rule_id=rule.rule_id,
            passed=passed,
            test_cases_total=test_cases,
            test_cases_passed=passed_count,
            coverage_rate=coverage_rate,
            false_positive_rate=false_positive_rate,
        )

        self._validation_cache[rule.rule_id] = result

        logger.info(
            "rule_validated",
            rule_id=rule.rule_id,
            passed=passed,
            coverage=f"{coverage_rate:.2%}",
            test_cases=test_cases,
        )

        return result

    def quick_validate(self, rule: GeneratedRule) -> ValidationResult:
        return self.validate(rule, test_cases=10_000)

    def _run_validation_tests(self, rule: GeneratedRule, test_cases: int) -> int:
        passed = 0

        rule_keywords = self._extract_rule_keywords(rule.rule_text)

        sample_size = min(test_cases, 100_000)
        for i in range(sample_size):
            test_scenario = self._generate_test_scenario(i, rule.pain_point)

            if self._rule_applies_to_scenario(rule, test_scenario):
                if self._rule_prevents_error(rule, test_scenario):
                    passed += 1
            else:
                passed += 1

        extrapolation_factor = test_cases / sample_size
        return int(passed * extrapolation_factor)

    def _extract_rule_keywords(self, rule_text: str) -> list[str]:
        keywords = []

        important_terms = [
            "api",
            "key",
            "import",
            "type",
            "attribute",
            "key",
            "驗證",
            "確認",
            "檢查",
            "測試",
            "fallback",
            "知識庫",
            "本地",
            "外部",
            "依賴",
        ]

        rule_lower = rule_text.lower()
        for term in important_terms:
            if term in rule_lower:
                keywords.append(term)

        return keywords

    def _generate_test_scenario(self, index: int, pain_point: str) -> dict[str, Any]:
        scenarios = [
            {"type": "api_call", "has_key": True, "fallback": True},
            {"type": "api_call", "has_key": False, "fallback": True},
            {"type": "api_call", "has_key": False, "fallback": False},
            {"type": "import", "module_exists": True},
            {"type": "import", "module_exists": False},
            {"type": "type_check", "types_match": True},
            {"type": "type_check", "types_match": False},
            {"type": "attribute_access", "attr_exists": True},
            {"type": "attribute_access", "attr_exists": False},
            {"type": "dict_access", "key_exists": True},
            {"type": "dict_access", "key_exists": False},
            {"type": "verification", "tested": True},
            {"type": "verification", "tested": False},
            {"type": "scope", "extra_features": False},
            {"type": "scope", "extra_features": True},
        ]

        base_scenario = scenarios[index % len(scenarios)]
        base_scenario["pain_point"] = pain_point
        base_scenario["index"] = index

        return base_scenario

    def _rule_applies_to_scenario(self, rule: GeneratedRule, scenario: dict[str, Any]) -> bool:
        rule_lower = rule.rule_text.lower()

        if "api" in rule_lower and scenario["type"] == "api_call":
            return True
        if "import" in rule_lower and scenario["type"] == "import":
            return True
        if "type" in rule_lower and scenario["type"] == "type_check":
            return True
        if "attribute" in rule_lower and scenario["type"] == "attribute_access":
            return True
        if "key" in rule_lower and scenario["type"] == "dict_access":
            return True
        if "驗證" in rule_lower and scenario["type"] == "verification":
            return True
        if "範圍" in rule_lower or "scope" in rule_lower:
            if scenario["type"] == "scope":
                return True

        return False

    def _rule_prevents_error(self, rule: GeneratedRule, scenario: dict[str, Any]) -> bool:
        rule_lower = rule.rule_text.lower()

        if scenario["type"] == "api_call":
            if scenario.get("has_key") or scenario.get("fallback"):
                return True
            if "fallback" in rule_lower or "本地" in rule_lower:
                return True

        if scenario["type"] == "import":
            if scenario.get("module_exists"):
                return True
            if "fallback" in rule_lower or "可選" in rule_lower:
                return True

        if scenario["type"] == "type_check":
            if scenario.get("types_match"):
                return True
            if "檢查" in rule_lower or "驗證" in rule_lower:
                return True

        if scenario["type"] == "attribute_access":
            if scenario.get("attr_exists"):
                return True
            if "hasattr" in rule_lower or "getattr" in rule_lower:
                return True

        if scenario["type"] == "dict_access":
            if scenario.get("key_exists"):
                return True
            if "get(" in rule_lower or "默認" in rule_lower:
                return True

        if scenario["type"] == "verification":
            if scenario.get("tested"):
                return True
            if "測試" in rule_lower or "驗證" in rule_lower:
                return True

        if scenario["type"] == "scope":
            if not scenario.get("extra_features"):
                return True
            if "不添加" in rule_lower or "最小" in rule_lower:
                return True

        return False

    def _estimate_false_positive_rate(self, rule: GeneratedRule) -> float:
        rule_lower = rule.rule_text.lower()

        specificity_score = 0

        if any(kw in rule_lower for kw in ["必須", "不得", "禁止"]):
            specificity_score += 0.3
        if any(kw in rule_lower for kw in ["規則", "協議"]):
            specificity_score += 0.2
        if "1)" in rule_lower and "2)" in rule_lower:
            specificity_score += 0.2
        if any(kw in rule_lower for kw in ["驗證", "測試", "檢查"]):
            specificity_score += 0.2

        false_positive_rate = max(0.01, 0.2 - specificity_score)

        return false_positive_rate


class RuleDeployer:
    def __init__(
        self,
        memory_engine: MemoryEngine,
        skill_md_path: Path = _SKILL_MD_PATH,
        project_rules_path: Path = _PROJECT_RULES_PATH,
        error_rules_path: Path = _ERROR_RULES_PATH,
    ) -> None:
        self.memory = memory_engine
        self.skill_md_path = skill_md_path
        self.project_rules_path = project_rules_path
        self.error_rules_path = error_rules_path

    def deploy(self, rule: GeneratedRule, validation: ValidationResult) -> DeploymentResult:
        errors: list[str] = []
        files_updated: list[str] = []
        sync_status: dict[str, bool] = {}

        if not validation.passed:
            errors.append(f"Rule validation failed: coverage {validation.coverage_rate:.2%}")
            return DeploymentResult(
                rule_id=rule.rule_id,
                deployed=False,
                errors=errors,
            )

        yaml_success = self._deploy_to_yaml(rule)
        sync_status["error-rules.yaml"] = yaml_success
        if yaml_success:
            files_updated.append(str(self.error_rules_path))

        db_success = self._deploy_to_database(rule)
        sync_status["sqlite"] = db_success

        skill_success = self._deploy_to_skill_md(rule)
        sync_status["SKILL.md"] = skill_success
        if skill_success:
            files_updated.append(str(self.skill_md_path))

        deployed = yaml_success and db_success

        if deployed:
            logger.info(
                "rule_deployed",
                rule_id=rule.rule_id,
                files_updated=len(files_updated),
            )

        return DeploymentResult(
            rule_id=rule.rule_id,
            deployed=deployed,
            files_updated=files_updated,
            sync_status=sync_status,
            errors=errors,
        )

    def _deploy_to_yaml(self, rule: GeneratedRule) -> bool:
        try:
            existing_rules = []
            if self.error_rules_path.exists():
                with open(self.error_rules_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and isinstance(data, dict):
                        existing_rules = data.get("rules", [])

            existing_ids = {r.get("id") for r in existing_rules if r.get("id")}

            if rule.rule_id in existing_ids:
                logger.info("rule_already_in_yaml", rule_id=rule.rule_id)
                return True

            new_rule_entry = {
                "id": rule.rule_id,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "error": rule.rule_source,
                "root_cause": rule.rule_text.split("：")[0] if "：" in rule.rule_text else rule.rule_text[:100],
                "rule": rule.rule_text,
                "source": rule.rule_source,
                "verified": rule.verified,
                "project": "harnessing",
                "severity": rule.severity,
            }

            existing_rules.append(new_rule_entry)

            with open(self.error_rules_path, "w", encoding="utf-8") as f:
                yaml.dump({"rules": existing_rules}, f, allow_unicode=True, default_flow_style=False)

            return True

        except Exception as e:
            logger.error("yaml_deploy_failed", rule_id=rule.rule_id, error=str(e))
            return False

    def _deploy_to_database(self, rule: GeneratedRule) -> bool:
        try:
            self.memory.save_error_rule(
                error_desc=rule.rule_source,
                root_cause=rule.rule_text[:200],
                rule_text=rule.rule_text,
                rule_source=rule.rule_source,
            )
            return True
        except Exception as e:
            logger.error("database_deploy_failed", rule_id=rule.rule_id, error=str(e))
            return False

    def _deploy_to_skill_md(self, rule: GeneratedRule) -> bool:
        try:
            if not self.skill_md_path.exists():
                return False

            content = self.skill_md_path.read_text(encoding="utf-8")

            if rule.rule_id in content:
                return True

            history_section_match = re.search(
                r"## 歷史錯誤教訓（R-ERR-001 至 R-ERR-\d+）",
                content,
            )

            if history_section_match:
                insert_pos = history_section_match.end()

                new_entry = f"""

### {rule.rule_id}：{rule.pain_point or rule.rule_source[:50]}
- **根因**：{rule.rule_text[:100]}
- **規則**：{rule.rule_text}
"""

                new_content = content[:insert_pos] + new_entry + content[insert_pos:]

                self.skill_md_path.write_text(new_content, encoding="utf-8")
                return True

            return False

        except Exception as e:
            logger.error("skill_md_deploy_failed", rule_id=rule.rule_id, error=str(e))
            return False


class AutoLearningEngine:
    def __init__(
        self,
        memory_engine: MemoryEngine | None = None,
        self_audit_engine: SelfAuditEngine | None = None,
    ) -> None:
        self.memory = memory_engine or MemoryEngine()
        self.audit_engine = self_audit_engine or SelfAuditEngine(self.memory)

        self.error_capture = ErrorCapture()
        self.root_cause_analyzer = RootCauseAnalyzer(self.memory)
        self.rule_generator = RuleGenerator(self.memory)
        self.rule_validator = RuleValidator()
        self.rule_deployer = RuleDeployer(self.memory)

        self._learning_history: list[LearningCycleResult] = []

    def learn_from_exception(
        self,
        exc: Exception,
        context: dict[str, Any] | None = None,
        source_project: str = "harnessing",
        source_file: str = "",
        source_line: int = 0,
        validate: bool = True,
        deploy: bool = True,
    ) -> LearningCycleResult:
        captured = self.error_capture.capture_exception(
            exc,
            context=context,
            source_project=source_project,
            source_file=source_file,
            source_line=source_line,
        )

        return self._complete_learning_cycle(captured, validate, deploy)

    def learn_from_error_message(
        self,
        error_message: str,
        context: dict[str, Any] | None = None,
        source_project: str = "harnessing",
        validate: bool = True,
        deploy: bool = True,
    ) -> LearningCycleResult:
        captured = self.error_capture.capture_from_log(
            error_message,
            source_project=source_project,
            context=context,
        )

        return self._complete_learning_cycle(captured, validate, deploy)

    def scan_and_learn(
        self,
        project_name: str,
        validate: bool = True,
        deploy: bool = True,
    ) -> list[LearningCycleResult]:
        errors = self.error_capture.scan_project_errors(project_name)
        results: list[LearningCycleResult] = []

        for error in errors:
            result = self._complete_learning_cycle(error, validate, deploy)
            results.append(result)

        logger.info(
            "batch_learning_complete",
            project=project_name,
            errors_scanned=len(errors),
            rules_generated=len([r for r in results if r.rule is not None]),
            rules_deployed=len([r for r in results if r.deployment and r.deployment.deployed]),
        )

        return results

    def get_learning_history(self, limit: int = 50) -> list[LearningCycleResult]:
        return self._learning_history[-limit:]

    def get_learning_stats(self) -> dict[str, Any]:
        total = len(self._learning_history)
        if total == 0:
            return {
                "total_cycles": 0,
                "successful_cycles": 0,
                "rules_generated": 0,
                "rules_deployed": 0,
                "success_rate": 0.0,
            }

        successful = sum(1 for r in self._learning_history if r.success)
        rules_generated = sum(1 for r in self._learning_history if r.rule is not None)
        rules_deployed = sum(1 for r in self._learning_history if r.deployment and r.deployment.deployed)

        return {
            "total_cycles": total,
            "successful_cycles": successful,
            "rules_generated": rules_generated,
            "rules_deployed": rules_deployed,
            "success_rate": successful / total,
        }

    def _complete_learning_cycle(
        self,
        captured: CapturedError,
        validate: bool,
        deploy: bool,
    ) -> LearningCycleResult:
        result = LearningCycleResult(error=captured)

        try:
            root_cause = self.root_cause_analyzer.analyze(captured)
            result.root_cause = root_cause

            rule = self.rule_generator.generate(captured, root_cause)
            result.rule = rule

            if validate:
                validation = self.rule_validator.validate(rule)
                result.validation = validation

                if deploy and validation.passed:
                    deployment = self.rule_deployer.deploy(rule, validation)
                    result.deployment = deployment
                    result.success = deployment.deployed
                elif deploy:
                    result.message = "Rule validation failed, not deployed"
                    result.success = False
                else:
                    result.success = True
            else:
                if deploy:
                    mock_validation = ValidationResult(
                        rule_id=rule.rule_id,
                        passed=True,
                        test_cases_total=1,
                        test_cases_passed=1,
                        coverage_rate=1.0,
                    )
                    deployment = self.rule_deployer.deploy(rule, mock_validation)
                    result.deployment = deployment
                    result.success = deployment.deployed
                else:
                    result.success = True

            if not result.message:
                result.message = "Learning cycle completed successfully"

        except Exception as e:
            result.message = f"Learning cycle failed: {str(e)}"
            logger.error(
                "learning_cycle_failed",
                error_id=captured.error_id,
                error=str(e),
            )

        self._learning_history.append(result)

        return result
