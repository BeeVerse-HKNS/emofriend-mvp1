import os
import re
from pathlib import Path

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


_KB_TOPIC_MAP = {
    "01": ["agent", "ai agent", "智能體", "五大核心", "感知", "規劃", "行動", "記憶", "反思", "agent fundamental"],
    "02": ["harness engineering", "約束工程", "harness 詳解", "harness 定義", "harness 起源"],
    "03": ["opc", "one person company", "一人公司", "商業模式", "agent 角色"],
    "04": ["cybernetics", "控制論", "前饋", "反饋控制", "香農熵", "信任債務", "魯棒性"],
    "05": ["codex", "openai codex", "實驗案例", "agents.md 設計", "100萬行"],
    "06": ["八大組件", "組件", "工作流", "工具策略", "驗證", "護欄", "觀測", "升級"],
    "07": ["核心功能", "感知", "規劃", "行動", "記憶", "反思", "工程實現"],
    "08": ["llm provider", "供應商", "openai", "anthropic", "本地模型", "多模型"],
    "09": ["python", "langchain", "crewai", "autogen", "pydantic", "生態"],
    "10": ["reference", "參考", "連結", "文章", "影片", "論文"],
    "11": ["methodology", "方法論", "實踐指南", "前饋反饋", "信任債務"],
    "12": ["n8n", "workflow", "工作流自動化", "mcp 整合"],
    "13": ["manus", "通用型智能體", "manus ai"],
    "14": ["china ai", "中國 ai", "百度", "騰訊", "字節", "智譜", "deepseek", "qwen", "kimi", "minimax", "訊飛", "商湯", "開源生態", "政策監管", "定價"],
    "15": ["coze", "dify", "fastgpt", "千帆", "元器", "百鍊", "lobechat", "maxkb", "ragflow", "agent 平台", "中國平台"],
    "16": ["agentic ai", "市場格局", "市場規模", "投資趨勢", "主要玩家"],
    "17": ["mcp", "a2a", "協議", "protocol", "model context", "agent to agent"],
    "18": ["harness latest", "最新發展", "context engineering", "guardrails", "評估框架", "entropy"],
    "19": ["model comparison", "模型對比", "基準測試", "benchmark", "中文能力", "推理", "編程", "多模態", "成本效益", "模型選擇"],
    "20": ["business model", "商業模式", "定價", "pricing", "商業化", "cursor", "devin", "replit"],
    "21": ["phase 1", "學習總結", "phase 1 回顧", "核心學習"],
    "22": ["youtube", "演算法", "algorithm", "社交媒體", "變現", "抖音", "b站", "跨平台", "上傳時間"],
    "23": ["verification", "驗證", "交叉驗證", "多源", "research verification"],
    "24": ["automation", "自動化技巧", "對比分析", "100 個", "gap 分析"],
    "25": ["model landscape", "模型全景", "1000 model", "china model", "ollama model", "rtx 3070", "vram", "deepseek-r1", "llama", "gemma", "phi", "mistral", "qwen3-coder", "devstral", "模型選擇", "模型策略"],
    "gap": ["gap analysis", "capability gap", "missing skill", "coverage", "skill installation", "缺口分析", "能力缺口", "覆蓋率", "技能安裝"],
}

_PROJECT_TOPIC_MAP = {
    "world-cup-2026": ["world cup", "世界杯", "football", "足球", "elo", "主場優勢", "賽事預測"],
    "email-agent": ["email", "郵件", "microsoft graph", "outlook", "自動回覆"],
    "linkedin-builder": ["linkedin", "個人資料", "profile", "職場"],
    "audit-engine": ["audit", "審計", "esg", "monica", "研究"],
    "voice-order": ["voice", "語音", "點餐", "order", "speech"],
    "audit-platform": ["audit platform", "審計平台", "efficiency", "效率", "工作流"],
    "business-plan": ["business plan", "商業計劃", "beeverse business"],
    "python-for-kids": ["kids", "兒童", "編程教學", "python 教學"],
    "ai-content-creator": ["content", "內容創作", "模板", "publisher", "發佈"],
}


class BeeVerseRAGRetriever:

    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = os.environ.get(
                "HARNESSING_ROOT", r"d:\My_Code_Projects\Harnessing"
            )
        self.root = Path(project_root)
        self._cache = {}

    def _read_file(self, relative_path: str) -> str:
        if relative_path in self._cache:
            return self._cache[relative_path]
        fp = self.root / relative_path
        try:
            content = fp.read_text(encoding="utf-8")
            self._cache[relative_path] = content
            return content
        except FileNotFoundError:
            return f"[File not found: {relative_path}]"

    def _classify_query(self, query: str) -> str:
        q = query.lower()

        rule_patterns = [
            r"\br(\d+)\b", r"\b規則\s*(\d+)", r"\brule\s*(\d+)",
            "rule", "規則", "r0", "r1", "r2", "r3", "r4", "r5",
            "r6", "r7", "r8", "r9",
        ]
        for p in rule_patterns:
            if re.search(p, q):
                return "rule"

        error_patterns = [
            r"\be(\d+)\b", r"\b教訓\s*(\d+)", r"\berror\s*(\d+)",
            "error", "教訓", "e1", "e2", "e3",
        ]
        for p in error_patterns:
            if re.search(p, q):
                return "error"

        decision_kw = ["decision", "決策", "d-0", "d-1", "d-2", "d-3", "為什麼選擇", "選擇理由"]
        for kw in decision_kw:
            if kw in q:
                return "decision"

        project_kw = []
        for kws in _PROJECT_TOPIC_MAP.values():
            project_kw.extend(kws)
        for kw in project_kw:
            if kw in q:
                return "project"

        knowledge_kw = []
        for kws in _KB_TOPIC_MAP.values():
            knowledge_kw.extend(kws)
        for kw in knowledge_kw:
            if kw in q:
                return "knowledge"

        skill_kw = ["skill", "技能", "s1", "s2", "s3", "能力"]
        for kw in skill_kw:
            if kw in q:
                return "skill"

        invention_kw = ["invention", "發明", "tier", "創新"]
        for kw in invention_kw:
            if kw in q:
                return "invention"

        method_kw = ["method", "方法論", "methodology", "情景代入", "組合創新", "迭代收斂"]
        for kw in method_kw:
            if kw in q:
                return "method"

        formula_kw = [
            "formula", "公式", "brainstorm", "運算符", "operator",
            "log(s+p)", "f²", "(c^h)", "8 operator", "8 運算符",
            "formula thinking", "公式思維", "8種運算符",
        ]
        for kw in formula_kw:
            if kw in q:
                return "formula"

        flow_kw = ["how", "如何", "process", "flow", "執行流程", "execution", "step"]
        for kw in flow_kw:
            if kw in q:
                return "flow"

        return "default"

    def _find_kb_files(self, query: str) -> list:
        q = query.lower()
        matched = []
        for kb_num, keywords in _KB_TOPIC_MAP.items():
            for kw in keywords:
                if kw in q:
                    matched.append(kb_num)
                    break
        return matched

    def _find_project_dirs(self, query: str) -> list:
        q = query.lower()
        matched = []
        for proj_name, keywords in _PROJECT_TOPIC_MAP.items():
            for kw in keywords:
                if kw in q:
                    matched.append(proj_name)
                    break
        return matched

    def _retrieve_from_kb(self, query: str) -> str:
        kb_nums = self._find_kb_files(query)
        if not kb_nums:
            return self._read_file("docs/knowledge-base/00-index.md")[:3000]

        results = []
        for kb_num in kb_nums:
            filename = f"docs/knowledge-base/{kb_num}-*.md"
            kb_dir = self.root / "docs" / "knowledge-base"
            if kb_dir.exists():
                for fp in kb_dir.iterdir():
                    if fp.name.startswith(f"{kb_num}-") and fp.suffix == ".md":
                        content = fp.read_text(encoding="utf-8")
                        results.append(self._extract_relevant_paragraphs(query, content, max_chars=4000))
                        break
        return "\n\n---\n\n".join(results) if results else self._read_file("docs/knowledge-base/00-index.md")[:3000]

    def _retrieve_from_agents(self, query: str) -> str:
        content = self._read_file("AGENTS.md")
        return self._extract_relevant_paragraphs(query, content, max_chars=4000)

    def _retrieve_from_decisions(self, query: str) -> str:
        content = self._read_file("data/decision-log.md")
        m = re.search(r"D-(\d+)", query, re.IGNORECASE)
        if m:
            target = f"D-{int(m.group(1)):03d}"
            pattern = re.compile(rf"^##\s*{re.escape(target)}", re.MULTILINE)
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if pattern.match(line.strip()):
                    end = len(lines)
                    for j in range(i + 1, len(lines)):
                        if re.match(r"^##\s*D-\d+", lines[j].strip()):
                            end = j
                            break
                    return "\n".join(lines[i:end])
        return self._extract_relevant_paragraphs(query, content, max_chars=4000)

    def _retrieve_from_projects(self, query: str) -> str:
        proj_dirs = self._find_project_dirs(query)
        if not proj_dirs:
            return self._read_file("AGENTS.md")[:2000]

        results = []
        for proj_name in proj_dirs:
            proj_path = self.root / "projects"
            for category_dir in proj_path.iterdir():
                if category_dir.is_dir():
                    target = category_dir / proj_name
                    if target.is_dir():
                        agents_file = target / "AGENTS.md"
                        if agents_file.exists():
                            content = agents_file.read_text(encoding="utf-8")
                            results.append(f"=== Project: {proj_name} ===\n{content}")
                        for py_file in target.glob("*.py"):
                            content = py_file.read_text(encoding="utf-8")
                            results.append(f"=== {py_file.name} ===\n{content[:3000]}")
                        break
        return "\n\n---\n\n".join(results) if results else "[No matching project found]"

    def _extract_relevant_paragraphs(self, query: str, content: str, max_chars: int = 8000) -> str:
        q_words = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]
        if not q_words:
            return content[:max_chars]

        paragraphs = re.split(r"\n\n+", content)
        scored = []
        for para in paragraphs:
            para_lower = para.lower()
            score = sum(1 for w in q_words if w in para_lower)
            if score > 0:
                scored.append((score, para))

        if not scored:
            return content[:max_chars]

        scored.sort(key=lambda x: x[0], reverse=True)
        result = []
        total = 0
        for score, para in scored:
            if total + len(para) > max_chars:
                break
            result.append(para)
            total += len(para)

        return "\n\n".join(result) if result else content[:max_chars]

    def _extract_rule(self, query: str, content: str) -> str:
        m = re.search(r"\bR?(\d+)\b", query, re.IGNORECASE)
        if not m:
            m = re.search(r"規則\s*(\d+)", query)
        if not m:
            m = re.search(r"rule\s*(\d+)", query, re.IGNORECASE)
        if not m:
            lines = content.split("\n")
            header_idx = None
            for i, line in enumerate(lines):
                if "KEY RULES" in line or "規則" in line.lower():
                    header_idx = i
                    break
            if header_idx is not None:
                return "\n".join(lines[header_idx:header_idx + 80])
            return content[:3000]

        rule_num = m.group(1)
        pattern = re.compile(
            rf"^(R{rule_num}\.|##\s*{rule_num}\.\s|R{rule_num}\b)",
            re.MULTILINE,
        )
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if pattern.match(line.strip()):
                start = max(0, i)
                end = len(lines)
                for j in range(i + 1, len(lines)):
                    if re.match(r"^(R\d+\.|##\s*\d+\.\s|R\d+\b)", lines[j].strip()):
                        end = j
                        break
                return "\n".join(lines[start:end])

        pattern2 = re.compile(rf"##\s*{rule_num}\.\s", re.MULTILINE)
        for i, line in enumerate(lines):
            if pattern2.match(line.strip()):
                start = max(0, i)
                end = len(lines)
                for j in range(i + 1, len(lines)):
                    if re.match(r"^##\s*\d+\.\s", lines[j].strip()):
                        end = j
                        break
                return "\n".join(lines[start:end])

        return content[:3000]

    def _extract_error(self, query: str, content: str) -> str:
        m = re.search(r"\bE(\d+)\b", query, re.IGNORECASE)
        if not m:
            m = re.search(r"教訓\s*(\d+)", query)
        if not m:
            m = re.search(r"error\s*(\d+)", query, re.IGNORECASE)

        if _YAML_AVAILABLE:
            try:
                data = yaml.safe_load(content)
                rules = data.get("rules", [])
                if m:
                    target_id = f"R-ERR-{int(m.group(1)):03d}"
                    for r in rules:
                        if r.get("id") == target_id:
                            parts = [
                                f"ID: {r.get('id')}",
                                f"Error: {r.get('error')}",
                                f"Root Cause: {r.get('root_cause')}",
                                f"Rule: {r.get('rule')}",
                                f"Source: {r.get('source')}",
                                f"Verified: {r.get('verified')}",
                            ]
                            if r.get("implementation"):
                                parts.append(f"Implementation: {r['implementation']}")
                            return "\n".join(parts)
                    return f"[Error rule {target_id} not found]"
                summary = []
                for r in rules:
                    summary.append(
                        f"{r.get('id')}: {r.get('rule')[:80]}"
                    )
                return "\n".join(summary)
            except yaml.YAMLError:
                pass

        if m:
            target_id = f"R-ERR-{int(m.group(1)):03d}"
            pattern = re.compile(
                rf'- id:\s*["\']?{re.escape(target_id)}["\']?',
                re.MULTILINE,
            )
            match = pattern.search(content)
            if match:
                start = match.start()
                next_match = re.search(r"\n\s*-\s*id:", content[start + 10:])
                if next_match:
                    end = start + 10 + next_match.start()
                else:
                    end = len(content)
                return content[start:end].strip()
            return f"[Error rule {target_id} not found]"

        lines = content.split("\n")
        header_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith("- id:"):
                header_idx = i
                break
        if header_idx is not None:
            return "\n".join(lines[header_idx:header_idx + 60])
        return content[:3000]

    def _extract_section(self, content: str, section_markers: list) -> str:
        lines = content.split("\n")
        start_idx = None
        for i, line in enumerate(lines):
            for marker in section_markers:
                if marker in line:
                    start_idx = i
                    break
            if start_idx is not None:
                break
        if start_idx is None:
            return content[:3000]

        end_idx = len(lines)
        section_headers = [
            "=== ALL INVENTIONS", "=== ALL SKILLS", "=== KEY RULES",
            "=== ALL ERROR", "=== SUB-PROJECTS", "=== BEEVERSE EXECUTION",
            "=== WHEN RESPONDING", "=== METHODOLOGY",
        ]
        for j in range(start_idx + 1, len(lines)):
            for hdr in section_headers:
                if hdr in lines[j]:
                    end_idx = j
                    break
            if end_idx != len(lines):
                break
        return "\n".join(lines[start_idx:end_idx])

    def _extract_skill_section(self, content: str) -> str:
        return self._extract_section(content, ["=== ALL SKILLS", "SKILLS ("])

    def _extract_invention_section(self, content: str) -> str:
        return self._extract_section(content, ["=== ALL INVENTIONS", "INVENTIONS ("])

    def _extract_method_section(self, content: str) -> str:
        return self._extract_section(content, ["=== METHODOLOGY 1", "METHODOLOGY 1"])

    def _extract_formula_section(self, content: str) -> str:
        return self._extract_section(content, ["=== METHODOLOGY 2", "METHODOLOGY 2"])

    def _extract_flow_section(self, content: str) -> str:
        return self._extract_section(content, ["=== BEEVERSE EXECUTION", "EXECUTION FLOW"])

    def _extract_quick_reference(self, content: str) -> str:
        return self._extract_section(content, ["=== QUICK REFERENCE", "QUICK REFERENCE"])

    def _multi_source_search(self, query: str) -> str:
        results = []

        kb_context = self._retrieve_from_kb(query)
        if kb_context and "[File not found]" not in kb_context:
            results.append(f"[KNOWLEDGE BASE]\n{kb_context}")

        agents_context = self._retrieve_from_agents(query)
        if agents_context and len(agents_context) > 50:
            results.append(f"[PROJECT CONTEXT]\n{agents_context[:6000]}")

        proj_context = self._retrieve_from_projects(query)
        if proj_context and "[No matching project" not in proj_context:
            results.append(f"[SUB-PROJECT]\n{proj_context[:6000]}")

        decision_context = self._retrieve_from_decisions(query)
        if decision_context and len(decision_context) > 50:
            results.append(f"[DECISION LOG]\n{decision_context[:4000]}")

        modelfile_content = self._read_file("config/Modelfile.full")
        qr = self._extract_quick_reference(modelfile_content)
        results.append(f"[BEEVERSE REFERENCE]\n{qr}")

        return "\n\n---\n\n".join(results)

    def retrieve_context(self, query: str) -> str:
        category = self._classify_query(query)

        if category == "rule":
            content = self._read_file(".trae/rules/project_rules.md")
            return self._extract_rule(query, content)

        if category == "error":
            content = self._read_file("data/error-rules.yaml")
            return self._extract_error(query, content)

        if category == "decision":
            return self._retrieve_from_decisions(query)

        if category == "project":
            return self._retrieve_from_projects(query)

        if category == "knowledge":
            return self._retrieve_from_kb(query)

        if category == "skill":
            content = self._read_file("config/Modelfile.full")
            return self._extract_skill_section(content)

        if category == "invention":
            content = self._read_file("config/Modelfile.full")
            return self._extract_invention_section(content)

        if category == "method":
            content = self._read_file("config/Modelfile.full")
            return self._extract_method_section(content)

        if category == "formula":
            content = self._read_file("config/Modelfile.full")
            return self._extract_formula_section(content)

        if category == "flow":
            content = self._read_file("config/Modelfile.full")
            return self._extract_flow_section(content)

        parts = []
        base = self._multi_source_search(query)
        if base:
            parts.append(base)

        gap_keywords = ["gap", "capability", "missing", "coverage", "improve", "install skill"]
        if any(kw in query.lower() for kw in gap_keywords):
            try:
                from .beeverse_skill_gap_analyzer import BeeVerseSkillGapAnalyzer
                ga = BeeVerseSkillGapAnalyzer()
                report = ga.analyze()
                gap_summary = f"[Gap Analysis] Coverage: {report.overall_coverage:.1f}%, Missing: {report.missing_count}, Critical: {len(report.critical_gaps)}"
                parts.append(gap_summary)
            except Exception:
                pass

        return "\n\n---\n\n".join(parts) if parts else ""

    def clear_cache(self):
        self._cache = {}
