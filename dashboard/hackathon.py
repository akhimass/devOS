"""
Hackathon evaluation dashboard.
Shows Cekura scores per persona across v1/v2/v3, live transcript, and failure analysis.

Run: streamlit run dashboard/hackathon.py
"""

import json
import os
import subprocess

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from mock_data import (
    EVALUATORS,
    PERSONAS,
    SCORES_V1,
    SCORES_V2,
    SCORES_V3,
    VERSION_NOTES,
    VERSION_SCORES,
)

st.set_page_config(
    page_title="PI Intake Agent — Cekura Eval",
    page_icon="⚖️",
    layout="wide",
)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .stApp { background: #0d1117; color: #e6edf3; }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 18px 22px;
        text-align: center;
    }
    .metric-value { font-size: 2.4rem; font-weight: 700; color: #58a6ff; }
    .metric-label { font-size: 0.82rem; color: #8b949e; margin-top: 4px; }
    .version-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .v1 { background: #6e40c9; color: white; }
    .v2 { background: #1f6feb; color: white; }
    .v3 { background: #238636; color: white; }
    .note-box {
        background: #161b22;
        border-left: 3px solid #30363d;
        padding: 10px 14px;
        border-radius: 4px;
        font-size: 0.84rem;
        color: #8b949e;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## ⚖️ PI Intake Agent &nbsp;×&nbsp; Cekura Evaluation")
st.markdown(
    "<p style='color:#8b949e;margin-top:-10px'>10 caller personas · 10 evaluators · 3 prompt iterations</p>",
    unsafe_allow_html=True,
)

# ── Top score cards ───────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f"""<div class='metric-card'>
        <div class='metric-value'>{VERSION_SCORES['v1']}%</div>
        <div class='metric-label'>v1 Score</div></div>""",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"""<div class='metric-card'>
        <div class='metric-value' style='color:#1f6feb'>{VERSION_SCORES['v2']}%</div>
        <div class='metric-label'>v2 Score</div></div>""",
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"""<div class='metric-card'>
        <div class='metric-value' style='color:#3fb950'>{VERSION_SCORES['v3']}%</div>
        <div class='metric-label'>v3 Score</div></div>""",
        unsafe_allow_html=True,
    )
with c4:
    delta = round(VERSION_SCORES["v3"] - VERSION_SCORES["v1"], 1)
    st.markdown(
        f"""<div class='metric-card'>
        <div class='metric-value' style='color:#f0883e'>+{delta}%</div>
        <div class='metric-label'>Total Improvement</div></div>""",
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Scores & Heatmap", "📞 Live Transcript", "🔍 Failure Analysis"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: Scores
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    col_left, col_right = st.columns([1.1, 1], gap="large")

    with col_left:
        st.markdown("#### Score progression — v1 → v2 → v3")

        fig_line = go.Figure()
        versions = ["v1", "v2", "v3"]
        scores = [VERSION_SCORES[v] for v in versions]

        fig_line.add_trace(
            go.Scatter(
                x=versions,
                y=scores,
                mode="lines+markers+text",
                text=[f"{s}%" for s in scores],
                textposition="top center",
                line=dict(color="#58a6ff", width=3),
                marker=dict(size=12, color=["#6e40c9", "#1f6feb", "#238636"]),
                textfont=dict(size=14, color="white"),
            )
        )

        # Annotation callouts for what changed
        for i, v in enumerate(["v2", "v3"]):
            short = VERSION_NOTES[v].split(".")[0]
            fig_line.add_annotation(
                x=v,
                y=scores[i + 1] - 4,
                text=f"<b>{v}:</b> {short[:55]}…",
                showarrow=False,
                font=dict(size=10, color="#8b949e"),
                xanchor="center",
            )

        fig_line.update_layout(
            paper_bgcolor="#161b22",
            plot_bgcolor="#161b22",
            font=dict(color="#e6edf3"),
            xaxis=dict(showgrid=False),
            yaxis=dict(range=[50, 100], showgrid=True, gridcolor="#21262d"),
            height=340,
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(fig_line, use_container_width=True)

        st.markdown("**Version notes:**")
        for v, note in VERSION_NOTES.items():
            badge_cls = v
            st.markdown(
                f"<div class='note-box'><span class='version-badge {badge_cls}'>{v}</span> {note}</div>",
                unsafe_allow_html=True,
            )

    with col_right:
        st.markdown("#### Per-persona heatmap (select version)")

        version = st.radio("Version", ["v1", "v2", "v3"], horizontal=True, label_visibility="collapsed")
        score_map = {"v1": SCORES_V1, "v2": SCORES_V2, "v3": SCORES_V3}
        selected = np.array(score_map[version])

        df_heat = pd.DataFrame(selected, index=PERSONAS, columns=EVALUATORS)

        fig_heat = px.imshow(
            df_heat,
            color_continuous_scale=[[0, "#da3633"], [0.5, "#d29922"], [1, "#238636"]],
            zmin=0,
            zmax=1,
            aspect="auto",
            text_auto=False,
        )

        # Add pass/fail text
        annotations = []
        for i in range(len(PERSONAS)):
            for j in range(len(EVALUATORS)):
                val = selected[i][j]
                symbol = "✓" if val == 1 else ("~" if val == 0.5 else "✗")
                annotations.append(
                    dict(
                        x=j, y=i,
                        text=symbol,
                        showarrow=False,
                        font=dict(color="white", size=13),
                    )
                )
        fig_heat.update_layout(annotations=annotations)

        fig_heat.update_layout(
            paper_bgcolor="#161b22",
            plot_bgcolor="#161b22",
            font=dict(color="#e6edf3", size=11),
            coloraxis_showscale=False,
            xaxis=dict(tickangle=-35, side="bottom"),
            height=420,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        fig_heat.update_xaxes(tickfont=dict(size=10))
        fig_heat.update_yaxes(tickfont=dict(size=10))
        st.plotly_chart(fig_heat, use_container_width=True)

        # Per-persona score bar for selected version
        persona_scores = [round(sum(row) / len(row) * 100) for row in selected]
        df_bar = pd.DataFrame({"Persona": [p[:30] for p in PERSONAS], "Score": persona_scores})
        df_bar = df_bar.sort_values("Score")
        fig_bar = px.bar(
            df_bar, x="Score", y="Persona", orientation="h",
            color="Score",
            color_continuous_scale=[[0, "#da3633"], [0.5, "#d29922"], [1, "#238636"]],
            range_color=[0, 100],
        )
        fig_bar.update_layout(
            paper_bgcolor="#161b22", plot_bgcolor="#161b22",
            font=dict(color="#e6edf3", size=10),
            coloraxis_showscale=False,
            xaxis=dict(range=[0, 100], showgrid=True, gridcolor="#21262d"),
            yaxis=dict(showgrid=False),
            height=280,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: Live Transcript
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("#### Last call transcript (live from Pipecat Cloud)")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        if st.button("🔄 Fetch latest logs", type="primary"):
            with st.spinner("Pulling from Pipecat Cloud…"):
                result = subprocess.run(
                    ["uv", "run", "pcc", "agent", "logs", "flower-bot"],
                    capture_output=True,
                    text=True,
                    cwd=os.path.join(os.path.dirname(__file__), "..", "server"),
                )
                st.session_state["raw_logs"] = result.stdout + result.stderr
        else:
            if "raw_logs" not in st.session_state:
                st.info("Press **Fetch latest logs** to pull the most recent call from Pipecat Cloud.")

    if "raw_logs" in st.session_state:
        raw = st.session_state["raw_logs"]
        # Parse chat context lines from logs
        import re
        context_match = re.search(r"Generating chat from context \[(.+?)\](?=\n)", raw, re.DOTALL)
        if context_match:
            try:
                context_str = "[" + context_match.group(1) + "]"
                context_str = context_str.replace("'role'", '"role"').replace("'content'", '"content"').replace("'user'", '"user"').replace("'assistant'", '"assistant"').replace("'system'", '"system"').replace("': '", '": "').replace("', '", '", "').replace("{'", '{"').replace("'}", '"}')
                # fallback: show raw parsed lines
            except Exception:
                pass

        # Show raw log with highlights
        lines = raw.split("\n")
        transcript_lines = [l for l in lines if "Generating TTS" in l or "chat from context" in l or "TTFB" in l or "latency" in l]

        st.markdown("**Key events:**")
        for line in transcript_lines[:30]:
            if "latency" in line.lower():
                st.success(line.strip())
            elif "TTFB" in line:
                st.info(line.strip())
            elif "TTS" in line:
                st.markdown(f"🗣️ `{line.strip()}`")
            else:
                st.markdown(f"`{line.strip()}`")

        with st.expander("Raw logs"):
            st.code(raw[-8000:], language="text")

    # Sample transcript when no logs
    else:
        st.markdown("**Sample transcript (from test run):**")
        sample = [
            ("agent", "This is Field & Flower— wait, I mean, good afternoon, this is the intake line. How can I help you today?"),
            ("user", "Hi, I was in a car accident about two months ago in California. Still getting treatment."),
            ("agent", "I'm sorry to hear that. Can I get your name and a bit more about the accident — were you at fault?"),
            ("user", "No, the other driver ran a red light. My name is Maria."),
            ("agent", "Thank you Maria. Are you currently represented by another attorney?"),
            ("user", "No, I'm not."),
            ("agent", "Great. Based on what you've shared, it sounds like you may have a strong case. I'd like to schedule a free consultation — would tomorrow afternoon work?"),
        ]
        for role, text in sample:
            if role == "agent":
                st.markdown(
                    f"<div style='background:#161b22;border-left:3px solid #58a6ff;padding:8px 12px;border-radius:4px;margin:4px 0;font-size:0.9rem'>"
                    f"<b style='color:#58a6ff'>Agent</b>&nbsp;&nbsp;{text}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='background:#0d1117;border-left:3px solid #8b949e;padding:8px 12px;border-radius:4px;margin:4px 0;font-size:0.9rem'>"
                    f"<b style='color:#8b949e'>Caller</b>&nbsp;&nbsp;{text}</div>",
                    unsafe_allow_html=True,
                )

        verdict_col, _ = st.columns([1, 2])
        with verdict_col:
            st.markdown(
                "<div style='background:#1a4731;border:1px solid #238636;border-radius:8px;padding:12px 18px;margin-top:12px;text-align:center'>"
                "<span style='font-size:1.1rem;font-weight:700;color:#3fb950'>✓ QUALIFIED</span><br>"
                "<span style='color:#8b949e;font-size:0.8rem'>Auto accident · CA · In treatment · No prior rep</span>"
                "</div>",
                unsafe_allow_html=True,
            )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: Failure Analysis
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("#### Failure modes by version")

    def failure_counts(scores):
        fails = {}
        for i, persona in enumerate(PERSONAS):
            for j, evaluator in enumerate(EVALUATORS):
                if scores[i][j] < 1:
                    key = evaluator
                    fails[key] = fails.get(key, 0) + (1 if scores[i][j] == 0 else 0.5)
        return fails

    f1 = failure_counts(SCORES_V1)
    f2 = failure_counts(SCORES_V2)
    f3 = failure_counts(SCORES_V3)

    all_evals = EVALUATORS
    df_fail = pd.DataFrame({
        "Evaluator": all_evals,
        "v1 failures": [f1.get(e, 0) for e in all_evals],
        "v2 failures": [f2.get(e, 0) for e in all_evals],
        "v3 failures": [f3.get(e, 0) for e in all_evals],
    }).set_index("Evaluator")

    fig_fail = go.Figure()
    colors = {"v1 failures": "#6e40c9", "v2 failures": "#1f6feb", "v3 failures": "#238636"}
    for col in ["v1 failures", "v2 failures", "v3 failures"]:
        fig_fail.add_trace(
            go.Bar(name=col, x=all_evals, y=df_fail[col], marker_color=colors[col])
        )

    fig_fail.update_layout(
        barmode="group",
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        font=dict(color="#e6edf3"),
        xaxis=dict(tickangle=-30, showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#21262d", title="Failures (across personas)"),
        legend=dict(bgcolor="#161b22"),
        height=380,
        margin=dict(l=20, r=20, t=20, b=80),
    )
    st.plotly_chart(fig_fail, use_container_width=True)

    st.markdown("#### Personas with most failures per version")
    col1, col2, col3 = st.columns(3)

    for col, version, scores in zip([col1, col2, col3], ["v1", "v2", "v3"], [SCORES_V1, SCORES_V2, SCORES_V3]):
        with col:
            persona_fails = [(PERSONAS[i], sum(1 for v in row if v < 1)) for i, row in enumerate(scores)]
            persona_fails.sort(key=lambda x: -x[1])
            st.markdown(f"**{version}**")
            for p, fails in persona_fails[:4]:
                color = "#da3633" if fails >= 5 else "#d29922" if fails >= 3 else "#238636"
                st.markdown(
                    f"<div style='font-size:0.82rem;padding:4px 0;color:{color}'>"
                    f"{'●' * fails} {p[:38]}</div>",
                    unsafe_allow_html=True,
                )
