#!/usr/bin/env python3
"""
==============================================================================
 V5 — UNIFIED NASA MISSION CONTROL (SINGLE FILE)
 Stack: STREAMLIT shell + DASH replay core (background thread) + GRAFANA wall
        + PLOTLY everywhere (Dynamic Sensor Auto-Detection).

 RUN:  python dashboard_try.py   (or: python -m streamlit run dashboard_try.py)
==============================================================================
"""
import os, sys, json, math, threading, socket, datetime, urllib.request, time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State, callback_context
import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# STREAMLIT RUNTIME DETECTION & PAGE CONFIG
# ---------------------------------------------------------------------------
try:
    from streamlit.runtime import exists as _rt_exists
    _UNDER_RT = _rt_exists()
except Exception:
    _UNDER_RT = False

if _UNDER_RT:
    st.set_page_config(page_title="MCC // MISSION CONTROL", page_icon="🛰️",
                       layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------------------------
# CONSTANTS & SHARED CONFIG
# ---------------------------------------------------------------------------
DASH_PORT = 8050
CONFIG_FILE = "mission_config.json"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FALLBACK = "data/telemetry_log.csv"

def resolve_path(p):
    if not p: return p
    if os.path.isabs(p) and os.path.exists(p): return p
    if os.path.exists(p): return os.path.abspath(p)
    alt = os.path.normpath(os.path.join(SCRIPT_DIR, p))
    if os.path.exists(alt): return alt
    return p

DEFAULT_CSV = next((resolve_path(c) for c in [
    "../Version_2/data/telemetry_log.csv",
    "../Version_1/data/telemetry_log.csv",
    "Version_2/data/telemetry_log.csv",
    "data/telemetry_log.csv"] if os.path.exists(resolve_path(c))), DATA_FALLBACK)

SPEED_MS = {"FAST": 250, "NORMAL": 1000, "DEMO": 1500}
DEFAULT_CFG = {"csv_path": DEFAULT_CSV, "speed_key": "DEMO", "warp": 1.0,
               "loop": True, "window": 100}

# Known limits table (only applied to channels that exist in your CSV)
KNOWN_LIMITS = {
    "temperature": {"warn_high": 30.0, "crit_high": 45.0, "unit": "°C", "min": 0, "max": 80, "name": "CHASSIS TEMPERATURE"},
    "temp":        {"warn_high": 30.0, "crit_high": 45.0, "unit": "°C", "min": 0, "max": 80, "name": "CHASSIS TEMPERATURE"},
    "battery":     {"warn_low": 20.0, "crit_low": 5.0, "unit": "%", "min": 0, "max": 100, "name": "BATTERY (SOC)"},
    "voltage":     {"warn_low": 3.6, "crit_low": 3.3, "warn_high": 35.0, "crit_high": 40.0, "unit": "V", "min": 0, "max": 45, "name": "BUS VOLTAGE REGULATION"},
    "current":     {"warn_high": 10.0, "crit_high": 15.0, "unit": "A", "min": 0, "max": 20, "name": "ELECTRICAL CURRENT"},
}

CHANNEL_COLORS = ["#00d2ff", "#39ff14", "#ff4d4d", "#ffb000", "#a855f7", "#ec4899"]
C = {"bg": "#0a0f1d", "panel": "#121826", "border": "#1f2a40", "text": "#e2e8f0", "dim": "#94a3b8",
     "blue": "#00d2ff", "green": "#39ff14", "orange": "#ffb000", "red": "#ff4d4d"}
BG, PANEL, CYAN, GREEN, RED, DIM = "#070b14", "#0b0f1c", "#38bdf8", "#22ff88", "#ff3b3b", "#5c7b96"

def read_config():
    cfg = dict(DEFAULT_CFG)
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                cfg.update(json.load(f))
    except Exception:
        pass
    return cfg

def save_config(cfg_dict):
    try:
        temp_file = f"{CONFIG_FILE}.tmp"
        with open(temp_file, "w") as f:
            json.dump(cfg_dict, f)
        os.replace(temp_file, CONFIG_FILE)
    except Exception:
        pass

def stat_color(s):
    if not isinstance(s, str): return C["green"]
    if "CRITICAL" in s.upper(): return C["red"]
    if "WARNING" in s.upper(): return C["orange"]
    return C["green"]

# ---------------------------------------------------------------------------
# DATA LOADER & AUTO-DETECTION
# ---------------------------------------------------------------------------
def _ensure_status(df):
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    if "timestamp" not in df.columns:
        if "time" in df.columns:
            df["timestamp"] = df["time"]
        else:
            base_time = datetime.datetime.utcnow()
            df["timestamp"] = [(base_time + datetime.timedelta(seconds=i*5)).strftime("%Y-%m-%dT%H:%M:%SZ") for i in range(len(df))]

    # Auto-detect numeric channels (excluding timestamp & status columns)
    channels = [c for c in df.columns if c not in ["timestamp", "time"] and not c.endswith("_status")]
    
    for p in channels:
        sc = f"{p}_status"
        if sc not in df.columns:
            L = KNOWN_LIMITS.get(p, {})
            out = []
            for v in pd.to_numeric(df[p], errors='coerce').fillna(0):
                s = "NOMINAL"
                if "crit_high" in L and v >= L["crit_high"]: s = "CRITICAL_HIGH"
                elif "warn_high" in L and v >= L["warn_high"]: s = "WARNING_HIGH"
                if "crit_low" in L and v <= L["crit_low"]: s = "CRITICAL_LOW"
                elif "warn_low" in L and v <= L["warn_low"]: s = "WARNING_LOW"
                out.append(s)
            df[sc] = out
    return df

_DF_CACHE = {}
def get_df():
    path = resolve_path(read_config().get("csv_path", DEFAULT_CSV))
    if not os.path.exists(path): path = resolve_path(DEFAULT_CSV)
    if not os.path.exists(path): path = resolve_path(DATA_FALLBACK)
    if not os.path.exists(path):
        os.makedirs("data", exist_ok=True)
        path = "data/telemetry_log.csv"
        n = 60
        ts = [(datetime.datetime.utcnow() + datetime.timedelta(seconds=10*i)).strftime("%Y-%m-%dT%H:%M:%SZ") for i in range(n)]
        t = 20 + 5*np.sin(np.linspace(0, 10, n)); t[18:28] += 25
        b = np.clip(100 - .25*np.arange(n), 0, 100); b[34:42] -= 10
        v = 32.4 + .1*np.random.randn(n); v[34:42] -= 4
        df = pd.DataFrame({"timestamp": ts, "temperature": t.round(2), "battery": b.round(2), "voltage": v.round(2)})
        df = _ensure_status(df); df.to_csv(path, index=False)
        return df

    mtime = os.path.getmtime(path)
    if _DF_CACHE.get("key") != (path, mtime):
        _DF_CACHE.clear(); _DF_CACHE["key"] = (path, mtime)
        try:
            raw = pd.read_csv(path)
            _DF_CACHE["df"] = _ensure_status(raw)
        except Exception:
            _DF_CACHE["df"] = _ensure_status(pd.DataFrame())
    return _DF_CACHE.get("df", pd.DataFrame())

def get_active_channels(df):
    return [c for c in df.columns if c not in ["timestamp", "time"] and not c.endswith("_status")]

# ===========================================================================
# DASH CORE — layout helpers & figures
# ===========================================================================
CARD = {"backgroundColor": C["panel"], "borderRadius": "8px", "border": f"1px solid {C['border']}",
        "padding": "14px", "boxShadow": "0 6px 16px rgba(0,0,0,0.4)"}
LBL = {"fontSize": "10px", "color": C["dim"], "letterSpacing": "1.5px", "fontWeight": "700"}
BTN = {"backgroundColor": "#1d273a", "color": C["text"], "border": f"1px solid {C['blue']}",
       "borderRadius": "4px", "padding": "8px 14px", "cursor": "pointer", "fontWeight": "700",
       "textTransform": "uppercase", "fontSize": "11px", "letterSpacing": "1px"}
GRID = lambda cols: {"display": "grid", "gridTemplateColumns": cols, "gap": "14px", "marginBottom": "14px"}

def make_gauge(name, value, status):
    L = KNOWN_LIMITS.get(name, {})
    mn = L.get("min", 0)
    mx = L.get("max", max(100, float(value) * 1.5 if value else 100))
    unit = L.get("unit", "")
    
    fig = go.Figure(go.Indicator(mode="gauge+number", value=value,
        number={"suffix": f" {unit}", "font": {"size": 18, "color": C["text"], "family": "Share Tech Mono"}, "valueformat": ".1f"},
        gauge={"axis": {"range": [mn, mx], "tickcolor": C["dim"]}, "bar": {"color": stat_color(status)},
               "bgcolor": "#0e1420", "borderwidth": 1, "bordercolor": C["border"],
               "threshold": {"line": {"color": C["blue"], "width": 2}, "thickness": 0.75, "value": value}}))
    fig.update_layout(margin={"t": 8, "b": 8, "l": 8, "r": 8}, paper_bgcolor="rgba(0,0,0,0)",
                      height=135, uirevision="const")
    return fig

def build_trends(recent, channels):
    if recent.empty or "timestamp" not in recent.columns or not channels:
        f = go.Figure(); f.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1321")
        return f
    xs = [str(pd.to_datetime(t).strftime("%H:%M:%S")) for t in recent["timestamp"]]
    fig = go.Figure()
    for i, ch in enumerate(channels):
        color = CHANNEL_COLORS[i % len(CHANNEL_COLORS)]
        L = KNOWN_LIMITS.get(ch, {})
        disp_name = L.get("name", ch.upper())
        fig.add_trace(go.Scatter(x=xs, y=recent[ch], mode="lines", line=dict(color=color, width=2), name=disp_name))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,19,33,0.65)",
                      margin=dict(l=40, r=40, t=10, b=25), hovermode="x unified", uirevision="const",
                      xaxis=dict(gridcolor=C["border"], tickfont=dict(color=C["dim"], size=9)),
                      yaxis=dict(gridcolor=C["border"], tickfont=dict(color=C["dim"], size=9)),
                      legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=9, color=C["text"])))
    return fig

def earth(frame_idx, total):
    total = max(1, total)
    r_e, r_s, inc = 6371.0, 7221.0, np.radians(65)
    lats, lons = np.meshgrid(np.linspace(-np.pi/2, np.pi/2, 30), np.linspace(-np.pi, np.pi, 30))
    traces = [go.Surface(x=r_e*np.cos(lats)*np.cos(lons), y=r_e*np.cos(lats)*np.sin(lons), z=r_e*np.sin(lats),
                         colorscale=[[0, "#0c1524"], [1, "#0e203d"]], showscale=False, opacity=0.45, hoverinfo="skip")]
    t = np.linspace(0, 2*np.pi, 120)
    traces.append(go.Scatter3d(x=r_s*np.cos(t), y=r_s*np.sin(t)*np.cos(inc), z=r_s*np.sin(t)*np.sin(inc),
                    mode="lines", line=dict(color=C["blue"], width=3), name="NOMINAL ORBIT TRACK", hoverinfo="skip"))
    ang = (frame_idx * (2*np.pi/total)) % (2*np.pi)
    hist = np.linspace(0, ang, max(2, frame_idx + 1))
    traces.append(go.Scatter3d(x=r_s*np.cos(hist), y=r_s*np.sin(hist)*np.cos(inc), z=r_s*np.sin(hist)*np.sin(inc),
                    mode="lines", line=dict(color=C["green"], width=4), name="COMPLETED FLIGHTPATH", hoverinfo="skip"))
    traces.append(go.Scatter3d(x=[r_s*np.cos(ang)], y=[r_s*np.sin(ang)*np.cos(inc)], z=[r_s*np.sin(ang)*np.sin(inc)],
                    mode="markers+text", marker=dict(size=9, color=C["green"], line=dict(color="#fff", width=2)),
                    text=["🛰️ LEO-SAT-109X"], textposition="top center",
                    textfont=dict(size=10, color="#fff", family="Share Tech Mono"), name="ACTIVE SATELLITE"))
    for nm, (gla, glo) in {"NASA Goldstone (DSN-14)": (35.4, -116.8), "Canberra (DSN-43)": (-35.4, 148.9),
                           "Madrid (DSN-63)": (40.4, -4.2)}.items():
        la, lo = np.radians(gla), np.radians(glo)
        traces.append(go.Scatter3d(x=[r_e*np.cos(la)*np.cos(lo)], y=[r_e*np.cos(la)*np.sin(lo)], z=[r_e*np.sin(la)],
                        mode="markers+text", marker=dict(size=5, color=C["orange"], symbol="diamond"),
                        text=[nm], textposition="bottom center", textfont=dict(size=8, color=C["dim"]),
                        showlegend=False, hoverinfo="skip"))
    cam = (frame_idx * 0.015) % (2*np.pi)
    fig = go.Figure(traces)
    fig.update_layout(scene=dict(xaxis_visible=False, yaxis_visible=False, zaxis_visible=False,
                                 bgcolor="rgba(0,0,0,0)", aspectmode="data",
                                 camera=dict(eye=dict(x=2.4*np.cos(cam), y=2.4*np.sin(cam), z=1.0))),
                      paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=0, b=0, l=0, r=0),
                      legend=dict(y=0.98, x=0.01, font=dict(size=9, color=C["dim"]),
                                  bgcolor="rgba(10,15,29,0.7)", bordercolor=C["border"], borderwidth=1))
    return fig

# ===========================================================================
# DASH CORE — app, layout, callbacks
# ===========================================================================
app = Dash(__name__, title="MCC // DASH CORE",
           external_stylesheets=["https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Share+Tech+Mono&display=swap"])

app.index_string = """<!DOCTYPE html>
<html>
<head>
{%metas%}
<title>{%title%}</title>
{%favicon%}
{%css%}
<style>
body{margin:0;background:#0a0f1d;color:#e2e8f0;font-family:'Share Tech Mono',monospace;}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-thumb{background:#1c2c47;border-radius:3px}
h1{font-family:'Orbitron',sans-serif}
</style>
</head>
<body>
{%app_entry%}
<footer>
{%config%}
{%scripts%}
{%renderer%}
</footer>
</body>
</html>"""

app.layout = html.Div(style={"backgroundColor": C["bg"], "color": C["text"], "minHeight": "100vh",
                             "padding": "16px", "fontFamily": "'Share Tech Mono', monospace"}, children=[
    dcc.Store(id="current-frame-store", data=0),
    dcc.Store(id="playing-store", data=True),
    dcc.Interval(id="replay-timer", interval=1500),
    dcc.Interval(id="cfg-poll", interval=2000),

    html.Div(style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                    "borderBottom": f"1px solid {C['border']}", "paddingBottom": "10px", "marginBottom": "14px"}, children=[
        html.Div([
            html.H1("🛰️ ORBITAL SATELLITE TELEMETRY MONITORING CONSOLE",
                    style={"margin": 0, "fontSize": "20px", "letterSpacing": "2px", "color": C["blue"]}),
            html.Span("FLIGHT OPERATIONS COMMAND SUITE // DASH REPLAY CORE // MISSION CONTROL LINK",
                      style={"fontSize": "10px", "color": C["dim"], "letterSpacing": "3px"}),
        ]),
        html.Div(style={"textAlign": "right"}, children=[
            html.Div("SATELLITE IDENTIFIER: LEO-SAT-109X", style={"fontSize": "12px", "fontWeight": "700", "color": C["blue"]}),
            html.Div("GROUND TRACK: COMM-STATION-ACT-04", style={"fontSize": "10px", "color": C["green"], "fontWeight": "600"}),
        ]),
    ]),

    html.Div(style={"display": "flex", "alignItems": "center", "gap": "8px", "flexWrap": "wrap",
                    "background": C["panel"], "border": f"1px solid {C['border']}", "borderRadius": "8px",
                    "padding": "10px", "marginBottom": "14px"}, children=[
        html.Button("⏮ RESET", id="btn-reset", n_clicks=0, style=BTN),
        html.Button("⏸ PAUSE", id="btn-pause-play", n_clicks=0, style={**BTN, "backgroundColor": "#2d3748"}),
        html.Button("⏭ STEP", id="btn-step", n_clicks=0, style=BTN),
        html.Div(id="transport-readout", style={"fontSize": "11px", "color": C["dim"], "marginLeft": "10px"}),
    ]),

    html.Div(style=GRID("1fr 1fr 1.2fr 1.2fr"), children=[
        html.Div(style=CARD, children=[
            html.Div("MISSION COMMAND SYSTEM STATUS", style=LBL),
            html.Div(id="mission-status-value", style={"fontSize": "20px", "fontWeight": "800", "marginTop": "8px", "color": C["green"]}),
            html.Div(id="mission-subtext", style={"fontSize": "9px", "color": C["dim"], "marginTop": "6px"}),
        ]),
        html.Div(style=CARD, children=[
            html.Div("INTELLIGENT SATELLITE HEALTH SCORE", style=LBL),
            html.Div(style={"display": "flex", "alignItems": "baseline", "gap": "6px"}, children=[
                html.Span(id="health-score-value", style={"fontSize": "30px", "fontWeight": "900", "color": C["green"]}),
                html.Span("/ 100", style={"fontSize": "12px", "color": C["dim"]}),
            ]),
            html.Div(id="health-subtext", style={"fontSize": "9px", "color": C["dim"]}),
        ]),
        html.Div(style={**CARD, "border": f"1px solid {C['blue']}"}, children=[
            html.Div("TELEMETRY REPLAY SYSTEM MODE", style={**LBL, "color": C["blue"]}),
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "8px", "marginTop": "8px"}, children=[
                html.Div([html.Div("FRAME", style={"fontSize": "8px", "color": C["dim"]}), html.Div(id="replay-frame-display", style={"fontSize": "12px", "fontWeight": "700"})]),
                html.Div([html.Div("PROGRESS", style={"fontSize": "8px", "color": C["dim"]}), html.Div(id="replay-progress-display", style={"fontSize": "12px", "fontWeight": "700"})]),
                html.Div([html.Div("STATE", style={"fontSize": "8px", "color": C["dim"]}), html.Div(id="replay-status-display", style={"fontSize": "12px", "fontWeight": "700", "color": C["green"]})]),
                html.Div([html.Div("SPEED", style={"fontSize": "8px", "color": C["dim"]}), html.Div(id="replay-speed-display", style={"fontSize": "12px", "fontWeight": "700"})]),
            ]),
        ]),
        html.Div(style=CARD, children=[
            html.Div("DURABLE DATASET SPECIFICATIONS", style=LBL),
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "8px", "marginTop": "8px", "fontSize": "11px"}, children=[
                html.Div([html.Span("TOTAL FRAMES: ", style={"color": C["dim"]}), html.Strong(id="ds-total")]),
                html.Div([html.Span("DURATION: ", style={"color": C["dim"]}), html.Strong(id="ds-duration")]),
                html.Div(id="replay-eta-display", style={"gridColumn": "span 2", "fontSize": "10px", "color": C["blue"], "fontWeight": "600"}),
            ]),
        ]),
    ]),

    # Dynamic Live Gauge Container
    html.Div(id="dynamic-gauges-container", style={"marginBottom": "14px"}),

    # Live Unified Trends
    html.Div(style=CARD, children=[
        html.Div("TELEMETRY SENSOR FLOW & HISTORICAL TREND TRACKING", style={"fontSize": "11px", "fontWeight": "700", "color": C["blue"], "marginBottom": "8px"}),
        dcc.Graph(id="live-unified-trends", style={"height": "280px"}),
    ]),

    html.Div(style={"height": "14px"}),

    html.Div(style=GRID("1.5fr 1fr"), children=[
        html.Div(style=CARD, children=[
            html.Div(style={"display": "flex", "justifyContent": "space-between"}, children=[
                html.Div("REAL-TIME CO-ALIGNMENT SAT TRACKER & EARTH GROUND PATH VISUALIZER",
                         style={"fontSize": "11px", "fontWeight": "700", "color": C["blue"], "letterSpacing": "1px"}),
                html.Span(id="current-coord-display", style={"fontSize": "10px", "color": C["green"]}),
            ]),
            dcc.Graph(id="earth-orbital-viz", style={"height": "430px"}, config={"scrollZoom": True}),
        ]),
        html.Div(style={"display": "flex", "flexDirection": "column", "gap": "14px"}, children=[
            html.Div(style=CARD, children=[
                html.Div("ACTIVE TELEMETRY EXCEPTION REGISTRY", style={"fontSize": "11px", "fontWeight": "700", "color": C["red"], "marginBottom": "8px"}),
                html.Div(style={"overflowY": "auto", "height": "190px", "border": f"1px solid {C['border']}"}, children=[
                    html.Table(style={"width": "100%", "borderCollapse": "collapse", "fontSize": "10px"}, children=[
                        html.Thead(html.Tr(style={"backgroundColor": "#172033", "textAlign": "left"}, children=[
                            html.Th(h, style={"padding": "6px"}) for h in ["FRAME", "TIME", "PARAMETER", "VALUE", "FLAG"]
                        ])),
                        html.Tbody(id="active-fault-tbody"),
                    ]),
                ]),
            ]),
            html.Div(style=CARD, children=[
                html.Div("MISSION COMM EVENT TIMELINE LOGGER", style={"fontSize": "11px", "fontWeight": "700", "color": C["green"], "marginBottom": "8px"}),
                html.Div(id="alert-timeline-log", style={"height": "180px", "overflowY": "auto", "fontSize": "10px",
                         "backgroundColor": "#0d1321", "border": f"1px solid {C['border']}", "borderRadius": "4px",
                         "padding": "8px", "lineHeight": "1.7"}),
            ]),
        ]),
    ]),
])

# ---------------- Dash callbacks ----------------
@app.callback(Output("playing-store", "data"), Input("btn-pause-play", "n_clicks"), State("playing-store", "data"))
def play_pause(n, playing):
    return True if not n else (not playing)

@app.callback(Output("btn-pause-play", "children"), Input("playing-store", "data"))
def btn_label(p): return "⏸ PAUSE" if p else "▶ PLAY"

@app.callback(Output("replay-timer", "interval"), Output("replay-timer", "disabled"),
              Input("playing-store", "data"), Input("cfg-poll", "n_intervals"))
def set_timer(playing, _):
    if not playing: return 500, True
    cfg = read_config()
    return max(50, int(SPEED_MS.get(cfg.get("speed_key", "DEMO"), 1500) / max(0.5, float(cfg.get("warp", 1.0))))), False

@app.callback(Output("current-frame-store", "data"),
              Input("replay-timer", "n_intervals"), Input("btn-step", "n_clicks"), Input("btn-reset", "n_clicks"),
              State("current-frame-store", "data"))
def cursor(tick, step, reset, cur):
    cur = 0 if cur is None else cur
    df = get_df()
    total = max(1, len(df))
    ctx = callback_context
    if not ctx.triggered:
        return 0
    trig = ctx.triggered[0]["prop_id"].split(".")[0]
    if trig == "btn-reset": return 0
    if trig == "btn-step": return min(cur + 1, total - 1)
    if cur >= total - 1:
        return 0 if read_config().get("loop", True) else cur
    return min(cur + 1, total - 1)

@app.callback(
    Output("mission-status-value", "children"), Output("mission-status-value", "style"),
    Output("mission-subtext", "children"),
    Output("health-score-value", "children"), Output("health-score-value", "style"),
    Output("health-subtext", "children"),
    Output("replay-frame-display", "children"), Output("replay-progress-display", "children"),
    Output("replay-status-display", "children"), Output("replay-status-display", "style"),
    Output("replay-speed-display", "children"), Output("ds-total", "children"),
    Output("ds-duration", "children"), Output("replay-eta-display", "children"),
    Output("dynamic-gauges-container", "children"),
    Output("live-unified-trends", "figure"),
    Output("earth-orbital-viz", "figure"), Output("current-coord-display", "children"),
    Output("active-fault-tbody", "children"), Output("alert-timeline-log", "children"),
    Output("transport-readout", "children"),
    Input("current-frame-store", "data"), State("playing-store", "data"))
def render(frame_idx, playing):
    frame_idx = 0 if frame_idx is None else frame_idx
    cfg = read_config()
    df = get_df()
    if df.empty:
        df = _ensure_status(pd.DataFrame())

    channels = get_active_channels(df)
    total = max(1, len(df))
    frame_idx = max(0, min(frame_idx, total - 1))
    sliced = df.iloc[:frame_idx + 1]
    rec = sliced.iloc[-1] if not sliced.empty else {}

    vals = {p: float(rec.get(p, 0.0)) for p in channels}
    stats = {p: str(rec.get(f"{p}_status", "NOMINAL")) for p in channels}

    health, msgs = 100, []
    for p in channels:
        s = stats.get(p, "NOMINAL")
        if "CRITICAL" in s: health -= 25; msgs.append(f"{p.upper()} CRITICAL ({vals.get(p,0):.1f})")
        elif "WARNING" in s: health -= 10; msgs.append(f"{p.upper()} WARNING ({vals.get(p,0):.1f})")
    health = max(0, health)
    h_col = C["green"] if health >= 90 else (C["orange"] if health >= 60 else C["red"])
    h_desc = ("System nominal. All channels within limits" if health >= 90 else
              "WARNING: degraded telemetry detected" if health >= 60 else "SEVERE: emergency state detected")

    if frame_idx >= total - 1 and total > 1:
        m_stat, m_col, m_sub = "MISSION REPLAY COMPLETE", C["blue"], "All recorded telemetry parsed. Awaiting reset."
    elif msgs:
        m_stat, m_col = (("CRITICAL SUBSYSTEM FAILURE", C["red"]) if health < 60 else ("DEGRADED TELEMETRY DETECTED", C["orange"]))
        m_sub = f"ALERT: {msgs[0]}"
    else:
        m_stat, m_col, m_sub = "NOMINAL TELEMETRY FLOW", C["green"], "Active ground link operational."

    prog = int(frame_idx / max(1, total - 1) * 100)
    p_state, p_col = (("REPLAY RUNNING", C["green"]) if playing and frame_idx < total - 1 else
                      (("TASK FINISHED", C["blue"]) if frame_idx >= total - 1 else ("REPLAY PAUSED", C["orange"])))
    base = SPEED_MS.get(cfg.get("speed_key", "DEMO"), 1500) / max(0.5, float(cfg.get("warp", 1.0)))
    eta = int((total - 1 - frame_idx) * base / 1000)
    try:
        d0, d1 = pd.to_datetime(df["timestamp"].iloc[0]), pd.to_datetime(df["timestamp"].iloc[-1])
        dur = f"{int((d1-d0).total_seconds())//60}m {int((d1-d0).total_seconds())%60}s"
    except Exception:
        dur = "N/A"

    # Build Dynamic Gauges
    num_cols = max(1, len(channels))
    grid_style = {"display": "grid", "gridTemplateColumns": f"repeat({num_cols}, 1fr)", "gap": "14px"}
    gauge_cards = []
    for ch in channels:
        L = KNOWN_LIMITS.get(ch, {})
        title = L.get("name", ch.upper())
        val = vals.get(ch, 0.0)
        st_val = stats.get(ch, "NOMINAL")
        fig_g = make_gauge(ch, val, st_val)
        unit = L.get("unit", "")
        gauge_cards.append(html.Div(style=CARD, children=[
            html.Div(title, style={"fontSize": "11px", "fontWeight": "700", "color": C["dim"], "textAlign": "center"}),
            dcc.Graph(figure=fig_g, config={"displayModeBar": False}, style={"height": "135px"}),
            html.Div(style={"display": "flex", "justifyContent": "space-between", "fontSize": "10px", "padding": "0 6px"}, children=[
                html.Span(["VAL: ", html.Strong(f"{val:.1f} {unit}")], style={"color": C["dim"]}),
                html.Strong(st_val, style={"color": stat_color(st_val)}),
            ]),
        ]))
    dynamic_gauges_div = html.Div(style=grid_style, children=gauge_cards)

    # Trends & Orbit Viz
    fig_trends = build_trends(sliced.tail(int(cfg.get("window", 100))), channels)
    fig_e = earth(frame_idx, total)

    inc = np.radians(65); ang = (frame_idx * (2*np.pi/total)) % (2*np.pi)
    gla = np.degrees(np.arcsin(np.sin(ang) * np.sin(inc)))
    glo = ((np.degrees(ang) + 180) % 360) - 180
    coords = f"RADIAL POS: {gla:.3f}° N, {glo:.3f}° E // ALT: 852.14 KM"

    fault_rows = []
    bad_mask = pd.Series(False, index=sliced.index)
    for p in channels:
        sc = f"{p}_status"
        if sc in sliced.columns:
            bad_mask |= ~sliced[sc].eq("NOMINAL")
    
    bad = sliced[bad_mask].tail(30).iloc[::-1]
    for idx, row in bad.iterrows():
        for p in channels:
            sc = f"{p}_status"
            if sc in row and row[sc] != "NOMINAL":
                s = row[sc]
                L = KNOWN_LIMITS.get(p, {})
                fault_rows.append(html.Tr(style={"borderBottom": f"1px solid {C['border']}"}, children=[
                    html.Td(f"FR-{idx}", style={"padding": "5px"}),
                    html.Td(str(pd.to_datetime(row["timestamp"]).strftime("%H:%M:%S")), style={"padding": "5px"}),
                    html.Td(L.get("name", p.upper()), style={"padding": "5px"}),
                    html.Td(f"{row[p]:.2f}", style={"padding": "5px"}),
                    html.Td(s, style={"padding": "5px", "color": stat_color(s), "fontWeight": "700"}),
                ]))
    if not fault_rows:
        fault_rows = [html.Tr(html.Td("NO DETECTED TELESYSTEM FAULTS", colSpan=5,
                        style={"padding": "16px", "textAlign": "center", "color": C["green"], "fontWeight": "700"}))]

    lines, prev = [], None
    for idx, row in sliced.iterrows():
        if prev is not None:
            for p in channels:
                sc = f"{p}_status"
                if sc in row and sc in prev and row[sc] != prev[sc]:
                    lines.append(html.Div([
                        html.Span(f"[{pd.to_datetime(row['timestamp']).strftime('%H:%M:%S')}] ", style={"color": C["dim"]}),
                        html.Span(f"◆ {p.upper()} TRANSITION: {prev[sc]} → {row[sc]} ({row[p]:.1f})",
                                  style={"color": stat_color(row[sc])})]))
        prev = row
    if not lines:
        lines = [html.Div("• STATION COMM LINK ESTABLISHED // LOG NOMINAL", style={"color": C["green"]})]

    readout = f"FRAME {frame_idx+1}/{total} · {prog}% · {p_state} · SPEED {cfg.get('speed_key','DEMO')} ({cfg.get('warp',1.0)}x)"

    return (m_stat, {"fontSize": "20px", "fontWeight": "800", "marginTop": "8px", "color": m_col}, m_sub,
            str(health), {"fontSize": "30px", "fontWeight": "900", "color": h_col}, h_desc,
            f"FRAME {frame_idx+1} / {total}", f"{prog}% COMPLETE",
            p_state, {"fontSize": "12px", "fontWeight": "700", "color": p_col},
            f"{cfg.get('speed_key','DEMO')} ({cfg.get('warp',1.0)}x)", str(total), dur,
            f"EST. ETA COMPLETE: {eta}s" if eta > 0 else "TASK COMPLETE",
            dynamic_gauges_div,
            fig_trends,
            fig_e, coords, fault_rows, html.Div(lines[::-1][-60:]), readout)

# ===========================================================================
# BOOT DASH CORE IN BACKGROUND THREAD (Safe Singleton)
# ===========================================================================
def _port_open(port):
    s = socket.socket()
    s.settimeout(0.3)
    try:
        s.connect(("localhost", port))
        return True
    except Exception:
        return False
    finally:
        s.close()

@st.cache_resource
def start_dash_server():
    if not _port_open(DASH_PORT):
        t = threading.Thread(target=lambda: app.run(host="127.0.0.1", port=DASH_PORT,
                                                    debug=False, use_reloader=False),
                             daemon=True)
        t.start()
        time.sleep(0.5)
    return True

if _UNDER_RT:
    start_dash_server()

# ===========================================================================
# STREAMLIT SHELL UI
# ===========================================================================
if _UNDER_RT:
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Share+Tech+Mono&display=swap');
    html, body, [class*="css"] {{ font-family: 'Share Tech Mono', monospace; }}
    .stApp {{ background: radial-gradient(ellipse at top, #0d1626 0%, {BG} 60%); color: #d7f4ff; }}
    [data-testid="stSidebar"] {{ background: {PANEL}; border-right: 1px solid #16233a; }}
    .mcc-title {{ font-family:'Orbitron'; font-weight:900; font-size:22px; color:#eaffff;
                  text-shadow:0 0 12px rgba(56,189,248,.45); }}
    .badge {{ display:inline-block; padding:3px 10px; border-radius:3px; font-family:'Orbitron';
              font-weight:700; font-size:10.5px; letter-spacing:1.5px; }}
    .badge-on {{ background:rgba(34,255,136,.1); color:{GREEN}; border:1px solid {GREEN}; }}
    .badge-off {{ background:rgba(255,59,59,.1); color:{RED}; border:1px solid {RED}; }}
    .graf-btn {{
        display: inline-block;
        padding: 10px 20px;
        background: linear-gradient(135deg, #ff6b00, #ff8800);
        color: white !important;
        font-family: 'Orbitron', sans-serif;
        font-weight: 700;
        text-decoration: none;
        border-radius: 6px;
        box-shadow: 0 4px 14px rgba(255,107,0,0.4);
        margin-bottom: 15px;
    }}
    .graf-btn:hover {{
        background: linear-gradient(135deg, #ff8800, #ffa500);
        color: white !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    def ping(url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return True
        except urllib.error.HTTPError:
            return True
        except Exception:
            return False

    st.sidebar.markdown("### 🛰️ MISSION CONFIG")
    csv_path = st.sidebar.text_input("Live telemetry CSV", value=DEFAULT_CSV, key="cfg_csv") or DEFAULT_CSV
    window = st.sidebar.slider("Chart window (last N readings)", 20, 500, 100, step=10, key="cfg_window") or 100
    speed_key = st.sidebar.radio("Replay speed", ["FAST", "NORMAL", "DEMO"], index=2, key="cfg_speed") or "DEMO"
    warp = st.sidebar.slider("Time dilation (x)", 0.5, 10.0, 1.0, 0.5, key="cfg_warp") or 1.0
    loop = st.sidebar.checkbox("Loop back to frame 1 at the end", value=True, key="cfg_loop")
    grafana_url = st.sidebar.text_input("Grafana URL", value="http://localhost:3000", key="cfg_grafana") or "http://localhost:3000"

    save_config({"csv_path": csv_path, "speed_key": speed_key, "warp": warp, "loop": loop, "window": window})

    dash_on = _port_open(DASH_PORT) or ping(f"http://localhost:{DASH_PORT}")
    graf_on = ping("http://localhost:3000")

    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
      <div><div class="mcc-title">🛰️ ORBITAL SATELLITE TELEMETRY MONITORING CONSOLE</div>
      <div style="color:{DIM}; font-size:10px; letter-spacing:3px;">V5 UNIFIED STACK // STREAMLIT SHELL + DASH CORE + GRAFANA WALL + PLOTLY ENGINE</div></div>
      <div style="text-align:right;">
        <span class="badge {'badge-on' if dash_on else 'badge-off'}">DASH CORE: {'ONLINE' if dash_on else 'BOOTING…'}</span>&nbsp;
        <span class="badge {'badge-on' if graf_on else 'badge-off'}">GRAFANA: {'ONLINE' if graf_on else 'OFFLINE'}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    tab_console, tab_graf, tab_report = st.tabs(["🎛️ LIVE CONSOLE (DASH)", "📡 GRAFANA TELEMETRY WALL", "📋 MISSION REPORT (V3)"])

    with tab_console:
        if dash_on:
            components.iframe(f"http://localhost:{DASH_PORT}", height=1150, scrolling=True)
        else:
            st.warning("⚠️ DASH CORE booting — please refresh in 2 seconds.")

    with tab_graf:
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; background:#121826; padding:16px; border-radius:8px; border:1px solid #1f2a40; margin-bottom:18px;">
            <div>
                <div style="font-family:'Orbitron'; font-size:16px; font-weight:700; color:#00d2ff;">🛰️ GRAFANA MISSION WALL LAUNCHER</div>
                <div style="font-size:11px; color:#94a3b8; margin-top:4px;">Launch your high-refresh multi-screen Grafana dashboard in full standalone operations mode.</div>
            </div>
            <a href="{grafana_url}" target="_blank" class="graf-btn">🚀 OPEN GRAFANA (FULLSCREEN ↗)</a>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div style="color:#00d2ff; font-family:Orbitron; letter-spacing:2px; font-size:13px; margin: 16px 0 10px 0;">🔴 LIVE TELEMETRY WALL (REAL-TIME STREAM)</div>', unsafe_allow_html=True)
        wdf = get_df()
        if not wdf.empty:
            active_ch = get_active_channels(wdf)
            wx = [pd.to_datetime(t).strftime("%H:%M:%S") for t in wdf["timestamp"]]
            
            def wall_panel(y, name, color, unit):
                fig = go.Figure(go.Scatter(x=wx, y=y, mode="lines", line=dict(color=color, width=2), name=name))
                fig.update_layout(height=260, margin=dict(l=35, r=10, t=24, b=25),
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d1321",
                                  title=dict(text=f"{name} ({unit})", font=dict(size=11, color=color)),
                                  xaxis=dict(gridcolor="#1f2a40", tickfont=dict(size=8, color="#94a3b8")),
                                  yaxis=dict(gridcolor="#1f2a40", tickfont=dict(size=8, color="#94a3b8")))
                return fig
            
            cols = st.columns(min(len(active_ch), 3))
            for idx, ch in enumerate(active_ch):
                col_idx = idx % len(cols)
                L = KNOWN_LIMITS.get(ch, {})
                title = L.get("name", ch.upper())
                color = CHANNEL_COLORS[idx % len(CHANNEL_COLORS)]
                unit = L.get("unit", "")
                with cols[col_idx]:
                    st.plotly_chart(wall_panel(wdf[ch], title, color, unit), use_container_width=True, config={"displayModeBar": False})

    with tab_report:
        if st.button("🔄 REFRESH REPORT", key="btn_refresh_report"):
            st.cache_data.clear()
        rc1, rc2 = st.columns(2)
        dfr = get_df()
        if dfr is not None and not dfr.empty:
            active_ch = get_active_channels(dfr)
            with rc1:
                st.markdown(f'<div style="color:{RED}; font-family:Orbitron; letter-spacing:2px; font-size:12px; margin-bottom:8px;">ACTIVE TELEMETRY EXCEPTION REGISTRY</div>', unsafe_allow_html=True)
                scols = [f"{c}_status" for c in active_ch if f"{c}_status" in dfr.columns]
                if scols:
                    norm = lambda s: "NOMINAL" if "NOMINAL" in set(s) else "Normal"
                    mask = pd.concat([dfr[c] != norm(dfr[c]) for c in scols], axis=1).any(axis=1)
                    st.dataframe(dfr[mask].tail(50), height=380, use_container_width=True)
                else:
                    st.caption("No status columns in CSV.")
            with rc2:
                st.markdown(f'<div style="color:{GREEN}; font-family:Orbitron; letter-spacing:2px; font-size:12px; margin-bottom:8px;">V3 HEALTH OVERVIEW</div>', unsafe_allow_html=True)
                v3 = resolve_path("../Version_3/health_scores.json")
                if os.path.exists(v3):
                    scores = json.load(open(v3))
                    for label, key in [("Battery", "Battery_score"), ("Thermal", "Thermal_score"),
                                       ("Overall", "Overall_score")]:
                        if key in scores:
                            v = scores.get(key, 0)
                            col = GREEN if v >= 75 else ("#ffb300" if v >= 40 else RED)
                            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px dashed #16233a;font-size:12.5px;"><span style="color:{DIM};">{label} score</span><span style="color:{col};font-weight:700;">{v}</span></div>', unsafe_allow_html=True)
                else:
                    st.caption("No `health_scores.json` found in Version_3 directory.")
        else:
            st.warning("Telemetry CSV not readable.")

    st.markdown(f'<div style="margin-top:10px;border-top:1px solid #16233a;padding-top:6px;color:#3a5670;font-size:10.5px;letter-spacing:1px;">SATELLITE TELEMETRY HEALTH MONITORING SYSTEM · V5 UNIFIED MISSION CONTROL · ONE FILE · STREAMLIT + DASH + GRAFANA + PLOTLY</div>', unsafe_allow_html=True)

# ===========================================================================
# SAFE RUNTIME ENTRYPOINT
# ===========================================================================
if __name__ == "__main__" and not _UNDER_RT:
    from streamlit.web import cli as stcli
    sys.argv = ["streamlit", "run", os.path.abspath(__file__)]
    sys.exit(stcli.main())