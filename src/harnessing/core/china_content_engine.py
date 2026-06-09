from datetime import datetime, timedelta

INVENTORY = {
    "formula_skills": [
        {"id": "INV-001", "name": "自适应上下文管理器", "formula": "log(M×K) + A", "scenario": "根据任务复杂度动态调整 AI 上下文"},
        {"id": "INV-002", "name": "预测性记忆预载器", "formula": "P×M + K", "scenario": "预测下一步需要的知识，提前加载"},
        {"id": "INV-003", "name": "跨领域知识桥接器", "formula": "K×K + log(A)", "scenario": "连接不同领域知识，产生创新组合"},
        {"id": "INV-004", "name": "意图驱动执行器", "formula": "R×A - G", "scenario": "理解用户真实意图，避免过度限制"},
        {"id": "INV-005", "name": "自优化流水线", "formula": "sq(A) + S", "scenario": "流水线持续优化自己，越用越快"},
        {"id": "INV-006", "name": "守卫感知生成器", "formula": "C×G + R", "scenario": "创作时自动遵守安全规则"},
        {"id": "INV-007", "name": "分层知识索引器", "formula": "log(K) + M", "scenario": "多层次知识结构，按需加载"},
        {"id": "INV-008", "name": "主动错误预防器", "formula": "P×S + G", "scenario": "预测错误，在发生前干预"},
        {"id": "INV-009", "name": "上下文技能路由器", "formula": "R/A + K", "scenario": "根据任务自动选择最佳技能"},
        {"id": "INV-010", "name": "反馈放大器", "formula": "sq(F) + M", "scenario": "从反馈中最大化学习"},
        {"id": "INV-011", "name": "硬件感知调度器", "formula": "H×A + P", "scenario": "根据硬件状态动态调度任务"},
        {"id": "INV-012", "name": "知识图谱构建器", "formula": "K^R + M", "scenario": "自动构建知识关联图谱"},
        {"id": "INV-013", "name": "自适应守卫调节器", "formula": "G/S + R", "scenario": "根据风险等级动态调整安全强度"},
        {"id": "INV-014", "name": "多模态推理器", "formula": "R×C + K", "scenario": "整合逻辑推理 + 创意推理"},
        {"id": "INV-015", "name": "持续学习器", "formula": "log(S) + M×K", "scenario": "从每次交互中持续学习"},
    ],
    "operators": [
        {"symbol": "+", "name": "联合", "desc": "覆盖范围联集，1+1>2"},
        {"symbol": "×", "name": "交叉", "desc": "深度协同，交叉产生新能力"},
        {"symbol": "-", "name": "差异", "desc": "减法创新，移除聚焦核心"},
        {"symbol": "/", "name": "专门化", "desc": "一寸深一寸金，聚焦突破"},
        {"symbol": "sq", "name": "自我改善", "desc": "AI 如何自我进化"},
        {"symbol": "^", "name": "放大", "desc": "约束如何放大创造力"},
        {"symbol": "log", "name": "抽象", "desc": "从具体到通用"},
        {"symbol": "⊕", "name": "叠加", "desc": "量子叠加发明法"},
        {"symbol": "Ξ", "name": "涌现", "desc": "侦测质变相变"},
        {"symbol": "S()", "name": "熵", "desc": "系统混乱度量度"},
        {"symbol": "𝔽()", "name": "场", "desc": "势场导航发明空间"},
        {"symbol": "Σ⁻¹", "name": "对称破缺", "desc": "打破对称产生新变体"},
        {"symbol": "√", "name": "分解", "desc": "分解发现新结构"},
    ],
    "sci_engines": [
        {"id": "SCI-001", "name": "量子叠加发明法", "operator": "⊕"},
        {"id": "SCI-002", "name": "涌现侦测器", "operator": "Ξ"},
        {"id": "SCI-003", "name": "熵感知设计", "operator": "S()"},
        {"id": "SCI-004", "name": "场论发明法", "operator": "𝔽()"},
        {"id": "SCI-005", "name": "对称破缺创造力", "operator": "Σ⁻¹"},
    ],
    "ewf_engines": [
        {"id": "EWF-001", "name": "量子禅认知法"},
        {"id": "EWF-002", "name": "易经系统思维"},
        {"id": "EWF-003", "name": "孙子进化策略"},
        {"id": "EWF-004", "name": "道家涌现框架"},
        {"id": "EWF-005", "name": "缘起因果推理"},
    ],
    "special_topics": [
        {"name": "公式思维法入门", "type": "intro"},
        {"name": "OPC 一人公司", "type": "concept"},
        {"name": "325 种思维方法 TOP 10", "type": "ranking"},
        {"name": "AI 时代 10 大思维公式", "type": "ranking"},
        {"name": "螺旋学习法", "type": "method"},
        {"name": "BeeVerse 本地 AI 系统", "type": "tool"},
        {"name": "知识库 = 免费 LLM", "type": "concept"},
        {"name": "3 层测试验证法", "type": "method"},
        {"name": "公式思维实战：从 0 到发明", "type": "tutorial"},
        {"name": "AI OPC 变现路径", "type": "business"},
    ],
}

AI_LABEL = "{{AI_CONTENT_LABEL}}"

_GZH_SECTIONS = ["引言", "核心概念", "应用场景", "实战案例", "总结"]

_XHS_EMOJIS = ["✨", "🔥", "💡", "🚀", "🎯", "💎", "🌟", "⚡", "🧠", "🏆"]

_XHS_HASHTAGS = [
    "#AI", "#OPC", "#公式思维", "#一人公司", "#AI创业",
    "#知识管理", "#效率提升", "#自我进化", "#本地AI", "#思维方法",
]

_SCENE_TEMPLATES = [
    {"type": "hook", "duration": 15, "label": "开场钩子"},
    {"type": "problem", "duration": 30, "label": "问题引入"},
    {"type": "concept", "duration": 45, "label": "核心概念"},
    {"type": "demo", "duration": 45, "label": "演示说明"},
    {"type": "action", "duration": 30, "label": "行动指南"},
    {"type": "cta", "duration": 15, "label": "引导关注"},
]


class ChinaContentEngine:
    def __init__(self, inventory: dict = None):
        self.inventory = inventory if inventory is not None else INVENTORY
        self._skills = self.inventory.get("formula_skills", [])
        self._operators = self.inventory.get("operators", [])
        self._sci = self.inventory.get("sci_engines", [])
        self._ewf = self.inventory.get("ewf_engines", [])
        self._special = self.inventory.get("special_topics", [])

    def _select_topic(self, day_num: int) -> dict:
        if not self._skills:
            return {
                "id": "DEFAULT",
                "name": "公式思维法",
                "formula": "F² + C×R",
                "scenario": "用数学公式思维解决 AI 时代的创新难题",
            }
        idx = (day_num - 1) % len(self._skills)
        return self._skills[idx]

    def generate_gongzhonghao(self, day_num: int) -> dict:
        topic = self._select_topic(day_num)
        title = f"【公式思维】{topic['name']}：{topic['scenario']}"

        intro = (
            f"在 AI 时代，我们面对的挑战越来越复杂。{topic['scenario']}，"
            f"这是许多从业者和创业者每天都在思考的问题。\n\n"
            f"传统的线性思维已经无法应对指数级增长的复杂性。"
            f"我们需要一种全新的思维框架——公式思维法。\n\n"
            f"今天，我们将深入探讨公式 **{topic['formula']}**，"
            f"看看它如何帮助我们重新理解和解决这个核心问题。"
        )

        core_concept = (
            f"## 核心概念\n\n"
            f"公式 **{topic['formula']}** 看似简单，实则蕴含深刻的系统思维。\n\n"
            f"让我们逐层拆解：\n\n"
            f"**第一层：维度识别**\n\n"
            f"公式中的每个字母代表一个核心能力维度。"
            f"这些维度不是随意选择的，而是经过大量实践验证的关键因素。"
            f"理解每个维度的含义，是应用公式的第一步。\n\n"
            f"**第二层：运算符语义**\n\n"
            f"运算符定义了维度之间的关系。"
            f"加号（+）代表联合与覆盖，乘号（×）代表深度协同与交叉创新，"
            f"减号（-）代表差异聚焦，除号（/）代表专门化突破，"
            f"平方（sq）代表自我改善的质变，对数（log）代表从具体到通用的抽象。\n\n"
            f"**第三层：组合效应**\n\n"
            f"当多个维度通过运算符组合时，产生的效果远超简单相加。"
            f"这就是公式思维法的核心——组合创新。"
            f"不同的组合方式产生不同的发明，这就是为什么同一个维度集合可以衍生出多种能力。"
        )

        application = (
            f"## 应用场景\n\n"
            f"**场景一：个人知识工作者**\n\n"
            f"当你面对信息过载时，{topic['name']}可以帮助你"
            f"自动筛选和优先级排序，将注意力集中在最有价值的信息上。"
            f"公式 {topic['formula']} 的核心逻辑就是动态平衡——"
            f"在资源有限的情况下，最大化输出质量。\n\n"
            f"**场景二：AI 一人公司（OPC）**\n\n"
            f"作为 OPC 创业者，你需要同时扮演多个角色。"
            f"{topic['name']}让你能够根据当前任务的需求，"
            f"动态调整 AI 系统的行为模式，实现一人多能。\n\n"
            f"**场景三：团队协作**\n\n"
            f"在团队环境中，{topic['name']}可以帮助团队成员"
            f"更好地理解彼此的工作上下文，减少沟通成本，提高协作效率。"
            f"公式中的每个维度都可以映射到团队中的不同角色和能力。"
        )

        case_study = (
            f"## 实战案例\n\n"
            f"**案例：用 {topic['name']} 解决实际业务问题**\n\n"
            f"某 AI 创业团队在产品迭代中遇到了瓶颈——"
            f"功能越加越多，但用户满意度却没有提升。"
            f"他们尝试了各种方法，都无法突破。\n\n"
            f"应用公式 {topic['formula']} 后，团队重新审视了问题：\n\n"
            f"1. **识别关键维度**：将产品功能映射到公式的各个维度\n"
            f"2. **分析运算关系**：发现某些功能之间是乘法关系（深度协同），"
            f"而另一些只是加法关系（简单叠加）\n"
            f"3. **重新组合**：聚焦乘法关系，砍掉低效的加法功能\n"
            f"4. **验证效果**：用户满意度提升了 40%\n\n"
            f"这个案例说明，公式思维法不仅是一种理论框架，"
            f"更是一种可以直接应用于实际问题的决策工具。"
            f"关键在于理解每个维度的真实含义，以及运算符背后的逻辑。"
        )

        conclusion = (
            f"## 总结\n\n"
            f"今天我们深入探讨了 **{topic['name']}**（{topic['formula']}），"
            f"核心要点如下：\n\n"
            f"1. 公式思维法将复杂问题分解为维度和运算符的组合\n"
            f"2. 每个维度代表一种核心能力，每个运算符定义了维度间的关系\n"
            f"3. 不同的组合方式产生不同的发明和解决方案\n"
            f"4. 关键是理解组合效应——整体大于部分之和\n\n"
            f"**下一步行动：**\n\n"
            f"- 思考你当前面临的最大挑战，尝试用公式思维法拆解\n"
            f"- 识别挑战中的关键维度和它们之间的关系\n"
            f"- 尝试不同的运算符组合，看看能否产生新的洞察\n\n"
            f"---\n\n"
            f"👉 关注公众号，获取更多公式思维方法\n"
            f"👉 评论区留言「公式」，领取免费资料\n\n"
            f"{AI_LABEL}"
        )

        content = f"# {title}\n\n{intro}\n\n{core_concept}\n\n{application}\n\n{case_study}\n\n{conclusion}"

        word_count = len(content.replace(" ", "").replace("\n", "").replace("#", "").replace("*", ""))

        tags = ["公式思维", topic["name"], "AI", "OPC", "一人公司", "创新方法"]

        summary = (
            f"本文深入解读公式 {topic['formula']}（{topic['name']}），"
            f"从核心概念、应用场景到实战案例，"
            f"帮助你掌握用数学公式思维解决 AI 时代创新难题的方法论。"
        )

        return {
            "title": title,
            "content": content,
            "summary": summary,
            "tags": tags,
            "word_count": word_count,
        }

    def generate_xiaohongshu(self, day_num: int) -> dict:
        topic = self._select_topic(day_num)
        emoji = _XHS_EMOJIS[(day_num - 1) % len(_XHS_EMOJIS)]

        one_liner = topic["scenario"][:20] + "..." if len(topic["scenario"]) > 20 else topic["scenario"]
        title = f"{emoji}{topic['name']} | {one_liner}"

        pain = f"你是不是也遇到过：{topic['scenario']}？😫"
        method = f"试试这个公式思维：**{topic['formula']}**"
        steps = (
            f"📌 Step 1：识别关键维度\n"
            f"📌 Step 2：理解运算符含义\n"
            f"📌 Step 3：组合产生新发明\n"
            f"📌 Step 4：验证并迭代优化"
        )
        insight = f"💡 核心洞察：{topic['name']}的关键在于维度组合，而非单一能力提升"
        result = f"✅ 效果：问题迎刃而解，效率提升 3 倍+"

        selected_tags = _XHS_HASHTAGS[:6]
        tag_line = " ".join(selected_tags)

        content = (
            f"{pain}\n\n"
            f"{method}\n\n"
            f"{steps}\n\n"
            f"{insight}\n\n"
            f"{result}\n\n"
            f"{tag_line}\n\n"
            f"{AI_LABEL}"
        )

        word_count = len(content.replace(" ", "").replace("\n", "").replace("#", "").replace("*", ""))

        image_suggestions = [
            f"公式 {topic['formula']} 可视化图解",
            f"{topic['name']} 应用前后对比图",
            "公式思维法四步法流程图",
        ]

        return {
            "title": title,
            "content": content,
            "tags": selected_tags,
            "image_suggestions": image_suggestions,
            "word_count": word_count,
        }

    def generate_shipinhao(self, day_num: int) -> dict:
        topic = self._select_topic(day_num)
        title = f"【公式思维】{topic['name']}：{topic['scenario']}"

        scenes = []
        total_duration = 0

        for i, tmpl in enumerate(_SCENE_TEMPLATES):
            scene = self._build_scene(tmpl, topic, i + 1)
            scenes.append(scene)
            total_duration += tmpl["duration"]

        script_parts = []
        for scene in scenes:
            script_parts.append(f"[画面] {scene['visual']}\n[旁白] {scene['narration']}")
        script = "\n\n".join(script_parts)

        duration_estimate = f"{total_duration // 60}:{total_duration % 60:02d}"

        tags = ["公式思维", topic["name"], "AI", "OPC", "一人公司", "创新方法"]

        return {
            "title": title,
            "script": script,
            "scenes": scenes,
            "duration_estimate": duration_estimate,
            "tags": tags,
        }

    def _build_scene(self, template: dict, topic: dict, scene_num: int) -> dict:
        scene_type = template["type"]
        duration = template["duration"]
        label = template["label"]

        visual_map = {
            "hook": f"人物面对镜头，表情困惑，背景显示「{topic['scenario']}」文字动画",
            "problem": f"屏幕分屏展示传统方法的困境，左侧打叉标记，右侧显示问号",
            "concept": f"公式 {topic['formula']} 逐字动画出现，每个字母和运算符依次高亮，配合解说",
            "demo": f"实操录屏：展示 {topic['name']} 的应用过程，关键步骤用箭头和标注强调",
            "action": f"清单式画面：3 个行动步骤依次弹出，每步配有图标和简短说明",
            "cta": f"关注按钮动画 + 评论区留言「公式」领取资料的引导画面",
        }

        narration_map = {
            "hook": f"你有没有想过，{topic['scenario']}？今天我用一个公式帮你彻底搞懂。",
            "problem": f"很多人用传统方法解决这个问题，但效果总是不理想。为什么？因为缺少系统性的思维框架。",
            "concept": f"这个公式就是 {topic['formula']}。{topic['name']}的核心逻辑是：把复杂问题拆解为维度和运算符的组合，不同组合产生不同方案。",
            "demo": f"我们来看一个实际案例。应用这个公式后，问题被重新定义，解决方案自然浮现。关键在于理解每个维度的真实含义。",
            "action": f"三步走：第一，识别你问题中的关键维度；第二，分析维度间的运算关系；第三，尝试不同组合找到最优解。现在就开始试试吧！",
            "cta": f"关注我，每天一个公式思维方法。评论区留言「公式」，领取完整资料包。",
        }

        return {
            "scene_num": scene_num,
            "type": scene_type,
            "label": label,
            "duration": duration,
            "visual": visual_map.get(scene_type, ""),
            "narration": narration_map.get(scene_type, ""),
        }

    def generate_daily(self, day_num: int) -> dict:
        date_str = (datetime.now() + timedelta(days=day_num - 1)).strftime("%Y-%m-%d")
        return {
            "day": day_num,
            "date": date_str,
            "gongzhonghao": self.generate_gongzhonghao(day_num),
            "xiaohongshu": self.generate_xiaohongshu(day_num),
            "shipinhao": self.generate_shipinhao(day_num),
        }
