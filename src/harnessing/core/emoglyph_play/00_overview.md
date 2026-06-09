# EmoGlyph Play — 項目總覽

**EmoGlyph Play = EmoGlyph v2.1 × Play Theory (LEGO Serious Play)**

> 「情感 × 遊戲化 = AI 決策嘅新範式」

---

## 🎯 項目定位

EmoGlyph Play 係 EmoGlyph 情感處理引擎同 Play Theory（特別係 LEGO Serious Play 4-step 流程）嘅深度融合。目標係令 AI Agent 具備：

1. **情感到位**（EmoGlyph 5-Layer Architecture）
2. **結構化探索**（LEGO Serious Play: Question → Build → Share → Reflect）
3. **可重複實驗**（Hypothesis → Test → Validate → Surprise）
4. **8 種 AI Player Types**（Stuart Brown 框架）

---

## 🧬 核心公式

```
EmoGlyph_Play = (E × P) + (C ^ S) - D

E = EmoGlyph emotional depth（5 層架構）
P = Play Theory structure（4-step 流程）
C = Creativity（創造力）
S = Surprise discovery（驚喜發現）
D = Defensive defaults（防禦性預設）
```

### 公式語義

| 維度 | 公式項 | 意義 |
|------|--------|------|
| 情感到位 | E × P | 情感 × 遊戲化嘅交叉協同 |
| 創意突破 | C ^ S | 創造力被驚喜放大 |
| 簡化核心 | - D | 減去防禦性預設，避免過度守衛 |

---

## 🏗️ 5 層架構 + 4 步流程

| EmoGlyph Layer | 對應 LSP 步驟 | 描述 |
|----------------|---------------|------|
| **L1 Pulse** | Question | 偵測情感脈衝 + 提出核心問題 |
| **L2 Current** | Build | 流動狀態 + 建構假設模型 |
| **L3 Construct** | Share | 結構化建構 + 分享故事 |
| **L4 Enactive** | Reflect | 行動反思 + 學習 |
| **L5 Resonance** | (Loop) | 共振檢測 + 重新提問 |

---

## 🧩 8 種 AI Player Types

基於 Stuart Brown 嘅 Play Theory，EmoGlyph Play 定義 8 種 AI Player：

| 類型 | 公式 | 觸發場景 |
|------|------|----------|
| **The Explorer** | log(C) + E | 新領域探索 |
| **The Creator** | C² + S | 創新發明 |
| **The Strategist** | P × R - G | 策略規劃 |
| **The Storyteller** | S × E + C | 內容創作 |
| **The Healer** | E + C - D | 修復/除錯 |
| **The Conductor** | C + S + A | 多 Agent 協調 |
| **The Builder** | B × T + Q | 系統建構 |
| **The Player** | P + S + F | 遊戲化任務 |

---

## 📂 項目結構

```
src/harnessing/core/emoglyph_play/
├── __init__.py
├── 00_overview.md          # 項目總覽（本文件）
├── 01_architecture.md      # 5-Layer × 4-Step 詳細架構
├── 02_player_types.md      # 8 種 AI Player 詳解
├── 03_lsp_ai_engine.py     # LEGO Serious Play AI Engine
├── 04_emoglyph_integration.py  # EmoGlyph v2.1 整合層
├── 05_play_formula.py      # 公式引擎
└── 06_sprint_runner.py     # 8 小時衝刺執行器
```

---

## 🎮 8 小時衝刺計劃（Sub-project Management）

EmoGlyph Play 嘅核心應用：用 Play Theory 結構化管理所有子項目。

### 衝刺公式

```
Sprint_Success = (P * E) + (C ^ S) - D

P = Play engagement（遊戲化投入度）
E = EmoGlyph emotional resonance（情感共振）
C = Creativity（創造力）
S = Surprise（驚喜）
D = Defensive drag（防禦阻力）
```

### 4 個衝刺階段（每階段 2 小時）

| Phase | LSP 步驟 | 任務 | 輸出 |
|-------|----------|------|------|
| **Phase 1 (0-2h)** | Question | 盤點 5 個子項目嘅健康狀態 | Health Report |
| **Phase 2 (2-4h)** | Build | 建立統一 EmoGlyph Play 抽象層 | `emoglyph_play/` 模組 |
| **Phase 3 (4-6h)** | Share | 修復最高斷連嘅 2 個子項目 | 修復 PR/Code |
| **Phase 4 (6-8h)** | Reflect | QA 驗證 + 寫 Sprint Report | 8-Sprint Report |

---

## 🎯 目標子項目

| 子項目 | 斷連嚴重度 | 優先級 | EmoGlyph Play 修復策略 |
|--------|-----------|--------|---------------------|
| World Cup 預測 | 🔴 HIGH | P0 | LSP Build → Test 循環 |
| Auditing SME | 🔴 HIGH | P0 | LSP Question → Reflect 循環 |
| Social Media | 🟡 MEDIUM | P1 | LSP Share → Reflect 循環 |
| Business Proposal | 🟡 MEDIUM | P1 | LSP 全 4-step |
| Auto Jobs | 🟢 LOW | P2 | 觀察 + 必要時介入 |

---

## 🔗 與現有模組嘅關係

```
EmoGlyph v2.1
    ↓
EmoGlyph Play 整合層 ← 本項目
    ↓
├── play/formula_engine.py (現有 Formula Engine)
├── play/innovation_lab.py (現有 Innovation Lab)
├── play/strategy_explorer.py (現有 Strategy Explorer)
├── SkillRouter (擴展 auto_invoke)
└── MasterOrchestrator (子項目管理)
```

---

## 📊 成功指標

- ✅ 8 種 Player Type 自動偵測準確率 > 80%
- ✅ LSP 4-step 流程可執行率 100%
- ✅ 5 個子項目健康度提升至少 1 級
- ✅ 0 個 TODO 留低
- ✅ 所有決策記錄到 decision-log

---

**Status**: ✅ Phase 1-3 Complete
**Last Updated**: 2026-06-05
**Maintainer**: BeeEmo

---

## Structure-Driven Processing — 結構驅動處理

EmoGlyph Play 現在採用**結構驅動處理**取代傳統的規則→技能→決策管道。

**核心轉變：** AI 不再通過關鍵詞匹配技能，而是通過 5 層循環模型同時處理所有輸入：
- **Pulse** 偵測情緒信號
- **Current** 分析情境 + 人格
- **Construct** 結構化規劃
- **Enactive** 人格匹配執行
- **Resonance** 品質評估

公式：`Output = ⊕(P,C,Co,E,R)^Ξ × PV × Flow - L`

規則變成結構的從屬模式——由結構調用，而非替代結構。
