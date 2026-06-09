"""EmoGlyphPlay — AI Coding Partner with Intelligent Routing Engine.

EmoGlyphPlay combines a Harness Engineering methodology with a multi-layered
personality-driven routing system to solve 48 major Vibe Coding pain points.
It provides 102 rules + 73 error rules + 157 CM integration rules, with
140 skills that auto-trigger based on context.

Core Components:
    ParallelMind: Multi-project parallel workspace management
    TokenSaver: Three-layer token optimization engine
    FlowNavigator: Flow state detection and navigation
    EastWestBridge: East-West thinking style fusion
    ConnectorHub: n8n-style external connector management
    SubscriptionManager: Tier-based feature gating
    LightDarkBalanceEngine: 正暗平衡 — Strategic awareness with ethical action
    ContextEngine: Environment sensing for context-aware routing
    EthicsGuard: Ethical boundary enforcement (always active)
    StrategyGenerator: Dark strategy synthesis from East+West traditions
    SpiralWisdomEngine: 螺旋智慧 — Temporal spiral dynamics for "知暗行明"
"""

from harnessing.emoglyphplay.core.connector_hub import BaseConnector, ConnectorHub
from harnessing.emoglyphplay.core.context_engine import (
    CompetitionLevel,
    ContextEngine,
    ContextSnapshot,
    Culture,
    MarketCondition,
    RegulatoryIntensity,
    RelationshipDepth,
)
from harnessing.emoglyphplay.core.east_west_bridge import EastWestBridge
from harnessing.emoglyphplay.core.ethics_guard import (
    EthicsCheckResult,
    EthicsGuard,
    ViolationCategory,
    ViolationSeverity,
)
from harnessing.emoglyphplay.core.flow_navigator import FlowNavigator
from harnessing.emoglyphplay.core.light_dark_balance import (
    LightDarkBalanceEngine,
    LightDarkBalanceResult,
    Strategy,
    StrategyMode,
    StrategyOrigin,
)
from harnessing.emoglyphplay.core.parallel_mind import ParallelMind
from harnessing.emoglyphplay.core.subscription import SubscriptionManager
from harnessing.emoglyphplay.core.token_saver import TokenSaver
from harnessing.emoglyphplay.dark_mapping import (
    EasternDarkMapper,
    StrategyGenerator,
    WesternDarkMapper,
)
from harnessing.emoglyphplay.core.spiral_wisdom import (
    SpiralCycleResult,
    SpiralPhase,
    SpiralStatus,
    SpiralWisdomEngine,
    SpiralWisdomResult,
    WisdomResidue,
    DriftMeasurement,
)

__all__ = [
    # Original engines
    "ParallelMind",
    "TokenSaver",
    "FlowNavigator",
    "EastWestBridge",
    "ConnectorHub",
    "BaseConnector",
    "SubscriptionManager",
    # LightDarkBalance
    "LightDarkBalanceEngine",
    "StrategyMode",
    "StrategyOrigin",
    "Strategy",
    "LightDarkBalanceResult",
    # Context Engine
    "ContextEngine",
    "ContextSnapshot",
    "Culture",
    "MarketCondition",
    "RegulatoryIntensity",
    "CompetitionLevel",
    "RelationshipDepth",
    # Ethics Guard
    "EthicsGuard",
    "EthicsCheckResult",
    "ViolationSeverity",
    "ViolationCategory",
    # Dark Mapping
    "EasternDarkMapper",
    "WesternDarkMapper",
    "StrategyGenerator",
    # SpiralWisdom
    "SpiralWisdomEngine",
    "SpiralWisdomResult",
    "SpiralCycleResult",
    "SpiralPhase",
    "SpiralStatus",
    "WisdomResidue",
    "DriftMeasurement",
]

__version__ = "0.3.0"
