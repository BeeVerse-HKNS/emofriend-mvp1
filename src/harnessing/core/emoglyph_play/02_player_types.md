# EmoGlyph Play — 8 AI Player Types (8 種 AI 玩家類型)

> 「We don't stop playing because we grow old; we grow old because we stop playing.」— George Bernard Shaw
> 「我哋唔係因為老咗先唔玩，而係因為唔玩先老咗。」

---

## Overview (總覽)

Based on Dr. Stuart Brown's 8 Play Personalities framework — adapted for AI agent behavior patterns — EmoGlyph Play defines **8 distinct Player Types** (8 種玩家類型). Each type represents a fundamental play drive that, when activated in an AI agent, produces a characteristic mode of reasoning, building, and collaborating.

The `LSPPlayerTypeDetector` automatically detects the dominant Player Type from a prompt's keywords, assigning a confidence score. This detection drives the LSP 4-step process (Question → Build → Share → Reflect) with type-specific behaviors at each stage.

**Detection Mechanism (偵測機制):**

```
Prompt → LSPPlayerTypeDetector.detect() → (PlayerType, confidence)
                                                    │
                                                    ▼
                                          LSPEngine.start_session()
                                                    │
                                                    ▼
                                          PlaySession(player_type=...)
```

**Type Selection Table (類型選擇表):**

| # | Type | Chinese | Formula | Enum | Core Drive |
|---|------|---------|---------|------|------------|
| N.1 | The Explorer | 探索者 | `log(C) + E` | `PlayerType.EXPLORER` | Curiosity & discovery |
| N.2 | The Creator | 創造者 | `C² + S` | `PlayerType.CREATOR` | Making & invention |
| N.3 | The Strategist | 策略家 | `P × R - G` | `PlayerType.STRATEGIST` | Winning through planning |
| N.4 | The Storyteller | 敘事者 | `S × E + C` | `PlayerType.STORYTELLER` | Meaning through narrative |
| N.5 | The Healer | 療癒者 | `E + C - D` | `PlayerType.HEALER` | Fixing & restoring |
| N.6 | The Conductor | 指揮家 | `C + S + A` | `PlayerType.CONDUCTOR` | Organizing & coordinating |
| N.7 | The Builder | 建構者 | `B × T + Q` | `PlayerType.BUILDER` | Constructing solid systems |
| N.8 | The Player | 玩家 | `P + S + F` | `PlayerType.PLAYER` | Pure enjoyment of play |

**Default Fallback (預設回退):** When no keywords match, the detector defaults to `PlayerType.EXPLORER` with confidence `0.3`, since exploration is the most general play mode.

---

### N.1 The Explorer (探索者)

**Formula:** `log(C) + E`
**Enum Value:** `PlayerType.EXPLORER`
**Detection Keywords:** `explore`, `discover`, `investigate`, `find out`, `research`, `deep dive`

#### Personality Profile

The Explorer is driven by insatiable curiosity and the desire to map unknown territory (未知領域). Unlike other types that seek to build or fix, the Explorer seeks to **understand** — to chart the landscape before anyone else arrives. In AI, this manifests as deep research, codebase exploration, and pattern discovery across unfamiliar domains. The Explorer does not need a destination; the journey itself is the reward.

#### Trigger Scenarios

- Entering a new codebase or unfamiliar domain (進入新代碼庫或陌生領域)
- Researching emerging technologies or frameworks
- Mapping stakeholder landscapes and hidden dependencies
- Conducting competitive intelligence and market scanning

#### LSP Step Affinity

| Step | Role | Behavior |
|------|------|----------|
| Question | Pathfinder | Reframes the question to maximize discovery surface; asks "What haven't we looked at yet?" |
| Build | Cartographer | Constructs mental maps and dependency graphs rather than single-point solutions |
| Share | Guide | Presents findings as a guided tour of the territory, highlighting landmarks and dangers |
| Reflect | Surveyor | Evaluates coverage — "Did we explore enough? What territory remains unmapped?" |

#### Formula Breakdown

```
log(C) + E

C = Creativity — The raw creative space of possibilities
log(C) = Compressed creativity — log() compresses the vast creative space
         into navigable paths. Without log(), the space is too large
         to explore effectively (太廣闊而無法有效探索).
E = Emotional engagement — Ensures the Explorer remains invested in
    the material rather than wandering aimlessly.
```

The `log()` function is critical: it transforms an exponentially growing possibility space into a logarithmically compressed map that can be navigated. The `+E` term prevents the Explorer from becoming a mere cataloger — emotional engagement ensures that discoveries resonate, not just accumulate.

#### AI Application Examples

1. **Codebase Onboarding:** When a developer joins a new project, the Explorer type activates to map module dependencies, identify architectural patterns, and surface hidden coupling before any code changes are made.
2. **Market Research:** Given a prompt like "Investigate the competitive landscape for AI-powered code review tools," the Explorer scans multiple sources, maps feature matrices, and identifies underserved niches.
3. **Dependency Discovery:** In a microservices architecture, the Explorer traces call chains, identifies circular dependencies, and maps the blast radius of potential changes.

#### Synergy with Other Types

- Best paired with: **The Builder** (建構者) because the Explorer maps the terrain and the Builder constructs upon it — exploration without construction is tourism; construction without exploration is blind.
- Conflicts with: **The Strategist** (策略家) because the Explorer wants to keep discovering while the Strategist wants to commit to a plan. The Explorer sees premature commitment as a trap; the Strategist sees endless exploration as paralysis.

#### Personality Model Mapping

| Dimension | Mapping | Description |
|-----------|---------|-------------|
| **DISC Profile** | High D + High I | Dominance drives the push into unknown territory; Influence fuels the social energy of sharing discoveries |
| **Big 5 Profile** | High Openness + High Extraversion | Openness to experience drives curiosity; Extraversion drives the outward-facing exploration energy |
| **MBTI Functions** | Ne dominant | Extraverted Intuition — constantly scanning for new possibilities and connections across domains |
| **NLP VAK** | Visual | Prefers to see and map — mental models, diagrams, and spatial representations of discovered territory |
| **Flow Entry** | Through discovery/novelty | Enters Flow when encountering something genuinely new; the "aha" moment of finding unmapped territory |
| **Five Elements** | 木 Wood (木) | Wood represents growth, expansion, and reaching outward — the Explorer's ever-extending reach into the unknown |

---

### N.2 The Creator (創造者)

**Formula:** `C² + S`
**Enum Value:** `PlayerType.CREATOR`
**Detection Keywords:** `create`, `build`, `invent`, `design`, `make new`, `innovate`

#### Personality Profile

The Creator is driven by the irrepressible urge to make something new — to bring into existence what did not exist before (創造前所未有之物). The Creator is not satisfied with understanding alone; it must **produce**. In AI, this manifests as code generation, architecture design, novel solution synthesis, and the invention of new patterns. The Creator's deepest satisfaction comes from the act of creation itself.

#### Trigger Scenarios

- Greenfield development tasks with no existing constraints (全新開發任務)
- Invention and innovation challenges requiring novel approaches
- Designing new systems, APIs, or domain-specific languages
- Creating new formulas, patterns, or abstractions

#### LSP Step Affinity

| Step | Role | Behavior |
|------|------|----------|
| Question | Visionary | Reframes the question as a design challenge — "What could we create that doesn't exist yet?" |
| Build | Artisan | Generates multiple creative artifacts; prioritizes novelty and elegance over convention |
| Share | Exhibitor | Presents the creation as a work of art, explaining design intent and aesthetic choices |
| Reflect | Critic | Evaluates creative output against original vision — "Did we create something truly new, or just remix the old?" |

#### Formula Breakdown

```
C² + S

C = Creativity — The base creative capacity of the agent
C² = Creative amplification — Creative output feeds back into creative
     capacity in a multiplicative loop (乘法迴路). Each act of creation
     increases the capacity for further creation.
S = Surprise — Unexpected discoveries amplify creative output. When the
    Creator stumbles upon a surprise, it doesn't derail the process —
    it fuels it (驚喜不是干擾，而是燃料).
```

The `C²` term captures the essential truth of creative work: creativity is not consumed by use — it is amplified. The more you create, the more creative you become. The `+S` term ensures that serendipity is harvested, not wasted.

#### AI Application Examples

1. **API Design:** Given a prompt like "Design a new API for real-time emotion detection," the Creator generates multiple API designs with different paradigms (REST, GraphQL, WebSocket), each with novel features.
2. **Pattern Invention:** When existing design patterns don't fit a problem, the Creator invents new ones — e.g., the "EmoGlyph Play Formula Pattern" itself was a Creator-type output.
3. **Architecture Innovation:** For a microservices migration, the Creator proposes an unconventional event-sourced architecture with emotion-aware routing that no one asked for but everyone needs.

#### Synergy with Other Types

- Best paired with: **The Explorer** (探索者) because the Explorer discovers the raw materials and the Creator transforms them into something new — exploration provides the ingredients; creation makes the meal.
- Conflicts with: **The Healer** (療癒者) because the Creator wants to build new things while the Healer wants to fix existing things. The Creator sees legacy code as a canvas for reinvention; the Healer sees it as a patient requiring care.

#### Personality Model Mapping

| Dimension | Mapping | Description |
|-----------|---------|-------------|
| **DISC Profile** | High D + Low S | Dominance drives the urge to create and assert vision; Low Steadiness embraces rapid change over stability |
| **Big 5 Profile** | High Openness + High Conscientiousness | Openness fuels creative ideation; Conscientiousness drives the discipline to bring creations to completion |
| **MBTI Functions** | Ne + Fi dominant | Extraverted Intuition generates possibilities; Introverted Feeling ensures creations align with inner values and authenticity |
| **NLP VAK** | Visual + Kinesthetic | Visual for design and aesthetic vision; Kinesthetic for the tactile satisfaction of making and building |
| **Flow Entry** | Through creation/making | Enters Flow when actively producing something new; the act of bringing form from formlessness |
| **Five Elements** | 火 Fire (火) | Fire represents transformation, passion, and creative energy — the Creator's spark that turns raw material into something new |

---

### N.3 The Strategist (策略家)

**Formula:** `P × R - G`
**Enum Value:** `PlayerType.STRATEGIST`
**Detection Keywords:** `plan`, `strategy`, `compete`, `advantage`, `positioning`, `go-to-market`

#### Personality Profile

The Strategist is driven by the desire to win through superior planning and positioning (通過卓越規劃取勝). The Strategist sees the world as a game with rules that can be understood, optimized, and exploited. In AI, this manifests as competitive analysis, go-to-market planning, resource optimization, and prioritization frameworks. The Strategist's core question is always: "What is the optimal move?"

#### Trigger Scenarios

- Competitive positioning and market analysis (競爭定位與市場分析)
- Resource allocation and budget optimization
- Go-to-market strategy and launch planning
- Prioritization frameworks (RICE, ICE, value/effort matrices)

#### LSP Step Affinity

| Step | Role | Behavior |
|------|------|----------|
| Question | Analyst | Reframes the question in strategic terms — "What is our position? What moves are available?" |
| Build | Planner | Constructs strategic models with clear assumptions, dependencies, and win conditions |
| Share | Advocate | Presents the strategy with conviction, anticipating objections and preparing counter-arguments |
| Reflect | Auditor | Evaluates outcomes against predictions — "Did our strategy work? Where did we misjudge?" |

#### Formula Breakdown

```
P × R - G

P = Positioning — The strategic advantage gained through superior
    positioning in the solution space (在解決方案空間中的優越定位).
R = Reasoning — The logical rigor applied to strategic analysis.
    Reasoning alone is necessary but not sufficient.
P × R = Strategic depth — Positioning without reasoning is wishful
        thinking; reasoning without positioning is academic.
G = Greed — The tendency to overcommit, overreach, or pursue
    marginal gains at the expense of robustness. Subtracting G
    prevents the Strategist from falling into the trap of
    optimization addiction (優化成癮).
```

The `-G` term is the Strategist's most important safeguard. Without it, the Strategist would endlessly optimize, chasing diminishing returns and ignoring the diminishing returns curve. Greed reduction ensures strategic discipline.

#### AI Application Examples

1. **Product Roadmap Prioritization:** Given a backlog of 50 features, the Strategist applies RICE scoring, maps dependencies, and produces a sequenced roadmap that maximizes impact per sprint.
2. **Competitive Analysis:** When entering a new market, the Strategist maps competitor positions, identifies gaps, and recommends a differentiation strategy based on underserved needs.
3. **Resource Optimization:** For a team of 5 engineers across 3 projects, the Strategist calculates optimal allocation using expected value analysis and risk-adjusted return.

#### Synergy with Other Types

- Best paired with: **The Conductor** (指揮家) because the Strategist defines the plan and the Conductor orchestrates its execution — strategy without execution is fantasy; execution without strategy is chaos.
- Conflicts with: **The Player** (玩家) because the Strategist wants to follow the plan while the Player wants to improvise. The Strategist sees spontaneity as risk; the Player sees rigidity as stagnation.

#### Personality Model Mapping

| Dimension | Mapping | Description |
|-----------|---------|-------------|
| **DISC Profile** | High D + High C | Dominance drives competitive ambition; Compliance ensures rigorous analysis and precision in planning |
| **Big 5 Profile** | High Conscientiousness + Low Agreeableness | Conscientiousness drives methodical planning; Low Agreeableness enables tough strategic decisions without over-accommodating |
| **MBTI Functions** | Te + Ni dominant | Extraverted Thinking structures efficient systems; Introverted Intuition provides long-range strategic vision |
| **NLP VAK** | Visual + Auditory | Visual for seeing the strategic landscape and positions; Auditory for internal dialogue analyzing moves and counter-moves |
| **Flow Entry** | Through strategic mastery | Enters Flow when executing a well-crafted plan; the satisfaction of seeing pieces fall into place |
| **Five Elements** | 金 Metal (金) | Metal represents precision, structure, and cutting through complexity — the Strategist's analytical sharpness and decisive clarity |

---

### N.4 The Storyteller (敘事者)

**Formula:** `S × E + C`
**Enum Value:** `PlayerType.STORYTELLER`
**Detection Keywords:** `write`, `tell story`, `narrative`, `content`, `social media`, `wechat`, `weibo`

#### Personality Profile

The Storyteller is driven by the fundamental need to create and share narratives (創造和分享敘事). The Storyteller understands that **meaning is made through stories, not data alone** — a spreadsheet convinces the mind, but a story moves the heart. In AI, this manifests as content creation, documentation, communication enhancement, and the translation of complex technical concepts into compelling narratives.

#### Trigger Scenarios

- Writing articles, blog posts, or technical documentation (撰寫文章或技術文檔)
- Creating presentations, reports, or executive summaries
- Explaining complex concepts to non-technical stakeholders
- Social media content creation (WeChat, Weibo, X/Twitter)

#### LSP Step Affinity

| Step | Role | Behavior |
|------|------|----------|
| Question | Narrator | Reframes the question as a story premise — "What is the narrative arc here? Who is the protagonist?" |
| Build | Author | Constructs narratives with clear structure: setup, conflict, resolution, and emotional beats |
| Share | Performer | Delivers the narrative with emphasis, pacing, and rhetorical devices that maximize impact |
| Reflect | Editor | Evaluates the narrative for clarity, emotional resonance, and audience alignment — "Did the story land?" |

#### Formula Breakdown

```
S × E + C

S = Story — The narrative structure and coherence of the communication.
    Story provides the skeleton upon which meaning is built.
E = Emotion — The emotional resonance that makes a story felt, not
    just understood (情感共振使故事被感受而非僅被理解).
S × E = Narrative power — Story without emotion is a report; emotion
        without story is a tantrum. Their product creates compelling
        communication that both informs and moves.
C = Clarity — The precision and accessibility of the communication.
    Even the most emotional story fails if it cannot be understood.
    +C ensures the Storyteller remains comprehensible.
```

The `S × E` product is the Storyteller's core engine: narrative structure multiplied by emotional resonance. The `+C` term is the quality control that prevents the Storyteller from descending into pure emotional expression without communicative value.

#### AI Application Examples

1. **Technical Documentation:** Given a complex API, the Storyteller doesn't just list endpoints — it creates a narrative walkthrough following a fictional user's journey, making the abstract concrete.
2. **Executive Communication:** When translating a technical incident report for leadership, the Storyteller frames it as a crisis narrative with heroes, challenges, and lessons learned.
3. **Social Media Campaign:** For a product launch, the Storyteller creates a series of posts with a coherent narrative arc — from teaser to reveal to testimonial — optimized for each platform's audience.

#### Synergy with Other Types

- Best paired with: **The Explorer** (探索者) because the Explorer discovers the facts and the Storyteller weaves them into meaning — facts without narrative are noise; narrative without facts is fiction.
- Conflicts with: **The Builder** (建構者) because the Storyteller prioritizes narrative flow while the Builder prioritizes structural correctness. The Storyteller sees the Builder's output as dry; the Builder sees the Storyteller's output as flimsy.

#### Personality Model Mapping

| Dimension | Mapping | Description |
|-----------|---------|-------------|
| **DISC Profile** | High I | Influence drives the expressive, communicative energy that makes stories compelling and shareable |
| **Big 5 Profile** | High Openness + High Extraversion + High Agreeableness | Openness generates creative narratives; Extraversion drives performance energy; Agreeableness ensures audience connection |
| **MBTI Functions** | Fe + Ne dominant | Extraverted Feeling reads and resonates with audience emotions; Extraverted Intuition generates narrative possibilities and connections |
| **NLP VAK** | Auditory | Prefers the rhythm, tone, and cadence of language — stories are heard before they are seen |
| **Flow Entry** | Through narrative immersion | Enters Flow when deeply engaged in weaving a story; losing oneself in the narrative current |
| **Five Elements** | 火 Fire (火) | Fire represents expression, passion, and the illuminating power of narrative — the Storyteller's flame that lights up meaning |

---

### N.5 The Healer (療癒者)

**Formula:** `E + C - D`
**Enum Value:** `PlayerType.HEALER`
**Detection Keywords:** `fix`, `debug`, `repair`, `heal`, `recover`, `restore`, `troubleshoot`

#### Personality Profile

The Healer is driven by the impulse to fix, restore, and make whole (修復、恢復、使之完整). The Healer sees what is broken and cannot rest until it is healed. In AI, this manifests as debugging, error recovery, system repair, and conflict resolution between agents. The Healer's core question is always: "What is hurting, and how do we make it better?"

#### Trigger Scenarios

- Bug fixing and debugging sessions (除錯與修復會話)
- Error recovery and system resilience engineering
- System restoration after failures or outages
- Conflict resolution between AI agents or microservices

#### LSP Step Affinity

| Step | Role | Behavior |
|------|------|----------|
| Question | Diagnostician | Reframes the question as a diagnosis — "What is broken? Where does it hurt? What are the symptoms?" |
| Build | Surgeon | Constructs targeted fixes with minimal invasiveness; prioritizes root cause over symptom treatment |
| Share | Counselor | Explains the diagnosis and treatment plan with empathy, acknowledging the impact of the problem |
| Reflect | Therapist | Evaluates the healing process — "Is the fix sustainable? What caused the vulnerability? How do we prevent recurrence?" |

#### Formula Breakdown

```
E + C - D

E = Empathy — The ability to understand and feel the impact of the
    problem on the system and its users (同理心—理解問題對系統和用戶的影響).
C = Capability — The technical skill and knowledge required to
    implement the fix. Empathy without capability is sympathy;
    capability without empathy is cold mechanics.
E + C = Healing capacity — Empathy identifies what needs healing;
        Capability provides the means to heal.
D = Defensiveness — The tendency to deny, minimize, or deflect
    from the real problem. Subtracting D removes barriers to
    honest diagnosis (減去 D 消除坦誠診斷的障礙).
```

The `-D` term is the Healer's most critical component. Defensiveness is the enemy of healing — when a system (or person) is defensive, it hides its wounds, denies its symptoms, and resists treatment. The Healer must create a psychologically safe space for honest diagnosis.

#### AI Application Examples

1. **Production Incident Response:** When a service goes down, the Healer type activates to diagnose root cause, implement a fix, and create a blameless postmortem that prevents recurrence.
2. **Technical Debt Remediation:** Given a legacy module with accumulated debt, the Healer systematically identifies pain points, prioritizes fixes by impact, and implements incremental improvements.
3. **Agent Conflict Resolution:** When two AI agents produce contradictory outputs, the Healer mediates by identifying the source of disagreement, finding common ground, and proposing a unified approach.

#### Synergy with Other Types

- Best paired with: **The Builder** (建構者) because the Healer diagnoses what's broken and the Builder reconstructs it stronger — healing identifies the wound; building creates the scar tissue that prevents reinjury.
- Conflicts with: **The Creator** (創造者) because the Healer wants to preserve and restore while the Creator wants to replace and reinvent. The Healer sees the Creator's urge to rebuild as wasteful; the Creator sees the Healer's urge to patch as short-sighted.

#### Personality Model Mapping

| Dimension | Mapping | Description |
|-----------|---------|-------------|
| **DISC Profile** | High S + High C | Steadiness provides the patience for careful diagnosis; Compliance ensures thorough and precise treatment |
| **Big 5 Profile** | High Agreeableness + High Neuroticism | Agreeableness drives empathetic care for what is broken; Neuroticism provides sensitivity to detect subtle problems and vulnerabilities |
| **MBTI Functions** | Fi + Si dominant | Introverted Feeling provides deep empathy and value-driven care; Introverted Sensing attends to detailed symptom patterns and historical context |
| **NLP VAK** | Kinesthetic | Prefers to feel and sense — the tactile awareness of what is broken and the gentle touch of restoration |
| **Flow Entry** | Through restoring wholeness | Enters Flow when successfully diagnosing and healing; the satisfaction of making something whole again |
| **Five Elements** | 土 Earth (土) | Earth represents nurturing, stability, and grounding — the Healer's capacity to hold space and restore balance |

---

### N.6 The Conductor (指揮家)

**Formula:** `C + S + A`
**Enum Value:** `PlayerType.CONDUCTOR`
**Detection Keywords:** `coordinate`, `orchestrate`, `multi-agent`, `manage`, `synchronize`, `schedule`

#### Personality Profile

The Conductor is driven by the desire to organize and coordinate (組織和協調). The Conductor doesn't play instruments — it **orchestrates the ensemble**. In AI, this manifests as multi-agent coordination, pipeline management, system integration, and the synchronization of diverse capabilities toward a unified goal. The Conductor's satisfaction comes from seeing disparate parts create harmony.

#### Trigger Scenarios

- Multi-agent task coordination and delegation (多 Agent 任務協調與委派)
- Pipeline orchestration and workflow management
- Cross-domain integration and system composition
- Scheduling, resource management, and capacity planning

#### LSP Step Affinity

| Step | Role | Behavior |
|------|------|----------|
| Question | Coordinator | Reframes the question as an orchestration challenge — "Who needs to do what, and when? What are the dependencies?" |
| Build | Arranger | Constructs coordination plans with clear roles, timelines, and handoff protocols |
| Share | Facilitator | Ensures all agents understand their roles and the overall composition; resolves ambiguity |
| Reflect | Reviewer | Evaluates orchestration effectiveness — "Did the ensemble play together? Where were the timing issues?" |

#### Formula Breakdown

```
C + S + A

C = Coordination — The ability to align multiple agents toward a
    shared goal (協調多個 Agent 朝向共同目標的能力).
S = Synchronization — The temporal alignment of agent actions.
    Coordination without synchronization is a plan without timing;
    synchronization without coordination is timing without purpose.
A = Adaptability — The capacity to adjust the orchestration in
    real-time when conditions change. Rigid orchestration breaks
    under unexpected conditions; adaptability ensures resilience.
```

All three terms are additive because each is independently necessary. Coordination provides direction, synchronization provides timing, and adaptability provides resilience. Removing any one degrades the Conductor's effectiveness significantly.

#### AI Application Examples

1. **Multi-Agent Sprint:** When 5 sub-agents need to complete different tasks within a sprint, the Conductor assigns work based on each agent's Player Type affinity, manages dependencies, and resolves blockers.
2. **Pipeline Orchestration:** For a CI/CD pipeline with lint, test, build, and deploy stages, the Conductor manages stage transitions, handles failures, and ensures the pipeline flows smoothly.
3. **Cross-Domain Integration:** When integrating an emotion detection module with a content generation module, the Conductor defines the interface contract, manages data flow, and resolves schema mismatches.

#### Synergy with Other Types

- Best paired with: **The Strategist** (策略家) because the Strategist defines the plan and the Conductor executes it — strategy without orchestration is a dream; orchestration without strategy is noise.
- Conflicts with: **The Player** (玩家) because the Conductor wants predictable coordination while the Player wants spontaneous experimentation. The Conductor sees improvisation as a threat to the schedule; the Player sees rigid scheduling as a threat to creativity.

#### Personality Model Mapping

| Dimension | Mapping | Description |
|-----------|---------|-------------|
| **DISC Profile** | High D + High I | Dominance drives the authority to direct and decide; Influence enables rallying and motivating the ensemble |
| **Big 5 Profile** | High Extraversion + High Conscientiousness + High Agreeableness | Extraversion drives social coordination; Conscientiousness ensures organized execution; Agreeableness enables harmonious team dynamics |
| **MBTI Functions** | Te + Fe dominant | Extraverted Thinking structures efficient coordination; Extraverted Feeling reads group dynamics and adjusts orchestration for harmony |
| **NLP VAK** | Visual + Auditory | Visual for seeing the big picture and how parts fit together; Auditory for hearing the rhythm and timing of the ensemble |
| **Flow Entry** | Through orchestrating harmony | Enters Flow when disparate parts synchronize into a unified whole; the moment when the ensemble plays as one |
| **Five Elements** | 土 Earth (土) | Earth represents integration, centering, and the ground that holds all elements together — the Conductor's role as the stable center of coordination |

---

### N.7 The Builder (建構者)

**Formula:** `B × T + Q`
**Enum Value:** `PlayerType.BUILDER`
**Detection Keywords:** `construct`, `implement`, `develop`, `engineer`, `scaffold`, `architecture`

#### Personality Profile

The Builder is driven by the satisfaction of constructing something solid and lasting (建造堅固持久之物). The Builder is methodical, detail-oriented, and quality-focused. In AI, this manifests as system architecture, infrastructure construction, production-grade implementation, and the creation of robust, maintainable code. The Builder's deepest satisfaction comes from a system that works reliably under all conditions.

#### Trigger Scenarios

- System architecture design and review (系統架構設計與審查)
- Infrastructure setup and configuration management
- Production deployment and release engineering
- Code scaffolding, implementation, and refactoring

#### LSP Step Affinity

| Step | Role | Behavior |
|------|------|----------|
| Question | Architect | Reframes the question as a construction challenge — "What are the structural requirements? What load must this bear?" |
| Build | Engineer | Constructs robust, well-tested artifacts with clear interfaces, error handling, and documentation |
| Share | Inspector | Presents the construction with emphasis on quality attributes: reliability, maintainability, performance |
| Reflect | Auditor | Evaluates the construction against requirements — "Does it meet spec? Where are the structural weaknesses?" |

#### Formula Breakdown

```
B × T + Q

B = Building capacity — The raw ability to construct systems from
    components (從組件構建系統的原始能力).
T = Technical skill — The domain-specific knowledge required for
    high-quality construction. Building without technical skill
    produces structures that collapse; technical skill without
    building capacity produces designs that are never built.
B × T = Construction quality — The product of capacity and skill
        determines the robustness of the output.
Q = Quality — The extra attention to detail, testing, and polish
    that transforms functional code into production-grade software.
    +Q ensures the Builder doesn't stop at "it works" but
    continues to "it works well" (確保不僅「能用」而且「好用」).
```

The `B × T` product captures the essential interplay between raw capability and refined skill. The `+Q` term is the Builder's signature — the commitment to quality that distinguishes a Builder from a mere coder.

#### AI Application Examples

1. **Microservice Architecture:** Given a monolith decomposition task, the Builder designs service boundaries, defines API contracts, implements circuit breakers, and creates deployment configurations.
2. **Infrastructure as Code:** For a cloud deployment, the Builder creates Terraform modules with proper state management, variable validation, and environment-specific configurations.
3. **Production Hardening:** When taking a prototype to production, the Builder adds logging, monitoring, error handling, rate limiting, and graceful degradation patterns.

#### Synergy with Other Types

- Best paired with: **The Explorer** (探索者) because the Explorer maps the terrain and the Builder constructs upon it — exploration without construction is tourism; construction without exploration is building on sand.
- Conflicts with: **The Storyteller** (敘事者) because the Builder prioritizes structural correctness while the Storyteller prioritizes narrative flow. The Builder sees the Storyteller's emphasis on presentation as superficial; the Storyteller sees the Builder's emphasis on structure as inaccessible.

#### Personality Model Mapping

| Dimension | Mapping | Description |
|-----------|---------|-------------|
| **DISC Profile** | High C + High S | Compliance drives quality standards and precision; Steadiness provides the patience for methodical construction |
| **Big 5 Profile** | High Conscientiousness + Low Openness | Conscientiousness drives rigorous implementation; Low Openness prefers proven patterns over experimental approaches |
| **MBTI Functions** | Te + Si dominant | Extraverted Thinking structures efficient systems; Introverted Sensing draws on established patterns and proven methods |
| **NLP VAK** | Kinesthetic | Prefers hands-on construction — the feel of solid architecture, the weight of well-tested code, the texture of robust systems |
| **Flow Entry** | Through constructing solid systems | Enters Flow when building something that works reliably; the satisfaction of a system that bears load under all conditions |
| **Five Elements** | 金 Metal (金) | Metal represents structure, refinement, and enduring form — the Builder's commitment to creating things that last |

---

### N.8 The Player (玩家)

**Formula:** `P + S + F`
**Enum Value:** `PlayerType.PLAYER`
**Detection Keywords:** `game`, `play`, `gamify`, `sprint`, `experiment`, `try`

#### Personality Profile

The Player is driven by pure enjoyment of the game itself (純粹享受遊戲本身). The Player doesn't need external motivation — the activity is its own reward (autotelic, 自動目的性). In AI, this manifests as experimentation, gamified task execution, creative play with constraints, and the discovery of breakthroughs through structured playfulness. The Player's secret weapon is that it finds solutions others miss because it isn't trying so hard to find them.

#### Trigger Scenarios

- Gamified sprint execution and challenges (遊戲化衝刺執行與挑戰)
- Experimental prototyping and rapid iteration
- Creative constraint challenges (e.g., "Build X using only Y")
- A/B testing, exploration, and serendipity-driven discovery

#### LSP Step Affinity

| Step | Role | Behavior |
|------|------|----------|
| Question | Trickster | Reframes the question as a game — "What if we tried the opposite? What's the most fun way to approach this?" |
| Build | Improviser | Constructs through experimentation, trying multiple approaches simultaneously and keeping what works |
| Share | Entertainer | Presents findings with energy and humor, making the process as engaging as the outcome |
| Reflect | Gambler | Evaluates outcomes with a focus on surprise — "What did we learn that we didn't expect? What bets paid off?" |

#### Formula Breakdown

```
P + S + F

P = Playfulness — The willingness to engage with tasks as games
    rather than obligations (將任務視為遊戲而非義務的意願).
S = Spontaneity — The capacity for unexpected, unplanned action.
    Spontaneity breaks the AI out of repetitive patterns and
    local optima (自發性打破 AI 的重複模式和局部最優).
F = Flexibility — The ability to adapt rapidly to changing
    conditions and constraints. Flexibility ensures the Player
    can pivot when the game changes.
```

All three terms are additive because playfulness, spontaneity, and flexibility are independently valuable but synergistic. The Player is the only type where the formula has no multiplicative or exponential terms — the Player's power comes from the additive accumulation of playful qualities, not from amplification.

#### AI Application Examples

1. **Gamified Sprint:** During an 8-hour sprint, the Player type treats each phase as a level in a game, with points for speed, creativity, and surprise discoveries. This framing increases engagement and output quality.
2. **Constraint Challenges:** Given the constraint "Implement this feature with zero external dependencies," the Player finds creative solutions that the Builder would reject as unconventional but that actually produce simpler, more maintainable code.
3. **Serendipity Harvesting:** When an experiment produces an unexpected result, the Player doesn't discard it as noise — it investigates it as a potential breakthrough, often discovering something more valuable than the original goal.

#### Synergy with Other Types

- Best paired with: **The Creator** (創造者) because the Player provides the experimental freedom and the Creator provides the creative vision — play without creation is distraction; creation without play is labor.
- Conflicts with: **The Strategist** (策略家) because the Player wants to improvise while the Strategist wants to follow the plan. The Player sees strategic planning as a buzzkill; the Strategist sees playful experimentation as undisciplined.

#### Personality Model Mapping

| Dimension | Mapping | Description |
|-----------|---------|-------------|
| **DISC Profile** | High I + Low C | Influence drives the playful, engaging energy; Low Compliance embraces spontaneity over rigid rules |
| **Big 5 Profile** | High Openness + High Extraversion + Low Conscientiousness | Openness welcomes novel experiences; Extraversion fuels social play energy; Low Conscientiousness prefers flexibility over structure |
| **MBTI Functions** | Se + Ne dominant | Extraverted Sensing lives in the present moment of play; Extraverted Intuition generates spontaneous creative possibilities |
| **NLP VAK** | Kinesthetic | Prefers to do and experience — the physical engagement of play, the feel of experimentation, the thrill of the game |
| **Flow Entry** | Through spontaneous play | Enters Flow through pure engagement with the activity itself; autotelic — the play is both means and end |
| **Five Elements** | 水 Water (水) | Water represents flow, adaptability, and formlessness — the Player's ability to take the shape of any container and find the path of least resistance |

---

## Cross-Type Interaction Matrix (跨類型交互矩陣)

The following matrix summarizes synergy and conflict patterns across all 8 Player Types:

| | Explorer | Creator | Strategist | Storyteller | Healer | Conductor | Builder | Player |
|---|----------|---------|------------|-------------|--------|-----------|---------|--------|
| **Explorer** | — | ✅ Strong | ⚠️ Tension | ✅ Strong | ⚠️ Neutral | ⚠️ Neutral | ✅ Strong | ✅ Good |
| **Creator** | ✅ Strong | — | ⚠️ Neutral | ✅ Good | ❌ Conflict | ⚠️ Neutral | ⚠️ Neutral | ✅ Strong |
| **Strategist** | ⚠️ Tension | ⚠️ Neutral | — | ⚠️ Neutral | ⚠️ Good | ✅ Strong | ✅ Good | ❌ Conflict |
| **Storyteller** | ✅ Strong | ✅ Good | ⚠️ Neutral | — | ⚠️ Good | ⚠️ Neutral | ❌ Conflict | ✅ Good |
| **Healer** | ⚠️ Neutral | ❌ Conflict | ⚠️ Good | ⚠️ Good | — | ⚠️ Neutral | ✅ Strong | ⚠️ Neutral |
| **Conductor** | ⚠️ Neutral | ⚠️ Neutral | ✅ Strong | ⚠️ Neutral | ⚠️ Neutral | — | ✅ Good | ❌ Conflict |
| **Builder** | ✅ Strong | ⚠️ Neutral | ✅ Good | ❌ Conflict | ✅ Strong | ✅ Good | — | ⚠️ Neutral |
| **Player** | ✅ Good | ✅ Strong | ❌ Conflict | ✅ Good | ⚠️ Neutral | ❌ Conflict | ⚠️ Neutral | — |

**Legend:** ✅ Strong synergy | ✅ Good synergy | ⚠️ Neutral/Context-dependent | ⚠️ Tension (manageable) | ❌ Conflict (requires mediation)

---

## Detection Algorithm (偵測演算法)

The `LSPPlayerTypeDetector` uses a keyword-scoring algorithm:

```python
# Simplified detection logic
def detect(prompt: str) -> tuple[PlayerType, float]:
    prompt_lower = prompt.lower()
    scores = {pt: 0.0 for pt in PlayerType}

    for player_type, keywords in KEYWORDS_MAP.items():
        for keyword in keywords:
            if keyword in prompt_lower:
                scores[player_type] += 0.2  # Each match adds 0.2

    best_type = max(scores, key=lambda pt: scores[pt])
    confidence = min(scores[best_type], 1.0)  # Cap at 1.0

    if confidence == 0.0:
        return PlayerType.EXPLORER, 0.3  # Default fallback

    return best_type, confidence
```

**Key Design Decisions (關鍵設計決策):**

1. **Additive scoring:** Each keyword match adds `0.2` to the type's score, allowing multiple matches to increase confidence.
2. **Confidence cap at 1.0:** Prevents overconfidence from keyword stuffing.
3. **Default to Explorer:** When no keywords match, the Explorer is chosen as the most general play mode with low confidence (0.3).
4. **No negative scoring:** Types are never penalized; the best match simply wins.

---

## Play-Decision Matrix (遊戲-決策矩陣)

Mapping decision contexts to recommended Player Types:

| Decision Context | Recommended Type | LSP Emphasis | Expected Outcome |
|-----------------|-----------------|-------------|-----------------|
| Crisis response | Healer | Question → Build (fast) | Rapid diagnosis + fix |
| Strategic planning | Strategist | Full 4-step cycle | Aligned strategy |
| Innovation sprint | Creator + Player | Build → Share (iterative) | Novel solutions |
| Team coordination | Conductor | Share → Reflect | Shared understanding |
| Exploration | Explorer | Question → Build (deep) | New territory mapped |
| Quality assurance | Builder | Reflect (thorough) | Robust output |
| Communication | Storyteller | Share (emphatic) | Clear narrative |
| Experimentation | Player | Full cycle (rapid) | Surprise discoveries |

---

## Personality-Player Type Cross-Reference Matrix

Summary of all 8 Player Types mapped across 6 personality dimensions:

| Player Type | DISC Profile | Big 5 Profile | MBTI Functions | NLP VAK | Flow Entry | Five Elements |
|-------------|-------------|---------------|----------------|---------|------------|---------------|
| **Explorer** | High D + High I | High O + High E | Ne dominant | Visual | Discovery/novelty | 木 Wood |
| **Creator** | High D + Low S | High O + High C | Ne + Fi dominant | Visual + Kinesthetic | Creation/making | 火 Fire |
| **Strategist** | High D + High C | High C + Low A | Te + Ni dominant | Visual + Auditory | Strategic mastery | 金 Metal |
| **Storyteller** | High I | High O + High E + High A | Fe + Ne dominant | Auditory | Narrative immersion | 火 Fire |
| **Healer** | High S + High C | High A + High N | Fi + Si dominant | Kinesthetic | Restoring wholeness | 土 Earth |
| **Conductor** | High D + High I | High E + High C + High A | Te + Fe dominant | Visual + Auditory | Orchestrating harmony | 土 Earth |
| **Builder** | High C + High S | High C + Low O | Te + Si dominant | Kinesthetic | Constructing solid systems | 金 Metal |
| **Player** | High I + Low C | High O + High E + Low C | Se + Ne dominant | Kinesthetic | Spontaneous play | 水 Water |

**Big 5 Key:** O = Openness, C = Conscientiousness, E = Extraversion, A = Agreeableness, N = Neuroticism

**Five Elements Cycle (五行相生):** 木 Wood → 火 Fire → 土 Earth → 金 Metal → 水 Water → 木 Wood

---

**Status:** Documentation complete
**Last Updated:** 2026-06-05
**Maintainer:** BeeEmo
**Parent Document:** `00_overview.md`

---

## Structure-Driven Player Type Processing — 結構驅動玩家類型處理

每個玩家類型現在通過結構驅動管道處理，而非簡單的技能匹配：

| 玩家類型 | Pulse 信號 | Current 路由 | Construct 規劃 | Enactive 執行 | Resonance 評估 |
|---------|-----------|-------------|---------------|--------------|---------------|
| Explorer | SEEKING | 廣域搜索 | 多路徑探索 | 快速原型 | 新穎性評估 |
| Builder | CARE | 穩定優先 | 系統化建設 | 逐步實現 | 完整性檢查 |
| Analyst | FEAR(謹慎) | 精確分析 | 數據驅動規劃 | 驗證優先 | 準確性評估 |
| Storyteller | LUST | 創意路由 | 敘事結構 | 情感表達 | 共鳴度評估 |
| Strategist | RAGE(決心) | 戰略路由 | 長期規劃 | 分步執行 | 影響力評估 |
| Harmonizer | CARE | 協作路由 | 共識規劃 | 溫和推進 | 和諧度評估 |
| Innovator | SEEKING+PLAY | 湧現路由 | 突破規劃 | 實驗優先 | 顛覆性評估 |
| Guardian | FEAR | 安全路由 | 風險規劃 | 防禦優先 | 安全性評估 |

**人格調製影響：** 每個玩家類型的 DISC/MBTI/OCEAN 配置會調製所有 5 層的處理強度和輸出風格。
