import re
from dataclasses import dataclass, field


@dataclass
class ExtractedRequirement:
    original_text: str
    intent: str
    action_type: str
    is_question: bool
    is_imperative: bool
    is_conditional: bool
    confidence: float
    ambiguity: list = field(default_factory=list)


@dataclass
class PromptAnalysis:
    raw_prompt: str
    word_count: int
    line_count: int
    requirements: list
    real_intentions: list
    ambiguities: list
    questions_to_ask: list
    completeness_check: dict


class PromptUnderstandingSkill:

    ACTION_TYPES = [
        "build", "create", "implement", "fix", "repair", "debug",
        "research", "study", "analyze", "compare", "test", "verify",
        "improve", "enhance", "optimize", "refactor",
        "delete", "remove", "clean",
        "explain", "understand", "learn",
        "deploy", "install", "setup", "configure",
        "redo", "retry", "restart", "rethink",
    ]

    CONDITIONAL_WORDS = [
        "if", "when", "unless", "only", "except", "but",
        "however", "should", "must", "need to", "have to",
        "please", "dont", "do not", "never", "always",
    ]

    QUESTION_WORDS = [
        "what", "why", "how", "when", "where", "who", "which",
        "can", "could", "would", "should", "is", "are", "do", "does",
    ]

    AMBIGUITY_PATTERNS = [
        (r"\bit\b", "pronoun 'it' — referent unclear"),
        (r"\bthis\b", "pronoun 'this' — referent unclear"),
        (r"\bthat\b", "pronoun 'that' — referent unclear"),
        (r"\bthey\b", "pronoun 'they' — referent unclear"),
        (r"\bsome\b", "vague quantifier 'some'"),
        (r"\bbetter\b", "comparative 'better' — better than what? by what metric?"),
        (r"\bproperly\b", "vague adverb 'properly' — what standard?"),
        (r"\bcorrectly\b", "vague adverb 'correctly' — what standard?"),
        (r"\bappropriately\b", "vague adverb 'appropriately' — what standard?"),
        (r"\bas needed\b", "vague condition 'as needed' — when exactly?"),
        (r"\betc\b", "incomplete list 'etc' — what else?"),
        (r"\blike\b", "vague comparison 'like' — similar in what way?"),
    ]

    def analyze(self, prompt: str) -> PromptAnalysis:
        words = prompt.split()
        lines = [l for l in prompt.split("\n") if l.strip()]

        requirements = self._extract_requirements(prompt)
        real_intentions = self._extract_real_intentions(prompt, requirements)
        ambiguities = self._detect_ambiguities(prompt)
        questions_to_ask = self._generate_clarification_questions(
            prompt, requirements, ambiguities
        )
        completeness_check = self._check_completeness(prompt, requirements)

        return PromptAnalysis(
            raw_prompt=prompt,
            word_count=len(words),
            line_count=len(lines),
            requirements=requirements,
            real_intentions=real_intentions,
            ambiguities=ambiguities,
            questions_to_ask=questions_to_ask,
            completeness_check=completeness_check,
        )

    def _extract_requirements(self, prompt: str) -> list:
        sentences = re.split(r'[.!?;]\s*', prompt)
        requirements = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 5:
                continue

            is_question = any(
                sentence.lower().startswith(qw)
                for qw in self.QUESTION_WORDS
            )
            is_imperative = any(
                f" {at} " in f" {sentence.lower()} "
                for at in self.ACTION_TYPES
            ) or sentence.lower().startswith(tuple(self.ACTION_TYPES))

            is_conditional = any(
                f" {cw} " in f" {sentence.lower()} "
                for cw in self.CONDITIONAL_WORDS
            )

            if is_question or is_imperative or is_conditional:
                intent = self._classify_intent(sentence)
                confidence = self._estimate_confidence(sentence)
                ambiguity = self._detect_ambiguities(sentence)

                requirements.append(ExtractedRequirement(
                    original_text=sentence,
                    intent=intent,
                    action_type=self._get_action_type(sentence),
                    is_question=is_question,
                    is_imperative=is_imperative,
                    is_conditional=is_conditional,
                    confidence=confidence,
                    ambiguity=[a[1] for a in ambiguity],
                ))

        if not requirements:
            requirements.append(ExtractedRequirement(
                original_text=prompt[:200],
                intent="general",
                action_type="understand",
                is_question=False,
                is_imperative=False,
                is_conditional=False,
                confidence=0.5,
                ambiguity=[],
            ))

        return requirements

    def _classify_intent(self, sentence: str) -> str:
        s = sentence.lower()
        if any(w in s for w in ["build", "create", "implement", "install", "setup"]):
            return "create"
        if any(w in s for w in ["fix", "repair", "debug", "solve"]):
            return "fix"
        if any(w in s for w in ["improve", "enhance", "optimize", "upgrade"]):
            return "improve"
        if any(w in s for w in ["research", "study", "analyze", "compare", "investigate"]):
            return "research"
        if any(w in s for w in ["test", "verify", "validate", "check"]):
            return "verify"
        if any(w in s for w in ["redo", "retry", "restart", "rethink", "again"]):
            return "redo"
        if any(w in s for w in ["explain", "understand", "learn", "what", "why", "how"]):
            return "understand"
        if any(w in s for w in ["delete", "remove", "clean"]):
            return "delete"
        if any(w in s for w in ["deploy", "publish", "release"]):
            return "deploy"
        return "general"

    def _get_action_type(self, sentence: str) -> str:
        s = sentence.lower()
        for at in self.ACTION_TYPES:
            if f" {at} " in f" {s} " or s.startswith(at):
                return at
        return "general"

    def _estimate_confidence(self, sentence: str) -> float:
        s = sentence.lower()
        confidence = 0.7

        if any(w in s for w in ["must", "always", "never", "dont", "do not"]):
            confidence += 0.15
        if any(w in s for w in ["maybe", "perhaps", "might", "could"]):
            confidence -= 0.2
        if any(w in s for w in ["please", "suggest", "recommend"]):
            confidence -= 0.1
        if any(w in s for w in ["it", "this", "that", "they"]):
            confidence -= 0.15

        return max(0.1, min(1.0, confidence))

    def _detect_ambiguities(self, text: str) -> list:
        found = []
        text_lower = text.lower()
        for pattern, description in self.AMBIGUITY_PATTERNS:
            if re.search(rf"\b{pattern}\b", text_lower):
                found.append((pattern, description))
        return found

    def _extract_real_intentions(self, prompt: str, requirements: list) -> list:
        intentions = []
        p = prompt.lower()

        intention_patterns = [
            (["dont want", "avoid", "prevent", "unacceptable", "totally unacceptable"],
             "AVOID — user explicitly does NOT want something"),
            (["should not", "must not", "never", "dont"],
             "CONSTRAINT — user is setting a hard boundary"),
            (["critical", "important", "key", "essential", "must"],
             "PRIORITY — user emphasizes this is critical"),
            (["same as", "identical", "match", "consistent"],
             "CONSISTENCY — user wants things to be the same"),
            (["super than", "better than", "outperform", "superior"],
             "COMPARISON — user wants one thing to beat another"),
            (["redo", "rethink", "again", "start over"],
             "REDO — user is not satisfied, wants a fresh attempt"),
            (["teach", "learn", "study", "method"],
             "LEARNING — user wants to transfer knowledge/methodology"),
            (["build", "create", "install", "integrate"],
             "BUILD — user wants concrete implementation"),
            (["complete", "finish", "done", "all"],
             "COMPLETENESS — user wants nothing left undone"),
        ]

        for keywords, intention in intention_patterns:
            if any(kw in p for kw in keywords):
                intentions.append(intention)

        if not intentions:
            for req in requirements:
                if req.is_imperative:
                    intentions.append(f"ACTION — user requests: {req.action_type}")
                if req.is_conditional:
                    intentions.append(f"CONDITION — user sets constraint")

        return intentions if intentions else ["GENERAL — understand user's request fully"]

    def _generate_clarification_questions(
        self, prompt: str, requirements: list, ambiguities: list
    ) -> list:
        questions = []

        for pattern, description in ambiguities:
            questions.append(f"Clarification needed: {description}")

        for req in requirements:
            if req.confidence < 0.5:
                questions.append(
                    f"Low confidence in understanding: '{req.original_text[:80]}...' "
                    f"— what exactly do you mean?"
                )
            if req.ambiguity:
                for amb in req.ambiguity:
                    questions.append(f"Ambiguity in requirement: {amb}")

        low_conf_reqs = [r for r in requirements if r.confidence < 0.6]
        if len(low_conf_reqs) > len(requirements) * 0.5:
            questions.append(
                "More than half of requirements have low confidence — "
                "should I confirm understanding before proceeding?"
            )

        return questions

    def _check_completeness(self, prompt: str, requirements: list) -> dict:
        p = prompt.lower()
        has_action = any(r.is_imperative for r in requirements)
        has_constraint = any(r.is_conditional for r in requirements)
        has_question = any(r.is_question for r in requirements)

        completeness = {
            "has_clear_action": has_action,
            "has_constraints": has_constraint,
            "has_questions": has_question,
            "can_proceed": has_action and len(requirements) > 0,
            "needs_clarification": len([r for r in requirements if r.confidence < 0.5]) > 0,
            "completeness_score": 0.0,
        }

        score = 0.0
        if has_action:
            score += 0.3
        if has_constraint:
            score += 0.2
        if len(requirements) >= 2:
            score += 0.2
        avg_conf = sum(r.confidence for r in requirements) / max(len(requirements), 1)
        score += avg_conf * 0.3
        completeness["completeness_score"] = round(score, 2)

        if completeness["completeness_score"] < 0.5:
            completeness["can_proceed"] = False
            completeness["needs_clarification"] = True

        return completeness

    def format_analysis(self, analysis: PromptAnalysis) -> str:
        lines = [
            "=== PROMPT UNDERSTANDING ANALYSIS ===",
            f"Word count: {analysis.word_count} | Line count: {analysis.line_count}",
            f"Requirements extracted: {len(analysis.requirements)}",
            "",
            "--- REQUIREMENTS ---",
        ]

        for i, req in enumerate(analysis.requirements, 1):
            lines.append(f"  {i}. [{req.intent.upper()}] {req.original_text[:100]}")
            lines.append(f"     Action: {req.action_type} | Confidence: {req.confidence:.0%}")
            if req.ambiguity:
                for amb in req.ambiguity:
                    lines.append(f"     ⚠️ Ambiguity: {amb}")

        lines.append("")
        lines.append("--- REAL INTENTIONS ---")
        for intent in analysis.real_intentions:
            lines.append(f"  • {intent}")

        if analysis.ambiguities:
            lines.append("")
            lines.append("--- AMBIGUITIES DETECTED ---")
            for pattern, desc in analysis.ambiguities:
                lines.append(f"  ⚠️ '{pattern}': {desc}")

        if analysis.questions_to_ask:
            lines.append("")
            lines.append("--- CLARIFICATION NEEDED ---")
            for q in analysis.questions_to_ask:
                lines.append(f"  ❓ {q}")

        lines.append("")
        lines.append("--- COMPLETENESS CHECK ---")
        cc = analysis.completeness_check
        lines.append(f"  Can proceed: {'✅ YES' if cc['can_proceed'] else '❌ NO — ask user first'}")
        lines.append(f"  Needs clarification: {'⚠️ YES' if cc['needs_clarification'] else '✅ NO'}")
        lines.append(f"  Completeness score: {cc['completeness_score']:.0%}")

        return "\n".join(lines)
