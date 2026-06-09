from __future__ import annotations

import random
import uuid
from datetime import datetime

import structlog

from harnessing.models.content_models import (
    Audience,
    ComicScene,
    ComicScript,
    Language,
    TopicProposal,
)

logger = structlog.get_logger()

_HOOKS: dict[str, list[str]] = {
    "zh-HK": [
        "你有冇諗過，{topic}可以改變你嘅工作方式？",
        "點解{audience}都要識{keyword}？今日話你知！",
        "{keyword}唔係得程式員先用得到！{topic}話你知點做",
        "如果我話你知，一個人都可以靠{keyword}開公司，你信唔信？",
        "停！你係咪仲用緊舊方法做{topic}？",
        "{topic}——呢個就係未來嘅工作模式！",
    ],
    "zh-CN": [
        "你有没有想过，{topic}可以改变你的工作方式？",
        "为什么{audience}都要懂{keyword}？今天告诉你！",
        "{keyword}不是只有程序员才用得到！{topic}告诉你怎么做",
        "如果我告诉你，一个人也可以靠{keyword}开公司，你信不信？",
        "停！你是不是还在用旧方法做{topic}？",
        "{topic}——这就是未来的工作模式！",
    ],
    "en-US": [
        "What if {topic} could completely change how you work?",
        "Why every {audience} needs to know about {keyword}!",
        "{keyword} isn't just for programmers! {topic} shows you how",
        "Can one person build a company with {keyword}? Watch this!",
        "Stop! Are you still doing {topic} the old way?",
        "{topic} — this is the future of work!",
    ],
}

_PROBLEMS: dict[str, list[str]] = {
    "zh-HK": [
        "好多{audience}面對嘅最大問題就係：工作量太大，一個人做唔嚟。",
        "你可能會覺得{keyword}好難，但其實最難嘅係唔知點開始。",
        "傳統做法有三大痛點：效率低、出錯多、重複性高。",
        "你係咪試過用 AI 幫手，但結果總係唔理想？呢個就係冇用 Harness 嘅問題。",
        "一人公司最大嘅敵人唔係競爭對手，而係時間唔夠用。",
    ],
    "zh-CN": [
        "很多{audience}面对的最大问题就是：工作量太大，一个人做不来。",
        "你可能觉得{keyword}很难，但其实最难的是不知道怎么开始。",
        "传统做法有三大痛点：效率低、出错多、重复性高。",
        "你是不是试过用 AI 帮忙，但结果总是不理想？这就是没用 Harness 的问题。",
        "一人公司最大的敌人不是竞争对手，而是时间不够用。",
    ],
    "en-US": [
        "The biggest challenge for {audience}: too much work, not enough time.",
        "You might think {keyword} is hard, but the hardest part is knowing where to start.",
        "Traditional approaches have 3 pain points: low efficiency, frequent errors, high repetition.",
        "Ever tried using AI but got disappointing results? That's because you didn't use a Harness.",
        "The biggest enemy of a one-person company isn't competition — it's running out of time.",
    ],
}

_CASE_STUDIES: dict[str, list[str]] = {
    "zh-HK": [
        "等我講個真實案例：有個創業者用{keyword}建立咗自動化工作流，由原本每日工作12個鐘，減到4個鐘就搞掂！",
        "舉個例子：一位自由工作者用 AI Agent 處理客戶查詢，回覆速度由2小時縮短到2分鐘。",
        "想像一下：你嘅 AI Agent 幫你做研究、寫初稿、排程發佈，你只需要審核同決策。",
        "有間一人公司用{keyword}自動生成社交媒體內容，月收入由0增長到5位數。",
        "一個真實故事：某技術人員用 Harness Engineering 方法論，將 AI 出錯率由40%降到5%以下。",
    ],
    "zh-CN": [
        "让我讲个真实案例：有个创业者用{keyword}建立了自动化工作流，从原来每天工作12小时，减少到4小时就搞定！",
        "举个例子：一位自由职业者用 AI Agent 处理客户查询，回复速度从2小时缩短到2分钟。",
        "想象一下：你的 AI Agent 帮你做研究、写初稿、排程发布，你只需要审核和决策。",
        "有家一人公司用{keyword}自动生成社交媒体内容，月收入从0增长到5位数。",
        "一个真实故事：某技术人员用 Harness Engineering 方法论，将 AI 出错率从40%降到5%以下。",
    ],
    "en-US": [
        "Real case: An entrepreneur built an automated workflow with {keyword}, "
        "cutting their 12-hour workday to just 4 hours!",
        "Example: A freelancer used AI Agents to handle client queries, "
        "cutting response time from 2 hours to 2 minutes.",
        "Imagine this: Your AI Agent does research, writes drafts, and schedules posts. "
        "You just review and decide.",
        "A one-person company used {keyword} to auto-generate social media content, "
        "growing monthly revenue from 0 to 5 figures.",
        "True story: A developer used Harness Engineering methodology to reduce AI error rate from 40% to under 5%.",
    ],
}

_SOLUTIONS: dict[str, list[str]] = {
    "zh-HK": [
        "解決方案就係 Harness Engineering：前饋約束 + 反饋驗證 = 閉環迭代。"
        "你設定規則，AI 喺規則內行動，出錯就自動修正。",
        "用{keyword}嘅正確方法：1) 定義清晰目標 2) 設定約束條件 "
        "3) 驗證每步結果 4) 迭代改進。呢個就係 Harness 方法論！",
        "關鍵在於：人類掌舵，智能體執行。你做決策，AI 做執行，Harness 確保唔出錯。",
        "Agent = Model + Harness。Model 提供能力，Harness 提供控制。兩者結合先係正確用法。",
    ],
    "zh-CN": [
        "解决方案就是 Harness Engineering：前馈约束 + 反馈验证 = 闭环迭代。"
        "你设定规则，AI 在规则内行动，出错就自动修正。",
        "用{keyword}的正确方法：1) 定义清晰目标 2) 设定约束条件 "
        "3) 验证每步结果 4) 迭代改进。这就是 Harness 方法论！",
        "关键在于：人类掌舵，智能体执行。你做决策，AI 做执行，Harness 确保不出错。",
        "Agent = Model + Harness。Model 提供能力，Harness 提供控制。两者结合才是正确用法。",
    ],
    "en-US": [
        "The solution is Harness Engineering: Feedforward constraints + Feedback verification "
        "= Closed-loop iteration. You set rules, AI acts within them, errors auto-correct.",
        "The correct way to use {keyword}: 1) Define clear goals 2) Set constraints "
        "3) Verify each step 4) Iterate and improve. This is the Harness methodology!",
        "The key principle: Human steers, Agent executes. "
        "You make decisions, AI executes, Harness ensures no errors.",
        "Agent = Model + Harness. Model provides capability, Harness provides control. "
        "Both together is the correct approach.",
    ],
}

_CTAS: dict[str, list[str]] = {
    "zh-HK": [
        "想學更多？訂閱我哋頻道，下集教你點樣由零開始建立你嘅 AI Agent 團隊！",
        "覺得有用嘅話，畀個 like 同分享！想深入了解{keyword}，留言話我知！",
        "追蹤我哋，每週都有新嘅 AI 同 Harness Engineering 實戰技巧！",
        "想用 AI 開你嘅一人公司？訂閱頻道，我哋一步步教你！",
    ],
    "zh-CN": [
        "想学更多？订阅我们频道，下集教你怎样从零开始建立你的 AI Agent 团队！",
        "觉得有用的话，给个赞和分享！想深入了解{keyword}，留言告诉我们！",
        "关注我们，每周都有新的 AI 和 Harness Engineering 实战技巧！",
        "想用 AI 开你的一人公司？订阅频道，我们一步步教你！",
    ],
    "en-US": [
        "Want to learn more? Subscribe and next time we'll show you how to build your AI Agent team from scratch!",
        "Found this useful? Like and share! Want to dive deeper into {keyword}? Leave a comment!",
        "Follow us for weekly AI and Harness Engineering practical tips!",
        "Want to start your one-person company with AI? Subscribe and we'll guide you step by step!",
    ],
}

_DIALOGUES: dict[str, list[list[str]]] = {
    "zh-HK": [
        ["小明：我每日做12個鐘都做唔完⋯⋯", "AI Agent：交畀我啦！我幫你處理重複性工作！"],
        ["老闆：呢個項目幾時搞掂？", "你：已經用 AI 自動化咗，今日就搞掂！"],
        ["學生：AI 會唔會取代我嘅工作？", "導師：唔會！識用 AI 嘅人先有競爭力！"],
        ["創業者：一個人點做咁多嘢？", "AI：你掌舵，我執行，就係咁簡單！"],
    ],
    "zh-CN": [
        ["小明：我每天做12个小时都做不完⋯⋯", "AI Agent：交给我吧！我帮你处理重复性工作！"],
        ["老板：这个项目什么时候搞定？", "你：已经用 AI 自动化了，今天就搞定！"],
        ["学生：AI 会不会取代我的工作？", "导师：不会！会用 AI 的人才有竞争力！"],
        ["创业者：一个人怎么做这么多事？", "AI：你掌舵，我执行，就这么简单！"],
    ],
    "en-US": [
        ["Tom: I work 12 hours a day and still can't finish...", "AI Agent: Let me handle the repetitive tasks!"],
        ["Boss: When will this project be done?", "You: Already automated with AI. Done today!"],
        ["Student: Will AI replace my job?", "Teacher: No! People who know how to use AI will have the edge!"],
        ["Entrepreneur: How can one person do so much?", "AI: You steer, I execute. Simple as that!"],
    ],
}

_IMAGE_PROMPTS: list[str] = [
    "comic style, {character} sitting at desk with laptop, "
    "thinking bubble with {keyword} icon, bright office background, cute cartoon style",
    "comic style, {character} looking surprised at glowing AI hologram, "
    "futuristic workspace, vibrant colors, speech bubble",
    "comic style, split panel: left side {character} stressed with messy desk, "
    "right side {character} relaxed with AI assistant helping, clean lines",
    "comic style, {character} high-fiving a cute robot, "
    "confetti falling, achievement unlocked banner, colorful background",
    "comic style, {character} standing on mountain top with AI drone assistant, "
    "sunrise background, determination expression, motivational poster style",
    "comic style, {character} at crossroads with signposts showing different AI tools, "
    "confused but curious expression, adventure map style",
]

_CHARACTERS: list[str] = [
    "young professional in business casual",
    "student with backpack and laptop",
    "friendly elderly person with glasses",
    "cute robot assistant with LED eyes",
    "creative freelancer with headphones",
]

_AUDIENCE_LABEL: dict[str, dict[Audience, str]] = {
    "zh-HK": {
        Audience.KIDS: "小朋友",
        Audience.STUDENTS: "學生",
        Audience.WORKING: "打工仔",
        Audience.ELDERLY: "長者",
    },
    "zh-CN": {
        Audience.KIDS: "小朋友",
        Audience.STUDENTS: "学生",
        Audience.WORKING: "上班族",
        Audience.ELDERLY: "长者",
    },
    "en-US": {
        Audience.KIDS: "kids",
        Audience.STUDENTS: "students",
        Audience.WORKING: "professionals",
        Audience.ELDERLY: "seniors",
    },
}


class TemplateEngine:
    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def generate_script(
        self,
        topic: TopicProposal,
        language: Language,
        episode_number: int = 1,
        total_episodes: int = 5,
        target_duration_seconds: float = 600.0,
    ) -> ComicScript:
        lang = language.value
        title = {
            Language.ZH_HK: topic.title_zh_hk,
            Language.ZH_CN: topic.title_zh_cn,
            Language.EN_US: topic.title_en,
        }.get(language, topic.title_en)

        keyword = self._rng.choice(topic.keywords)
        audience = self._rng.choice(topic.target_audience)
        audience_label = _AUDIENCE_LABEL.get(lang, _AUDIENCE_LABEL["en-US"]).get(audience, "people")
        character = self._rng.choice(_CHARACTERS)

        fmt: dict[str, str] = {
            "topic": title,
            "keyword": keyword,
            "audience": audience_label,
            "character": character,
            "episode": str(episode_number),
            "total": str(total_episodes),
        }

        hook = self._fill(self._rng.choice(_HOOKS.get(lang, _HOOKS["en-US"])), fmt)
        problem = self._fill(self._rng.choice(_PROBLEMS.get(lang, _PROBLEMS["en-US"])), fmt)
        case_study = self._fill(self._rng.choice(_CASE_STUDIES.get(lang, _CASE_STUDIES["en-US"])), fmt)
        solution = self._fill(self._rng.choice(_SOLUTIONS.get(lang, _SOLUTIONS["en-US"])), fmt)
        cta = self._fill(self._rng.choice(_CTAS.get(lang, _CTAS["en-US"])), fmt)
        dialogue_set = self._rng.choice(_DIALOGUES.get(lang, _DIALOGUES["en-US"]))

        phase_durations = self._distribute_duration(target_duration_seconds)

        scenes: list[ComicScene] = []

        scenes.append(self._make_scene(
            scene_number=1, phase="HOOK",
            description=f"Hook opening about {title}",
            narration=hook,
            dialogue=[],
            image_prompt=self._fill(self._rng.choice(_IMAGE_PROMPTS), {**fmt, "keyword": "AI"}),
            duration_seconds=phase_durations[0],
            language=language,
        ))

        scenes.append(self._make_scene(
            scene_number=2, phase="PROBLEM",
            description=f"Problem statement for {audience_label}",
            narration=problem,
            dialogue=dialogue_set[:1],
            image_prompt=self._fill(self._rng.choice(_IMAGE_PROMPTS), fmt),
            duration_seconds=phase_durations[1],
            language=language,
        ))

        case_dialogue = dialogue_set[1:] if len(dialogue_set) > 1 else dialogue_set
        scenes.append(self._make_scene(
            scene_number=3, phase="CASE_STUDY",
            description=f"Case study about {keyword}",
            narration=case_study,
            dialogue=case_dialogue,
            image_prompt=self._fill(self._rng.choice(_IMAGE_PROMPTS), fmt),
            duration_seconds=phase_durations[2],
            language=language,
        ))

        scenes.append(self._make_scene(
            scene_number=4, phase="SOLUTION",
            description=f"Harness Engineering solution with {keyword}",
            narration=solution,
            dialogue=[],
            image_prompt=self._fill(self._rng.choice(_IMAGE_PROMPTS), fmt),
            duration_seconds=phase_durations[3],
            language=language,
        ))

        scenes.append(self._make_scene(
            scene_number=5, phase="CTA",
            description="Call to action",
            narration=cta,
            dialogue=[],
            image_prompt=self._fill(self._rng.choice(_IMAGE_PROMPTS), {**fmt, "keyword": "subscribe"}),
            duration_seconds=phase_durations[4],
            language=language,
        ))

        total = sum(s.duration_seconds for s in scenes)

        script = ComicScript(
            id=f"CS-{uuid.uuid4().hex[:8]}",
            topic_id=topic.id,
            hook=hook,
            scenes=scenes,
            cta=cta,
            total_duration_seconds=total,
            language=language,
            created_at=datetime.now(),
        )

        logger.info(
            "template_script_generated",
            topic_id=topic.id,
            language=lang,
            scenes=len(scenes),
            duration=total,
            mode="template_only",
        )

        return script

    def _fill(self, template: str, fmt: dict[str, str]) -> str:
        try:
            return template.format(**{k: v for k, v in fmt.items() if "{" + k + "}" in template})
        except (KeyError, IndexError):
            return template

    def _distribute_duration(self, total: float) -> list[float]:
        ratios = [0.05, 0.20, 0.35, 0.30, 0.10]
        return [round(total * r, 1) for r in ratios]

    def _make_scene(
        self,
        scene_number: int,
        phase: str,
        description: str,
        narration: str,
        dialogue: list[str],
        image_prompt: str,
        duration_seconds: float,
        language: Language,
    ) -> ComicScene:
        return ComicScene(
            scene_number=scene_number,
            description=description,
            narration_zh_hk=narration if language == Language.ZH_HK else "",
            narration_zh_cn=narration if language == Language.ZH_CN else "",
            narration_en=narration if language == Language.EN_US else "",
            dialogue=dialogue,
            image_prompt=image_prompt,
            duration_seconds=duration_seconds,
        )
