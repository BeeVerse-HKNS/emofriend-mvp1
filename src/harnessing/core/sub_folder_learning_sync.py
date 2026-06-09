from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .auto_rule_learner import AutoRuleLearner


@dataclass
class Learning:
    source_path: str
    type: str
    text: str
    signature: str
    raw_id: Optional[str] = None
    line_no: int = 0


@dataclass
class SyncReport:
    subfolders_scanned: int
    learnings_extracted: int
    new_rules_added: int
    errors: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0
    timestamp: str = ""
    subfolders_list: List[str] = field(default_factory=list)
    new_rule_signatures: List[str] = field(default_factory=list)


class SubFolderLearningSync:
    PATTERN_DECISION = re.compile(r"^###\s+D-(\d+)\s*[:：]\s*(.+)$", re.MULTILINE)
    PATTERN_DECISION_ALT = re.compile(r"^###\s+D-(\d+)\s*\|\s*", re.MULTILINE)
    PATTERN_RULE_NUMBERED = re.compile(r"^##\s+(\d+)\.\s+", re.MULTILINE)
    PATTERN_RULE_KEYWORD = re.compile(r"^##\s+Rule\s+(\d+)\s*[:：]?\s*(.+)$", re.MULTILINE | re.IGNORECASE)
    PATTERN_BULLET_RULE = re.compile(r"^-\s+\*\*Rule\s+(\d+)\*\*", re.MULTILINE | re.IGNORECASE)
    SOURCE_FILES = ("AGENTS.md", "decision-log.md", "tasks.md", "README.md")

    def __init__(
        self,
        projects_root: str = "d:/My_Code_Projects/Harnessing/projects",
        master_rules_path: str = ".trae/rules/project_rules.md",
        rule_learner: Optional[AutoRuleLearner] = None,
    ) -> None:
        self.projects_root = projects_root
        self.master_rules_path = master_rules_path
        self.rule_learner = rule_learner or AutoRuleLearner()
        self._existing_signatures: Set[str] = set()
        self._refresh_existing_signatures()

    def _refresh_existing_signatures(self) -> None:
        self._existing_signatures = set()
        if not os.path.exists(self.master_rules_path):
            return
        try:
            with open(self.master_rules_path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return
        for sig in re.findall(r"簽名: `([a-zA-Z0-9_]+)`", content):
            self._existing_signatures.add(sig)
        for title in re.findall(r"^##\s+\d+\.\s+(.+?)\s+規則", content, re.MULTILINE):
            self._existing_signatures.add(self._hash_title(title))
        for title in re.findall(r"^##\s+AutoRule:\s+(.+?)\s+規則", content, re.MULTILINE):
            self._existing_signatures.add(self._hash_title(title))

    def _hash_title(self, title: str) -> str:
        return hashlib.md5(title.strip().lower().encode("utf-8")).hexdigest()[:12]

    def scan_subfolders(self) -> List[str]:
        if not os.path.isdir(self.projects_root):
            return []
        subfolders: List[str] = []
        for entry in sorted(os.listdir(self.projects_root)):
            full = os.path.join(self.projects_root, entry)
            if os.path.isdir(full) and not entry.startswith("."):
                subfolders.append(full)
        return subfolders

    def extract_learnings(self, subfolder: str) -> List[Learning]:
        learnings: List[Learning] = []
        for fname in self.SOURCE_FILES:
            path = os.path.join(subfolder, fname)
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue
            learnings.extend(self._extract_decisions(path, content))
            learnings.extend(self._extract_rules(path, content))
        return learnings

    def _extract_decisions(self, path: str, content: str) -> List[Learning]:
        learnings: List[Learning] = []
        for m in self.PATTERN_DECISION.finditer(content):
            d_id = m.group(1)
            title = m.group(2).strip()
            line_no = content[: m.start()].count("\n") + 1
            text = self._extract_block(content, m.start())
            signature = self._decision_signature(d_id, title)
            learnings.append(Learning(
                source_path=path,
                type="decision",
                text=text,
                signature=signature,
                raw_id=f"D-{d_id}",
                line_no=line_no,
            ))
        for m in self.PATTERN_DECISION_ALT.finditer(content):
            d_id = m.group(1)
            signature = self._decision_signature(d_id, "")
            if any(l.signature == signature for l in learnings):
                continue
            line_no = content[: m.start()].count("\n") + 1
            text = self._extract_block(content, m.start())
            learnings.append(Learning(
                source_path=path,
                type="decision",
                text=text,
                signature=signature,
                raw_id=f"D-{d_id}",
                line_no=line_no,
            ))
        return learnings

    def _extract_rules(self, path: str, content: str) -> List[Learning]:
        learnings: List[Learning] = []
        for m in self.PATTERN_RULE_NUMBERED.finditer(content):
            n = m.group(1)
            line_no = content[: m.start()].count("\n") + 1
            text = self._extract_block(content, m.start())
            signature = self._rule_signature(n, text)
            learnings.append(Learning(
                source_path=path,
                type="rule",
                text=text,
                signature=signature,
                raw_id=f"Rule-{n}",
                line_no=line_no,
            ))
        for m in self.PATTERN_RULE_KEYWORD.finditer(content):
            n = m.group(1)
            title = m.group(2).strip()
            line_no = content[: m.start()].count("\n") + 1
            text = self._extract_block(content, m.start())
            signature = self._rule_signature(n, title)
            if any(l.signature == signature for l in learnings):
                continue
            learnings.append(Learning(
                source_path=path,
                type="rule",
                text=text,
                signature=signature,
                raw_id=f"Rule-{n}",
                line_no=line_no,
            ))
        return learnings

    def _extract_block(self, content: str, start: int, max_len: int = 400) -> str:
        rest = content[start:]
        lines = rest.split("\n")
        collected: List[str] = []
        total = 0
        for line in lines[:6]:
            if total + len(line) > max_len:
                break
            collected.append(line)
            total += len(line)
        return "\n".join(collected).strip()

    def _decision_signature(self, d_id: str, title: str) -> str:
        h = hashlib.md5(f"D-{d_id}-{title}".encode("utf-8")).hexdigest()[:12]
        return f"DEC-{d_id}-{h}"

    def _rule_signature(self, n: str, body: str) -> str:
        h = hashlib.md5(f"R-{n}-{body[:80]}".encode("utf-8")).hexdigest()[:12]
        return f"RULE-{n}-{h}"

    def dedupe_against_master(self, learnings: List[Learning]) -> List[Learning]:
        unique: List[Learning] = []
        seen: Set[str] = set()
        for l in learnings:
            if l.signature in self._existing_signatures:
                continue
            if l.signature in seen:
                continue
            seen.add(l.signature)
            unique.append(l)
        return unique

    def _convert_to_rule(self, learning: Learning) -> str:
        title = re.sub(r"[^A-Za-z0-9_]+", " ", learning.text[:60]).strip()
        if not title:
            title = f"SubFolder-{learning.raw_id or 'Unknown'}"
        title = title.title()[:50]
        body = learning.text.replace("`", "'")[:300]
        rule = [
            f"## AutoRule: {title} 規則",
            "",
            f"從子資料夾自動同步嘅規則（{learning.raw_id or learning.type}）。",
            "",
            "### 核心原則",
            f"- 子資料夾學習必須自動同步到 master project_rules.md",
            f"- 規則來源：{learning.source_path}",
            f"- 類型：{learning.type}",
            "- 自動同步必須經過 dedupe + signature 校驗",
            "",
            "### 硬性約束",
            "- 不得將子資料夾嘅同一條規則重複加入 master",
            "- 必須保留 source_path 同 raw_id 供追溯",
            "- 規則內容不得包含 API Key / 密碼 / 個人資料",
            "",
            "### 內容摘要",
            f"```",
            f"{body}",
            f"```",
            "",
            f"> 自動同步自 `{learning.source_path}` (line {learning.line_no}) — 簽名: `{learning.signature}`",
        ]
        return "\n".join(rule)

    def merge_to_master(self, new_learnings: List[Learning]) -> int:
        added = 0
        for l in new_learnings:
            rule_text = self._convert_to_rule(l)
            if self.rule_learner.append_to_master(rule_text, self.master_rules_path):
                self._existing_signatures.add(l.signature)
                added += 1
        return added

    def sync_all(self) -> SyncReport:
        started = time.time()
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        errors: List[str] = []
        subfolders = self.scan_subfolders()
        all_learnings: List[Learning] = []
        for sf in subfolders:
            try:
                all_learnings.extend(self.extract_learnings(sf))
            except Exception as e:
                errors.append(f"{sf}: {e}")
        new_unique = self.dedupe_against_master(all_learnings)
        added = self.merge_to_master(new_unique)
        elapsed = (time.time() - started) * 1000.0
        return SyncReport(
            subfolders_scanned=len(subfolders),
            learnings_extracted=len(all_learnings),
            new_rules_added=added,
            errors=errors,
            elapsed_ms=elapsed,
            timestamp=timestamp,
            subfolders_list=subfolders,
            new_rule_signatures=[l.signature for l in new_unique[:added]],
        )

    def stats(self) -> Dict[str, object]:
        return {
            "projects_root": self.projects_root,
            "master_rules_path": self.master_rules_path,
            "existing_signatures": len(self._existing_signatures),
            "source_files": list(self.SOURCE_FILES),
            "rule_learner": self.rule_learner.stats(),
        }
