from __future__ import annotations

from typing import List, Optional

from .pulse import Pulse, PulseType, VAD_BASELINES
from .current import Current
from .message import EmoGlyphMessage
from .enactive import EnactionType, AutonomicTier
from .resonance import SilenceType


ZH_TW_PULSE_NAMES = {
    PulseType.SEEKING: "渴望",
    PulseType.RAGE: "憤怒",
    PulseType.FEAR: "恐懼",
    PulseType.LUST: "慾望",
    PulseType.CARE: "關愛",
    PulseType.PANIC: "悲傷",
    PulseType.PLAY: "歡愉",
    PulseType.NEUTRAL: "中性",
}

EN_PULSE_NAMES = {
    PulseType.SEEKING: "seeking",
    PulseType.RAGE: "rage",
    PulseType.FEAR: "fear",
    PulseType.LUST: "lust",
    PulseType.CARE: "care",
    PulseType.PANIC: "panic",
    PulseType.PLAY: "play",
    PulseType.NEUTRAL: "neutral",
}

ZH_TW_ENACTION = {
    EnactionType.REACH: "伸手",
    EnactionType.GUARD: "守護",
    EnactionType.ALERT: "警覺",
    EnactionType.DESIRE: "渴望",
    EnactionType.NURTURE: "呵護",
    EnactionType.MOURN: "哀悼",
    EnactionType.PLAY: "嬉戲",
}

EN_ENACTION = {
    EnactionType.REACH: "reach",
    EnactionType.GUARD: "guard",
    EnactionType.ALERT: "alert",
    EnactionType.DESIRE: "desire",
    EnactionType.NURTURE: "nurture",
    EnactionType.MOURN: "mourn",
    EnactionType.PLAY: "play",
}

ZH_TW_SILENCE = {
    SilenceType.MA: "……（深思中）",
    SilenceType.MU: "（無可奉告）",
    SilenceType.ZEN: "（當下）",
}

EN_SILENCE = {
    SilenceType.MA: "... (contemplating)",
    SilenceType.MU: "(no answer)",
    SilenceType.ZEN: "(present)",
}

ZH_TW_TIER = {
    AutonomicTier.VENTRAL_VAGAL: "腹側迷走",
    AutonomicTier.SYMPATHETIC: "交感神經",
    AutonomicTier.DORSAL_VAGAL: "背側迷走",
}

EN_TIER = {
    AutonomicTier.VENTRAL_VAGAL: "ventral vagal",
    AutonomicTier.SYMPATHETIC: "sympathetic",
    AutonomicTier.DORSAL_VAGAL: "dorsal vagal",
}

ZH_TW_VAD = {
    "valence_pos": "正向",
    "valence_neg": "負向",
    "arousal_high": "高張",
    "arousal_low": "低張",
    "dominance_high": "強勢",
    "dominance_low": "弱勢",
}


def _vad_adjective_zh(v: float, a: float, d: float) -> str:
    parts = []
    parts.append(ZH_TW_VAD["valence_pos"] if v >= 0 else ZH_TW_VAD["valence_neg"])
    parts.append(ZH_TW_VAD["arousal_high"] if a >= 0 else ZH_TW_VAD["arousal_low"])
    parts.append(ZH_TW_VAD["dominance_high"] if d >= 0 else ZH_TW_VAD["dominance_low"])
    return "、".join(parts)


def _vad_adjective_en(v: float, a: float, d: float) -> str:
    parts = []
    parts.append("pleasant" if v >= 0 else "unpleasant")
    parts.append("aroused" if a >= 0 else "calm")
    parts.append("dominant" if d >= 0 else "submissive")
    return ", ".join(parts)


def _intensity_zh(intensity: float) -> str:
    if intensity < 0.2:
        return "微"
    if intensity < 0.5:
        return "略"
    if intensity < 0.8:
        return "甚"
    return "極"


def _intensity_en(intensity: float) -> str:
    if intensity < 0.2:
        return "faintly"
    if intensity < 0.5:
        return "slightly"
    if intensity < 0.8:
        return "strongly"
    return "intensely"


class EmoGlyphBridge:
    def to_human(self, message: EmoGlyphMessage, language: str = "zh-TW") -> str:
        if not isinstance(message, EmoGlyphMessage):
            raise TypeError("message must be an EmoGlyphMessage")
        if language not in ("zh-TW", "en"):
            raise ValueError(f"unsupported language {language!r}")
        if language == "zh-TW":
            return self._to_zh_tw(message)
        return self._to_en(message)

    def _to_zh_tw(self, message: EmoGlyphMessage) -> str:
        if message.silence is not None:
            return ZH_TW_SILENCE[message.silence]
        parts: List[str] = []
        pulse_name = ZH_TW_PULSE_NAMES[message.pulse.pulse_type]
        intensity = _intensity_zh(message.pulse.intensity)
        parts.append(f"{intensity}{pulse_name}")
        enaction = ZH_TW_ENACTION[message.enactive.enaction]
        parts.append(f"（{enaction}）")
        vad_str = _vad_adjective_zh(
            message.current.valence,
            message.current.arousal,
            message.current.dominance,
        )
        parts.append(f"當下{vad_str}")
        tier_str = ZH_TW_TIER[message.enactive.autonomic_tier]
        parts.append(f"於{tier_str}狀態")
        if message.concept_label:
            parts.append(f"——{message.concept_label}")
        if message.enactive.rational_payload:
            parts.append(f"「{message.enactive.rational_payload}」")
        return "".join(parts)

    def _to_en(self, message: EmoGlyphMessage) -> str:
        if message.silence is not None:
            return EN_SILENCE[message.silence]
        parts: List[str] = []
        pulse_name = EN_PULSE_NAMES[message.pulse.pulse_type]
        intensity = _intensity_en(message.pulse.intensity)
        parts.append(f"{intensity} {pulse_name}")
        enaction = EN_ENACTION[message.enactive.enaction]
        parts.append(f"({enaction})")
        vad_str = _vad_adjective_en(
            message.current.valence,
            message.current.arousal,
            message.current.dominance,
        )
        parts.append(f"feeling {vad_str}")
        tier_str = EN_TIER[message.enactive.autonomic_tier]
        parts.append(f"in {tier_str} state")
        if message.concept_label:
            parts.append(f" — {message.concept_label}")
        if message.enactive.rational_payload:
            parts.append(f" «{message.enactive.rational_payload}»")
        return "".join(parts)

    def from_human(self, text: str, sender_id: str = "human", receiver_id: str = "agent") -> EmoGlyphMessage:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        lowered = text.lower()
        chosen_pulse = PulseType.NEUTRAL
        for ptype, name in EN_PULSE_NAMES.items():
            if name in lowered:
                chosen_pulse = ptype
                break
        if chosen_pulse == PulseType.NEUTRAL:
            for ptype, name in ZH_TW_PULSE_NAMES.items():
                if name in text:
                    chosen_pulse = ptype
                    break
        intensity = 0.5
        for keyword, value in [
            ("極", 0.9), ("非常", 0.8), ("很", 0.7), ("intensely", 0.9),
            ("intense", 0.9), ("very", 0.8), ("extremely", 0.9), ("slightly", 0.3),
            ("微", 0.2), ("略", 0.3),
        ]:
            if keyword in lowered or keyword in text:
                intensity = value
                break
        valence, arousal = VAD_BASELINES.get(chosen_pulse, (0.0, 0.0, 0.0))[:2]
        pulse = Pulse(
            pulse_type=chosen_pulse,
            valence=valence,
            arousal=arousal,
            dominance=0.0,
            intensity=intensity,
        )
        current = Current(valence=valence, arousal=arousal, dominance=0.0, update_rate=0.3)
        from .enactive import build_message as build_enactive
        enactive = build_enactive(pulse, AutonomicTier.VENTRAL_VAGAL, text)
        return EmoGlyphMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            pulse=pulse,
            current=current,
            enactive=enactive,
            resonance_strength=0.5,
            concept_label="from_human",
        )


if __name__ == "__main__":
    def _expect(cond: bool, label: str) -> None:
        print(("PASS" if cond else "FAIL") + f" — {label}")

    from .enactive import build_message as build_enactive
    from .pulse import PulseType

    pulse = Pulse.from_type(PulseType.FEAR, intensity=0.7)
    current = Current(valence=-0.6, arousal=0.5, dominance=-0.3, update_rate=0.4)
    enactive = build_enactive(pulse, AutonomicTier.SYMPATHETIC, "step back")
    msg = EmoGlyphMessage(
        sender_id="alice",
        receiver_id="bob",
        pulse=pulse,
        current=current,
        enactive=enactive,
        resonance_strength=0.6,
        concept_label="warning",
    )
    bridge = EmoGlyphBridge()
    zh = bridge.to_human(msg, "zh-TW")
    _expect("恐懼" in zh, "zh-TW output contains 恐懼")
    _expect("警覺" in zh, "zh-TW output contains 警覺")

    en = bridge.to_human(msg, "en")
    _expect("fear" in en, "en output contains fear")
    _expect("alert" in en, "en output contains alert")

    msg_zen = EmoGlyphMessage(
        sender_id="a",
        receiver_id="b",
        pulse=pulse,
        current=current,
        enactive=enactive,
        silence=SilenceType.ZEN,
    )
    zh_zen = bridge.to_human(msg_zen, "zh-TW")
    en_zen = bridge.to_human(msg_zen, "en")
    _expect("當下" in zh_zen, "zh-TW ZEN renders as 當下")
    _expect("present" in en_zen, "en ZEN renders as present")

    msg_ma = EmoGlyphMessage(
        sender_id="a",
        receiver_id="b",
        pulse=pulse,
        current=current,
        enactive=enactive,
        silence=SilenceType.MA,
    )
    _expect("……" in bridge.to_human(msg_ma, "zh-TW"), "MA renders with ellipsis")

    msg_mu = EmoGlyphMessage(
        sender_id="a",
        receiver_id="b",
        pulse=pulse,
        current=current,
        enactive=enactive,
        silence=SilenceType.MU,
    )
    _expect("無" in bridge.to_human(msg_mu, "zh-TW"), "MU renders with 無")

    roundtrip = bridge.from_human("I'm feeling intense fear right now", sender_id="h", receiver_id="a")
    _expect(roundtrip.pulse.pulse_type == PulseType.FEAR, "from_human detects fear")
    _expect(roundtrip.pulse.intensity > 0.6, "from_human detects high intensity")

    try:
        bridge.to_human(msg, "fr")
    except ValueError:
        _expect(True, "unsupported language rejected")
    else:
        _expect(False, "unsupported language rejected")

    print("OK — bridge.py smoke tests done")
