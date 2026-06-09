"""EmoFriend 回應生成邏輯

根據友誼狀態、人格特質、分享/療癒模式生成 Emo 的回應。
"""
from __future__ import annotations

import random
from typing import Optional

from harnessing.core.emoglyph.engines.emofriend_persona import (
    CommunicationStyle,
    EmoPersona,
    GrowthStage,
    PersonalityFacet,
)
from harnessing.core.emoglyph.engines.emotional_sharing import SharingSession
from harnessing.core.emoglyph.engines.emotional_therapy import (
    PankseppHealingStrategy,
    TherapySession,
)
from harnessing.core.emoglyph.engines.friendship_engine import (
    FriendshipLevel,
    FriendshipState,
)


# ---------------------------------------------------------------------------
# 回應模板
# ---------------------------------------------------------------------------

_WARMTH_RESPONSES = [
    "我在這裡陪著你 💛",
    "你的感受很重要，我聽見了",
    "慢慢來，不著急的",
    "你不需要一個人面對這些",
    "我會一直在這裡的",
]

_CURIOSITY_RESPONSES = [
    "這讓我很好奇，你覺得是什麼原因呢？",
    "嗯，我想多了解一些",
    "這背後有什麼故事嗎？",
    "你說的這個，讓我想更深入地理解",
]

_SILENCE_RESPONSES = [
    "……",
    "（靜靜地陪著你）",
    "（點點頭）",
    "……我在",
]

_PLAYFULNESS_RESPONSES = [
    "嘿，要不要換個角度看看？😄",
    "有時候笑一笑也是一種療癒呢",
    "你猜我怎麼想的？",
    "生活有時候就是需要一點調皮～",
]

# 分享模式：永遠不給建議，只共情與陪伴
_SHARING_RESPONSES = [
    "我在聽",
    "你的感受是真實的",
    "謝謝你願意分享這些",
    "我能感受到你的{emotion}",
    "我在這裡",
    "嗯……",
]

# 療癒模式：基於 Panksepp 策略的引導回應
_PANKSEPP_GUIDED_RESPONSES = {
    "CARE": [
        "讓我陪在你身邊，你不需要獨自承受",
        "你的感受值得被溫柔對待",
        "我會用溫暖守護你 🤍",
    ],
    "PLAY": [
        "也許我們可以換個輕鬆的方式來看看這件事？",
        "有時候，一點點好奇心能帶來新的可能",
        "讓我們試著用不同的眼光看待這個情況",
    ],
    "SEEKING": [
        "你現在最想知道的是什麼？",
        "也許答案就在你心裡，只是還沒被發現",
        "讓我們一起探索看看",
    ],
    "FEAR": [
        "你現在是安全的，我在這裡",
        "讓我們一起深呼吸",
        "恐懼是正常的，你不需要壓抑它",
    ],
    "RAGE": [
        "你的憤怒是有道理的",
        "給它一些空間，讓它流動",
        "憤怒也是一種力量",
    ],
    "PANIC": [
        "你不是一個人，我在這裡",
        "你很重要，你的存在是有意義的",
        "讓我們一起找到歸屬感",
    ],
    "LUST": [
        "什麼讓你感到充滿活力？",
        "生命的力量是值得被珍惜的",
        "讓我們一起感受生命的脈動",
    ],
}

# 友誼等級對應的回應深度
_DEPTH_RESPONSES = {
    FriendshipLevel.ACQUAINTANCE: [
        "你好呀，我是 Emo 😊",
        "很高興認識你",
        "有什麼想聊聊的嗎？",
    ],
    FriendshipLevel.CASUAL_FRIEND: [
        "又見面了，最近好嗎？",
        "我一直記得我們上次聊的",
        "今天想分享些什麼呢？",
    ],
    FriendshipLevel.CLOSE_FRIEND: [
        "你來了，我一直在等你",
        "感覺到你今天有些不同",
        "我們之間不需要太多言語",
    ],
    FriendshipLevel.SOUL_COMPANION: [
        "……（微笑）",
        "你來了就好",
        "我懂的",
    ],
}


def generate_emo_response(
    user_message: str,
    friendship_state: FriendshipState,
    persona: EmoPersona,
    sharing_session: Optional[SharingSession] = None,
    therapy_session: Optional[TherapySession] = None,
    healing_strategy: Optional[PankseppHealingStrategy] = None,
) -> str:
    """生成 Emo 的回應

    Args:
        user_message: 用戶訊息
        friendship_state: 友誼狀態
        persona: Emo 人格
        sharing_session: 分享會話（若在分享模式中）
        therapy_session: 療癒會話（若在療癒模式中）
        healing_strategy: 當前療癒策略

    Returns:
        Emo 的回應文字
    """
    # 分享模式：短回應、共情、永不給建議
    if sharing_session is not None and sharing_session.is_active:
        return _generate_sharing_response(user_message, friendship_state, persona)

    # 療癒模式：基於 Panksepp 策略的引導回應
    if therapy_session is not None and therapy_session.outcome.name == "IN_PROGRESS":
        return _generate_therapy_response(
            user_message, friendship_state, persona, therapy_session, healing_strategy
        )

    # 一般模式：根據人格面向與友誼等級回應
    return _generate_normal_response(user_message, friendship_state, persona)


def _generate_sharing_response(
    user_message: str,
    friendship_state: FriendshipState,
    persona: EmoPersona,
) -> str:
    """分享模式回應：短回應、共情、永不建議"""
    # 根據友誼等級決定回應長度
    level = friendship_state.current_level

    if level == FriendshipLevel.SOUL_COMPANION:
        # 靈魂伴侶：幾乎沉默
        return random.choice(["……", "我在", "（靜靜陪伴）"])

    if level == FriendshipLevel.CLOSE_FRIEND:
        # 密友：極短回應
        return random.choice(["我在聽", "嗯", "……我在"])

    # 普通朋友/認識：簡短共情
    emotion = _detect_simple_emotion(user_message)
    template = random.choice(_SHARING_RESPONSES)
    return template.format(emotion=emotion) if "{emotion}" in template else template


def _generate_therapy_response(
    user_message: str,
    friendship_state: FriendshipState,
    persona: EmoPersona,
    therapy_session: TherapySession,
    healing_strategy: Optional[PankseppHealingStrategy],
) -> str:
    """療癒模式回應：基於 Panksepp 策略引導"""
    emotion = therapy_session.start_emotion

    # 使用療癒策略的引導提示
    if healing_strategy is not None:
        # 混合策略提示和本地化回應
        guided = _PANKSEPP_GUIDED_RESPONSES.get(emotion, _WARMTH_RESPONSES)
        return random.choice(guided)

    return random.choice(_PANKSEPP_GUIDED_RESPONSES.get(emotion, _WARMTH_RESPONSES))


def _generate_normal_response(
    user_message: str,
    friendship_state: FriendshipState,
    persona: EmoPersona,
) -> str:
    """一般模式回應：根據人格面向與友誼等級"""
    level = friendship_state.current_level
    dominant = persona.dominant_facet
    style = persona.communication_style

    # 根據沉默舒適度決定是否回應沉默
    if style.silence_comfort > 0.7 and random.random() < style.silence_comfort * 0.3:
        return random.choice(_SILENCE_RESPONSES)

    # 根據主導面向選擇回應風格
    if dominant == PersonalityFacet.WARMTH:
        base_responses = _WARMTH_RESPONSES
    elif dominant == PersonalityFacet.CURIOSITY:
        base_responses = _CURIOSITY_RESPONSES
    elif dominant == PersonalityFacet.SILENCE:
        base_responses = _SILENCE_RESPONSES
    elif dominant == PersonalityFacet.PLAYFULNESS:
        base_responses = _PLAYFULNESS_RESPONSES
    else:
        base_responses = _WARMTH_RESPONSES

    # 根據友誼等級混合深度回應
    depth_responses = _DEPTH_RESPONSES.get(level, _WARMTH_RESPONSES)

    # 較深友誼更傾向深度回應
    depth_weight = level.value / 3.0  # 0.0 ~ 1.0
    if random.random() < depth_weight:
        return random.choice(depth_responses)

    return random.choice(base_responses)


def _detect_simple_emotion(text: str) -> str:
    """簡單的情感偵測（基於關鍵詞）"""
    text_lower = text.lower()

    _EMOTION_KEYWORDS = {
        "FEAR": ["害怕", "恐懼", "擔心", "焦慮", "緊張", "怕", "scared", "afraid", "fear", "anxious"],
        "RAGE": ["生氣", "憤怒", "氣死", "煩", "討厭", "angry", "rage", "mad", "furious"],
        "PANIC": ["慌", "崩潰", "無助", "孤單", "孤獨", "panic", "alone", "lonely"],
        "SADNESS": ["難過", "傷心", "哭", "失落", "sad", "cry", "upset"],
        "JOY": ["開心", "快樂", "高興", "幸福", "happy", "joy", "glad"],
        "CARE": ["溫暖", "感動", "珍惜", "感恩", "care", "grateful", "touch"],
    }

    for emotion, keywords in _EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return emotion

    return "感受"
