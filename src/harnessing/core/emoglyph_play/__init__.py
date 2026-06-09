"""EmoGlyph Play — 統一抽象層

EmoGlyph v2.1 (5-Layer) × Play Theory (4-Step) 整合

Phase 2 新增：
  - DomainMap: 领域知识地图
  - SituationAnalyzer: 情境分析引擎
  - IntelligentSkillRouter: 智能路由器（LSP 4步驱动）
  - SkillDiscovery: 1M+ 技能市场研究
  - AutoInstaller: 自动注册引擎
  - SkillInvention: Formula Thinking 新技能发明
"""

import importlib as _importlib

from .lsp_ai_engine import (
    LSPEngine,
    LSPPlayerTypeDetector,
    LSPStage,
    PlayModuleBridge,
    PlaySession,
    PlayerType,
    run_lsp_cycle,
)
from .health_monitor import (
    HealthDimension,
    HealthMonitor,
    HealthScore,
    ProjectHealthReport,
)
from .model_config import ModelConfig, ModelSelector

_emoglyph_integration = _importlib.import_module(".04_emoglyph_integration", __name__)
EmoGlyphLSPBridge = _emoglyph_integration.EmoGlyphLSPBridge
EmoGlyphPlaySession = _emoglyph_integration.EmoGlyphPlaySession
RESONANCE_THRESHOLD = _emoglyph_integration.RESONANCE_THRESHOLD
MAX_AUTO_CYCLES = _emoglyph_integration.MAX_AUTO_CYCLES

_play_formula = _importlib.import_module(".05_play_formula", __name__)
PlayFormulaEngine = _play_formula.PlayFormulaEngine
PlayFormulaResult = _play_formula.PlayFormulaResult
SprintFormulaResult = _play_formula.SprintFormulaResult

_sprint_runner = _importlib.import_module(".06_sprint_runner", __name__)
SprintRunner = _sprint_runner.SprintRunner
SprintReport = _sprint_runner.SprintReport
SprintPhase = _sprint_runner.SprintPhase
SubProject = _sprint_runner.SubProject

# Phase 2: 智能技能路由
from .domain_map import DomainMap, DomainEntry, DOMAIN_MAP
from .situation_analyzer import SituationAnalyzer, Situation
from .intelligent_router import (
    IntelligentSkillRouter,
    IntelligentRouteResult,
    SkillRecommendation,
    FeedbackTracker,
)
from .skill_discovery import SkillDiscovery, DiscoveredSkill, SKILL_MARKETS
from .auto_installer import AutoInstaller, RegistrationResult, BatchRegistrationResult
from .skill_invention import SkillInvention, SkillGap

__version__ = "0.2.0"
__all__ = [
    # Phase 1 (existing)
    "LSPEngine",
    "LSPPlayerTypeDetector",
    "LSPStage",
    "PlayModuleBridge",
    "PlaySession",
    "PlayerType",
    "run_lsp_cycle",
    "ModelConfig",
    "ModelSelector",
    "EmoGlyphLSPBridge",
    "EmoGlyphPlaySession",
    "RESONANCE_THRESHOLD",
    "MAX_AUTO_CYCLES",
    "PlayFormulaEngine",
    "PlayFormulaResult",
    "SprintFormulaResult",
    "SprintRunner",
    "SprintReport",
    "SprintPhase",
    "SubProject",
    "HealthDimension",
    "HealthMonitor",
    "HealthScore",
    "ProjectHealthReport",
    # Phase 2 (new)
    "DomainMap",
    "DomainEntry",
    "DOMAIN_MAP",
    "SituationAnalyzer",
    "Situation",
    "IntelligentSkillRouter",
    "IntelligentRouteResult",
    "SkillRecommendation",
    "FeedbackTracker",
    "SkillDiscovery",
    "DiscoveredSkill",
    "SKILL_MARKETS",
    "AutoInstaller",
    "RegistrationResult",
    "BatchRegistrationResult",
    "SkillInvention",
    "SkillGap",
]
