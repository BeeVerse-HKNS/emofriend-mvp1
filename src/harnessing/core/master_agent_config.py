"""
Master Agent 配置文件

定義 Master Agent 系統嘅所有配置選項。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class AutoScanConfig:
    enabled: bool = True
    interval_seconds: int = 300
    projects_dir: str = "projects"


@dataclass
class BugDetectionConfig:
    enabled: bool = True
    static_analysis: bool = True
    git_analysis: bool = True
    dependency_scan: bool = True
    security_scan: bool = True


@dataclass
class DashboardConfig:
    cli_enabled: bool = True
    web_enabled: bool = True
    web_port: int = 11436
    websocket_enabled: bool = True


@dataclass
class SelfLearningConfig:
    enabled: bool = True
    learn_from_subprojects: bool = True
    update_master_md: bool = True
    enhance_rules: bool = True
    feedback_weight: float = 0.8


@dataclass
class AlertConfig:
    channels: list[str] = field(default_factory=lambda: ["cli", "log"])
    severity_threshold: str = "medium"


@dataclass
class MasterAgentConfig:
    auto_scan: AutoScanConfig = field(default_factory=AutoScanConfig)
    bug_detection: BugDetectionConfig = field(default_factory=BugDetectionConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    self_learning: SelfLearningConfig = field(default_factory=SelfLearningConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)

    @classmethod
    def from_yaml(cls, path: str) -> "MasterAgentConfig":
        config_path = Path(path)
        if not config_path.exists():
            return cls()
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            master_data = data.get("master_agent", {})
            
            auto_scan_data = master_data.get("auto_scan", {})
            auto_scan = AutoScanConfig(
                enabled=auto_scan_data.get("enabled", True),
                interval_seconds=auto_scan_data.get("interval_seconds", 300),
                projects_dir=auto_scan_data.get("projects_dir", "projects"),
            )
            
            bug_data = master_data.get("bug_detection", {})
            bug_detection = BugDetectionConfig(
                enabled=bug_data.get("enabled", True),
                static_analysis=bug_data.get("static_analysis", {}).get("enabled", True),
                git_analysis=bug_data.get("git_analysis", {}).get("enabled", True),
                dependency_scan=bug_data.get("dependency_scan", {}).get("enabled", True),
                security_scan=bug_data.get("security_scan", {}).get("enabled", True),
            )
            
            dashboard_data = master_data.get("dashboard", {})
            dashboard = DashboardConfig(
                cli_enabled=dashboard_data.get("cli", {}).get("enabled", True),
                web_enabled=dashboard_data.get("web", {}).get("enabled", True),
                web_port=dashboard_data.get("web", {}).get("port", 11436),
                websocket_enabled=dashboard_data.get("web", {}).get("websocket", True),
            )
            
            learning_data = master_data.get("self_learning", {})
            self_learning = SelfLearningConfig(
                enabled=learning_data.get("enabled", True),
                learn_from_subprojects=learning_data.get("learn_from_subprojects", True),
                update_master_md=learning_data.get("update_master_md", True),
                enhance_rules=learning_data.get("enhance_rules", True),
                feedback_weight=learning_data.get("feedback_weight", 0.8),
            )
            
            alerts_data = master_data.get("alerts", {})
            alerts = AlertConfig(
                channels=alerts_data.get("channels", ["cli", "log"]),
                severity_threshold=alerts_data.get("severity_threshold", "medium"),
            )
            
            return cls(
                auto_scan=auto_scan,
                bug_detection=bug_detection,
                dashboard=dashboard,
                self_learning=self_learning,
                alerts=alerts,
            )
        except Exception:
            return cls()

    def to_yaml(self, path: str) -> bool:
        config_path = Path(path)
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "master_agent": {
                    "auto_scan": {
                        "enabled": self.auto_scan.enabled,
                        "interval_seconds": self.auto_scan.interval_seconds,
                        "projects_dir": self.auto_scan.projects_dir,
                    },
                    "bug_detection": {
                        "enabled": self.bug_detection.enabled,
                        "static_analysis": {"enabled": self.bug_detection.static_analysis},
                        "git_analysis": {"enabled": self.bug_detection.git_analysis},
                        "dependency_scan": {"enabled": self.bug_detection.dependency_scan},
                        "security_scan": {"enabled": self.bug_detection.security_scan},
                    },
                    "dashboard": {
                        "cli": {"enabled": self.dashboard.cli_enabled},
                        "web": {
                            "enabled": self.dashboard.web_enabled,
                            "port": self.dashboard.web_port,
                            "websocket": self.dashboard.websocket_enabled,
                        },
                    },
                    "self_learning": {
                        "enabled": self.self_learning.enabled,
                        "learn_from_subprojects": self.self_learning.learn_from_subprojects,
                        "update_master_md": self.self_learning.update_master_md,
                        "enhance_rules": self.self_learning.enhance_rules,
                        "feedback_weight": self.self_learning.feedback_weight,
                    },
                    "alerts": {
                        "channels": self.alerts.channels,
                        "severity_threshold": self.alerts.severity_threshold,
                    },
                }
            }
            
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            
            return True
        except Exception:
            return False


DEFAULT_CONFIG_YAML = """# Master Agent Configuration
master_agent:
  auto_scan:
    enabled: true
    interval_seconds: 300  # 5 minutes
    projects_dir: "projects"
  
  bug_detection:
    enabled: true
    static_analysis:
      enabled: true
      tools: ["ruff", "mypy"]
    git_analysis:
      enabled: true
      risk_threshold: 0.7
    dependency_scan:
      enabled: true
      check_interval_hours: 24
    security_scan:
      enabled: true
      patterns: ["api_key", "password", "token", "secret"]
  
  dashboard:
    cli:
      enabled: true
      color_output: true
    web:
      enabled: true
      port: 11436
      websocket: true
  
  self_learning:
    enabled: true
    learn_from_subprojects: true
    update_master_md: true
    enhance_rules: true
    feedback_weight: 0.8
  
  alerts:
    channels: ["cli", "log"]
    severity_threshold: "medium"
"""


def create_default_config(path: str) -> bool:
    config_path = Path(path)
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")
        return True
    except Exception:
        return False
