from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ObservationRecord:
    id: int
    text: str
    category: str
    created_at: float


@dataclass
class ErrorRecord:
    signature: str
    occurrence: int
    first_seen: float
    last_seen: float
    samples: List[str] = field(default_factory=list)


@dataclass
class GeneratedRule:
    signature: str
    rule_text: str
    occurrence: int
    is_duplicate: bool
    appended: bool


class AutoRuleLearner:
    DEFAULT_THRESHOLD = 3
    RULE_TITLE_PREFIX = "##"

    def __init__(self, db_path: str = "data/auto_rule_learner.db", threshold: int = DEFAULT_THRESHOLD) -> None:
        self.db_path = db_path
        self.threshold = threshold
        self._ensure_db()
        self._generated_rules: List[GeneratedRule] = []

    def _ensure_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    signature TEXT PRIMARY KEY,
                    occurrence INTEGER NOT NULL DEFAULT 0,
                    first_seen REAL NOT NULL,
                    last_seen REAL NOT NULL,
                    samples TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    category TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

    def record_error(self, error_signature: str, context: str) -> int:
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT occurrence, samples FROM errors WHERE signature = ?",
                (error_signature,),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO errors (signature, occurrence, first_seen, last_seen, samples) VALUES (?, ?, ?, ?, ?)",
                    (error_signature, 1, now, now, context),
                )
                conn.commit()
                return 1
            occurrence, samples = row
            sample_list = [s for s in samples.split("\n---\n") if s]
            if context and context not in sample_list:
                sample_list.append(context)
                if len(sample_list) > 5:
                    sample_list = sample_list[-5:]
            new_occurrence = occurrence + 1
            conn.execute(
                "UPDATE errors SET occurrence = ?, last_seen = ?, samples = ? WHERE signature = ?",
                (new_occurrence, now, "\n---\n".join(sample_list), error_signature),
            )
            conn.commit()
            return new_occurrence

    def record_observation(self, text: str, category: str) -> None:
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO observations (text, category, created_at) VALUES (?, ?, ?)",
                (text, category, now),
            )
            conn.commit()

    def should_generate_rule(self, error_signature: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT occurrence FROM errors WHERE signature = ?",
                (error_signature,),
            ).fetchone()
        if row is None:
            return False
        return row[0] >= self.threshold

    def get_error_record(self, error_signature: str) -> Optional[ErrorRecord]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT signature, occurrence, first_seen, last_seen, samples FROM errors WHERE signature = ?",
                (error_signature,),
            ).fetchone()
        if row is None:
            return None
        sig, occ, first, last, samples = row
        return ErrorRecord(
            signature=sig,
            occurrence=occ,
            first_seen=first,
            last_seen=last,
            samples=[s for s in samples.split("\n---\n") if s],
        )

    def generate_rule(self, error_signature: str, samples: Optional[List[str]] = None) -> str:
        record = self.get_error_record(error_signature)
        if record is None:
            record = ErrorRecord(
                signature=error_signature,
                occurrence=0,
                first_seen=time.time(),
                last_seen=time.time(),
                samples=samples or [],
            )
        if samples:
            record.samples = (record.samples + samples)[-5:]
        safe_sig = re.sub(r"[^A-Za-z0-9_]+", "_", error_signature)[:48]
        slug = self._humanize(error_signature)
        timestamp = time.strftime("%Y-%m-%d", time.gmtime(record.first_seen))
        core = [
            f"## AutoRule: {slug} 規則",
            "",
            f"自動從錯誤簽名 `{error_signature}` 推導（出現 {record.occurrence} 次，首次記錄 {timestamp}）。",
            "",
            "### 核心原則",
            f"- 必須在首次偵測到 `{error_signature}` 時立即記錄到 error-rules.yaml",
            f"- 同類錯誤累計 {self.threshold}+ 次必須轉化為可執行防護代碼",
            f"- 修復必須同步到 project_rules.md + error-rules.yaml + SKILL.md（Rule 82 復利式修復）",
            f"- 每次重現必須提供 1 個 reproduction case 寫入 error_ecosystem_state.json",
            "",
            "### 硬性約束",
            f"- 不得跳過 `{error_signature}` 防護直接執行（避免 silent failure）",
            f"- 同類錯誤第 {self.threshold}+ 次必須 raise 而非 log.warning（CRITICAL 違規）",
            f"- 修復方案必須包含 detection mechanism + auto-fix code + test case 三件套",
            "- 不得只改 Prompt 而不改 Harness（Rule 82）",
            f"- 違規必須記錄到 `data/auto_rule_learner.db` 同 `data/error-rules.yaml`",
            "",
            "### 樣本",
        ]
        for s in (record.samples or samples or [])[:3]:
            core.append(f"- `{s[:80]}`")
        core.append("")
        core.append(f"> 自動生成於 {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} — 簽名: `{safe_sig}`")
        return "\n".join(core)

    def dedupe_against_existing(self, new_rule: str, rules_path: str) -> bool:
        if not os.path.exists(rules_path):
            return True
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                existing = f.read()
        except OSError:
            return True
        new_hash = self._rule_signature(new_rule)
        existing_hashes = re.findall(r"簽名: `([a-zA-Z0-9_]+)`", existing)
        if new_hash in existing_hashes:
            return False
        title_match = re.search(r"^##\s+AutoRule:\s+(.+?)\s+規則", new_rule, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            if f"## AutoRule: {title} 規則" in existing:
                return False
            if f"## AutoRule: {title}" in existing:
                return False
        sig_match = re.search(r"`([a-zA-Z0-9_./:]{8,80})`", new_rule)
        if sig_match:
            sig = sig_match.group(1)
            if sig in existing:
                return False
        return True

    def append_to_master(self, rule_text: str, rules_path: str) -> bool:
        if not self.dedupe_against_existing(rule_text, rules_path):
            return False
        os.makedirs(os.path.dirname(rules_path) or ".", exist_ok=True)
        sep = "\n\n" if os.path.exists(rules_path) and os.path.getsize(rules_path) > 0 else ""
        with open(rules_path, "a", encoding="utf-8") as f:
            f.write(sep + rule_text + "\n")
        return True

    def process_error(self, error_signature: str, context: str, rules_path: str) -> GeneratedRule:
        occurrence = self.record_error(error_signature, context)
        if not self.should_generate_rule(error_signature):
            return GeneratedRule(
                signature=error_signature,
                rule_text="",
                occurrence=occurrence,
                is_duplicate=False,
                appended=False,
            )
        record = self.get_error_record(error_signature) or ErrorRecord(
            signature=error_signature, occurrence=occurrence,
            first_seen=time.time(), last_seen=time.time(), samples=[context],
        )
        rule_text = self.generate_rule(error_signature, record.samples)
        is_dup = not self.dedupe_against_existing(rule_text, rules_path)
        appended = False
        if not is_dup:
            appended = self.append_to_master(rule_text, rules_path)
        record_entry = GeneratedRule(
            signature=error_signature,
            rule_text=rule_text,
            occurrence=occurrence,
            is_duplicate=is_dup,
            appended=appended,
        )
        self._generated_rules.append(record_entry)
        return record_entry

    def _rule_signature(self, rule_text: str) -> str:
        h = hashlib.md5(rule_text.encode("utf-8")).hexdigest()[:12]
        sig_match = re.search(r"簽名: `([a-zA-Z0-9_]+)`", rule_text)
        return sig_match.group(1) if sig_match else h

    def _humanize(self, text: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9]+", " ", text).strip()
        return cleaned.title()[:60] if cleaned else "UnnamedError"

    def get_recent_observations(self, limit: int = 20) -> List[ObservationRecord]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, text, category, created_at FROM observations ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            ObservationRecord(id=r[0], text=r[1], category=r[2], created_at=r[3])
            for r in rows
        ]

    def get_top_errors(self, limit: int = 10) -> List[ErrorRecord]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT signature, occurrence, first_seen, last_seen, samples FROM errors ORDER BY occurrence DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            ErrorRecord(
                signature=r[0], occurrence=r[1], first_seen=r[2], last_seen=r[3],
                samples=[s for s in r[4].split("\n---\n") if s],
            )
            for r in rows
        ]

    def stats(self) -> Dict[str, object]:
        with sqlite3.connect(self.db_path) as conn:
            error_count = conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
            total_occurrences = conn.execute("SELECT COALESCE(SUM(occurrence), 0) FROM errors").fetchone()[0]
            obs_count = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        return {
            "db_path": self.db_path,
            "threshold": self.threshold,
            "error_signatures": error_count,
            "total_error_occurrences": total_occurrences,
            "observations": obs_count,
            "generated_rules": len(self._generated_rules),
        }
