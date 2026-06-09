"""EmoGlyph Engines — KB-50 公式實作

5 個新發明引擎，根據 KB-50 §十三「5 個新發明公式」實作：

1. EmotionalInsightGenerator  - Emotional_Insight = (K * R) + (C / S)
2. ResilienceAmplifier        - Resilience = (R + G + A) * (P^2)
3. CompassionateResponseEngine - Compassionate_Response = (E * T) + (R / D) - A
4. EmbodiedWisdomSynthesizer  - Embodied_Wisdom = (S × C) + (A - M) ^ P
5. EmotionalRealityReconstructor - Reality_Reconstruction = (G × B) + (T - N) - F

每個 engine 都有：
- 公式原文 (KB-50)
- 元素語義 (K/R/C/S 等)
- 運算語義 (乘 / 除 / 加 / 平方)
- EmoGlyph 整合點 (邊一層)
- 預期新能力
- 3 Layer Testing 預期

設計原則：
- 全保留 (No deletion) - 永遠保留原始 KB-50 公式，不可以「改良」成新公式
- 元素都可解釋 (Explainable) - 每個輸入都有來源書名
- 數值穩定 (Numerically stable) - 防止除以 0 / 極大值
"""
from .insight_generator import EmotionalInsightGenerator, InsightResult
from .resilience_amplifier import ResilienceAmplifier, ResilienceResult
from .compassionate_response import CompassionateResponseEngine, CompassionResult
from .embodied_wisdom import EmbodiedWisdomSynthesizer, EmbodiedResult
from .reality_reconstructor import EmotionalRealityReconstructor, ReconstructionResult
from .personality_vector_engine import (
    PersonalityVector, DISCProfile, OCEANProfile, MBTIProfile, VAKProfile, EasternProfile,
    DISCType, CailloisPlayType, FlowZone, VAKChannel, MBTIFunction, FiveElement,
    disc_to_ocean, ocean_to_eastern, detect_disc_from_text, detect_vak_from_text,
    create_personality_vector_from_text,
)
from .play_spectrum_engine import (
    PlaySpectrum, FlowState, PlayFlowBridge, FlowStateNavigator,
    CailloisPlayType as PlayCailloisType, PlayContext, FlowZone as PlayFlowZone,
)
from .disc_communication_adapter import (
    DISCCommunicationAdapter, CommunicationStyle, DISCStyle,
)
from .mbti_cognitive_router import (
    MBTICognitiveRouter, CognitiveFunction, ProcessingMode, MBTI_FUNCTION_STACKS,
)
from .personality_aware_decision_matrix import (
    PersonalityAwareDecisionMatrix, AgentMode, ModeRecommendation,
)
from .emoglyph_structure_driver import (
    EmoGlyphStructureDriver, LayerState, EmergencePattern, StructureProcessingResult,
    InterdependencyType, ProcessingMode as StructureProcessingMode,
)
from .emoglyph_constitution import (
    EmoGlyphConstitution, ConstitutionalGuard, ConstitutionalPrinciple,
    ConstitutionalConflict, ConstitutionalAmendment, PrincipleViolation,
    ConflictResolution, AmendmentStatus,
)
from .structural_thinking_router import (
    StructuralThinkingRouter, StructuralProcessingPlan, EmotionalSignal, ContextualAnalysis,
    RoutingStrategy, ProcessingDepth, DomainType,
)
from .subproject_remote_controller import (
    SubProjectRemoteController, SubProjectInfo, RemoteOperation, RemoteControlResult,
    SubProjectStatus, OperationType, OperationRisk,
)
from .context_isolation_barrier import (
    ContextIsolationBarrier, BarrierPolicy, InformationType,
)
from .task_bridge import (
    TaskBridge, BridgeInstruction, BridgeResult,
)
from .parallel_workspace_engine import (
    ParallelWorkspaceEngine, WorkspaceContext, EmoGlyphLayerResult,
)
# EmoFriend 情感療癒陪伴產品引擎
from .friendship_engine import (
    FriendshipEngine, FriendshipLevel, FriendshipState, SharedMoment, ResponseStrategy,
)
from .emotional_therapy import (
    EmotionalTherapyEngine, TherapyOutcome, SilenceTherapyStage,
    TherapyIntervention, TherapySession, PankseppHealingStrategy,
)
from .emotional_sharing import (
    EmotionalSharingEngine, ListeningMode, EmotionShare, EmoResponse,
    DiaryEntry, SharingSession,
)
from .emotional_profile import (
    UserEmotionalProfileManager, RiskLevel, EmotionalPattern,
    HealingPreferences, EmotionalSnapshot, EmotionalProfile, WarningResult,
)
from .emofriend_persona import (
    EmoFriendPersonaEngine, PersonalityFacet, GrowthStage,
    EmoMemory, CommunicationStyle, EmoPersona,
)

# EmoFriend 七竅 (Seven Apertures) 多模態感官引擎 — IDEA-076
from .emo_eye import (
    EmoEyeEngine, EmoEyeResult, HeadPose, ShoulderPosition,
    EmoEyeBackend, CloudEmoEyeBackend, LocalEmoEyeBackend,
    FACIAL_EXPRESSION_MAP,
)
from .emo_ear import (
    EmoEarEngine, EmoEarResult, ProsodyFeatures,
    EmoEarBackend, CloudEmoEarBackend, LocalEmoEarBackend,
    MANNER_PANKSEPP_MAP, AMBIENT_STRESS_MAP,
)
from .emo_mouth import (
    EmoMouthEngine, EmoMouthResult, EmoMouthConfig,
    SilenceType, BreathingPattern, BreathingPhase,
    EmoMouthBackend, CloudEmoMouthBackend, LocalEmoMouthBackend,
    SILENCE_CONFIGS, BREATHING_PATTERNS, VOICE_STYLE_PANKSEPP,
)
from .emo_heart import (
    EmoHeartEngine, EmoHeartResult, HRVMetrics as HeartHRVMetrics,
    SleepData, ActivityData, AutonomicState, RecoveryStatus,
    WearableAdapter, AppleHealthKitAdapter, OuraAPIAdapter, FitbitAPIAdapter,
)
from .emo_brain import (
    EmoBrainEngine, EmoBrainResult, CognitiveState,
)
from .emo_hand import (
    EmoHandEngine, EmoHandResult, KeyEvent, ScrollEvent, AppUsageData,
    KeystrokeMetrics, ScrollMetrics,
)
from .emo_body import (
    EmoBodyEngine, EmoBodyResult, PostureMetrics, GaitMetrics, CircadianMetrics,
    Chronotype, FallRiskAssessment, CircadianAlert,
)
from .emo_sense import (
    EmoSenseEngine, FusedEmotionalState, SensoryInput,
    Contradiction, SafetySignal, JITAIAction,
    SafetySeverity, JITAIActionType,
)

# EmoFriend MVP1 Audience Configuration
from .audience_config import (
    AudienceMode, AudienceConfig,
    KIDS_CONFIG, ELDERLY_CONFIG, get_config,
)

# EmoFriend MVP1 Emotion Buttons
from .emotion_buttons import (
    EmotionButton, KIDS_EMOTION_BUTTONS, ELDERLY_EMOTION_BUTTONS,
    emotion_to_pulse, get_buttons_for_mode, find_button_by_emoji,
)

# EmoFriend MVP1 Onboarding
from .onboarding import (
    OnboardingStep, OnboardingState, SensorConsent,
    SENSOR_EXPLANATIONS, generate_onboarding_prompt,
    advance_onboarding, validate_step,
)

# EmoFriend MVP1 Family Dashboard
from .family_dashboard import (
    WellnessSummary, SafetyEventLog,
    PANKSEPP_TO_WELLNESS_LABEL, generate_wellness_summary,
    generate_family_notification_text, create_safety_event,
)

__all__ = [
    "EmotionalInsightGenerator",
    "InsightResult",
    "ResilienceAmplifier",
    "ResilienceResult",
    "CompassionateResponseEngine",
    "CompassionResult",
    "EmbodiedWisdomSynthesizer",
    "EmbodiedResult",
    "EmotionalRealityReconstructor",
    "ReconstructionResult",
    # Personality & Flow engines
    "PersonalityVector", "DISCProfile", "OCEANProfile", "MBTIProfile", "VAKProfile", "EasternProfile",
    "DISCType", "CailloisPlayType", "FlowZone", "VAKChannel", "MBTIFunction", "FiveElement",
    "disc_to_ocean", "ocean_to_eastern", "detect_disc_from_text", "detect_vak_from_text",
    "create_personality_vector_from_text",
    "PlaySpectrum", "FlowState", "PlayFlowBridge", "FlowStateNavigator",
    "PlayCailloisType", "PlayContext", "PlayFlowZone",
    "DISCCommunicationAdapter", "CommunicationStyle", "DISCStyle",
    "MBTICognitiveRouter", "CognitiveFunction", "ProcessingMode", "MBTI_FUNCTION_STACKS",
    "PersonalityAwareDecisionMatrix", "AgentMode", "ModeRecommendation",
    # Structure-Driven engines
    "EmoGlyphStructureDriver", "LayerState", "EmergencePattern", "StructureProcessingResult",
    "InterdependencyType", "StructureProcessingMode",
    "EmoGlyphConstitution", "ConstitutionalGuard", "ConstitutionalPrinciple",
    "ConstitutionalConflict", "ConstitutionalAmendment", "PrincipleViolation",
    "ConflictResolution", "AmendmentStatus",
    "StructuralThinkingRouter", "StructuralProcessingPlan", "EmotionalSignal", "ContextualAnalysis",
    "RoutingStrategy", "ProcessingDepth", "DomainType",
    # SubProject Remote Controller
    "SubProjectRemoteController", "SubProjectInfo", "RemoteOperation", "RemoteControlResult",
    "SubProjectStatus", "OperationType", "OperationRisk",
    # Parallel Workspace engines
    "ContextIsolationBarrier", "BarrierPolicy", "InformationType",
    "TaskBridge", "BridgeInstruction", "BridgeResult",
    "ParallelWorkspaceEngine", "WorkspaceContext", "EmoGlyphLayerResult",
    # EmoFriend 情感療癒陪伴產品引擎
    "FriendshipEngine", "FriendshipLevel", "FriendshipState", "SharedMoment", "ResponseStrategy",
    "EmotionalTherapyEngine", "TherapyOutcome", "SilenceTherapyStage",
    "TherapyIntervention", "TherapySession", "PankseppHealingStrategy",
    "EmotionalSharingEngine", "ListeningMode", "EmotionShare", "EmoResponse",
    "DiaryEntry", "SharingSession",
    "UserEmotionalProfileManager", "RiskLevel", "EmotionalPattern",
    "HealingPreferences", "EmotionalSnapshot", "EmotionalProfile", "WarningResult",
    "EmoFriendPersonaEngine", "PersonalityFacet", "GrowthStage",
    "EmoMemory", "CommunicationStyle", "EmoPersona",
    # 七竅 (Seven Apertures) 多模態感官引擎 — IDEA-076
    "EmoEyeEngine", "EmoEyeResult", "HeadPose", "ShoulderPosition",
    "EmoEyeBackend", "CloudEmoEyeBackend", "LocalEmoEyeBackend",
    "FACIAL_EXPRESSION_MAP",
    "EmoEarEngine", "EmoEarResult", "ProsodyFeatures",
    "EmoEarBackend", "CloudEmoEarBackend", "LocalEmoEarBackend",
    "MANNER_PANKSEPP_MAP", "AMBIENT_STRESS_MAP",
    "EmoMouthEngine", "EmoMouthResult", "EmoMouthConfig",
    "SilenceType", "BreathingPattern", "BreathingPhase",
    "EmoMouthBackend", "CloudEmoMouthBackend", "LocalEmoMouthBackend",
    "SILENCE_CONFIGS", "BREATHING_PATTERNS", "VOICE_STYLE_PANKSEPP",
    "EmoHeartEngine", "EmoHeartResult", "HeartHRVMetrics",
    "SleepData", "ActivityData", "AutonomicState", "RecoveryStatus",
    "WearableAdapter", "AppleHealthKitAdapter", "OuraAPIAdapter", "FitbitAPIAdapter",
    "EmoBrainEngine", "EmoBrainResult", "CognitiveState",
    "EmoHandEngine", "EmoHandResult", "KeyEvent", "ScrollEvent", "AppUsageData",
    "KeystrokeMetrics", "ScrollMetrics",
    "EmoBodyEngine", "EmoBodyResult", "PostureMetrics", "GaitMetrics", "CircadianMetrics",
    "Chronotype", "FallRiskAssessment", "CircadianAlert",
    "EmoSenseEngine", "FusedEmotionalState", "SensoryInput",
    "Contradiction", "SafetySignal", "JITAIAction",
    "SafetySeverity", "JITAIActionType",
    # Audience Configuration
    "AudienceMode", "AudienceConfig",
    "KIDS_CONFIG", "ELDERLY_CONFIG", "get_config",
    # Emotion Buttons
    "EmotionButton", "KIDS_EMOTION_BUTTONS", "ELDERLY_EMOTION_BUTTONS",
    "emotion_to_pulse", "get_buttons_for_mode", "find_button_by_emoji",
    # Onboarding
    "OnboardingStep", "OnboardingState", "SensorConsent",
    "SENSOR_EXPLANATIONS", "generate_onboarding_prompt",
    "advance_onboarding", "validate_step",
    # Family Dashboard
    "WellnessSummary", "SafetyEventLog",
    "PANKSEPP_TO_WELLNESS_LABEL", "generate_wellness_summary",
    "generate_family_notification_text", "create_safety_event",
]
