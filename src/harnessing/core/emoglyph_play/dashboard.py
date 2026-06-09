"""
EmoGlyph Play Dashboard — Sub-Project Health & Sprint Management

Run: streamlit run src/harnessing/core/emoglyph_play/dashboard.py
"""
import sys
from pathlib import Path

# Ensure project root is on path
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
import pandas as pd

from src.harnessing.core.emoglyph_play.health_monitor import HealthMonitor, HealthDimension
from src.harnessing.core.emoglyph_play.model_config import ModelSelector
from src.harnessing.core.emoglyph_play import (
    SprintRunner,
    PlayFormulaEngine,
    run_lsp_cycle,
)

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="EmoGlyph Play Dashboard",
    page_icon="🎮",
    layout="wide",
)

# ── Cached data loaders ──────────────────────────────────────────────

@st.cache_data
def load_health_reports():
    """Run health check once and cache the results."""
    monitor = HealthMonitor()
    return monitor.check_all()


@st.cache_data
def load_health_summary():
    """Generate summary from cached report data."""
    monitor = HealthMonitor()
    reports = monitor.check_all()
    return monitor.generate_summary(reports)


# ── Helper: status color mapping ────────────────────────────────────

_STATUS_COLORS = {
    "GREEN": "🟢",
    "YELLOW": "🟡",
    "RED": "🔴",
}

_STATUS_CSS = {
    "GREEN": "background-color: #d4edda; color: #155724",
    "YELLOW": "background-color: #fff3cd; color: #856404",
    "RED": "background-color: #f8d7da; color: #721c24",
}


def _style_status_cell(val):
    """Return CSS style for a status cell based on value."""
    if isinstance(val, str) and val in _STATUS_CSS:
        return _STATUS_CSS[val]
    return ""


# ── Tabs ─────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "🏥 Sub-Project Health",
    "🏃 Sprint Runner",
    "🧮 Play Formula",
    "🤖 Model Config",
])

# =====================================================================
# Tab 1: Sub-Project Health
# =====================================================================

with tab1:
    st.header("Sub-Project Health Monitor")

    reports = load_health_reports()

    # Build dataframe
    rows = []
    for r in reports:
        row = {
            "Project": r.project_name,
            "Engine": r.scores[HealthDimension.ENGINE].score,
            "Interface": r.scores[HealthDimension.INTERFACE].score,
            "Deployment": r.scores[HealthDimension.DEPLOYMENT].score,
            "Testing": r.scores[HealthDimension.TESTING].score,
            "Overall": r.overall_score,
            "Status": r.overall_status,
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Color-code the status column
    styled_df = df.style.map(_style_status_cell, subset=["Status"])

    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # Bar chart of overall scores
    st.subheader("Overall Scores by Project")
    chart_df = df[["Project", "Overall"]].set_index("Project")
    st.bar_chart(chart_df)

    # Summary metrics
    summary = load_health_summary()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Score", f"{summary['average_score']:.1f}")
    with col2:
        st.metric("Most Severe", summary.get("most_severe", "N/A"))
    with col3:
        dist = summary.get("by_status", {})
        st.metric(
            "Health Distribution",
            f"🟢 {dist.get('GREEN', 0)}  🟡 {dist.get('YELLOW', 0)}  🔴 {dist.get('RED', 0)}",
        )

    # Detailed issues and recommendations
    with st.expander("📋 Detailed Issues & Recommendations"):
        for r in reports:
            icon = _STATUS_COLORS.get(r.overall_status, "⚪")
            st.markdown(f"**{icon} {r.project_name}** — Overall: {r.overall_score}")
            if r.issues:
                st.markdown("  Issues: " + "; ".join(r.issues))
            if r.recommendations:
                for rec in r.recommendations:
                    st.markdown(f"  - {rec}")

# =====================================================================
# Tab 2: Sprint Runner
# =====================================================================

with tab2:
    st.header("EmoGlyph Play Sprint")

    st.markdown(
        "Run a full 4-phase sprint: **Question → Build → Share → Reflect**"
    )

    if st.button("🚀 Run Full Sprint", type="primary"):
        with st.spinner("Running sprint across all sub-projects..."):
            runner = SprintRunner()
            report = runner.run_full_sprint()

        st.success(f"Sprint `{report.sprint_id}` completed!")

        # Phase summary
        st.subheader("Phases Completed")
        phase_cols = st.columns(4)
        phase_labels = ["QUESTION", "BUILD", "SHARE", "REFLECT"]
        for i, (col, label) in enumerate(zip(phase_cols, phase_labels)):
            with col:
                completed = label in [p.value for p in report.phases_completed]
                icon = "✅" if completed else "❌"
                st.metric(f"{icon} {label}", "Done" if completed else "Pending")

        # Sub-projects assessed
        st.subheader("Sub-Projects Assessed")
        sp_rows = []
        for sp in report.sub_projects:
            sp_rows.append({
                "Project": sp.name,
                "Priority": sp.priority,
                "Health": sp.overall_health,
                "Severity": f"{sp.disconnection_severity:.2f}",
                "Player Type": sp.recommended_player_type.value,
            })
        if sp_rows:
            st.dataframe(pd.DataFrame(sp_rows), use_container_width=True, hide_index=True)

        # Formula result
        if report.formula_result is not None:
            st.subheader("Sprint Formula Result")
            fr = report.formula_result
            col_e, col_p, col_c, col_s, col_d = st.columns(5)
            col_e.metric("E (Emotion)", f"{fr.avg_emotional_depth:.4f}")
            col_p.metric("P (Play)", f"{fr.avg_play_structure:.4f}")
            col_c.metric("C (Creativity)", f"{fr.avg_creativity:.4f}")
            col_s.metric("S (Surprise)", f"{fr.avg_surprise:.4f}")
            col_d.metric("D (Defensive)", f"{fr.avg_defensive_defaults:.4f}")
            st.metric("Sprint Score", f"{fr.sprint_score:.4f}")
            st.code(fr.formula_expression, language="text")

        # Recommendations
        if report.recommendations:
            st.subheader("Recommendations")
            for rec in report.recommendations:
                st.markdown(f"- {rec}")

# =====================================================================
# Tab 3: Play Formula
# =====================================================================

with tab3:
    st.header("Play Formula Engine")

    st.markdown(
        "**Formula:** `(E × P) + (C ^ S) - D`\n\n"
        "| Variable | Meaning |\n"
        "|----------|--------|\n"
        "| E | EmoGlyph emotional depth (0-1) |\n"
        "| P | Play structure completeness (0-1) |\n"
        "| C | Creativity score (0-1) |\n"
        "| S | Surprise discovery score (0-1) |\n"
        "| D | Defensive defaults penalty (0-1) |"
    )

    question = st.text_input(
        "Question",
        value="How can we fix the disconnection with sub-projects?",
        key="formula_question",
    )

    if st.button("🔄 Run LSP Cycle", type="primary"):
        with st.spinner("Running LSP cycle and evaluating formula..."):
            session = run_lsp_cycle(
                question=question,
                hypothesis=f"Hypothesis for: {question}",
                narrative=f"Narrative exploring: {question}",
                learning=f"Learning from: {question}",
                surprise_score=0.3,
            )

            formula_engine = PlayFormulaEngine()
            result = formula_engine.evaluate(session)

        st.success("LSP cycle complete!")

        # Score display
        col_e, col_p, col_c, col_s, col_d = st.columns(5)
        col_e.metric("E (Emotion)", f"{result.emotional_depth:.4f}")
        col_p.metric("P (Play)", f"{result.play_structure:.4f}")
        col_c.metric("C (Creativity)", f"{result.creativity:.4f}")
        col_s.metric("S (Surprise)", f"{result.surprise:.4f}")
        col_d.metric("D (Defensive)", f"{result.defensive_defaults:.4f}")

        st.metric("Play Score", f"{result.play_score:.4f}")

        # Formula expression
        st.subheader("Formula Expression")
        st.code(result.formula_expression, language="text")

        # Session details
        with st.expander("📝 Session Details"):
            st.markdown(f"**Session ID:** {session.session_id}")
            st.markdown(f"**Player Type:** {session.player_type.value}")
            st.markdown(f"**Status:** {session.status}")
            st.markdown(f"**Resonance:** {session.resonance:.2f}")
            st.markdown(f"**Steps:** {len(session.steps)}")
            for step in session.steps:
                st.markdown(
                    f"- **{step.stage.value}** (confidence: {step.confidence:.2f}): "
                    f"{step.content[:100]}{'…' if len(step.content) > 100 else ''}"
                )

# =====================================================================
# Tab 4: Model Config
# =====================================================================

with tab4:
    st.header("AI Model Configuration")

    selector = ModelSelector()
    config = selector._config

    # Current models
    col_primary, col_fallback = st.columns(2)

    with col_primary:
        st.subheader("Primary Model")
        primary_info = selector.get_model_info(config.primary_model)
        st.markdown(f"**Name:** {primary_info['name']}")
        st.markdown(f"**Context Window:** {primary_info['context_window']:,} tokens")
        st.markdown(f"**Multimodal:** {'Yes' if primary_info['multimodal'] else 'No'}")
        st.markdown(f"**Coding Tier:** {primary_info['coding_tier']}")
        st.markdown(f"**Cost:** {primary_info['cost']}")

    with col_fallback:
        st.subheader("Fallback Model")
        fallback_info = selector.get_model_info(config.fallback_model)
        st.markdown(f"**Name:** {fallback_info['name']}")
        st.markdown(f"**Context Window:** {fallback_info['context_window']:,} tokens")
        st.markdown(f"**Multimodal:** {'Yes' if fallback_info['multimodal'] else 'No'}")
        st.markdown(f"**Coding Tier:** {fallback_info['coding_tier']}")
        st.markdown(f"**Cost:** {fallback_info['cost']}")

    # A/B Testing Rationale
    st.subheader("A/B Testing Rationale")
    st.text(selector.ab_test_rationale())

    # Task type selector
    st.subheader("Model Recommendation by Task")
    task_type = st.selectbox(
        "Select Task Type",
        options=["coding", "analysis", "multimodal", "general"],
        index=0,
        key="task_type_selector",
    )

    requires_multimodal = task_type == "multimodal"
    recommended = selector.select_model(
        task_type=task_type,
        requires_multimodal=requires_multimodal,
    )
    st.info(f"**Recommended model for `{task_type}` tasks:** `{recommended}`")

    rec_info = selector.get_model_info(recommended)
    st.markdown(
        f"- Context Window: {rec_info['context_window']:,} tokens\n"
        f"- Multimodal: {'Yes' if rec_info['multimodal'] else 'No'}\n"
        f"- Coding Tier: {rec_info['coding_tier']}\n"
        f"- Cost: {rec_info['cost']}"
    )
