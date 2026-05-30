"""FirstCall — AI Intake console (Cekura × Agiloft styled, light theme)."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from data import (
    AGENT_NAME,
    AGENT_PROVIDER,
    AGENT_VERSION,
    AVG_CASE_VALUE,
    FIRM_NAME,
    FIRM_TAGLINE,
    call_kpis,
    estimated_pipeline,
    format_currency,
    get_call_heatmap,
    get_calls,
    get_decline_reasons,
    get_funnel,
    get_today,
    get_week,
)

import auth

try:
    from mock_data import (
        EVALUATORS,
        PERSONAS,
        SCORES_V1,
        SCORES_V2,
        SCORES_V3,
        VERSION_NOTES,
        VERSION_SCORES,
    )
    HAS_SIM = True
except Exception:  # pragma: no cover
    HAS_SIM = False

# ── shadcn/ui design tokens (neutral base · light) ───────────────────────────
INK = "#0a0a0a"          # foreground (neutral-950)
BODY = "#404040"         # body text (neutral-700)
MUTE = "#737373"         # muted-foreground (neutral-500)
FAINT = "#a3a3a3"        # neutral-400
HAIRLINE = "#e5e5e5"     # border (neutral-200)
HAIRLINE_SOFT = "#f5f5f5"  # neutral-100
CANVAS = "#ffffff"       # background / card
CANVAS_SOFT = "#fafafa"  # neutral-50 (muted surfaces)
SIDEBAR_BG = "#fafafa"
ACCENT = "#171717"       # primary (neutral-900)
ACCENT_SOFT = "#f5f5f5"  # secondary
ACCENT_TEXT = "#171717"  # secondary-foreground
RING = "#a3a3a3"

# Semantic badge tones (kept for disposition legibility)
GREEN_BG, GREEN_TX = "#dcfce7", "#15803d"
RED_BG, RED_TX = "#fee2e2", "#b91c1c"
AMBER_BG, AMBER_TX = "#fef3c7", "#b45309"
BLUE_BG, BLUE_TX = "#e0eaff", "#1d4ed8"

# Monochrome chart ramp (dark → light), the shadcn way
RAMP = ["#171717", "#404040", "#525252", "#737373", "#a3a3a3", "#d4d4d4"]

FONT = "'Geist', 'Inter', system-ui, -apple-system, sans-serif"
FONT_MONO = "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace"

PLOT_CONFIG = {"displayModeBar": False}

st.set_page_config(
    page_title=f"{AGENT_NAME} · Intake Console",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

PUBLIC_PAGES = {"landing", "signup", "signin"}

# Sign out: clear session then continue as a public visitor.
if st.query_params.get("out"):
    auth.sign_out()
    for _k in ("firm_name", "signup_step", "signup_data"):
        st.session_state.pop(_k, None)
    st.query_params.clear()
    st.query_params["page"] = "landing"
    st.rerun()

AUTHED = st.session_state.get("authed", False)
_default_page = "calls" if AUTHED else "landing"
PAGE = st.query_params.get("page", _default_page)
FILTER = st.query_params.get("f", "all")

# Gate: unauthenticated visitors can only see public pages.
if not AUTHED and PAGE not in PUBLIC_PAGES:
    PAGE = "landing"

# Tenant (law firm) name — set during sign-up, defaults to the demo firm.
FIRM = st.session_state.get("firm_name", FIRM_NAME)

# ── Icons (Lucide-style strokes) ─────────────────────────────────────────────
def _icon(paths: str) -> str:
    return (
        f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" '
        f'width="18" height="18">{paths}</svg>'
    )


ICONS = {
    "home": _icon('<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>'),
    "agent": _icon('<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M7 20l3-4M17 20l-3-4"/><circle cx="9" cy="10" r="1"/><circle cx="15" cy="10" r="1"/>'),
    "metrics": _icon('<path d="M21 12a9 9 0 1 1-9-9v9z"/><path d="M12 3a9 9 0 0 1 9 9h-9z"/>'),
    "labs": _icon('<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/><path d="M7 16h10"/>'),
    "personality": _icon('<circle cx="12" cy="8" r="4"/><path d="M5 21a7 7 0 0 1 14 0"/>'),
    "evaluator": _icon('<path d="M3 5a2 2 0 0 1 2-2h6v18H5a2 2 0 0 1-2-2z"/><path d="M21 5a2 2 0 0 0-2-2h-6v18h6a2 2 0 0 0 2-2z"/>'),
    "results": _icon('<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>'),
    "runs": _icon('<path d="M3 3v18h18"/><path d="M7 14l3-4 3 3 5-6"/>'),
    "calls": _icon('<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.6A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.6a16 16 0 0 0 6 6l1.1-1.1a2 2 0 0 1 2.1-.5c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>'),
    "overview": _icon('<path d="M3 3v18h18"/><rect x="7" y="11" width="3" height="7"/><rect x="12" y="7" width="3" height="11"/><rect x="17" y="13" width="3" height="5"/>'),
    "search": _icon('<circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/>'),
    "copy": _icon('<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>'),
    "flask": _icon('<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/>'),
    "trash": _icon('<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>'),
    "globe": _icon('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18z"/>'),
    "dots": _icon('<circle cx="12" cy="5" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="12" cy="19" r="1.4"/>'),
}

# ── Navigation model ─────────────────────────────────────────────────────────
NAV = [
    ("AGENTS", [("home", "Home"), ("agent", "Agent Settings")]),
    ("METRICS", [("metrics", "Metrics"), ("labs", "Labs")]),
    ("SIMULATION", [("personality", "Personality"), ("evaluator", "Evaluator"),
                    ("results", "Results"), ("runs", "Runs Overview")]),
    ("OBSERVABILITY", [("calls", "Calls"), ("overview", "Overview")]),
]

PAGE_META = {
    "home": ("Home", "Operational snapshot for your intake agent"),
    "agent": ("Agent Settings", "Voice, model, and qualification configuration"),
    "metrics": ("Metrics", "Quality, latency, and accuracy over time"),
    "labs": ("Labs", "Saved calls staged for replay and regression"),
    "personality": ("Personality", "Caller personas used in simulation"),
    "evaluator": ("Evaluator", "Pass / fail criteria graded on every call"),
    "results": ("Results", "Simulation scores across prompt versions"),
    "runs": ("Runs Overview", "History of simulation runs"),
    "calls": ("Calls", "Every intake call captured by the agent"),
    "overview": ("Overview", "Pipeline, funnel, and after-hours capture"),
}

# ── Global CSS ───────────────────────────────────────────────────────────────
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

header[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], #MainMenu, footer {{ display:none !important; height:0 !important; }}

.stApp {{ background:{CANVAS}; color:{INK}; font-family:{FONT};
  font-feature-settings:"cv11","ss01"; -webkit-font-smoothing:antialiased; letter-spacing:-0.011em; }}
h1, h2, h3, .topbar h1, .panel h3, .sectitle {{ letter-spacing:-0.025em; }}

.block-container {{ padding:0 !important; max-width:100% !important; }}
[data-testid="stVerticalBlock"] {{ gap:0 !important; }}
[data-testid="stMain"] {{ background:{CANVAS}; }}
[data-testid="stMainBlockContainer"] {{ padding:0 !important; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{ background:{SIDEBAR_BG}; border-right:1px solid {HAIRLINE}; }}
[data-testid="stSidebar"] > div {{ padding:0 !important; }}
[data-testid="stSidebarContent"] {{ padding:0 !important; }}
[data-testid="stSidebarHeader"], [data-testid="stSidebarCollapseButton"] {{ display:none !important; }}
[data-testid="stSidebarUserContent"] {{ padding:0 !important; }}

.sb-brand {{
  display:flex; align-items:center; gap:10px;
  padding:20px 18px 18px; border-bottom:1px solid {HAIRLINE};
}}
.sb-logo {{
  width:30px; height:30px; border-radius:8px; flex-shrink:0;
  background:{ACCENT}; color:#fff; display:flex; align-items:center; justify-content:center;
  font-weight:700; font-size:14px; letter-spacing:-0.02em;
  box-shadow:0 1px 2px rgba(10,10,10,0.25);
}}
.sb-brand .nm {{ font-size:15px; font-weight:600; letter-spacing:-0.01em; color:{INK}; line-height:1.1; }}
.sb-brand .sub {{ font-size:11px; color:{MUTE}; margin-top:2px; }}

.sb-nav {{ padding:14px 12px 24px; }}
.sb-group {{ font-size:10.5px; font-weight:600; letter-spacing:1px; color:{FAINT};
  text-transform:uppercase; padding:14px 10px 7px; }}
.sb-item {{
  display:flex; align-items:center; gap:11px;
  padding:8px 10px; margin:1px 0; border-radius:8px;
  font-size:14px; font-weight:500; color:{BODY};
  text-decoration:none; transition:background .15s ease, color .15s ease;
}}
.sb-item svg {{ color:{FAINT}; transition:color .15s ease; }}
.sb-item:hover {{ background:#f1f2f4; color:{INK}; }}
.sb-item:hover svg {{ color:{MUTE}; }}
.sb-item.active {{ background:#eceef1; color:{INK}; font-weight:600; }}
.sb-item.active svg {{ color:{ACCENT}; }}

/* ── Topbar ── */
.topbar {{
  position:sticky; top:0; z-index:50;
  display:flex; align-items:center; justify-content:space-between;
  padding:16px 28px; background:rgba(255,255,255,0.9);
  backdrop-filter:blur(8px); border-bottom:1px solid {HAIRLINE};
}}
.topbar h1 {{ font-size:20px; font-weight:600; letter-spacing:-0.02em; margin:0; color:{INK}; }}
.topbar .crumb {{ font-size:12.5px; color:{MUTE}; margin-top:3px; }}
.tb-right {{ display:flex; align-items:center; gap:10px; }}
.searchbox {{
  display:flex; align-items:center; gap:8px;
  background:{CANVAS_SOFT}; border:1px solid {HAIRLINE}; border-radius:9px;
  padding:7px 12px; font-size:13px; color:{FAINT}; min-width:220px;
}}
.searchbox svg {{ color:{FAINT}; }}
.live {{
  display:inline-flex; align-items:center; gap:7px;
  background:{GREEN_BG}; color:{GREEN_TX};
  font-size:12px; font-weight:600; padding:6px 12px; border-radius:9999px;
}}
.live .dot {{ width:7px; height:7px; border-radius:50%; background:{GREEN_TX}; }}
.vbadge {{
  font-size:12px; font-weight:600; color:{ACCENT_TEXT};
  background:{ACCENT_SOFT}; border:1px solid {HAIRLINE}; padding:6px 11px; border-radius:8px;
}}
.avatar {{
  width:32px; height:32px; border-radius:50%; background:{INK}; color:#fff;
  display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:600;
}}

.page {{ padding:24px 28px 60px; max-width:1320px; }}

/* ── KPI cards ── */
.kpis {{ display:grid; grid-template-columns:repeat(5,1fr); gap:14px; margin-bottom:22px; }}
@media (max-width:1100px){{ .kpis {{ grid-template-columns:repeat(2,1fr); }} }}
.kpi {{ background:{CANVAS}; border:1px solid {HAIRLINE}; border-radius:12px; padding:16px 18px; }}
.kpi .lbl {{ font-size:11.5px; font-weight:600; letter-spacing:.4px; text-transform:uppercase; color:{MUTE}; }}
.kpi .val {{ font-size:30px; font-weight:700; letter-spacing:-0.03em; color:{INK}; margin-top:8px; line-height:1; }}
.kpi .val.accent {{ color:{ACCENT}; }}
.kpi .delta {{ font-size:12.5px; margin-top:8px; color:{MUTE}; }}
.kpi .delta.up {{ color:{GREEN_TX}; }}

/* ── Toolbar / filter pills ── */
.toolbar {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; gap:12px; flex-wrap:wrap; }}
.segs {{ display:inline-flex; background:{CANVAS_SOFT}; border:1px solid {HAIRLINE}; border-radius:10px; padding:3px; gap:2px; }}
.seg {{ font-size:13px; font-weight:500; color:{MUTE}; text-decoration:none; padding:6px 14px; border-radius:8px; transition:all .15s ease; }}
.seg:hover {{ color:{INK}; }}
.seg.active {{ background:{CANVAS}; color:{INK}; font-weight:600; box-shadow:0 1px 2px rgba(15,23,42,0.08); }}
.tb-actions {{ display:flex; gap:8px; }}
.btn {{ font-size:13px; font-weight:500; color:{BODY}; background:{CANVAS}; border:1px solid {HAIRLINE};
  border-radius:9px; padding:7px 13px; cursor:default; }}
.btn.primary {{ background:{ACCENT}; color:#fff; border-color:{ACCENT}; }}

/* ── Data table ── */
.tbl-wrap {{ border:1px solid {HAIRLINE}; border-radius:13px; overflow:visible; background:{CANVAS}; }}
table.dt {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
table.dt thead th {{
  text-align:left; font-size:11.5px; font-weight:600; letter-spacing:.4px; text-transform:uppercase;
  color:{MUTE}; background:{CANVAS_SOFT}; padding:12px 14px; border-bottom:1px solid {HAIRLINE};
  white-space:nowrap;
}}
table.dt tbody td {{ padding:13px 14px; border-bottom:1px solid {HAIRLINE_SOFT}; color:{BODY}; vertical-align:middle; }}
table.dt tbody tr:last-child td {{ border-bottom:none; }}
table.dt tbody tr:hover {{ background:{CANVAS_SOFT}; }}
.cell-id {{
  display:inline-flex; align-items:center; gap:6px;
  font-family:{FONT_MONO}; font-size:12.5px; color:{INK};
  background:{CANVAS_SOFT}; border:1px solid {HAIRLINE}; border-radius:7px; padding:5px 9px;
  max-width:170px;
}}
.cell-id span {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.copy {{ display:inline-flex; color:{FAINT}; border:1px solid {HAIRLINE}; border-radius:6px; padding:3px; background:{CANVAS}; }}
.caller {{ font-weight:600; color:{INK}; }}
.caller small {{ display:block; font-weight:400; color:{FAINT}; font-size:11.5px; margin-top:1px; }}
.badge {{ display:inline-flex; align-items:center; gap:5px; font-size:12px; font-weight:600; padding:3px 10px; border-radius:9999px; }}
.dot {{ width:6px; height:6px; border-radius:50%; }}
.tag {{ font-size:11.5px; font-weight:500; color:{MUTE}; background:{CANVAS_SOFT}; border:1px solid {HAIRLINE}; padding:3px 8px; border-radius:6px; }}
.score {{ font-weight:600; font-variant-numeric:tabular-nums; }}
.cbx {{ width:15px; height:15px; border:1.5px solid #cbd0d6; border-radius:4px; display:inline-block; }}
.chev {{ color:{FAINT}; }}

/* row action popover */
details.rowmenu {{ position:relative; }}
details.rowmenu > summary {{ list-style:none; cursor:pointer; color:{FAINT}; display:inline-flex; padding:4px; border-radius:6px; }}
details.rowmenu > summary::-webkit-details-marker {{ display:none; }}
details.rowmenu[open] > summary {{ background:{CANVAS_SOFT}; color:{INK}; }}
.menu {{
  position:absolute; left:0; top:28px; z-index:80; width:210px;
  background:{CANVAS}; border:1px solid {HAIRLINE}; border-radius:12px;
  box-shadow:0 12px 32px rgba(15,23,42,0.14); padding:6px; text-align:left;
}}
.menu .mh {{ font-size:11px; font-weight:600; letter-spacing:.5px; text-transform:uppercase; color:{FAINT}; padding:8px 10px 6px; }}
.menu a {{ display:flex; align-items:center; gap:10px; padding:9px 10px; border-radius:8px; font-size:13.5px; color:{BODY}; text-decoration:none; }}
.menu a:hover {{ background:{CANVAS_SOFT}; color:{INK}; }}
.menu a svg {{ color:{MUTE}; }}
.menu a.danger:hover {{ background:{RED_BG}; color:{RED_TX}; }}
.menu a.danger:hover svg {{ color:{RED_TX}; }}

/* ── Panels / charts ── */
.panel {{ background:{CANVAS}; border:1px solid {HAIRLINE}; border-radius:13px; padding:20px 22px; height:100%; }}
.panel h3 {{ font-size:15px; font-weight:600; margin:0 0 2px; color:{INK}; }}
.panel .cap {{ font-size:12.5px; color:{MUTE}; margin-bottom:6px; }}
.eyebrow {{ font-size:11px; font-weight:600; letter-spacing:.8px; text-transform:uppercase; color:{FAINT}; margin-bottom:10px; }}

/* ── Config / list rows ── */
.kv {{ display:grid; grid-template-columns:200px 1fr; gap:0; }}
.kv .k {{ padding:13px 0; border-bottom:1px solid {HAIRLINE_SOFT}; font-size:13px; color:{MUTE}; font-weight:500; }}
.kv .v {{ padding:13px 0; border-bottom:1px solid {HAIRLINE_SOFT}; font-size:13.5px; color:{INK}; }}
.listrow {{ display:flex; align-items:center; justify-content:space-between; padding:13px 16px; border:1px solid {HAIRLINE}; border-radius:10px; margin-bottom:8px; }}
.listrow .t {{ font-size:14px; font-weight:500; color:{INK}; }}
.listrow .d {{ font-size:12.5px; color:{MUTE}; margin-top:2px; }}
.sectitle {{ font-size:16px; font-weight:600; color:{INK}; margin:6px 0 14px; }}
[data-testid="stPlotlyChart"] {{ margin-top:4px; }}

/* ── shadcn-styled native Streamlit widgets ── */
.stMainBlockContainer .toolwrap {{ padding:0 28px; max-width:1320px; }}

/* Text input → shadcn Input */
[data-testid="stTextInputRootElement"] {{ border:1px solid {HAIRLINE}; border-radius:8px; background:{CANVAS}; box-shadow:0 1px 2px rgba(10,10,10,0.04); }}
[data-testid="stTextInputRootElement"]:focus-within {{ border-color:{ACCENT}; box-shadow:0 0 0 3px rgba(10,10,10,0.08); }}
[data-testid="stTextInput"] input {{ font-family:{FONT}; font-size:13.5px !important; color:{INK}; padding:8px 12px; }}
[data-testid="stTextInput"] input::placeholder {{ color:{FAINT}; }}
[data-testid="stTextInputRootElement"] > div {{ border:none !important; }}

/* Segmented control / pills → shadcn Tabs / ToggleGroup */
[data-testid="stSegmentedControl"] [role="radiogroup"],
[data-testid="stPills"] [role="radiogroup"] {{
  background:{CANVAS_SOFT}; border:1px solid {HAIRLINE}; border-radius:9px; padding:3px; gap:2px;
}}
[data-testid="stSegmentedControl"] button, [data-testid="stPills"] button {{
  background:transparent !important; border:none !important; color:{MUTE} !important;
  font-family:{FONT}; font-size:13px !important; font-weight:500 !important;
  border-radius:7px !important; padding:5px 14px !important; box-shadow:none !important;
}}
[data-testid="stSegmentedControl"] button:hover, [data-testid="stPills"] button:hover {{ color:{INK} !important; }}
[data-testid="stSegmentedControl"] button[aria-checked="true"],
[data-testid="stPills"] button[aria-checked="true"] {{
  background:{CANVAS} !important; color:{INK} !important; font-weight:600 !important;
  box-shadow:0 1px 2px rgba(10,10,10,0.1) !important;
}}

/* Buttons → shadcn Button (outline + primary) */
[data-testid="stButton"] button {{
  font-family:{FONT}; font-size:13px; font-weight:500; border-radius:8px;
  border:1px solid {HAIRLINE}; background:{CANVAS}; color:{INK};
  padding:7px 14px; box-shadow:0 1px 2px rgba(10,10,10,0.04); transition:background .15s ease;
}}
[data-testid="stButton"] button:hover {{ background:{CANVAS_SOFT}; border-color:{HAIRLINE}; color:{INK}; }}
[data-testid="stButton"] button[kind="primary"], [data-testid="stBaseButton-primary"] {{
  background:{ACCENT}; color:#fafafa; border-color:{ACCENT};
}}
[data-testid="stButton"] button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {{
  background:#262626; color:#fafafa; border-color:#262626;
}}

/* Multiselect → shadcn-style chips */
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
  border:1px solid {HAIRLINE} !important; border-radius:8px; background:{CANVAS}; min-height:38px;
  box-shadow:0 1px 2px rgba(10,10,10,0.04);
}}
[data-testid="stMultiSelect"] [data-baseweb="tag"] {{
  background:{ACCENT_SOFT} !important; color:{INK} !important; border-radius:6px;
  font-family:{FONT}; font-weight:500; font-size:12px;
}}
[data-testid="stMultiSelect"] [data-baseweb="tag"] svg {{ fill:{MUTE}; }}

/* Labels → shadcn label (text-sm font-medium) */
[data-testid="stWidgetLabel"] label p {{ font-family:{FONT}; font-size:12.5px; font-weight:500; color:{BODY}; }}

/* Toast → shadcn sonner */
[data-testid="stToast"] {{
  background:{CANVAS}; border:1px solid {HAIRLINE}; border-radius:10px;
  color:{INK}; box-shadow:0 8px 24px rgba(10,10,10,0.12); font-family:{FONT};
}}

/* Selection action bar */
.actionbar {{
  display:flex; align-items:center; gap:14px;
  background:{INK}; color:#fafafa; border-radius:10px; padding:10px 16px; margin:4px 0 14px;
  font-size:13px; font-weight:500; box-shadow:0 8px 24px rgba(10,10,10,0.18);
}}
.actionbar .cnt {{ background:rgba(255,255,255,0.16); border-radius:6px; padding:2px 9px; font-weight:600; font-variant-numeric:tabular-nums; }}
tr.sel td {{ background:{CANVAS_SOFT}; }}
.cbx.on {{ background:{ACCENT}; border-color:{ACCENT}; position:relative; }}
.cbx.on::after {{ content:""; position:absolute; left:4px; top:1px; width:4px; height:8px; border:solid #fff; border-width:0 1.6px 1.6px 0; transform:rotate(45deg); }}
.labtag {{ font-size:10.5px; font-weight:600; color:{ACCENT_TEXT}; background:{ACCENT_SOFT}; border:1px solid {HAIRLINE}; padding:2px 7px; border-radius:6px; margin-left:6px; }}
</style>
""",
    unsafe_allow_html=True,
)


# ── Sidebar ──────────────────────────────────────────────────────────────────
def render_sidebar() -> None:
    caps = [ch for ch in AGENT_NAME if ch.isupper()]
    initials = ("".join(caps) or AGENT_NAME)[:2].upper()
    html = [
        f'<div class="sb-brand"><div class="sb-logo">{initials}</div>'
        f'<div><div class="nm">{AGENT_NAME}</div><div class="sub">{FIRM}</div></div></div>',
        '<div class="sb-nav">',
    ]
    for group, items in NAV:
        html.append(f'<div class="sb-group">{group}</div>')
        for key, label in items:
            active = "active" if key == PAGE else ""
            icon = ICONS.get(key, "")
            html.append(
                f'<a class="sb-item {active}" href="?page={key}" target="_self">{icon}<span>{label}</span></a>'
            )
    html.append(
        f'<div class="sb-group" style="margin-top:18px">ACCOUNT</div>'
        f'<a class="sb-item" href="?page=landing&out=1" target="_self">{ICONS["globe"]}<span>Sign out</span></a>'
    )
    html.append("</div>")
    st.sidebar.markdown("".join(html), unsafe_allow_html=True)


def topbar() -> None:
    title, crumb = PAGE_META.get(PAGE, ("", ""))
    st.markdown(
        f"""
<div class="topbar">
  <div>
    <h1>{title}</h1>
    <div class="crumb">{crumb}</div>
  </div>
  <div class="tb-right">
    <div class="searchbox">{ICONS['search']}<span>Search calls, leads…</span></div>
    <span class="vbadge">{AGENT_VERSION}</span>
    <span class="live"><span class="dot"></span>Live</span>
    <div class="avatar">MA</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def light_layout(**overrides) -> dict:
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=BODY, size=12),
        margin=dict(l=8, r=8, t=8, b=8),
        hoverlabel=dict(bgcolor=CANVAS, bordercolor=HAIRLINE, font=dict(family=FONT, color=INK)),
    )
    base.update(overrides)
    return base


def disposition_badge(d: str) -> str:
    palette = {
        "Qualified": (GREEN_BG, GREEN_TX),
        "Declined": (RED_BG, RED_TX),
        "Transferred": (BLUE_BG, BLUE_TX),
    }
    bg, tx = palette.get(d, (CANVAS_SOFT, MUTE))
    return f'<span class="badge" style="background:{bg};color:{tx}"><span class="dot" style="background:{tx}"></span>{d}</span>'


# ── Stateful action handling (row 3-dot + bulk) ──────────────────────────────
def _init_state() -> None:
    for key in ("deleted_ids", "lab_ids", "sim_ids"):
        if key not in st.session_state:
            st.session_state[key] = set()


def _handle_row_action() -> None:
    """Row 3-dot menu links set ?act=&cid=; perform, flash, clean URL."""
    act = st.query_params.get("act")
    cid = st.query_params.get("cid")
    if not (act and cid):
        return
    label = {"lab": "Added to Lab", "delete": "Deleted call", "sim": "Simulation created from"}.get(act, "")
    if act == "delete":
        st.session_state.deleted_ids.add(cid)
    elif act == "lab":
        st.session_state.lab_ids.add(cid)
    elif act == "sim":
        st.session_state.sim_ids.add(cid)
    st.session_state.flash = f"{label} {cid}"
    f = st.query_params.get("f", "all")
    st.query_params.clear()
    st.query_params["page"] = "calls"
    st.query_params["f"] = f
    st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# PAGE: Calls  (Cekura × Agiloft data table — fully interactive)
# ════════════════════════════════════════════════════════════════════════════
def page_calls() -> None:
    _init_state()
    _handle_row_action()
    if "flash" in st.session_state:
        st.toast(st.session_state.pop("flash"), icon="✅")

    deleted = st.session_state.deleted_ids
    lab_ids = st.session_state.lab_ids
    calls = [c for c in get_calls() if c.call_id not in deleted]
    k = call_kpis(calls)
    qrate = round(k["qualified"] / k["total"] * 100) if k["total"] else 0

    st.markdown(
        f"""
<div class="page" style="padding-bottom:14px">
  <div class="kpis">
    <div class="kpi"><div class="lbl">Total calls</div><div class="val">{k['total']}</div><div class="delta">Last 48 hours</div></div>
    <div class="kpi"><div class="lbl">Qualified</div><div class="val accent">{k['qualified']}</div><div class="delta up">↑ {qrate}% qualification rate</div></div>
    <div class="kpi"><div class="lbl">Declined</div><div class="val">{k['declined']}</div><div class="delta">Out of scope / SoL</div></div>
    <div class="kpi"><div class="lbl">After-hours</div><div class="val">{k['after_hours']}</div><div class="delta">Would've gone to voicemail</div></div>
    <div class="kpi"><div class="lbl">Avg eval score</div><div class="val accent">{k['avg_score']}</div><div class="delta up">↑ +14 vs v1</div></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ── Interactive toolbar: search + filter + bulk selection ──
    st.markdown('<div class="toolwrap">', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.3], gap="small")
    with c1:
        query = st.text_input("Search", placeholder="Search caller, case, or ID…",
                              label_visibility="collapsed", key="calls_q")
    with c2:
        seg_labels = ["All", "Qualified", "Declined", "Transferred", "After-hours"]
        choice = st.segmented_control("Filter", seg_labels, default="All",
                                      label_visibility="collapsed", key="calls_seg")

    q = (query or "").strip().lower()

    def keep(c) -> bool:
        if choice == "After-hours":
            disp_ok = c.channel == "After-hours"
        elif choice and choice != "All":
            disp_ok = c.disposition == choice
        else:
            disp_ok = True
        text = f"{c.call_id} {c.caller} {c.case_type} {c.summary}".lower()
        return disp_ok and (q in text if q else True)

    visible = [c for c in calls if keep(c)]
    ids = [c.call_id for c in visible]
    caller_by_id = {c.call_id: c.caller for c in calls}

    selected = st.multiselect(
        "Select calls for bulk actions", ids,
        format_func=lambda i: f"{i}  ·  {caller_by_id.get(i, '')}",
        label_visibility="collapsed", placeholder="Select calls for bulk actions…",
        key="calls_sel",
    )
    sel_set = {i for i in selected if i in ids}

    if sel_set:
        st.markdown(
            f'<div class="actionbar"><span class="cnt">{len(sel_set)}</span> selected</div>',
            unsafe_allow_html=True,
        )
        b1, b2, b3, _ = st.columns([1, 1.2, 1, 4])
        if b1.button("Add to Lab", key="bulk_lab"):
            st.session_state.lab_ids |= sel_set
            st.toast(f"Added {len(sel_set)} call(s) to Lab", icon="✅")
            st.rerun()
        if b2.button("Create Simulation", key="bulk_sim"):
            st.session_state.sim_ids |= sel_set
            st.toast(f"Created simulation from {len(sel_set)} call(s)", icon="✅")
            st.rerun()
        if b3.button("Delete", key="bulk_del", type="primary"):
            st.session_state.deleted_ids |= sel_set
            st.toast(f"Deleted {len(sel_set)} call(s)", icon="✅")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Table ──
    rows = []
    for c in visible:
        on = "on" if c.call_id in sel_set else ""
        selcls = "sel" if c.call_id in sel_set else ""
        lang_tag = "🌐 ES" if c.language == "Spanish" else "EN"
        sc = GREEN_TX if c.score >= 90 else (AMBER_TX if c.score >= 85 else MUTE)
        labtag = '<span class="labtag">Lab</span>' if c.call_id in lab_ids else ""
        rows.append(
            f"""
<tr class="{selcls}">
  <td><span class="cbx {on}"></span></td>
  <td>
    <details class="rowmenu"><summary>{ICONS['dots']}</summary>
      <div class="menu">
        <div class="mh">Actions</div>
        <a href="?page=calls&f={FILTER}&act=lab&cid={c.call_id}" target="_self">{ICONS['flask']} Add to Lab</a>
        <a href="?page=calls&f={FILTER}&act=sim&cid={c.call_id}" target="_self">{ICONS['globe']} Create a Simulation</a>
        <a href="?page=calls&f={FILTER}&act=delete&cid={c.call_id}" target="_self" class="danger">{ICONS['trash']} Delete</a>
      </div>
    </details>
  </td>
  <td><span class="cell-id"><span>{c.call_id}</span></span> <span class="copy">{ICONS['copy']}</span>{labtag}</td>
  <td style="white-space:nowrap">{c.started_at}</td>
  <td><div class="caller">{c.caller}<small>{c.phone}</small></div></td>
  <td>{c.case_type}</td>
  <td>{disposition_badge(c.disposition)}</td>
  <td><span class="score" style="color:{sc}">{c.score}</span></td>
  <td style="font-variant-numeric:tabular-nums">{c.duration}</td>
  <td><span class="tag">{c.channel}</span></td>
  <td><span class="tag">{lang_tag}</span></td>
</tr>"""
        )

    empty = (
        f'<tr><td colspan="11" style="text-align:center;color:{MUTE};padding:40px">'
        f'No calls match your filters.</td></tr>'
    )
    st.markdown(
        f"""
<div class="page" style="padding-top:0">
  <div class="tbl-wrap">
    <table class="dt">
      <thead><tr>
        <th style="width:34px"></th>
        <th style="width:34px"></th>
        <th>Call ID</th><th>Time</th><th>Caller</th><th>Case type</th>
        <th>Disposition</th><th>Score</th><th>Duration</th><th>Channel</th><th>Lang</th>
      </tr></thead>
      <tbody>{''.join(rows) if rows else empty}</tbody>
    </table>
  </div>
  <div style="font-size:12.5px;color:{MUTE};margin-top:10px">
    Showing {len(visible)} of {k['total']} calls{' · ' + str(len(deleted)) + ' deleted this session' if deleted else ''}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════════════════════
# PAGE: Overview
# ════════════════════════════════════════════════════════════════════════════
def page_overview() -> None:
    today = get_today()
    week = get_week()
    funnel = get_funnel()
    declines = get_decline_reasons()
    hours, days, heat = get_call_heatmap()
    pipeline = estimated_pipeline(week.qualified_leads)
    qual_rate = today.qualified / today.total_calls * 100 if today.total_calls else 0
    ah_pct = today.after_hours_calls / today.total_calls * 100 if today.total_calls else 0

    st.markdown(
        f"""
<div class="page">
  <div class="kpis">
    <div class="kpi"><div class="lbl">Today's calls</div><div class="val">{today.total_calls}</div><div class="delta">{today.business_hours_calls} business · {today.after_hours_calls} after-hours</div></div>
    <div class="kpi"><div class="lbl">Qualified</div><div class="val accent">{today.qualified}</div><div class="delta up">↑ {qual_rate:.0f}% qualification rate</div></div>
    <div class="kpi"><div class="lbl">After-hours share</div><div class="val">{ah_pct:.0f}%</div><div class="delta">{today.after_hours_qualified} qualified after-hours</div></div>
    <div class="kpi"><div class="lbl">Weekly qualified</div><div class="val accent">{week.qualified_leads}</div><div class="delta up">↑ +12% vs last week</div></div>
    <div class="kpi"><div class="lbl">Est. pipeline</div><div class="val">{format_currency(pipeline)}</div><div class="delta">{week.qualified_leads} × {format_currency(AVG_CASE_VALUE)} avg</div></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div style="padding:0 28px;max-width:1320px">', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.15], gap="medium")
    with c1:
        st.markdown('<div class="panel"><div class="eyebrow">This week</div><h3>Conversion funnel</h3>'
                    '<p class="cap">Call → qualified → consultation → retainer</p>', unsafe_allow_html=True)
        fig = go.Figure(go.Funnel(
            y=[s.label for s in funnel], x=[s.count for s in funnel],
            textinfo="value", textfont=dict(color="#fff", size=15, family=FONT),
            marker=dict(color=["#d4d4d4", "#a3a3a3", "#525252", ACCENT]),
            connector=dict(line=dict(color=HAIRLINE, width=1)),
        ))
        fig.update_layout(**light_layout(height=300))
        st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="panel"><div class="eyebrow">30 days</div><h3>Top decline reasons</h3>'
                    '<p class="cap">Why callers did not qualify</p>', unsafe_allow_html=True)
        fig = go.Figure(go.Pie(
            labels=list(declines.keys()), values=list(declines.values()), hole=0.6,
            marker=dict(colors=RAMP, line=dict(color=CANVAS, width=2)),
            textinfo="value", textfont=dict(color="#fff", size=13),
            hovertemplate="%{label}<br>%{value} calls (%{percent})<extra></extra>",
        ))
        fig.update_layout(**light_layout(height=300), showlegend=True,
                          legend=dict(font=dict(size=11, color=MUTE), x=1.0, y=0.5))
        st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><div class="eyebrow">Volume</div><h3>Call heatmap</h3>'
                '<p class="cap">Hour blocks × day of week — evening & weekend peaks</p>', unsafe_allow_html=True)
    fig = go.Figure(go.Heatmap(
        z=heat, x=days, y=hours, xgap=2, ygap=2,
        colorscale=[[0, "#fafafa"], [0.35, "#d4d4d4"], [0.7, "#737373"], [1, ACCENT]],
        hovertemplate="%{y} · %{x}<br>%{z} calls<extra></extra>",
        colorbar=dict(tickfont=dict(color=MUTE), outlinewidth=0, thickness=10),
    ))
    fig.update_layout(**light_layout(height=360),
                      xaxis=dict(side="top", tickfont=dict(color=MUTE)),
                      yaxis=dict(autorange="reversed", tickfont=dict(color=MUTE)))
    st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)
    st.markdown("</div></div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: Metrics
# ════════════════════════════════════════════════════════════════════════════
def page_metrics() -> None:
    scores = VERSION_SCORES if HAS_SIM else {"v1": 62, "v2": 77, "v3": 89}
    st.markdown(
        f"""
<div class="page">
  <div class="kpis">
    <div class="kpi"><div class="lbl">Qualification accuracy</div><div class="val accent">{scores['v3']}%</div><div class="delta up">↑ +{scores['v3']-scores['v1']}pp vs v1</div></div>
    <div class="kpi"><div class="lbl">Median latency</div><div class="val">740ms</div><div class="delta up">↓ -180ms vs v1</div></div>
    <div class="kpi"><div class="lbl">Avg call duration</div><div class="val">5:24</div><div class="delta">Across qualified calls</div></div>
    <div class="kpi"><div class="lbl">Containment</div><div class="val">82%</div><div class="delta">Handled without transfer</div></div>
    <div class="kpi"><div class="lbl">Eval pass rate</div><div class="val accent">{scores['v3']}%</div><div class="delta up">↑ trending up</div></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown('<div style="padding:0 28px;max-width:1320px">', unsafe_allow_html=True)
    c1, c2 = st.columns([1.15, 1], gap="medium")
    with c1:
        st.markdown('<div class="panel"><div class="eyebrow">Quality</div><h3>Score progression</h3>'
                    '<p class="cap">Aggregate evaluator score by prompt version</p>', unsafe_allow_html=True)
        versions = ["v1", "v2", "v3"]
        ys = [scores[v] for v in versions]
        fig = go.Figure(go.Scatter(
            x=versions, y=ys, mode="lines+markers+text",
            text=[f"{v}%" for v in ys], textposition="top center",
            textfont=dict(color=INK, size=13), line=dict(color=ACCENT, width=3),
            marker=dict(size=12, color=ACCENT),
        ))
        fig.update_layout(**light_layout(height=320),
                          yaxis=dict(range=[50, 100], gridcolor=HAIRLINE, tickfont=dict(color=MUTE)),
                          xaxis=dict(tickfont=dict(color=MUTE)))
        st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="panel"><div class="eyebrow">Latency</div><h3>Response time by version</h3>'
                    '<p class="cap">Median time-to-first-byte (ms)</p>', unsafe_allow_html=True)
        fig = go.Figure(go.Bar(
            x=["v1", "v2", "v3"], y=[920, 810, 740],
            marker=dict(color=["#d4d4d4", "#737373", ACCENT], cornerradius=8),
            text=["920", "810", "740"], textposition="outside", textfont=dict(color=INK, size=13), width=0.5,
        ))
        fig.update_layout(**light_layout(height=320), bargap=0.4,
                          yaxis=dict(gridcolor=HAIRLINE, tickfont=dict(color=MUTE)),
                          xaxis=dict(tickfont=dict(color=MUTE)))
        st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: Simulation Results
# ════════════════════════════════════════════════════════════════════════════
def page_results() -> None:
    if not HAS_SIM:
        st.markdown('<div class="page"><div class="panel">Simulation data unavailable.</div></div>',
                    unsafe_allow_html=True)
        return
    scores = VERSION_SCORES
    delta = round(scores["v3"] - scores["v1"], 1)
    st.markdown(
        f"""
<div class="page">
  <div class="kpis" style="grid-template-columns:repeat(4,1fr)">
    <div class="kpi"><div class="lbl">v1 baseline</div><div class="val">{scores['v1']}%</div><div class="delta">Initial prompt</div></div>
    <div class="kpi"><div class="lbl">v2</div><div class="val">{scores['v2']}%</div><div class="delta up">↑ SoL + empathy</div></div>
    <div class="kpi"><div class="lbl">v3 current</div><div class="val accent">{scores['v3']}%</div><div class="delta up">↑ Spanish + fault logic</div></div>
    <div class="kpi"><div class="lbl">Total gain</div><div class="val accent">+{delta}pp</div><div class="delta up">10 personas · 10 evaluators</div></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown('<div style="padding:0 28px;max-width:1320px">', unsafe_allow_html=True)
    st.markdown('<div class="panel"><div class="eyebrow">Latest run</div><h3>Per-persona evaluator heatmap (v3)</h3>'
                '<p class="cap">Each cell = one evaluator graded against one caller persona</p>', unsafe_allow_html=True)
    sel = SCORES_V3
    fig = go.Figure(go.Heatmap(
        z=sel, x=EVALUATORS, y=[p[:26] for p in PERSONAS],
        colorscale=[[0, RED_BG], [0.5, AMBER_BG], [1, "#86efac"]], zmin=0, zmax=1,
        xgap=3, ygap=3, showscale=False,
        hovertemplate="%{y}<br>%{x}: %{z}<extra></extra>",
    ))
    ann = []
    for i in range(len(PERSONAS)):
        for j in range(len(EVALUATORS)):
            v = sel[i][j]
            sym = "✓" if v == 1 else ("~" if v == 0.5 else "✗")
            col = GREEN_TX if v == 1 else (AMBER_TX if v == 0.5 else RED_TX)
            ann.append(dict(x=j, y=i, text=sym, showarrow=False, font=dict(color=col, size=12)))
    fig.update_layout(**light_layout(height=440), annotations=ann,
                      xaxis=dict(tickangle=-35, side="bottom", tickfont=dict(color=MUTE, size=10)),
                      yaxis=dict(tickfont=dict(color=MUTE, size=11)))
    st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div style="height:16px"></div><div class="panel"><h3>Version notes</h3>', unsafe_allow_html=True)
    badge = {"v1": (ACCENT_SOFT, MUTE), "v2": (ACCENT_SOFT, BODY), "v3": (GREEN_BG, GREEN_TX)}
    for v, note in VERSION_NOTES.items():
        bg, tx = badge[v]
        st.markdown(
            f'<div class="listrow"><div><span class="badge" style="background:{bg};color:{tx}">{v}</span>'
            f'<span class="d" style="margin-top:6px">{note}</span></div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div></div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: Personality / Evaluator / Runs (simple list pages)
# ════════════════════════════════════════════════════════════════════════════
def page_personality() -> None:
    items = PERSONAS if HAS_SIM else []
    st.markdown('<div class="page"><div class="sectitle">Caller personas</div>', unsafe_allow_html=True)
    for i, p in enumerate(items, 1):
        st.markdown(
            f'<div class="listrow"><div><div class="t">{p}</div>'
            f'<div class="d">Synthetic caller · used across simulation runs</div></div>'
            f'<span class="tag">persona {i:02d}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def page_evaluator() -> None:
    items = EVALUATORS if HAS_SIM else []
    st.markdown('<div class="page"><div class="sectitle">Evaluators</div>', unsafe_allow_html=True)
    for ev in items:
        st.markdown(
            f'<div class="listrow"><div><div class="t">{ev}</div>'
            f'<div class="d">Pass / partial / fail · graded on every call</div></div>'
            f'<span class="badge" style="background:{GREEN_BG};color:{GREEN_TX}">active</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def page_runs() -> None:
    runs = [
        ("run_0188", "Nov 4 · 2:10 PM", "v3", "89%", "Qualified", "Completed"),
        ("run_0187", "Nov 3 · 6:42 PM", "v3", "88%", "Mixed", "Completed"),
        ("run_0181", "Nov 2 · 11:05 AM", "v2", "77%", "Mixed", "Completed"),
        ("run_0166", "Oct 30 · 9:20 AM", "v1", "62%", "Baseline", "Completed"),
    ]
    rows = "".join(
        f"""<tr><td><span class="cell-id"><span>{r[0]}</span></span></td><td>{r[1]}</td>
        <td><span class="vbadge">{r[2]}</span></td><td><span class="score" style="color:{GREEN_TX}">{r[3]}</span></td>
        <td>{r[4]}</td><td>{disposition_badge('Qualified') if r[5]=='Completed' else r[5]}</td></tr>"""
        for r in runs
    )
    st.markdown(
        f"""
<div class="page"><div class="sectitle">Simulation runs</div>
  <div class="tbl-wrap"><table class="dt">
    <thead><tr><th>Run ID</th><th>Started</th><th>Version</th><th>Score</th><th>Outcome</th><th>Status</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
</div>
""",
        unsafe_allow_html=True,
    )


def page_labs() -> None:
    _init_state()
    lab_ids = st.session_state.lab_ids
    all_calls = get_calls()
    if lab_ids:
        calls = [c for c in all_calls if c.call_id in lab_ids]
        note = "Calls you staged from the Calls table. They become regression tests against future prompt versions."
    else:
        calls = [c for c in all_calls if c.disposition != "Qualified"][:4]
        note = "Example staged calls. Use the row menu on the Calls page to add your own."
    st.markdown(f'<div class="page"><div class="sectitle">Labs — staged for replay</div>'
                f'<p class="cap" style="margin-bottom:16px">{note}</p>',
                unsafe_allow_html=True)
    for c in calls:
        st.markdown(
            f'<div class="listrow"><div><div class="t">{c.caller} · {c.case_type}</div>'
            f'<div class="d">{c.call_id} · {c.summary}</div></div>{disposition_badge(c.disposition)}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: Home / Agent Settings
# ════════════════════════════════════════════════════════════════════════════
def page_home() -> None:
    today = get_today()
    week = get_week()
    pipeline = estimated_pipeline(week.qualified_leads)
    st.markdown(
        f"""
<div class="page">
  <div class="panel" style="margin-bottom:18px;background:linear-gradient(180deg,#fafafa,#ffffff);border-color:{HAIRLINE}">
    <div class="eyebrow">Welcome back</div>
    <h3 style="font-size:22px">{AGENT_NAME} handled {today.total_calls} calls today</h3>
    <p class="cap">{today.qualified} qualified · {today.after_hours_calls} after-hours · {format_currency(pipeline)} in estimated weekly pipeline.
    Running {AGENT_VERSION} on {AGENT_PROVIDER}.</p>
  </div>
  <div class="kpis">
    <div class="kpi"><div class="lbl">Calls today</div><div class="val">{today.total_calls}</div></div>
    <div class="kpi"><div class="lbl">Qualified</div><div class="val accent">{today.qualified}</div></div>
    <div class="kpi"><div class="lbl">After-hours</div><div class="val">{today.after_hours_calls}</div></div>
    <div class="kpi"><div class="lbl">Weekly qualified</div><div class="val accent">{week.qualified_leads}</div></div>
    <div class="kpi"><div class="lbl">Est. pipeline</div><div class="val">{format_currency(pipeline)}</div></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def page_agent() -> None:
    rows = [
        ("Agent name", AGENT_NAME),
        ("Firm", f"{FIRM} — {st.session_state.get('firm_tagline', FIRM_TAGLINE)}"),
        ("Active version", AGENT_VERSION),
        ("Orchestration", "Pipecat Cloud"),
        ("LLM", "NVIDIA Nemotron 3 Super 120B"),
        ("Speech-to-text", "Nemotron Speech Streaming"),
        ("Text-to-speech", "Gradium"),
        ("Telephony", "Twilio (after-hours overflow + dedicated line)"),
        ("Languages", "English, Spanish (bilingual handoff)"),
        ("Practice area", "Personal injury — auto, slip & fall, dog bite, motorcycle"),
        ("Qualification policy", "Injury + treatment + within SoL + not represented"),
    ]
    kv = "".join(f'<div class="k">{k}</div><div class="v">{v}</div>' for k, v in rows)
    st.markdown(
        f"""
<div class="page">
  <div class="panel">
    <div class="eyebrow">Configuration</div>
    <h3>Agent settings</h3>
    <p class="cap" style="margin-bottom:10px">Read-only summary of the deployed intake agent.</p>
    <div class="kv">{kv}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════════════════════
# PUBLIC: marketing CSS + landing + sign-up journey
# ════════════════════════════════════════════════════════════════════════════
LP_ACCENT = "#6366f1"
LP_ACCENT_2 = "#a855f7"


def _md(s: str, **_kwargs: object) -> None:
    """Render raw HTML, stripping per-line indentation so Markdown
    never reinterprets indented HTML as a code block.

    Extra kwargs (e.g. ``unsafe_allow_html``) are accepted and ignored so
    call sites can mirror ``st.markdown``'s signature."""
    st.markdown("\n".join(line.lstrip() for line in s.splitlines()), unsafe_allow_html=True)


def public_css() -> None:
    st.markdown(
        f"""
<style>
[data-testid="stSidebar"] {{ display:none !important; }}
[data-testid="stMain"] {{ background:{CANVAS}; }}

.lp {{ font-family:{FONT}; color:{INK}; }}
.lp a {{ text-decoration:none; }}

/* ── Dark hero block ── */
.lp-dark {{
  position:relative; background:#070708; color:#fafafa; overflow:hidden;
  padding:0 24px 90px; margin-bottom:0;
}}
.lp-dark::before {{
  content:""; position:absolute; inset:0; pointer-events:none;
  background:
    radial-gradient(60% 50% at 50% -8%, rgba(99,102,241,0.35), transparent 60%),
    radial-gradient(40% 40% at 85% 10%, rgba(168,85,247,0.22), transparent 60%),
    radial-gradient(45% 45% at 12% 20%, rgba(56,189,248,0.14), transparent 60%);
}}
.lp-dark::after {{
  content:""; position:absolute; inset:0; pointer-events:none; opacity:.5;
  background-image:linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
                   linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
  background-size:54px 54px;
  -webkit-mask-image:radial-gradient(70% 60% at 50% 0%, #000, transparent 75%);
          mask-image:radial-gradient(70% 60% at 50% 0%, #000, transparent 75%);
}}
.lp-inner {{ position:relative; z-index:2; max-width:1120px; margin:0 auto; }}

/* nav */
.lp-nav {{ display:flex; align-items:center; justify-content:space-between; padding:20px 4px; }}
.lp-brand {{ display:flex; align-items:center; gap:10px; font-weight:600; font-size:16px; color:#fff; letter-spacing:-0.02em; }}
.lp-logo {{ width:30px; height:30px; border-radius:8px; display:flex; align-items:center; justify-content:center;
  font-weight:700; font-size:13px; color:#fff; background:linear-gradient(135deg,{LP_ACCENT},{LP_ACCENT_2});
  box-shadow:0 4px 16px rgba(99,102,241,0.5); }}
.lp-navlinks {{ display:flex; gap:28px; align-items:center; }}
.lp-navlinks a {{ color:#c7c7d1; font-size:14px; font-weight:500; transition:color .15s; }}
.lp-navlinks a:hover {{ color:#fff; }}
.lp-navcta {{ display:flex; gap:10px; align-items:center; }}
.lp-btn {{ display:inline-flex; align-items:center; gap:8px; font-size:14px; font-weight:600;
  padding:9px 18px; border-radius:10px; transition:transform .15s, box-shadow .2s, background .2s; cursor:pointer; }}
.lp-btn-ghost {{ color:#e7e7ee; }}
.lp-btn-ghost:hover {{ color:#fff; }}
.lp-btn-light {{ background:#fff; color:#0a0a0a; }}
.lp-btn-light:hover {{ transform:translateY(-1px); box-shadow:0 10px 30px rgba(255,255,255,0.18); }}
.lp-btn-grad {{ color:#fff; background:linear-gradient(135deg,{LP_ACCENT},{LP_ACCENT_2}); box-shadow:0 8px 26px rgba(99,102,241,0.45); }}
.lp-btn-grad:hover {{ transform:translateY(-1px); box-shadow:0 12px 36px rgba(99,102,241,0.6); }}
.lp-btn-lg {{ font-size:15px; padding:13px 24px; }}

/* hero */
.lp-hero {{ text-align:center; padding:54px 0 12px; }}
.lp-pill {{ display:inline-flex; align-items:center; gap:8px; font-size:13px; font-weight:500; color:#d7d7e6;
  background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); padding:6px 14px; border-radius:9999px; margin-bottom:26px; }}
.lp-pill .gd {{ width:7px; height:7px; border-radius:50%; background:#34d399; box-shadow:0 0 10px #34d399; }}
.lp-hero h1 {{ font-size:clamp(40px,6.4vw,74px); line-height:1.03; font-weight:600; letter-spacing:-0.035em; margin:0 0 22px; }}
.lp-grad {{ background:linear-gradient(120deg,#a5b4fc,#c084fc 60%,#f0abfc); -webkit-background-clip:text; background-clip:text; color:transparent; }}
.lp-sub {{ font-size:19px; line-height:1.6; color:#b4b4c2; max-width:620px; margin:0 auto 34px; }}
.lp-herocta {{ display:flex; gap:14px; justify-content:center; align-items:center; flex-wrap:wrap; }}
.lp-trust {{ margin-top:26px; font-size:13px; color:#83838f; }}

/* product mock */
.lp-mockwrap {{ position:relative; z-index:2; max-width:1040px; margin:54px auto -150px; padding:0 12px; }}
.lp-window {{ background:#0f0f12; border:1px solid rgba(255,255,255,0.1); border-radius:16px; overflow:hidden;
  box-shadow:0 40px 120px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04); }}
.lp-bar {{ display:flex; align-items:center; gap:7px; padding:12px 16px; border-bottom:1px solid rgba(255,255,255,0.08); }}
.lp-bar .d {{ width:11px; height:11px; border-radius:50%; }}
.lp-shot {{ display:grid; grid-template-columns:200px 1fr; background:#fff; }}
.lp-msb {{ background:{SIDEBAR_BG}; border-right:1px solid {HAIRLINE}; padding:16px 12px; }}
.lp-msb .b {{ display:flex; align-items:center; gap:9px; font-weight:600; font-size:13px; color:{INK}; margin-bottom:16px; }}
.lp-msb .b i {{ width:24px; height:24px; border-radius:7px; background:linear-gradient(135deg,{LP_ACCENT},{LP_ACCENT_2}); display:inline-block; }}
.lp-msb .it {{ font-size:12.5px; color:{MUTE}; padding:7px 9px; border-radius:7px; margin-bottom:3px; }}
.lp-msb .it.on {{ background:#eceef1; color:{INK}; font-weight:600; }}
.lp-msc {{ padding:20px; }}
.lp-mkpis {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:16px; }}
.lp-mk {{ border:1px solid {HAIRLINE}; border-radius:11px; padding:13px 15px; }}
.lp-mk .l {{ font-size:9.5px; font-weight:600; letter-spacing:.5px; text-transform:uppercase; color:{MUTE}; }}
.lp-mk .v {{ font-size:24px; font-weight:700; letter-spacing:-0.03em; color:{INK}; margin-top:5px; }}
.lp-mk .v.a {{ color:{LP_ACCENT}; }}
.lp-mtbl {{ border:1px solid {HAIRLINE}; border-radius:11px; overflow:hidden; }}
.lp-mtbl .r {{ display:grid; grid-template-columns:1.3fr 1fr 1fr .8fr; gap:8px; padding:11px 14px; font-size:12px; color:{BODY}; border-bottom:1px solid {HAIRLINE_SOFT}; align-items:center; }}
.lp-mtbl .r.h {{ background:{CANVAS_SOFT}; font-size:9.5px; font-weight:600; letter-spacing:.5px; text-transform:uppercase; color:{MUTE}; }}
.lp-mtbl .r:last-child {{ border-bottom:none; }}
.lp-mid {{ font-family:{FONT_MONO}; font-size:11px; background:{CANVAS_SOFT}; border:1px solid {HAIRLINE}; border-radius:6px; padding:3px 7px; display:inline-block; }}
.lp-mbadge {{ font-size:10.5px; font-weight:600; padding:2px 8px; border-radius:9999px; }}

/* ── Light sections ── */
.lp-section {{ max-width:1120px; margin:0 auto; padding:96px 24px; }}
.lp-eyebrow {{ font-size:12.5px; font-weight:700; letter-spacing:1.4px; text-transform:uppercase;
  background:linear-gradient(120deg,{LP_ACCENT},{LP_ACCENT_2}); -webkit-background-clip:text; background-clip:text; color:transparent; }}
.lp-h2 {{ font-size:clamp(30px,4vw,44px); font-weight:600; letter-spacing:-0.03em; margin:12px 0 14px; color:{INK}; }}
.lp-lead {{ font-size:18px; color:{MUTE}; max-width:600px; line-height:1.6; }}
.lp-center {{ text-align:center; }}
.lp-center .lp-lead {{ margin:0 auto; }}

.lp-stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:20px; padding:56px 24px;
  max-width:1120px; margin:0 auto; border-top:1px solid {HAIRLINE}; border-bottom:1px solid {HAIRLINE}; }}
.lp-stat .n {{ font-size:42px; font-weight:700; letter-spacing:-0.04em;
  background:linear-gradient(120deg,{INK},#525252); -webkit-background-clip:text; background-clip:text; color:transparent; }}
.lp-stat .l {{ font-size:14px; color:{MUTE}; margin-top:6px; }}

.lp-feats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:18px; margin-top:46px; }}
.lp-feat {{ border:1px solid {HAIRLINE}; border-radius:16px; padding:26px; background:{CANVAS}; transition:transform .2s, box-shadow .25s, border-color .2s; }}
.lp-feat:hover {{ transform:translateY(-4px); box-shadow:0 20px 50px rgba(10,10,10,0.08); border-color:#d8d8d8; }}
.lp-feat .ic {{ width:42px; height:42px; border-radius:11px; display:flex; align-items:center; justify-content:center; color:#fff;
  background:linear-gradient(135deg,{LP_ACCENT},{LP_ACCENT_2}); box-shadow:0 8px 22px rgba(99,102,241,0.35); margin-bottom:16px; }}
.lp-feat h3 {{ font-size:18px; font-weight:600; letter-spacing:-0.01em; margin:0 0 7px; color:{INK}; }}
.lp-feat p {{ font-size:14.5px; line-height:1.6; color:{MUTE}; margin:0; }}

.lp-steps {{ display:grid; grid-template-columns:repeat(3,1fr); gap:34px; margin-top:46px; }}
.lp-step {{ position:relative; }}
.lp-step .num {{ width:40px; height:40px; border-radius:11px; display:flex; align-items:center; justify-content:center;
  font-weight:700; font-size:16px; color:{INK}; background:{CANVAS_SOFT}; border:1px solid {HAIRLINE}; margin-bottom:16px; }}
.lp-step h3 {{ font-size:18px; font-weight:600; margin:0 0 7px; color:{INK}; }}
.lp-step p {{ font-size:14.5px; line-height:1.6; color:{MUTE}; margin:0; }}

.lp-quote {{ max-width:860px; margin:0 auto; text-align:center; }}
.lp-quote p {{ font-size:clamp(22px,3vw,30px); font-weight:500; letter-spacing:-0.02em; line-height:1.4; color:{INK}; }}
.lp-quote .who {{ margin-top:22px; font-size:14px; color:{MUTE}; }}

.lp-ctaband {{ position:relative; overflow:hidden; background:#070708; border-radius:24px; padding:64px 32px; text-align:center; }}
.lp-ctaband::before {{ content:""; position:absolute; inset:0;
  background:radial-gradient(60% 120% at 50% 0%, rgba(99,102,241,0.4), transparent 60%),
             radial-gradient(50% 120% at 80% 100%, rgba(168,85,247,0.3), transparent 60%); }}
.lp-ctaband > * {{ position:relative; z-index:2; }}
.lp-ctaband h2 {{ font-size:clamp(28px,4vw,44px); font-weight:600; letter-spacing:-0.03em; color:#fff; margin:0 0 14px; }}
.lp-ctaband p {{ font-size:17px; color:#b4b4c2; margin:0 auto 28px; max-width:520px; }}

.lp-footer {{ border-top:1px solid {HAIRLINE}; }}
.lp-footin {{ max-width:1120px; margin:0 auto; padding:40px 24px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:16px; }}
.lp-footin .c {{ font-size:13px; color:{MUTE}; }}
.lp-footlinks {{ display:flex; gap:22px; }}
.lp-footlinks a {{ font-size:13px; color:{MUTE}; }}
.lp-footlinks a:hover {{ color:{INK}; }}

/* ── Auth split layout ── */
.lp-auth {{ display:grid; grid-template-columns:1.05fr 1fr; min-height:100vh; }}
@media (max-width:900px) {{ .lp-auth {{ grid-template-columns:1fr; }} .lp-authleft {{ display:none; }} }}
.lp-authleft {{ position:relative; background:#070708; color:#fafafa; padding:48px; overflow:hidden; }}
.lp-authleft::before {{ content:""; position:absolute; inset:0;
  background:radial-gradient(50% 50% at 30% 15%, rgba(99,102,241,0.35), transparent 60%),
             radial-gradient(40% 40% at 90% 80%, rgba(168,85,247,0.25), transparent 60%); }}
.lp-authleft > * {{ position:relative; z-index:2; }}
.lp-authleft h2 {{ font-size:34px; font-weight:600; letter-spacing:-0.03em; line-height:1.15; margin:28px 0 16px; }}
.lp-vp {{ display:flex; gap:13px; align-items:flex-start; margin-bottom:16px; font-size:15px; color:#cfcfda; }}
.lp-vp .ck {{ flex-shrink:0; width:22px; height:22px; border-radius:6px; background:rgba(255,255,255,0.1);
  display:flex; align-items:center; justify-content:center; color:#a5b4fc; }}
.lp-authright {{ padding:48px 40px; display:flex; flex-direction:column; justify-content:center; max-width:560px; }}
.lp-steps-dots {{ display:flex; gap:8px; margin-bottom:22px; }}
.lp-dot {{ height:5px; border-radius:9999px; background:{HAIRLINE}; flex:1; transition:background .2s; }}
.lp-dot.on {{ background:linear-gradient(90deg,{LP_ACCENT},{LP_ACCENT_2}); }}
.lp-authright .step-lbl {{ font-size:12.5px; font-weight:600; color:{LP_ACCENT}; letter-spacing:.4px; text-transform:uppercase; }}
.lp-authright h1 {{ font-size:27px; font-weight:600; letter-spacing:-0.03em; margin:8px 0 6px; color:{INK}; }}
.lp-authright .desc {{ font-size:15px; color:{MUTE}; margin-bottom:8px; }}
.lp-finish {{ text-align:center; padding:20px 0; }}
.lp-finish .big {{ width:64px; height:64px; border-radius:18px; margin:0 auto 20px; display:flex; align-items:center; justify-content:center;
  color:#fff; font-size:30px; background:linear-gradient(135deg,{LP_ACCENT},{LP_ACCENT_2}); box-shadow:0 14px 36px rgba(99,102,241,0.45); }}
</style>
""",
        unsafe_allow_html=True,
    )


def _check_icon() -> str:
    return _icon('<path d="M20 6L9 17l-5-5"/>')


def page_landing() -> None:
    public_css()
    fc_logo = "FC"
    # ── Dark hero + product mock ──
    _md(
        f"""
<div class="lp">
<div class="lp-dark">
  <div class="lp-inner">
    <nav class="lp-nav">
      <div class="lp-brand"><span class="lp-logo">{fc_logo}</span> FirstCall</div>
      <div class="lp-navlinks">
        <a href="#features">Features</a>
        <a href="#how">How it works</a>
        <a href="#pricing">Pricing</a>
        <a href="?page=signin" target="_self">Sign in</a>
      </div>
      <div class="lp-navcta">
        <a class="lp-btn lp-btn-grad" href="?page=signup" target="_self">Get started</a>
      </div>
    </nav>

    <div class="lp-hero">
      <div class="lp-pill"><span class="gd"></span> Now answering in English &amp; Spanish · 24/7</div>
      <h1>Never miss a case.<br>Your firm's intake,<br><span class="lp-grad">answered by AI.</span></h1>
      <p class="lp-sub">FirstCall picks up every call — day, night, and weekend — qualifies the lead,
      checks the statute of limitations, and books the consult. So your firm only talks to cases worth taking.</p>
      <div class="lp-herocta">
        <a class="lp-btn lp-btn-light lp-btn-lg" href="?page=signup" target="_self">Start free trial →</a>
        <a class="lp-btn lp-btn-ghost lp-btn-lg" href="#how">See how it works</a>
      </div>
      <div class="lp-trust">No credit card required · Live in under 10 minutes · Trusted by 200+ PI firms</div>
    </div>
  </div>

  <div class="lp-mockwrap">
    <div class="lp-window">
      <div class="lp-bar">
        <span class="d" style="background:#ff5f57"></span>
        <span class="d" style="background:#febc2e"></span>
        <span class="d" style="background:#28c840"></span>
      </div>
      <div class="lp-shot">
        <div class="lp-msb">
          <div class="b"><i></i> FirstCall</div>
          <div class="it">Home</div>
          <div class="it">Metrics</div>
          <div class="it">Results</div>
          <div class="it on">Calls</div>
          <div class="it">Overview</div>
        </div>
        <div class="lp-msc">
          <div class="lp-mkpis">
            <div class="lp-mk"><div class="l">Calls today</div><div class="v">23</div></div>
            <div class="lp-mk"><div class="l">Qualified</div><div class="v a">14</div></div>
            <div class="lp-mk"><div class="l">After-hours</div><div class="v">11</div></div>
          </div>
          <div class="lp-mtbl">
            <div class="r h"><span>Caller</span><span>Case type</span><span>Disposition</span><span>Score</span></div>
            <div class="r"><span>Maria Delgado</span><span>Auto accident</span><span><span class="lp-mbadge" style="background:{GREEN_BG};color:{GREEN_TX}">Qualified</span></span><span>96</span></div>
            <div class="r"><span>James Okafor</span><span>Slip &amp; fall</span><span><span class="lp-mbadge" style="background:{GREEN_BG};color:{GREEN_TX}">Qualified</span></span><span>91</span></div>
            <div class="r"><span>Priya Nair</span><span>Auto accident</span><span><span class="lp-mbadge" style="background:{RED_BG};color:{RED_TX}">Declined</span></span><span>88</span></div>
            <div class="r"><span>Carlos Mendoza</span><span>Auto · ES</span><span><span class="lp-mbadge" style="background:{GREEN_BG};color:{GREEN_TX}">Qualified</span></span><span>94</span></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<div style="height:170px"></div>

<!-- stats -->
<div class="lp-stats">
  <div class="lp-stat"><div class="n">24/7</div><div class="l">Always answering, never on hold</div></div>
  <div class="lp-stat"><div class="n">3.2×</div><div class="l">More qualified leads captured</div></div>
  <div class="lp-stat"><div class="n">&lt;1s</div><div class="l">Average response latency</div></div>
  <div class="lp-stat"><div class="n">$4,200</div><div class="l">Saved monthly vs. answering services</div></div>
</div>

<!-- features -->
<div class="lp-section" id="features">
  <div class="lp-eyebrow">Built for plaintiff firms</div>
  <div class="lp-h2">Everything your intake team does — automatically.</div>
  <p class="lp-lead">FirstCall isn't a generic chatbot. It's trained on personal-injury intake and graded on every call.</p>
  <div class="lp-feats">
    <div class="lp-feat"><div class="ic">{_icon('<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.6A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.6a16 16 0 0 0 6 6l1.1-1.1a2 2 0 0 1 2.1-.5c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>')}</div>
      <h3>After-hours capture</h3><p>Evenings, nights, and weekends — the calls that used to hit voicemail now become signed cases.</p></div>
    <div class="lp-feat"><div class="ic">{_check_icon()}</div>
      <h3>Instant qualification</h3><p>Confirms injury, treatment, fault, and representation, then scores the lead before it reaches your team.</p></div>
    <div class="lp-feat"><div class="ic">{_icon('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18z"/>')}</div>
      <h3>Bilingual intake</h3><p>Seamless English and Spanish handling with a warm handoff to your bilingual staff when needed.</p></div>
    <div class="lp-feat"><div class="ic">{_icon('<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/>')}</div>
      <h3>Statute-of-limitations checks</h3><p>Flags time-barred matters automatically so you stop wasting consults on cases you can't take.</p></div>
    <div class="lp-feat"><div class="ic">{_icon('<path d="M3 3v18h18"/><path d="M7 14l3-4 3 3 5-6"/>')}</div>
      <h3>Quality, measured</h3><p>Every conversation is evaluated and trended — see exactly how your intake improves over time.</p></div>
    <div class="lp-feat"><div class="ic">{_icon('<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>')}</div>
      <h3>Drops into your CRM</h3><p>Qualified leads, transcripts, and summaries flow straight to your inbox, Litify, or Clio.</p></div>
  </div>
</div>

<!-- how it works -->
<div class="lp-section" id="how" style="padding-top:0">
  <div class="lp-eyebrow">Live in minutes</div>
  <div class="lp-h2">Three steps to never missing a call.</div>
  <div class="lp-steps">
    <div class="lp-step"><div class="num">1</div><h3>Forward your number</h3><p>Point your after-hours or overflow line to FirstCall. No new hardware, no IT project.</p></div>
    <div class="lp-step"><div class="num">2</div><h3>AI answers &amp; qualifies</h3><p>FirstCall greets the caller, gathers the facts, screens the matter, and books the consult.</p></div>
    <div class="lp-step"><div class="num">3</div><h3>Qualified leads, delivered</h3><p>You wake up to scored, summarized, ready-to-sign cases — and a full audit trail.</p></div>
  </div>
</div>

<!-- testimonial -->
<div class="lp-section" style="padding-top:0">
  <div class="lp-quote">
    <p>“FirstCall booked four signed cases in its first weekend — calls we would have lost to voicemail. It paid for itself before Monday.”</p>
    <div class="who"><b>Dana Morrison</b> · Managing Partner, Morrison &amp; Associates</div>
  </div>
</div>

<!-- final CTA -->
<div class="lp-section" id="pricing" style="padding-top:0">
  <div class="lp-ctaband">
    <h2>Stop losing cases to voicemail.</h2>
    <p>Spin up your firm's AI intake line today. Free for 14 days — live before your next missed call.</p>
    <a class="lp-btn lp-btn-light lp-btn-lg" href="?page=signup" target="_self">Create your workspace →</a>
  </div>
</div>

<!-- footer -->
<div class="lp-footer"><div class="lp-footin">
  <div class="lp-brand" style="color:{INK}"><span class="lp-logo">{fc_logo}</span> FirstCall</div>
  <div class="c">© 2026 FirstCall AI · Built on Pipecat &amp; NVIDIA Nemotron</div>
  <div class="lp-footlinks"><a href="#features">Features</a><a href="#pricing">Pricing</a><a href="?page=signin" target="_self">Sign in</a></div>
</div></div>
</div>
"""
    )


PRACTICE_AREAS = ["Personal injury", "Auto accidents", "Medical malpractice",
                  "Workers' compensation", "Mass tort", "General practice"]
CALL_VOLUMES = ["Under 50 / month", "50–200 / month", "200–500 / month", "500+ / month"]
PLANS = ["Starter — $299/mo", "Growth — $799/mo", "Firm — Custom"]


def page_signup() -> None:
    public_css()
    if "signup_step" not in st.session_state:
        st.session_state.signup_step = 1
    step = st.session_state.signup_step
    total = 3

    left, right = st.columns([1.05, 1], gap="large")
    with left:
        vps = [
            "Live in under 10 minutes — just forward a number",
            "Answers 24/7 in English &amp; Spanish",
            "Only pay for the calls worth taking",
            "Free for 14 days · no credit card",
        ]
        vp_html = "".join(
            f'<div class="lp-vp"><span class="ck">{_check_icon()}</span><span>{v}</span></div>' for v in vps
        )
        _md(
            f"""
<div class="lp"><div class="lp-authleft" style="border-radius:16px;min-height:560px">
<div class="lp-brand"><span class="lp-logo">FC</span> FirstCall</div>
<h2>Give your firm an<br>intake team that<br>never sleeps.</h2>
{vp_html}
<div style="margin-top:34px;padding:16px 18px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:12px;font-size:14px;color:#cfcfda">
“We stopped losing weekend cases the day we switched on FirstCall.”<br>
<span style="color:#8f8f9c">— Dana Morrison, Managing Partner</span>
</div>
</div></div>
"""
        )

    with right:
        dots = "".join(f'<span class="lp-dot {"on" if i <= step else ""}"></span>' for i in range(1, total + 1))
        titles = {
            1: ("Create your account", "Tell us who you are."),
            2: ("About your firm", "We'll tune intake to your practice."),
            3: ("Route your calls", "Where should FirstCall pick up?"),
        }
        if step <= total:
            t, d = titles[step]
            st.markdown(
                f'<div class="lp"><div class="lp-authright" style="padding:8px 4px">'
                f'<div class="lp-steps-dots">{dots}</div>'
                f'<div class="step-lbl">Step {step} of {total}</div>'
                f'<h1>{t}</h1><div class="desc">{d}</div></div></div>',
                unsafe_allow_html=True,
            )

        if step == 1:
            st.text_input("Work email", placeholder="you@firm.com", key="su_email")
            st.text_input("Your full name", placeholder="Jane Advocate", key="su_name")
            st.text_input("Firm name", placeholder="Morrison & Associates", key="su_firm")
            c1, c2 = st.columns([1, 1])
            if c2.button("Continue →", type="primary", key="su_next1"):
                if st.session_state.get("su_firm"):
                    st.session_state.signup_step = 2
                    st.rerun()
                else:
                    st.warning("Please enter your firm name to continue.")
            c1.markdown(
                '<div class="lp" style="font-size:13px;color:#737373;padding-top:10px">Already have an account? '
                '<a href="?page=signin" target="_self" style="color:#6366f1;font-weight:600">Sign in</a></div>',
                unsafe_allow_html=True,
            )

        elif step == 2:
            st.selectbox("Primary practice area", PRACTICE_AREAS, key="su_area")
            st.text_input("States you practice in", placeholder="California, Nevada", key="su_states")
            st.selectbox("Monthly call volume", CALL_VOLUMES, index=1, key="su_volume")
            c1, c2 = st.columns([1, 1])
            if c1.button("← Back", key="su_back2"):
                st.session_state.signup_step = 1
                st.rerun()
            if c2.button("Continue →", type="primary", key="su_next2"):
                st.session_state.signup_step = 3
                st.rerun()

        elif step == 3:
            st.text_input("After-hours number to forward", placeholder="+1 (415) 555-0142", key="su_phone")
            st.selectbox("Choose a plan", PLANS, index=1, key="su_plan")
            st.checkbox("Forward only after business hours (recommended)", value=True, key="su_afterhours")
            c1, c2 = st.columns([1, 1])
            if c1.button("← Back", key="su_back3"):
                st.session_state.signup_step = 2
                st.rerun()
            if c2.button("Create workspace ✓", type="primary", key="su_finish"):
                st.session_state.authed = True
                st.session_state.firm_name = st.session_state.get("su_firm") or FIRM_NAME
                area = st.session_state.get("su_area", "Personal injury")
                states = st.session_state.get("su_states") or "California"
                st.session_state.firm_tagline = f"{area} · {states}"
                st.session_state.signup_step = 4
                st.rerun()

        else:  # finished
            firm = st.session_state.get("firm_name", FIRM_NAME)
            _md(
                f"""
<div class="lp"><div class="lp-authright" style="padding:8px 4px">
<div class="lp-finish">
<div class="big">✓</div>
<h1 style="text-align:center">Welcome to FirstCall, {firm}!</h1>
<div class="desc" style="text-align:center">Your AI intake workspace is ready. Forward your number and you're live.</div>
</div>
</div></div>
"""
            )
            _, mid, _ = st.columns([1, 2, 1])
            if mid.button("Enter your dashboard →", type="primary", key="su_enter"):
                st.session_state.pop("signup_step", None)
                st.query_params.clear()
                st.query_params["page"] = "home"
                st.rerun()


def page_signin() -> None:
    public_css()
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        _md(
            """
<div class="lp"><div class="lp-authleft" style="border-radius:16px;min-height:520px">
<div class="lp-brand"><span class="lp-logo">FC</span> FirstCall</div>
<h2>Welcome back.<br>Your cases are<br>waiting.</h2>
<div class="lp-vp"><span class="ck">✓</span><span>Every after-hours call, captured overnight</span></div>
<div class="lp-vp"><span class="ck">✓</span><span>Scored, summarized, ready to sign</span></div>
</div></div>
"""
        )
    with right:
        st.markdown(
            '<div class="lp"><div class="lp-authright" style="padding:8px 4px">'
            '<h1>Sign in to FirstCall</h1><div class="desc">Access your firm\'s intake dashboard.</div></div></div>',
            unsafe_allow_html=True,
        )
        st.text_input("Work email", placeholder="you@firm.com", key="si_email")
        st.text_input("Password", type="password", placeholder="••••••••", key="si_pw")
        if st.button("Sign in →", type="primary", key="si_go"):
            ok, err = auth.sign_in(
                st.session_state.get("si_email", ""), st.session_state.get("si_pw", "")
            )
            if ok:
                st.session_state.firm_name = FIRM_NAME
                st.query_params.clear()
                st.query_params["page"] = "calls"
                st.rerun()
            else:
                st.error(err or "Sign in failed.")
        st.markdown(
            '<div class="lp" style="font-size:13px;color:#737373;padding-top:10px">New to FirstCall? '
            '<a href="?page=signup" target="_self" style="color:#6366f1;font-weight:600">Create a workspace</a></div>',
            unsafe_allow_html=True,
        )


# ── Router ───────────────────────────────────────────────────────────────────
PUBLIC_ROUTES = {
    "landing": page_landing,
    "signup": page_signup,
    "signin": page_signin,
}

if PAGE in PUBLIC_PAGES:
    PUBLIC_ROUTES[PAGE]()
else:
    render_sidebar()
    topbar()
    ROUTES = {
        "home": page_home,
        "agent": page_agent,
        "metrics": page_metrics,
        "labs": page_labs,
        "personality": page_personality,
        "evaluator": page_evaluator,
        "results": page_results,
        "runs": page_runs,
        "calls": page_calls,
        "overview": page_overview,
    }
    ROUTES.get(PAGE, page_calls)()
