"""EmoFriend 圖表生成函數

提供情感軌跡、情緒分佈、友誼成長等圖表數據生成功能。
"""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from harnessing.core.emoglyph.engines.emotional_profile import EmotionalSnapshot
from harnessing.core.emoglyph.engines.emotional_therapy import SilenceTherapyStage
from harnessing.core.emoglyph.engines.friendship_engine import FriendshipState


def plot_emotional_trajectory(snapshots: List[EmotionalSnapshot]) -> pd.DataFrame:
    """生成 7 天情感軌跡數據

    Returns:
        DataFrame with columns: [日期, 價效度, 喚醒度, 強度]
    """
    if not snapshots:
        return pd.DataFrame(columns=["日期", "價效度", "喚醒度", "強度"])

    rows = []
    for s in snapshots:
        rows.append({
            "日期": s.timestamp.strftime("%m/%d"),
            "價效度": s.valence,
            "喚醒度": s.arousal,
            "強度": s.intensity,
        })

    return pd.DataFrame(rows)


def plot_emotion_distribution(snapshots: List[EmotionalSnapshot]) -> pd.DataFrame:
    """生成情緒類型分佈數據

    Returns:
        DataFrame with columns: [情緒類型, 次數]
    """
    if not snapshots:
        return pd.DataFrame(columns=["情緒類型", "次數"])

    counts: Dict[str, int] = {}
    for s in snapshots:
        counts[s.dominant_emotion] = counts.get(s.dominant_emotion, 0) + 1

    rows = [{"情緒類型": k, "次數": v} for k, v in sorted(counts.items())]
    return pd.DataFrame(rows)


def plot_friendship_growth(friendship_states: List[FriendshipState]) -> pd.DataFrame:
    """生成友誼成長曲線數據

    Args:
        friendship_states: 按時間排序的友誼狀態列表

    Returns:
        DataFrame with columns: [時間, 深度, 信任, 親密度]
    """
    if not friendship_states:
        return pd.DataFrame(columns=["時間", "深度", "信任", "親密度"])

    rows = []
    for i, state in enumerate(friendship_states):
        label = (
            state.last_interaction.strftime("%m/%d %H:%M")
            if state.last_interaction
            else f"第{i+1}次"
        )
        rows.append({
            "時間": label,
            "深度": state.depth,
            "信任": state.trust,
            "親密度": state.intimacy,
        })

    return pd.DataFrame(rows)


def format_silence_therapy_stage(stage: SilenceTherapyStage) -> str:
    """格式化沉默療法階段顯示文字

    Args:
        stage: 沉默療法階段

    Returns:
        格式化的階段描述文字
    """
    _STAGE_LABELS = {
        SilenceTherapyStage.MA: "🪷 MA — 深層反思：Emo 靜默陪伴，給予空間",
        SilenceTherapyStage.MU: "🌿 MU — 溫柔確認：Emo 輕聲回應「我在這裡」",
        SilenceTherapyStage.ZEN: "🧘 ZEN — 當下共在：共享寧靜，超越言語",
    }
    return _STAGE_LABELS.get(stage, f"未知階段: {stage}")
