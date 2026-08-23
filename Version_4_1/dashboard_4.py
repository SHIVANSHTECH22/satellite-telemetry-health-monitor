"""
==============================================================================
 V4 — TELEMETRY VISUALIZATION DASHBOARD  (Mission Control Console)
 Satellite Telemetry Health Monitoring System
==============================================================================
Tabbed, no-scroll mission-control style dashboard, driven live off the
real V1/V2 telemetry CSV, replayed frame-by-frame from row 1 onward.

  OVERVIEW  — status cards, 3D ground-track tracker, instrument gauges
  GRAPHS    — thermal/power and bus/fuel strip charts
  MISSION REPORT — live exception registry, event log, V3 health overview

SMOOTH UPDATES: the whole data section runs inside a single st.fragment
with run_every=<speed>, so periodic playback ticks only redraw that
fragment — the sidebar, page chrome, and layout never get torn down and
rebuilt, which is what was causing the full-page "blink" before.

FIXES IN THIS VERSION:
  * Header/title now renders FIRST, transport bar sits directly below it.
  * Transport bar (RESET / PLAY-PAUSE / STEP + status) is STICKY — it stays
    pinned to the top of the viewport so controls are ALWAYS visible,
    even while scrolling or while playback is running.
  * Buttons get icons + forced high-contrast white-on-dark styling.
  * Plotly charts use uirevision="constant" for smooth (non-jumping) updates.

RUN:
    pip install streamlit plotly pandas
    streamlit run dashboard.py
==============================================================================
"""

import os
import json
import ast
import re
import math
from datetime import datetime, UTC

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# ------------------------------------------------------------------------
# PAGE CONFIG — sidebar expanded by default so Mission Config is always visible
# ------------------------------------------------------------------------
st.set_page_config(
    page_title="MCC // Satellite Telemetry",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------------
# THRESHOLDS  (must match monitor/fault_detector.py)
# ------------------------------------------------------------------------
THRESHOLDS = {
    "temperature": {"warn": 80, "crit": 90, "unit": "°C", "direction": "high", "min": 0, "max": 110},
    "battery":     {"warn": 20, "crit": 5,  "unit": "%",  "direction": "low",  "min": 0, "max": 100},
    "voltage":     {"warn": 3.6, "crit": 3.3, "unit": "V", "direction": "low", "min": 3.0, "max": 5.0},
    "fuel":        {"warn": 15, "crit": 5,  "unit": "%",  "direction": "low",  "min": 0, "max": 100},
}
STATUS_COL = {
    "temperature": "temp_status",
    "battery": "battery_status",
    "voltage": "voltage_status",
    "fuel": "fuel_status",
}
LABELS = {"temperature": "CHASSIS TEMPERATURE", "battery": "SOLID STATE BATTERY (SOC)",
          "voltage": "BUS VOLTAGE REGULATION", "fuel": "PROPELLANT PRESSURE & FUEL"}
SHORT_LABELS = {"temperature": "THERMAL", "battery": "BATTERY", "voltage": "VOLTAGE", "fuel": "FUEL"}

COLOR_NOMINAL = "#22ff88"
COLOR_WARNING = "#ffb300"
COLOR_CRITICAL = "#ff3b3b"
COLOR_DIM = "#3a4a5c"
COLOR_CYAN = "#38bdf8"
BG = "#070b14"
PANEL_BG = "#0b0f1c"


def status_color(status: str) -> str:
    if not isinstance(status, str):
        return COLOR_DIM
    s = status.lower()
    if "critical" in s:
        return COLOR_CRITICAL
    if "warning" in s:
        return COLOR_WARNING
    if "normal" in s:
        return COLOR_NOMINAL
    return COLOR_DIM


# ------------------------------------------------------------------------
# CSS — compact, no-scroll mission control look
# ------------------------------------------------------------------------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Share+Tech+Mono&display=swap');

html, body, [class*="css"] {{ font-family: 'Share Tech Mono', monospace; }}
.stApp {{
    background: radial-gradient(ellipse at top, #0d1626 0%, {BG} 60%);
    color: #d7f4ff;
}}
.block-container {{
    padding-top: 1.1rem !important;
    padding-bottom: 0.6rem !important;
    padding-left: 1.4rem !important;
    padding-right: 1.4rem !important;
    max-width: 100% !important;
}}
[data-testid="stSidebar"] {{ background: {PANEL_BG}; border-right: 1px solid #16233a; }}
h1, h2, h3 {{ font-family: 'Orbitron', sans-serif !important; letter-spacing: 1px; }}

.mcc-title {{
    font-family:'Orbitron', sans-serif; font-weight:900; font-size:22px;
    color:#eaffff; text-shadow: 0 0 12px rgba(56,189,248,0.45); margin-bottom:0;
}}
.mcc-sub {{ color:#5c7b96; font-size:11px; letter-spacing:3px; text-transform:uppercase; }}
.mcc-id {{ text-align:right; color:{COLOR_CYAN}; font-size:12px; font-weight:700; letter-spacing:1px; }}
.mcc-id-sub {{ text-align:right; color:{COLOR_NOMINAL}; font-size:11px; letter-spacing:1px; }}

/* tabs styled as nav buttons */
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 1px solid #16233a; }}
.stTabs [data-baseweb="tab"] {{
    background: {PANEL_BG}; border:1px solid #16233a; border-radius:5px 5px 0 0;
    color:#5c7b96; font-family:'Orbitron', sans-serif; font-size:12px; letter-spacing:1px;
    padding: 8px 18px;
}}
.stTabs [aria-selected="true"] {{
    color: {COLOR_CYAN} !important; border-color:{COLOR_CYAN} !important;
    box-shadow: inset 0 -2px 0 {COLOR_CYAN};
}}

.card {{
    background: linear-gradient(180deg, rgba(15,26,43,0.9), rgba(7,12,22,0.9));
    border:1px solid #16233a; border-radius:6px; padding:10px 14px; height:100%;
}}
.card-label {{ font-size:10.5px; color:#5c7b96; letter-spacing:2px; text-transform:uppercase; }}
.card-value-lg {{ font-family:'Orbitron', sans-serif; font-weight:800; font-size:19px; color:{COLOR_NOMINAL}; line-height:1.3; }}
.card-value-sm {{ font-size:11.5px; color:#9db8cc; margin-top:1px; }}
.gauge-title {{ text-align:center; font-size:11px; color:#8fabc2; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:-6px;}}
.gauge-footer {{ display:flex; justify-content:space-between; font-size:11px; padding:0 10px; margin-top:-8px; }}
.gauge-footer .l {{ color:#5c7b96; }}
.gauge-footer .r {{ font-weight:700; }}

.led {{ display:inline-block; width:9px; height:9px; border-radius:50%; box-shadow:0 0 7px 2px currentColor; margin-right:6px; }}

.log-box {{
    background: rgba(0,0,0,0.25); border:1px solid #16233a; border-radius:5px;
    padding:8px 10px; height: 230px; overflow-y:auto; font-size:12px;
}}
.log-box::-webkit-scrollbar {{ width:5px; }}
.log-box::-webkit-scrollbar-thumb {{ background:#1c2c47; border-radius:3px; }}
.alert-item {{ padding:5px 8px; border-left:3px solid; margin-bottom:5px; border-radius:2px; background:rgba(255,255,255,0.02); }}
.timeline-item {{ color:{COLOR_NOMINAL}; padding:2px 0; }}

.section-title {{
    font-family:'Orbitron', sans-serif; font-size:12.5px; letter-spacing:2px; color:{COLOR_CYAN};
    text-transform:uppercase; margin-bottom:6px;
}}
.section-title.red {{ color:{COLOR_CRITICAL}; }}
.section-title.green {{ color:{COLOR_NOMINAL}; }}

[data-testid="stMetric"] {{ background:transparent; }}
div[data-testid="stExpander"] {{ border:1px solid #16233a; border-radius:6px; background:{PANEL_BG}; }}
.badge {{ display:inline-block; padding:3px 10px; border-radius:3px; font-family:'Orbitron',sans-serif; font-weight:700; font-size:10.5px; letter-spacing:1.5px; }}
.badge-live {{ background:rgba(34,255,136,0.1); color:{COLOR_NOMINAL}; border:1px solid {COLOR_NOMINAL}; }}
.badge-offline {{ background:rgba(255,59,59,0.1); color:{COLOR_CRITICAL}; border:1px solid {COLOR_CRITICAL}; }}

/* =====================================================================
   STICKY PLAYBACK TRANSPORT BAR
   The only horizontal block that contains stButtons is the transport row,
   so we pin it to the top of the viewport. Controls stay visible no matter
   how far the user scrolls or how fast the fragment ticks.
   ===================================================================== */
div[data-testid="stHorizontalBlock"]:has(> div div[data-testid="stButton"]) {{
    position: sticky;
    top: 0;
    z-index: 999;
    background: {BG};
    padding: 10px 0 8px 0;
    margin-bottom: 6px;
    border-bottom: 1px solid #16233a;
    box-shadow: 0 6px 14px rgba(0,0,0,0.6);
}}

/* playback control buttons — forced high contrast, always visible */
div[data-testid="stButton"] > button,
.stButton > button {{
    background: rgba(56,189,248,0.10) !important;
    border: 1.5px solid {COLOR_CYAN} !important;
    color: #eaffff !important;
    font-family: 'Orbitron', sans-serif !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    letter-spacing: 1.5px !important;
    opacity: 1 !important;
    text-shadow: 0 0 6px rgba(56,189,248,0.55);
}}
div[data-testid="stButton"] > button:hover,
.stButton > button:hover {{
    background: rgba(56,189,248,0.25) !important;
    border-color: #ffffff !important;
    color: #ffffff !important;
    text-shadow: 0 0 10px rgba(255,255,255,0.9);
}}
/* force every inner node (span/p/div) to inherit the bright text color */
div[data-testid="stButton"] > button *,
.stButton > button * {{
    color: inherit !important;
    opacity: 1 !important;
}}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------------
# SIDEBAR — mission config (expanded by default, always visible)
# ------------------------------------------------------------------------
st.sidebar.markdown("### 🛰️ MISSION CONFIG")
default_csv_candidates = [
    "../Version_2/data/telemetry_log.csv",
    "../Version_1/data/telemetry_log.csv",
    "data/telemetry_log.csv",
]
default_csv = next((p for p in default_csv_candidates if os.path.exists(p)), default_csv_candidates[0])
csv_path = st.sidebar.text_input("Live telemetry CSV", value=default_csv)
window = st.sidebar.slider("Chart window (last N readings)", 20, 500, 100, step=10)
st.sidebar.markdown("**Replay speed**")
SPEED_MAP = {"FAST (250ms)": 0.25, "NORMAL (1000ms)": 1.0, "DEMO (1500ms)": 1.5}
speed_label = st.sidebar.radio("Replay speed", list(SPEED_MAP.keys()), index=2, label_visibility="collapsed")
refresh_rate = SPEED_MAP[speed_label]
loop_playback = st.sidebar.checkbox("Loop back to frame 1 at the end", value=True)
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 MISSION ANALYSIS (V3)")
v3_dir = st.sidebar.text_input("V3 outputs folder", value="../Version_3")
satellite_id = st.sidebar.text_input("Satellite ID", value="LEO-SAT-109X")
st.sidebar.markdown("---")
st.sidebar.caption("Satellite Telemetry Health Monitoring System — V4")


# ------------------------------------------------------------------------
# STATIC HELPERS (pure functions — safe to keep outside the fragment)
# ------------------------------------------------------------------------
def load_telemetry(path):
    if not os.path.exists(path):
        return None, f"File not found: `{path}`"
    try:
        df = pd.read_csv(path)
        if df.empty:
            return None, "File exists but has no rows yet — waiting for V1/V2 to write data."
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df, None
    except Exception as e:
        return None, f"Could not read/parse CSV: {e}"


def load_json_safe(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def load_mission_timeline(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            raw = f.read()
        try:
            return json.loads(raw)
        except Exception:
            pass
        raw2 = raw.strip()
        if raw2.startswith('"') and raw2.endswith('"'):
            raw2 = json.loads(raw2)
        raw2 = re.sub(r"Timestamp\('([^']+)'\)", r"'\1'", raw2)
        return ast.literal_eval(raw2)
    except Exception:
        return None


GROUND_STATIONS = [
    {"name": "NASA Goldstone (DSN-14)", "lat": 35.4267, "lon": -116.89},
    {"name": "Madrid Comm Array (DSN-63)", "lat": 40.4314, "lon": -4.2481},
    {"name": "Canberra Array (DSN-43)", "lat": -35.4014, "lon": 148.9819},
]
ORBIT_ALT_KM = 852.14
EARTH_R_KM = 6371.0
INCLINATION_DEG = 51.6
ORBIT_PERIOD_S = 6100.0  # ~101.7 min, realistic for ~850km LEO


def simulated_orbit_state(elapsed_seconds):
    frac = (elapsed_seconds % ORBIT_PERIOD_S) / ORBIT_PERIOD_S
    lat = INCLINATION_DEG * math.sin(2 * math.pi * frac)
    lon = ((elapsed_seconds / ORBIT_PERIOD_S) * 360.0 - (elapsed_seconds / 86164.0) * 360.0) % 360.0
    lon = lon - 360 if lon > 180 else lon
    return lat, lon, frac


def latlon_to_xyz(lat_deg, lon_deg, radius):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    x = radius * math.cos(lat) * math.cos(lon)
    y = radius * math.cos(lat) * math.sin(lon)
    z = radius * math.sin(lat)
    return x, y, z


# ==========================================================================
# EVERYTHING BELOW RUNS INSIDE A FRAGMENT.
# ==========================================================================
@st.fragment(run_every=refresh_rate)
def render_console():
    df, err = load_telemetry(csv_path)
    if err:
        st.markdown('<div class="mcc-title">SATELLITE TELEMETRY DASHBOARD</div>', unsafe_allow_html=True)
        st.warning(f"⚠️ {err}\n\nStart the V1 (or V2) `main.py` loop to begin streaming telemetry, or point the sidebar at an existing CSV.")
        return

    # ---------------- playback state ----------------
    if "frame_idx" not in st.session_state:
        st.session_state.frame_idx = 0
    if "playing" not in st.session_state:
        st.session_state.playing = True
    st.session_state.frame_idx = min(st.session_state.frame_idx, len(df) - 1)

    # ---------------- header FIRST (title above the transport bar) ----------------
    h1, h2 = st.columns([3, 1.4])
    with h1:
        st.markdown('<div class="mcc-sub">FLIGHT OPERATIONS COMMAND SUITE // MISSION CONTROL SATELLITE LINK</div>', unsafe_allow_html=True)
        st.markdown('<div class="mcc-title">🛰️ ORBITAL SATELLITE TELEMETRY MONITORING CONSOLE</div>', unsafe_allow_html=True)
    with h2:
        badge = '<span class="badge badge-live">● REPLAY RUNNING</span>' if st.session_state.playing else '<span class="badge badge-offline">● PAUSED</span>'
        st.markdown(f'<div class="mcc-id">SATELLITE ID: {satellite_id} &nbsp; {badge}</div>', unsafe_allow_html=True)

    # ---------------- STICKY transport bar (always visible) ----------------
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1, 1, 1, 3])
    if ctrl1.button("⏮ RESET", width="stretch", key="btn_reset"):
        st.session_state.frame_idx = 0
    if ctrl2.button("⏸ PAUSE" if st.session_state.playing else "▶ PLAY", width="stretch", key="btn_playpause"):
        st.session_state.playing = not st.session_state.playing
    if ctrl3.button("⏭ STEP", width="stretch", key="btn_step"):
        st.session_state.playing = False
        st.session_state.frame_idx = min(st.session_state.frame_idx + 1, len(df) - 1)

    frame_idx = st.session_state.frame_idx
    with ctrl4:
        pct = round((frame_idx + 1) / len(df) * 100)
        state_label = "REPLAY COMPLETE" if frame_idx >= len(df) - 1 and not loop_playback else \
                      ("REPLAY RUNNING" if st.session_state.playing else "PAUSED")
        state_color = COLOR_NOMINAL if st.session_state.playing else (COLOR_CYAN if frame_idx >= len(df) - 1 else COLOR_WARNING)
        st.markdown(f"""<div style="font-size:12px; padding-top:8px;">
            <b style="color:{state_color};">{state_label}</b> &nbsp;
            <span style="color:#9db8cc;">FRAME {frame_idx + 1} / {len(df)} &nbsp;·&nbsp; {pct}% COMPLETE &nbsp;·&nbsp; SPEED: {speed_label}</span>
        </div>""", unsafe_allow_html=True)

    # ---------------- data slices ----------------
    df_visible = df.iloc[: frame_idx + 1]
    latest = df_visible.iloc[-1]
    recent = df_visible.tail(window)
    now_utc = datetime.now(UTC)
    met = df_visible["timestamp"].iloc[-1] - df["timestamp"].iloc[0]

    v3_scores = load_json_safe(os.path.join(v3_dir, "health_scores.json"))
    if v3_scores and "Overall_score" in v3_scores:
        health_score = round(v3_scores["Overall_score"])
    else:
        total = len(df_visible)
        anomalies = sum((df_visible[STATUS_COL[p]] != "Normal").sum() for p in THRESHOLDS)
        health_score = max(0, round(100 - (anomalies / max(total, 1)) * 100))

    elapsed = met.total_seconds()
    sat_lat, sat_lon, orbit_frac = simulated_orbit_state(elapsed)

    def build_orbit_figure():
        r_earth = 1.0
        r_orbit = r_earth * (1 + ORBIT_ALT_KM / EARTH_R_KM)

        n = 260
        phi = math.pi * (3.0 - math.sqrt(5.0))
        ex, ey, ez = [], [], []
        for i in range(n):
            yv = 1 - (i / float(n - 1)) * 2
            radius_at_y = math.sqrt(max(0, 1 - yv * yv))
            theta = phi * i
            ex.append(math.cos(theta) * radius_at_y * r_earth)
            ez.append(yv * r_earth)
            ey.append(math.sin(theta) * radius_at_y * r_earth)

        ring_n = 120
        rx, ry, rz = [], [], []
        for i in range(ring_n + 1):
            t = 2 * math.pi * i / ring_n
            x0, y0, z0 = r_orbit * math.cos(t), r_orbit * math.sin(t), 0
            inc = math.radians(INCLINATION_DEG)
            rx.append(x0)
            ry.append(y0 * math.cos(inc) - z0 * math.sin(inc))
            rz.append(y0 * math.sin(inc) + z0 * math.cos(inc))

        trail_n = 40
        tx, ty, tz = [], [], []
        for i in range(trail_n + 1):
            f = orbit_frac - 0.15 * (1 - i / trail_n)
            t = 2 * math.pi * (f % 1.0)
            x0, y0, z0 = r_orbit * math.cos(t), r_orbit * math.sin(t), 0
            inc = math.radians(INCLINATION_DEG)
            tx.append(x0)
            ty.append(y0 * math.cos(inc) - z0 * math.sin(inc))
            tz.append(y0 * math.sin(inc) + z0 * math.cos(inc))

        sx, sy, sz = latlon_to_xyz(sat_lat, sat_lon, r_orbit)

        fig = go.Figure()
        fig.add_trace(go.Scatter3d(x=ex, y=ey, z=ez, mode="markers",
                                    marker=dict(size=1.6, color="#7fa8c2", opacity=0.55),
                                    name="Earth reference grid", hoverinfo="skip"))
        fig.add_trace(go.Scatter3d(x=rx, y=ry, z=rz, mode="lines",
                                    line=dict(color=COLOR_CYAN, width=3),
                                    name="Nominal orbit track", hoverinfo="skip"))
        fig.add_trace(go.Scatter3d(x=tx, y=ty, z=tz, mode="lines",
                                    line=dict(color=COLOR_NOMINAL, width=5),
                                    name="Completed flightpath trace", hoverinfo="skip"))
        fig.add_trace(go.Scatter3d(x=[sx], y=[sy], z=[sz], mode="markers+text",
                                    marker=dict(size=6, color=COLOR_NOMINAL, symbol="circle",
                                                line=dict(color="white", width=1)),
                                    text=[satellite_id], textposition="top center",
                                    textfont=dict(color="#eaffff", size=10),
                                    name=f"Active satellite ({satellite_id})"))
        gx = [latlon_to_xyz(g["lat"], g["lon"], r_earth * 1.01)[0] for g in GROUND_STATIONS]
        gy = [latlon_to_xyz(g["lat"], g["lon"], r_earth * 1.01)[1] for g in GROUND_STATIONS]
        gz = [latlon_to_xyz(g["lat"], g["lon"], r_earth * 1.01)[2] for g in GROUND_STATIONS]
        gtext = [g["name"] for g in GROUND_STATIONS]
        fig.add_trace(go.Scatter3d(x=gx, y=gy, z=gz, mode="markers+text",
                                    marker=dict(size=4, color="#ffa726", symbol="diamond"),
                                    text=gtext, textposition="middle left",
                                    textfont=dict(color="#9db8cc", size=9),
                                    name="Active deep space comm ground stations"))

        axis = dict(visible=False, showbackground=False)
        fig.update_layout(
            scene=dict(xaxis=axis, yaxis=axis, zaxis=axis, aspectmode="cube",
                       camera=dict(eye=dict(x=1.4, y=1.4, z=0.9))),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0), height=360,
            legend=dict(orientation="v", x=0.01, y=0.99, font=dict(color="#c9def0", size=10.5),
                        bgcolor="rgba(6,10,20,0.55)", bordercolor="#16233a", borderwidth=1),
            showlegend=True,
            uirevision="constant",
        )
        return fig

    def make_gauge(param, height=150):
        t = THRESHOLDS[param]
        val = latest[param]
        color = status_color(latest[STATUS_COL[param]])
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=val,
            number={"suffix": f" {t['unit']}", "font": {"color": "#eaffff", "family": "Share Tech Mono", "size": 20}},
            gauge={
                "axis": {"range": [t["min"], t["max"]], "tickcolor": "#5c7b96", "tickfont": {"color": "#5c7b96", "size": 8}},
                "bar": {"color": color, "thickness": 0.28},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 1, "bordercolor": "#16233a",
                "threshold": {"line": {"color": "white", "width": 2}, "thickness": 0.75, "value": val},
            },
            domain={"x": [0, 1], "y": [0, 1]},
        ))
        fig.update_layout(height=height, margin=dict(l=16, r=16, t=6, b=0),
                           paper_bgcolor="rgba(0,0,0,0)", font={"color": "#d7f4ff"},
                           transition={"duration": max(200, int(refresh_rate * 700)), "easing": "linear"},
                           uirevision="constant")
        return fig

    def strip_chart(param_left, param_right, height=270):
        tl, tr = THRESHOLDS[param_left], THRESHOLDS[param_right]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=recent["timestamp"], y=recent[param_left], mode="lines",
                                  line=dict(color=COLOR_CYAN, width=2, shape="spline", smoothing=0.35),
                                  name=f"{SHORT_LABELS[param_left].title()} ({tl['unit']})",
                                  yaxis="y1"))
        fig.add_trace(go.Scatter(x=recent["timestamp"], y=recent[param_right], mode="lines",
                                  line=dict(color=COLOR_NOMINAL, width=2, dash="dash", shape="spline", smoothing=0.35),
                                  name=f"{SHORT_LABELS[param_right].title()} ({tr['unit']})", yaxis="y2"))
        fig.update_layout(
            height=height, margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, color="#5c7b96", tickfont=dict(size=9)),
            yaxis=dict(title=dict(text=SHORT_LABELS[param_left].title(), font=dict(color=COLOR_CYAN, size=10)),
                       showgrid=True, gridcolor="rgba(255,255,255,0.05)", color=COLOR_CYAN, tickfont=dict(size=9)),
            yaxis2=dict(title=dict(text=SHORT_LABELS[param_right].title(), font=dict(color=COLOR_NOMINAL, size=10)),
                        overlaying="y", side="right", showgrid=False, color=COLOR_NOMINAL, tickfont=dict(size=9)),
            legend=dict(orientation="h", y=1.18, font=dict(color="#c9def0", size=10)),
            transition={"duration": max(200, int(refresh_rate * 600)), "easing": "cubic-in-out"},
            uirevision="constant",
        )
        return fig

    # ---------------- MET line under the transport bar ----------------
    st.markdown(f'<div class="mcc-id-sub" style="text-align:left; margin-bottom:4px;">GROUND TRACK: COMM-STATION-ACT-04 &nbsp;|&nbsp; MET {str(met).split(".")[0]}</div>', unsafe_allow_html=True)

    tab_overview, tab_graphs, tab_report = st.tabs(["🛰️  OVERVIEW", "📊  GRAPHS", "📋  MISSION REPORT"])

    # ---------------- TAB 1 — OVERVIEW ----------------
    with tab_overview:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""<div class="card"><div class="card-label">MISSION COMMAND SYSTEM STATUS</div>
            <div class="card-value-lg" style="color:{COLOR_NOMINAL};">NOMINAL TELEMETRY FLOW</div>
            <div class="card-value-sm">Replaying recorded log — frame {frame_idx + 1} of {len(df)}.</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="card"><div class="card-label">INTELLIGENT SATELLITE HEALTH SCORE</div>
            <div class="card-value-lg" style="font-size:26px;">{health_score} <span style="font-size:14px;color:#5c7b96;">/ 100</span></div>
            <div class="card-value-sm">{'System nominal. All loops reporting within limits.' if health_score >= 80 else 'Degraded — review anomalies.'}</div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="card" style="border-color:{COLOR_CYAN};"><div class="card-label" style="color:{COLOR_CYAN};">TELEMETRY REPLAY SYSTEM MODE</div>
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-top:4px;">
                <div><span style="color:#5c7b96;">FRAME</span><br><b>{frame_idx + 1} / {len(df)}</b></div>
                <div><span style="color:#5c7b96;">STATE</span><br><b style="color:{COLOR_NOMINAL if st.session_state.playing else COLOR_WARNING};">{'RUNNING' if st.session_state.playing else 'PAUSED'}</b></div>
            </div></div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""<div class="card"><div class="card-label">DURABLE DATASET SPECIFICATIONS</div>
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-top:4px;">
                <div><span style="color:#5c7b96;">TOTAL FRAMES</span><br><b>{len(df)}</b></div>
                <div><span style="color:#5c7b96;">DURATION</span><br><b>{str(met).split('.')[0]}</b></div>
            </div></div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        oc1, oc2 = st.columns([1.55, 1])
        with oc1:
            st.markdown(f"""<div class="section-title">REAL-TIME CO-ALIGNMENT SAT TRACKER & EARTH GROUND PATH VISUALIZER
                <span style="float:right; color:{COLOR_NOMINAL}; font-size:11px;">SIMULATED — RADIAL POS: {sat_lat:.3f}° {'N' if sat_lat>=0 else 'S'}, {abs(sat_lon):.3f}° {'E' if sat_lon>=0 else 'W'} // ALT: {ORBIT_ALT_KM:.2f} KM</span></div>""", unsafe_allow_html=True)
            st.plotly_chart(build_orbit_figure(), width="stretch", config={"displayModeBar": True, "displaylogo": False}, key="orbit_chart")
        with oc2:
            st.markdown('<div class="section-title">INSTRUMENT PANEL</div>', unsafe_allow_html=True)
            g1, g2 = st.columns(2)
            g3, g4 = st.columns(2)
            for gcol, param in zip([g1, g2, g3, g4], ["temperature", "battery", "voltage", "fuel"]):
                with gcol:
                    status = latest[STATUS_COL[param]]
                    color = status_color(status)
                    st.markdown(f'<div class="gauge-title">{SHORT_LABELS[param]}</div>', unsafe_allow_html=True)
                    st.plotly_chart(make_gauge(param, height=118), width="stretch", config={"displayModeBar": False}, key=f"gauge_{param}")
                    st.markdown(f'<div class="gauge-footer"><span class="l">VAL: {latest[param]:.1f}</span><span class="r" style="color:{color};">{status}</span></div>', unsafe_allow_html=True)

    # ---------------- TAB 2 — GRAPHS ----------------
    with tab_graphs:
        gc1, gc2 = st.columns(2)
        with gc1:
            st.markdown('<div class="section-title">THERMAL / POWER REGULATION TRACKING</div>', unsafe_allow_html=True)
            st.plotly_chart(strip_chart("temperature", "battery", height=430), width="stretch", config={"displayModeBar": False}, key="strip_thermal")
        with gc2:
            st.markdown('<div class="section-title">BUS POTENTIALS / FUEL FLOW DEPLETION TRACKING</div>', unsafe_allow_html=True)
            st.plotly_chart(strip_chart("voltage", "fuel", height=430), width="stretch", config={"displayModeBar": False}, key="strip_bus")

    # ---------------- TAB 3 — MISSION REPORT ----------------
    with tab_report:
        rc1, rc2, rc3 = st.columns(3)

        with rc1:
            st.markdown('<div class="section-title red">ACTIVE TELEMETRY EXCEPTION REGISTRY</div>', unsafe_allow_html=True)
            alert_rows = df_visible[
                (df_visible["temp_status"] != "Normal") | (df_visible["battery_status"] != "Normal") |
                (df_visible["voltage_status"] != "Normal") | (df_visible["fuel_status"] != "Normal")
            ].tail(25).iloc[::-1]
            if alert_rows.empty:
                html = '<div class="log-box" style="color:{};">NO DETECTED TELESYSTEM ANOMALIES</div>'.format(COLOR_NOMINAL)
            else:
                html = '<div class="log-box">'
                for idx, row in alert_rows.iterrows():
                    for param in ["temperature", "battery", "voltage", "fuel"]:
                        st_val = row[STATUS_COL[param]]
                        if st_val != "Normal":
                            color = status_color(st_val)
                            html += f"""<div class="alert-item" style="border-left-color:{color};">
                                <b style="color:{color};">[{st_val.upper()}]</b> FRAME #{idx} — {SHORT_LABELS[param]} = {row[param]:.2f}{THRESHOLDS[param]['unit']}
                                <span style="float:right; color:#5c7b96;">{row['timestamp']}</span></div>"""
                html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

        with rc2:
            st.markdown('<div class="section-title green">MISSION COMM EVENT TIMELINE LOGGER</div>', unsafe_allow_html=True)
            transitions = []
            for param in ["temperature", "battery", "voltage", "fuel"]:
                col = STATUS_COL[param]
                changed = df_visible[col] != df_visible[col].shift(1)
                for idx in df_visible[changed].index[-10:]:
                    transitions.append((df_visible.loc[idx, "timestamp"], SHORT_LABELS[param], df_visible.loc[idx, col]))
            transitions.sort(key=lambda x: x[0], reverse=True)
            if not transitions:
                log_html = '<div class="log-box"><span class="timeline-item">• STATION COMM LINK ESTABLISHED // MONITOR LOG EMPTY NOMINAL STATS</span></div>'
            else:
                log_html = '<div class="log-box">'
                for ts, label, status in transitions[:25]:
                    color = status_color(status)
                    log_html += f'<div class="timeline-item" style="color:{color};">• {ts} — {label} → {status.upper()}</div>'
                log_html += "</div>"
            st.markdown(log_html, unsafe_allow_html=True)

        with rc3:
            st.markdown('<div class="section-title">MISSION HEALTH OVERVIEW (V3)</div>', unsafe_allow_html=True)
            if v3_scores:
                for label, key in [("Battery", "Battery_score"), ("Thermal", "Thermal_score"),
                                    ("Fuel", "Fuel_score"), ("Overall", "Overall_score")]:
                    v = v3_scores.get(key, 0)
                    c = COLOR_NOMINAL if v >= 75 else (COLOR_WARNING if v >= 40 else COLOR_CRITICAL)
                    st.markdown(f"""<div style="display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px dashed #16233a; font-size:12.5px;">
                        <span style="color:#5c7b96;">{label} score</span><span style="color:{c}; font-weight:700;">{v}</span></div>""", unsafe_allow_html=True)
            else:
                st.caption(f"No `health_scores.json` found in `{v3_dir}`. Run V3's `main.py` on this log to populate this panel.")

            report_path = os.path.join(v3_dir, "mission_report.txt")
            if os.path.exists(report_path):
                with st.popover("📄 View full mission_report.txt"):
                    with open(report_path) as f:
                        st.text(f.read())
            fault_log_path = os.path.join(v3_dir, "fault_log.csv")
            if os.path.exists(fault_log_path):
                try:
                    fdf = pd.read_csv(fault_log_path)
                    with st.popover("🗂 View fault_log.csv"):
                        st.dataframe(fdf.tail(50), width="stretch", height=350)
                except Exception:
                    pass

    # ---------------- footer ----------------
    st.markdown(f"""
    <div style="margin-top:8px; padding-top:6px; border-top:1px solid #16233a; color:#3a5670; font-size:10.5px; letter-spacing:1px; display:flex; justify-content:space-between;">
        <span>SATELLITE TELEMETRY HEALTH MONITORING SYSTEM · V4 MISSION CONTROL CONSOLE</span>
        <span>SOURCE: {csv_path} · UTC {now_utc.strftime('%Y-%m-%d %H:%M:%S')}</span>
    </div>
    """, unsafe_allow_html=True)

    # ---------------- advance playback frame for the NEXT tick ----------------
    if st.session_state.playing:
        if st.session_state.frame_idx < len(df) - 1:
            st.session_state.frame_idx += 1
        elif loop_playback:
            st.session_state.frame_idx = 0
        else:
            st.session_state.playing = False


render_console()