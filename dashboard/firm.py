"""
Firm-owner dashboard — PI law firm managing partner view.
Monday-morning snapshot: pipeline, after-hours capture, ROI, funnel.

Run: streamlit run dashboard/firm.py
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from mock_data import (
    CALL_VOLUME,
    DAYS,
    DECLINE_REASONS,
    FIRM_STATS,
    FUNNEL,
    HOURS,
)

st.set_page_config(
    page_title="LexIntake — Firm Intelligence",
    page_icon="⚖️",
    layout="wide",
)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, .stApp { background: #08090a; font-family: 'Inter', sans-serif; }

    .top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 0 28px 0;
        border-bottom: 1px solid #1c1f26;
        margin-bottom: 28px;
    }
    .brand { font-size: 1.4rem; font-weight: 700; color: #ffffff; letter-spacing: -0.5px; }
    .brand span { color: #6366f1; }
    .sub { font-size: 0.78rem; color: #52556b; margin-top: 2px; }

    .kpi-grid { display: grid; grid-template-columns: repeat(5,1fr); gap: 14px; margin-bottom: 24px; }
    .kpi {
        background: #0f1117;
        border: 1px solid #1c1f26;
        border-radius: 12px;
        padding: 20px 20px 16px;
    }
    .kpi-val { font-size: 2rem; font-weight: 700; color: #ffffff; line-height: 1.1; }
    .kpi-label { font-size: 0.73rem; color: #52556b; margin-top: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-delta { font-size: 0.78rem; margin-top: 4px; }
    .delta-pos { color: #22c55e; }
    .delta-neg { color: #ef4444; }

    .section-title { font-size: 0.82rem; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 14px; }

    .highlight-card {
        background: linear-gradient(135deg, #1a1d2e 0%, #0f1117 100%);
        border: 1px solid #2d2f45;
        border-radius: 14px;
        padding: 24px;
    }
    .big-num { font-size: 3rem; font-weight: 800; color: #6366f1; line-height: 1; }
    .big-label { font-size: 0.82rem; color: #9ca3af; margin-top: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class='top-bar'>
        <div>
            <div class='brand'>Lex<span>Intake</span> &nbsp;Intelligence</div>
            <div class='sub'>AI-powered intake analytics &nbsp;·&nbsp; Week of May 26 – June 1, 2025</div>
        </div>
        <div style='font-size:0.78rem;color:#52556b;text-align:right'>
            Last updated: today, 9:14 AM<br>
            <span style='color:#22c55e'>● Live</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── KPI row ───────────────────────────────────────────────────────────────────
s = FIRM_STATS
kpis = [
    ("$235K", "Revenue pipeline (week)", "+18%", True),
    ("47", "Qualified leads (week)", "+12", True),
    ("31", "After-hours calls captured", "would've been missed", None),
    ("$4,200", "Monthly cost savings vs. human answering", "vs. $7K/mo service", True),
    ("89%", "Qualification accuracy", "+14pp vs. v1", True),
]

cols = st.columns(5)
for col, (val, label, delta, pos) in zip(cols, kpis):
    if pos is True:
        delta_html = f"<div class='kpi-delta delta-pos'>↑ {delta}</div>"
    elif pos is False:
        delta_html = f"<div class='kpi-delta delta-neg'>↓ {delta}</div>"
    else:
        delta_html = f"<div class='kpi-delta' style='color:#52556b'>{delta}</div>"
    col.markdown(
        f"<div class='kpi'><div class='kpi-val'>{val}</div><div class='kpi-label'>{label}</div>{delta_html}</div>",
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 2: Today snapshot + Funnel + Decline reasons ─────────────────────────
col_today, col_funnel, col_decline = st.columns([1, 1.4, 1], gap="large")

with col_today:
    st.markdown("<div class='section-title'>Today's activity</div>", unsafe_allow_html=True)

    total = s["calls_today"]
    qual = s["qualified_today"]
    decl = s["declined_today"]

    fig_today = go.Figure(go.Pie(
        values=[qual, decl],
        labels=["Qualified", "Declined"],
        hole=0.68,
        marker_colors=["#6366f1", "#1c1f26"],
        textinfo="none",
    ))
    fig_today.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:11px'>calls</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=22, color="white"),
    )
    fig_today.update_layout(
        paper_bgcolor="#0f1117", showlegend=True,
        legend=dict(font=dict(color="#9ca3af", size=11), bgcolor="#0f1117"),
        height=220, margin=dict(l=0, r=0, t=0, b=0),
    )
    st.plotly_chart(fig_today, use_container_width=True)

    for label, val, color in [
        (f"Qualified ({qual})", qual / total, "#6366f1"),
        (f"Declined ({decl})", decl / total, "#374151"),
    ]:
        pct = int(val * 100)
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:0.82rem;color:#9ca3af'>"
            f"<div style='flex:1;background:#1c1f26;border-radius:4px;height:6px'>"
            f"<div style='width:{pct}%;background:{color};border-radius:4px;height:6px'></div></div>"
            f"{label}</div>",
            unsafe_allow_html=True,
        )

with col_funnel:
    st.markdown("<div class='section-title'>Conversion funnel (this week)</div>", unsafe_allow_html=True)

    labels = [f[0] for f in FUNNEL]
    values = [f[1] for f in FUNNEL]
    colors = ["#6366f1", "#818cf8", "#a5b4fc", "#c7d2fe"]

    fig_funnel = go.Figure(go.Funnel(
        y=labels,
        x=values,
        marker=dict(color=colors),
        textinfo="value+percent initial",
        textfont=dict(color="white", size=13),
        connector=dict(line=dict(color="#1c1f26", width=2)),
    ))
    fig_funnel.update_layout(
        paper_bgcolor="#0f1117",
        plot_bgcolor="#0f1117",
        font=dict(color="#9ca3af", size=12),
        height=280,
        margin=dict(l=20, r=20, t=10, b=10),
    )
    st.plotly_chart(fig_funnel, use_container_width=True)

    # Conversion rates
    for i in range(len(FUNNEL) - 1):
        rate = round(FUNNEL[i + 1][1] / FUNNEL[i][1] * 100)
        st.markdown(
            f"<div style='font-size:0.78rem;color:#52556b;margin-bottom:2px'>"
            f"{FUNNEL[i][0]} → {FUNNEL[i+1][0]}: <b style='color:#9ca3af'>{rate}%</b></div>",
            unsafe_allow_html=True,
        )

with col_decline:
    st.markdown("<div class='section-title'>Decline reasons</div>", unsafe_allow_html=True)

    fig_decline = go.Figure(go.Pie(
        labels=list(DECLINE_REASONS.keys()),
        values=list(DECLINE_REASONS.values()),
        hole=0.55,
        marker_colors=["#dc2626", "#d97706", "#7c3aed", "#374151"],
        textinfo="percent",
        textfont=dict(size=11, color="white"),
    ))
    fig_decline.update_layout(
        paper_bgcolor="#0f1117",
        showlegend=True,
        legend=dict(font=dict(color="#9ca3af", size=10), bgcolor="#0f1117", orientation="v"),
        height=280,
        margin=dict(l=0, r=0, t=0, b=0),
    )
    st.plotly_chart(fig_decline, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 3: Call volume heatmap + After-hours highlight ────────────────────────
col_heat, col_ah = st.columns([2.5, 1], gap="large")

with col_heat:
    st.markdown("<div class='section-title'>Call volume — hour of day × day of week</div>", unsafe_allow_html=True)

    df_heat = pd.DataFrame(CALL_VOLUME, index=DAYS, columns=[f"{h:02d}:00" for h in HOURS])

    fig_heat = px.imshow(
        df_heat,
        color_continuous_scale=[[0, "#0f1117"], [0.4, "#1e1b4b"], [0.7, "#4338ca"], [1, "#6366f1"]],
        aspect="auto",
        labels=dict(color="Calls"),
    )
    fig_heat.update_layout(
        paper_bgcolor="#0f1117",
        plot_bgcolor="#0f1117",
        font=dict(color="#9ca3af", size=10),
        xaxis=dict(tickangle=-45, showgrid=False),
        yaxis=dict(showgrid=False),
        coloraxis_colorbar=dict(tickfont=dict(color="#9ca3af"), title=dict(font=dict(color="#9ca3af"))),
        height=240,
        margin=dict(l=10, r=10, t=10, b=40),
    )

    # Highlight after-hours band
    fig_heat.add_shape(
        type="rect",
        x0=-0.5, x1=7.5, y0=-0.5, y1=6.5,
        line=dict(color="#6366f1", width=1, dash="dot"),
        fillcolor="rgba(99,102,241,0.04)",
    )
    fig_heat.add_shape(
        type="rect",
        x0=17.5, x1=23.5, y0=-0.5, y1=6.5,
        line=dict(color="#6366f1", width=1, dash="dot"),
        fillcolor="rgba(99,102,241,0.04)",
    )

    st.plotly_chart(fig_heat, use_container_width=True)
    st.markdown(
        "<div style='font-size:0.74rem;color:#52556b'>Dotted boxes = after-hours windows (before 8AM / after 6PM)</div>",
        unsafe_allow_html=True,
    )

with col_ah:
    st.markdown("<div class='section-title'>After-hours ROI</div>", unsafe_allow_html=True)

    # Count after-hours calls in mock data
    ah_calls = sum(
        CALL_VOLUME[d][h]
        for d in range(7)
        for h in HOURS
        if h < 8 or h > 17
    )
    ah_value = ah_calls * FIRM_STATS["avg_case_value"] * 0.48  # qualified rate applied

    st.markdown(
        f"""
        <div class='highlight-card' style='margin-bottom:12px'>
            <div class='big-num'>{s['after_hours_captured']}</div>
            <div class='big-label'>after-hours calls captured this week</div>
        </div>
        <div class='highlight-card' style='margin-bottom:12px'>
            <div class='big-num'>${int(ah_value / 1000)}K</div>
            <div class='big-label'>estimated pipeline from after-hours alone</div>
        </div>
        <div class='highlight-card'>
            <div class='big-num'>${s['cost_savings_monthly']:,}</div>
            <div class='big-label'>monthly savings vs. human answering service</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center;font-size:0.72rem;color:#374151;padding-top:16px;border-top:1px solid #1c1f26'>"
    "LexIntake AI · Powered by NVIDIA Nemotron + Pipecat Cloud · Data refreshes every 15 min"
    "</div>",
    unsafe_allow_html=True,
)
