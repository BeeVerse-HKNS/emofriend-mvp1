"""
Abandonment Detector (R-ERR-084)
D-100 Daily Learning Cycle 2026-06-03

偵測並防止「三大應用場景半途而廢」問題：
- M1: 5 平台開通 + 第 1 集影片
- M3: 知識星球 + 直播帶貨
- M6: 評估助理 + 投資設備

通用半途而廢模式：
1. 開始但無後續（STARTED_NO_FOLLOWUP）
2. 規劃但無執行（PLANNED_NO_EXECUTION）
3. 投資但無回報（INVESTED_NO_RETURN）

7 日無進度自動觸發提醒，根據任務複雜度自動重啟或人類介入。

信心等級：🔍 已研究（基於 D-100 用戶反饋 + ByteDance DeerFlow 2.0）
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class AbandonmentPattern(str, Enum):
    """半途而廢模式分類"""
    STARTED_NO_FOLLOWUP = "STARTED_NO_FOLLOWUP"  # 開始但無後續
    PLANNED_NO_EXECUTION = "PLANNED_NO_EXECUTION"  # 規劃但無執行
    INVESTED_NO_RETURN = "INVESTED_NO_RETURN"  # 投資但無回報


class TaskComplexity(str, Enum):
    """任務複雜度"""
    SIMPLE = "SIMPLE"  # < 4 小時工作量
    COMPLEX = "COMPLEX"  # >= 4 小時工作量


class ActionType(str, Enum):
    """自動觸發嘅行動"""
    REMIND = "REMIND"  # 自動提醒
    AUTO_RESTART = "AUTO_RESTART"  # 自動重啟（簡單任務）
    ESCALATE = "ESCALATE"  # 升級人類介入（複雜任務）
    NO_ACTION = "NO_ACTION"  # 唔行動


@dataclass
class MilestoneScenario:
    """M1/M3/M6 應用場景定義"""
    code: str  # M1, M3, M6
    name: str
    description: str
    abandonment_triggers: list[str]
    critical_milestones: list[str]


@dataclass
class TaskRecord:
    """任務記錄"""
    id: str
    name: str
    scenario_code: Optional[str]  # M1/M3/M6 或 None
    pattern: AbandonmentPattern
    complexity: TaskComplexity
    status: str  # PENDING / IN_PROGRESS / COMPLETED / ABANDONED
    created_at: str
    last_update: str
    estimated_hours: float
    progress: float = 0.0  # 0-1
    metadata: dict[str, Any] = field(default_factory=dict)

    def days_since_update(self) -> float:
        last = datetime.fromisoformat(self.last_update)
        now = datetime.now(timezone.utc)
        return (now - last).total_seconds() / 86400


@dataclass
class AbandonmentAlert:
    """半途而廢告警"""
    task_id: str
    task_name: str
    pattern: AbandonmentPattern
    days_inactive: float
    action: ActionType
    message: str
    options: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


DEFAULT_INACTIVITY_DAYS = 7


class AbandonmentDetector:
    """半途而廢偵測器 — 從文字規則升級為可執行代碼 (R-ERR-084)"""

    def __init__(
        self,
        db_path: str | Path = "data/tasks.db",
        inactivity_days: int = DEFAULT_INACTIVITY_DAYS,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.inactivity_days = inactivity_days
        self._scenarios = self._load_default_scenarios()
        self._init_schema()

    def _load_default_scenarios(self) -> dict[str, MilestoneScenario]:
        return {
            "M1": MilestoneScenario(
                code="M1",
                name="5 平台開通 + 第 1 集影片",
                description="YouTube/B站/小紅書/微信公眾號/視頻號 開通 + 首支影片發佈",
                abandonment_triggers=[
                    "平台開通後 7 日無影片上傳",
                    "影片製作中途放棄",
                    "Baidu AI Studio URL 48 小時過期後無補救",
                ],
                critical_milestones=[
                    "5 平台賬號全部開通",
                    "第 1 集影片完成並上傳",
                    "獲得首 100 觀看",
                ],
            ),
            "M3": MilestoneScenario(
                code="M3",
                name="知識星球 + 直播帶貨",
                description="知識星球運營 + 直播帶貨冷啟動",
                abandonment_triggers=[
                    "知識星球創建後 7 日無內容發佈",
                    "直播準備完成但無實際開播",
                    "選品完成但無上架",
                ],
                critical_milestones=[
                    "知識星球建立並定價",
                    "首次直播成功",
                    "首筆訂單成交",
                ],
            ),
            "M6": MilestoneScenario(
                code="M6",
                name="評估助理 + 投資設備",
                description="評估是否雇傭助理 + 投資設備升級",
                abandonment_triggers=[
                    "評估啟動後 30 日無結論",
                    "設備研究完成但無購買決策",
                    "預算規劃後無執行",
                ],
                critical_milestones=[
                    "完成成本效益分析",
                    "設備升級方案確定",
                    "投資回報期預估",
                ],
            ),
        }

    def _init_schema(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    scenario_code TEXT,
                    pattern TEXT NOT NULL,
                    complexity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_update TEXT NOT NULL,
                    estimated_hours REAL NOT NULL,
                    progress REAL DEFAULT 0.0,
                    metadata_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_last_update ON tasks(last_update);
                CREATE INDEX IF NOT EXISTS idx_tasks_scenario ON tasks(scenario_code);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    days_inactive REAL NOT NULL,
                    action TEXT NOT NULL,
                    message TEXT NOT NULL,
                    options_json TEXT,
                    timestamp TEXT NOT NULL,
                    resolved INTEGER DEFAULT 0,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                );
                """
            )
            conn.commit()

    def get_scenario(self, code: str) -> Optional[MilestoneScenario]:
        """獲取 M1/M3/M6 場景定義"""
        return self._scenarios.get(code)

    def get_all_scenarios(self) -> list[MilestoneScenario]:
        """獲取所有場景"""
        return list(self._scenarios.values())

    def register_task(self, task: TaskRecord) -> None:
        """註冊任務"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO tasks
                (id, name, scenario_code, pattern, complexity,
                 status, created_at, last_update, estimated_hours,
                 progress, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.id,
                    task.name,
                    task.scenario_code,
                    task.pattern.value,
                    task.complexity.value,
                    task.status,
                    task.created_at,
                    task.last_update,
                    task.estimated_hours,
                    task.progress,
                    str(task.metadata),
                ),
            )
            conn.commit()

    def update_task_progress(self, task_id: str, progress: float) -> bool:
        """更新任務進度"""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute(
                "UPDATE tasks SET progress = ?, last_update = ? WHERE id = ?",
                (progress, now, task_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def detect_abandonment(self) -> list[AbandonmentAlert]:
        """偵測所有半途而廢任務並生成告警"""
        alerts = []
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                """SELECT id, name, scenario_code, pattern, complexity, status,
                          created_at, last_update, estimated_hours, progress
                   FROM tasks
                   WHERE status IN ('PENDING', 'IN_PROGRESS')"""
            ).fetchall()

        for row in rows:
            task = self._row_to_task(row)
            if task.days_since_update() < self.inactivity_days:
                continue
            alert = self._create_alert(task)
            if alert.action != ActionType.NO_ACTION:
                alerts.append(alert)
                self._save_alert(alert)
        return alerts

    def _row_to_task(self, row: tuple[Any, ...]) -> TaskRecord:
        return TaskRecord(
            id=row[0],
            name=row[1],
            scenario_code=row[2],
            pattern=AbandonmentPattern(row[3]),
            complexity=TaskComplexity(row[4]),
            status=row[5],
            created_at=row[6],
            last_update=row[7],
            estimated_hours=row[8],
            progress=row[9],
        )

    def _create_alert(self, task: TaskRecord) -> AbandonmentAlert:
        days_inactive = task.days_since_update()
        # 簡單任務自動重啟，複雜任務人類介入
        if task.complexity == TaskComplexity.SIMPLE and days_inactive >= self.inactivity_days:
            return AbandonmentAlert(
                task_id=task.id,
                task_name=task.name,
                pattern=task.pattern,
                days_inactive=days_inactive,
                action=ActionType.AUTO_RESTART,
                message=f"簡單任務已 {days_inactive:.1f} 日無進度，將自動重啟",
                options=["查看詳情", "延遲重啟", "手動標記完成"],
            )
        if task.complexity == TaskComplexity.COMPLEX and days_inactive >= self.inactivity_days:
            return AbandonmentAlert(
                task_id=task.id,
                task_name=task.name,
                pattern=task.pattern,
                days_inactive=days_inactive,
                action=ActionType.ESCALATE,
                message=f"複雜任務已 {days_inactive:.1f} 日無進度，建議人類介入",
                options=["重啟任務", "放棄任務", "重新規劃"],
            )
        return AbandonmentAlert(
            task_id=task.id,
            task_name=task.name,
            pattern=task.pattern,
            days_inactive=days_inactive,
            action=ActionType.REMIND,
            message=f"任務已 {days_inactive:.1f} 日無進度",
        )

    def _save_alert(self, alert: AbandonmentAlert) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """INSERT INTO alerts (task_id, pattern, days_inactive, action, message, options_json, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    alert.task_id,
                    alert.pattern.value,
                    alert.days_inactive,
                    alert.action.value,
                    alert.message,
                    str(alert.options),
                    alert.timestamp,
                ),
            )
            conn.commit()

    def get_pending_alerts(self) -> list[AbandonmentAlert]:
        """獲取未解決嘅告警"""
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                """SELECT task_id, pattern, days_inactive, action,
                   message, options_json, timestamp
                   FROM alerts WHERE resolved = 0
                   ORDER BY timestamp DESC"""
            ).fetchall()
        return [
            AbandonmentAlert(
                task_id=r[0],
                task_name="",
                pattern=AbandonmentPattern(r[1]),
                days_inactive=r[2],
                action=ActionType(r[3]),
                message=r[4],
                options=eval(r[5]) if r[5] else [],
                timestamp=r[6],
            )
            for r in rows
        ]

    def resolve_alert(self, task_id: str) -> bool:
        """標記告警為已解決"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute(
                "UPDATE alerts SET resolved = 1 WHERE task_id = ?",
                (task_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def estimate_complexity(self, estimated_hours: float) -> TaskComplexity:
        """根據預估工時判斷任務複雜度"""
        return TaskComplexity.SIMPLE if estimated_hours < 4 else TaskComplexity.COMPLEX
