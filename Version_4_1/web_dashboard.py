#!/usr/bin/env python3
"""
SATELLITE TELEMETRY HEALTH MONITORING DASHBOARD (FINAL DASH VERSION)
Senior Aerospace Telemetry Operations Software Engineer
"""

import os
import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State, callback_context

# ==========================================
# 1. CONSTANTS & SYSTEM CONFIGURATION
# ==========================================
DATA_FILE = "data/telemetry_log.csv"
REPLAY_MODE = True

# Replay speeds in milliseconds for 1x reference
FAST_BASE = 250
NORMAL_BASE = 1000
DEMO_BASE = 1500

DEFAULT_SPEED_KEY = "DEMO"

# Limits and Nominal Conditions for telemetry validation
LIMITS = {
    "temperature": {"warn_high": 30.0, "crit_high": 45.0, "unit": "°C", "color": "#ff4d4d"},
    "battery": {"warn_low": 85.0, "crit_low": 75.0, "unit": "%", "color": "#39ff14"},
    "voltage": {"warn_low": 28.0, "crit_low": 26.5, "warn_high": 35.0, "crit_high": 40.0, "unit": "V", "color": "#1f77b4"},
    "fuel": {"warn_low": 20.0, "crit_low": 5.0, "unit": "%", "color": "#ffaa00"},
}

# Ensure data directory exists and has fallback data if needed
if not os.path.exists("data"):
    os.makedirs("data")

if not os.path.exists(DATA_FILE):
    # Safe guard fallback data generation
    timestamps = [
        (datetime.datetime.utcnow() + datetime.timedelta(seconds=10 * i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for i in range(60)
    ]
    # Simple sine and linear values
    df_temp = 20.0 + 5.0 * np.sin(np.linspace(0, 10, 60))
    df_temp[18:28] += 25.0  # Simulated heat spike anomaly
    df_batt = np.clip(100.0 - 0.25 * np.arange(60), 0, 100)
    df_batt[34:42] -= 10.0  # Battery discharge anomaly
    df_volt = 32.4 + 0.1 * np.random.randn(60)
    df_volt[34:42] -= 4.0
    df_fuel = np.clip(100.0 - 0.12 * np.arange(60), 0, 100)

    # Compile status arrays
    temp_status = []
    for t in df_temp:
        if t >= LIMITS["temperature"]["crit_high"]: temp_status.append("CRITICAL_HIGH")
        elif t >= LIMITS["temperature"]["warn_high"]: temp_status.append("WARNING_HIGH")
        else: temp_status.append("NOMINAL")

    battery_status = []
    for b in df_batt:
        if b <= LIMITS["battery"]["crit_low"]: battery_status.append("CRITICAL_LOW")
        elif b <= LIMITS["battery"]["warn_low"]: battery_status.append("WARNING_LOW")
        else: battery_status.append("NOMINAL")

    voltage_status = []
    for v in df_volt:
        if v <= LIMITS["voltage"]["crit_low"] or v >= LIMITS["voltage"]["crit_high"]: voltage_status.append("CRITICAL")
        elif v <= LIMITS["voltage"]["warn_low"] or v >= LIMITS["voltage"]["warn_high"]: voltage_status.append("WARNING")
        else: voltage_status.append("NOMINAL")

    fuel_status = ["NOMINAL"] * 60

    fallback_df = pd.DataFrame({
        "timestamp": timestamps,
        "temperature": np.round(df_temp, 2),
        "battery": np.round(df_batt, 2),
        "voltage": np.round(df_volt, 2),
        "fuel": np.round(df_fuel, 2),
        "temp_status": temp_status,
        "battery_status": battery_status,
        "voltage_status": voltage_status,
        "fuel_status": fuel_status
    })
    fallback_df.to_csv(DATA_FILE, index=False)

# Load global dataset references
df_master = pd.read_csv(DATA_FILE)
TOTAL_ROWS = len(df_master)

# Calc static metrics for Dataset Stats panel
first_ts = df_master.iloc[0]["timestamp"]
last_ts = df_master.iloc[-1]["timestamp"]
try:
    dt_start = pd.to_datetime(first_ts)
    dt_end = pd.to_datetime(last_ts)    
    duration_sec = int((dt_end - dt_start).total_seconds())
    duration_str = f"{duration_sec // 60}m {duration_sec % 60}s"
except Exception:
    duration_str = "N/A"

# ==========================================
# 2. PURE DASH STYLING DEFINITIONS (NO TAILWIND)
# ==========================================
COLORS = {
    "bg_dark": "#0a0f1d",       # Outer vacuum midnight
    "panel_bg": "#121826",      # Sleek aerospace graphite panel
    "border_color": "#1f2a40",  # Structural rivet steel
    "text": "#e2e8f0",          # Star-white readability
    "text_dark": "#94a3b8",     # Muted telemetry text
    "accent_blue": "#00d2ff",   # Laser ion beam blue
    "green": "#39ff14",         # Safe glowing green
    "orange": "#ffb000",        # Warning orange alert
    "red": "#ff4d4d",           # Critical solar flare red
}

PAGE_STYLE = {
    "backgroundColor": COLORS["bg_dark"],
    "color": COLORS["text"],
    "fontFamily": "Inter, 'Segoe UI', system-ui, sans-serif",
    "margin": "0",
    "padding": "24px",
    "minHeight": "100vh"
}

HEADER_STYLE = {
    "display": "flex",
    "justifyContent": "space-between",
    "alignItems": "center",
    "borderBottom": f"1px solid {COLORS['border_color']}",
    "paddingBottom": "16px",
    "marginBottom": "24px"
}

TITLE_STYLE = {
    "margin": "0",
    "fontSize": "26px",
    "fontWeight": "700",
    "textTransform": "uppercase",
    "letterSpacing": "2px",
    "color": COLORS["accent_blue"],
    "display": "flex",
    "alignItems": "center",
    "gap": "10px"
}

CARD_STYLE = {
    "backgroundColor": COLORS["panel_bg"],
    "borderRadius": "8px",
    "border": f"1px solid {COLORS['border_color']}",
    "padding": "16px",
    "boxShadow": "0 6px 16px rgba(0, 0, 0, 0.4)",
}

GRID_KPI = {
    "display": "grid",
    "gridTemplateColumns": "1fr 1fr 1fr 1.2fr",
    "gap": "16px",
    "marginBottom": "20px"
}

GRID_TELEMETRY = {
    "display": "grid",
    "gridTemplateColumns": "repeat(4, 1fr)",
    "gap": "16px",
    "marginBottom": "20px"
}

GRID_CHARTS = {
    "display": "grid",
    "gridTemplateColumns": "1fr 1fr",
    "gap": "16px",
    "marginBottom": "20px"
}

GRID_INTEL = {
    "display": "grid",
    "gridTemplateColumns": "1.2fr 1fr 0.8fr",
    "gap": "16px",
    "marginBottom": "20px"
}

BUTTON_STYLE = {
    "backgroundColor": "#1d273a",
    "color": COLORS["text"],
    "border": f"1px solid {COLORS['accent_blue']}",
    "borderRadius": "4px",
    "padding": "8px 16px",
    "cursor": "pointer",
    "fontWeight": "600",
    "textTransform": "uppercase",
    "fontSize": "11px",
    "letterSpacing": "1px",
    "transition": "all 0.2s ease-in-out",
}

CONTROL_PANEL_STYLE = {
    "display": "flex",
    "alignItems": "center",
    "gap": "8px",
    "flexWrap": "wrap"
}

TABLE_STYLE = {
    "width": "100%",
    "borderCollapse": "collapse",
    "fontSize": "12px",
    "color": COLORS["text"]
}

# ==========================================
# 3. APP INITIALIZATION & LAYOUT
# ==========================================
app = Dash(__name__, title="Satellite Health Telemetry Console")
# Exposing server for production execution CJS compliance
server = app.server

app.layout = html.Div(style=PAGE_STYLE, children=[
    # Global state management stores
    dcc.Store(id="current-frame-store", data=0),
    dcc.Store(id="playing-store", data=True),
    dcc.Store(id="speed-multiplier-store", data=1.0),
    
    # Static config storage
    dcc.Interval(id="replay-timer", interval=int(DEMO_BASE), disabled=False),

    # --- TOP CAP HEADER ---
    html.Header(style=HEADER_STYLE, children=[
        html.Div(children=[
            html.H1("🛰️ ORBITAL SATELLITE TELEMETRY MONITORING CONSOLE", style=TITLE_STYLE),
            html.Span("FLIGHT OPERATIONS COMMAND SUITE // MISSION CONTROL SATELLITE LINK", 
                      style={"fontSize": "11px", "color": COLORS["text_dark"], "letterSpacing": "3px", "fontWeight": "600"})
        ]),
        html.Div(style={"textAlign": "right"}, children=[
            html.Div("SATELLITE IDENTIFIER: LEO-SAT-109X", style={"fontSize": "13px", "fontWeight": "bold", "color": COLORS["accent_blue"]}),
            html.Div("GROUND TRACK: COMM-STATION-ACT-04", style={"fontSize": "10px", "color": COLORS["green"], "marginTop": "4px", "fontWeight": "600"})
        ])
    ]),

    # --- ROW 1: TOP KPI CARDS ---
    html.Div(style=GRID_KPI, children=[
        # Card 1: Mission Status
        html.Div(style=CARD_STYLE, children=[
            html.Div("MISSION COMMAND SYSTEM STATUS", style={"fontSize": "11px", "color": COLORS["text_dark"], "letterSpacing": "1px", "fontWeight": "bold"}),
            html.Div(id="mission-status-value", children="NOMINAL OPERATIONS", 
                     style={"fontSize": "22px", "fontWeight": "800", "marginTop": "10px", "color": COLORS["green"]}),
            html.Div(id="mission-subtext", children="AUTO-MONITORING LIVE TRACK ACTIVE", 
                     style={"fontSize": "10px", "color": COLORS["text_dark"], "marginTop": "6px", "letterSpacing": "0.5px"})
        ]),
        # Card 2: Health Score Card
        html.Div(style=CARD_STYLE, children=[
            html.Div("INTELLIGENT SATELLITE HEALTH SCORE", style={"fontSize": "11px", "color": COLORS["text_dark"], "letterSpacing": "1px", "fontWeight": "bold"}),
            html.Div(style={"display": "flex", "alignItems": "baseline", "gap": "8px", "marginTop": "6px"}, children=[
                html.Span(id="health-score-value", children="100", 
                          style={"fontSize": "32px", "fontWeight": "900", "color": COLORS["green"]}),
                html.Span("/ 100", style={"fontSize": "14px", "color": COLORS["text_dark"]})
            ]),
            html.Div(id="health-subtext", children="All subsystems reporting within limits", 
                     style={"fontSize": "10px", "color": COLORS["text_dark"], "marginTop": "2px"})
        ]),
        # Card 3: Telemetry Replay Status Panel
        html.Div(style={**CARD_STYLE, "border": f"1px solid {COLORS['accent_blue']}"}, children=[
            html.Div("TELEMETRY REPLAY SYSTEM MODE", style={"fontSize": "11px", "color": COLORS["accent_blue"], "letterSpacing": "1.5px", "fontWeight": "bold"}),
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "10px", "marginTop": "10px"}, children=[
                html.Div([
                    html.Div("FRAME STATUS", style={"fontSize": "9px", "color": COLORS["text_dark"]}),
                    html.Div(id="replay-frame-display", style={"fontSize": "13px", "fontWeight": "700"}),
                ]),
                html.Div([
                    html.Div("PROGRESS %", style={"fontSize": "9px", "color": COLORS["text_dark"]}),
                    html.Div(id="replay-progress-display", style={"fontSize": "13px", "fontWeight": "700"}),
                ]),
                html.Div([
                    html.Div("PLAYBACK STATE", style={"fontSize": "9px", "color": COLORS["text_dark"]}),
                    html.Div(id="replay-status-display", style={"fontSize": "13px", "fontWeight": "700", "color": COLORS["green"]}),
                ]),
                html.Div([
                    html.Div("ACTIVE REPLAY SPEED", style={"fontSize": "9px", "color": COLORS["text_dark"]}),
                    html.Div(id="replay-speed-display", style={"fontSize": "13px", "fontWeight": "700"}),
                ])
            ])
        ]),
        # Card 4: Dataset Statistics
        html.Div(style=CARD_STYLE, children=[
            html.Div("DURABLE DATASET SPECIFICATIONS", style={"fontSize": "11px", "color": COLORS["text_dark"], "letterSpacing": "1px", "fontWeight": "bold"}),
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1.2fr", "gap": "8px", "marginTop": "8px", "fontSize": "11px"}, children=[
                html.Div([
                    html.Span("TOTAL FRAMES: ", style={"color": COLORS["text_dark"]}),
                    html.Strong(str(TOTAL_ROWS))
                ]),
                html.Div([
                    html.Span("DURATION: ", style={"color": COLORS["text_dark"]}),
                    html.Strong(duration_str)
                ]),
                html.Div([
                    html.Span("FIRST TIME: ", style={"color": COLORS["text_dark"]}),
                    html.Strong(pd.to_datetime(first_ts).strftime("%H:%M:%S"), style={"fontSize": "10px"})
                ]),
                html.Div([
                    html.Span("LAST TIME: ", style={"color": COLORS["text_dark"]}),
                    html.Strong(pd.to_datetime(last_ts).strftime("%H:%M:%S"), style={"fontSize": "10px"})
                ]),
            ]),
            html.Div(id="replay-eta-display", style={"fontSize": "10px", "color": COLORS["accent_blue"], "marginTop": "8px", "fontWeight": "600"})
        ])
    ]),

    # --- ROW 2: TELEMETRY GAUGES CARD ROW ---
    html.Div(style=GRID_TELEMETRY, children=[
        # Temperature Subsystem
        html.Div(style=CARD_STYLE, children=[
            html.Div("CHASSIS TEMPERATURE", style={"fontSize": "12px", "fontWeight": "bold", "color": COLORS["text_dark"], "textAlign": "center"}),
            dcc.Graph(id="temperature-gauge", config={"displayModeBar": False}, style={"height": "140px"}),
            html.Div(style={"display": "flex", "justifyContent": "space-between", "fontSize": "11px", "marginTop": "4px", "padding": "0 8px"}, children=[
                html.Span("VAL: ", style={"color": COLORS["text_dark"]}),
                html.Strong(id="temperature-value-text", style={"color": COLORS["accent_blue"]}),
                html.Span("STATE: ", style={"color": COLORS["text_dark"]}),
                html.Strong(id="temperature-status-text")
            ])
        ]),
        # Battery Subsystem
        html.Div(style=CARD_STYLE, children=[
            html.Div("SOLID STATE BATTERY (SOC)", style={"fontSize": "12px", "fontWeight": "bold", "color": COLORS["text_dark"], "textAlign": "center"}),
            dcc.Graph(id="battery-gauge", config={"displayModeBar": False}, style={"height": "140px"}),
            html.Div(style={"display": "flex", "justifyContent": "space-between", "fontSize": "11px", "marginTop": "4px", "padding": "0 8px"}, children=[
                html.Span("VAL: ", style={"color": COLORS["text_dark"]}),
                html.Strong(id="battery-value-text", style={"color": COLORS["green"]}),
                html.Span("STATE: ", style={"color": COLORS["text_dark"]}),
                html.Strong(id="battery-status-text")
            ])
        ]),
        # Voltage Subsystem
        html.Div(style=CARD_STYLE, children=[
            html.Div("BUS VOLTAGE REGULATION", style={"fontSize": "12px", "fontWeight": "bold", "color": COLORS["text_dark"], "textAlign": "center"}),
            dcc.Graph(id="voltage-gauge", config={"displayModeBar": False}, style={"height": "140px"}),
            html.Div(style={"display": "flex", "justifyContent": "space-between", "fontSize": "11px", "marginTop": "4px", "padding": "0 8px"}, children=[
                html.Span("VAL: ", style={"color": COLORS["text_dark"]}),
                html.Strong(id="voltage-value-text", style={"color": COLORS["accent_blue"]}),
                html.Span("STATE: ", style={"color": COLORS["text_dark"]}),
                html.Strong(id="voltage-status-text")
            ])
        ]),
        # Fuel Subsystem
        html.Div(style=CARD_STYLE, children=[
            html.Div("PROPELLANT PRESSURE & FUEL", style={"fontSize": "12px", "fontWeight": "bold", "color": COLORS["text_dark"], "textAlign": "center"}),
            dcc.Graph(id="fuel-gauge", config={"displayModeBar": False}, style={"height": "140px"}),
            html.Div(style={"display": "flex", "justifyContent": "space-between", "fontSize": "11px", "marginTop": "4px", "padding": "0 8px"}, children=[
                html.Span("VAL: ", style={"color": COLORS["text_dark"]}),
                html.Strong(id="fuel-value-text", style={"color": COLORS["orange"]}),
                html.Span("STATE: ", style={"color": COLORS["text_dark"]}),
                html.Strong(id="fuel-status-text")
            ])
        ])
    ]),

    # --- ROW 3: SENSOR HISTORIC TRENDS ---
    html.Div(style=GRID_CHARTS, children=[
        html.Div(style=CARD_STYLE, children=[
            html.Div("THERMAL / POWER REGULATION TRACKING", style={"fontSize": "12px", "fontWeight": "bold", "marginBottom": "8px", "color": COLORS["accent_blue"]}),
            dcc.Graph(id="thermal-power-trends", style={"height": "285px"})
        ]),
        html.Div(style=CARD_STYLE, children=[
            html.Div("BUS POTENTIALS / FUEL FLOW DEPLETION TRACKING", style={"fontSize": "12px", "fontWeight": "bold", "marginBottom": "8px", "color": COLORS["accent_blue"]}),
            dcc.Graph(id="bus-fuel-trends", style={"height": "285px"})
        ])
    ]),

    # --- ROW 4: INTELLIGENCE PANEL & REPLAY CONTROLS ---
    html.Div(style=GRID_INTEL, children=[
        # Panel A: Deep Diagnostics Active Fault Table
        html.Div(style=CARD_STYLE, children=[
            html.Div("ACTIVE TELEMETRY EXCEPTION REGISTRY", style={"fontSize": "12px", "fontWeight": "bold", "marginBottom": "12px", "color": COLORS["red"]}),
            html.Div(style={"overflowY": "auto", "height": "210px", "border": f"1px solid {COLORS['border_color']}"}, children=[
                html.Table(id="active-fault-table", style=TABLE_STYLE, children=[
                    html.Thead(children=[
                        html.Tr(style={"backgroundColor": "#172033", "textAlign": "left", "borderBottom": f"1px solid {COLORS['border_color']}"}, children=[
                            html.Th("FRAME ID", style={"padding": "8px"}),
                            html.Th("TIMESTAMP", style={"padding": "8px"}),
                            html.Th("PARAMETER", style={"padding": "8px"}),
                            html.Th("VALUE", style={"padding": "8px"}),
                            html.Th("ANOMALY FLAG", style={"padding": "8px"}),
                        ])
                    ]),
                    html.Tbody(id="active-fault-tbody")
                ])
            ])
        ]),

        # Panel B: Alert Status Event Log Timeline
        html.Div(style=CARD_STYLE, children=[
            html.Div("MISSION COMM EVENT TIMELINE LOGGER", style={"fontSize": "12px", "fontWeight": "bold", "marginBottom": "12px", "color": COLORS["green"]}),
            html.Div(id="alert-timeline-log", style={
                "height": "210px", "overflowY": "auto", "fontSize": "11px", "padding": "8px",
                "backgroundColor": "#0d1321", "borderRadius": "4px", "border": f"1px solid {COLORS['border_color']}",
                "lineHeight": "1.6", "fontFamily": "Courier New, monospace"
            })
        ]),

        # Panel C: Replay Hardware Controls
        html.Div(style=CARD_STYLE, children=[
            html.Div("MISSION SIMULATION PLAYBACK CONTROL", style={"fontSize": "12px", "fontWeight": "bold", "marginBottom": "12px", "color": COLORS["accent_blue"]}),
            
            # Button Suite
            html.Div(style=CONTROL_PANEL_STYLE, children=[
                html.Button("◀◀ RESET", id="btn-reset", n_clicks=0, style={**BUTTON_STYLE, "flex": "1"}),
                html.Button("⏸ PAUSE", id="btn-pause-play", n_clicks=0, style={**BUTTON_STYLE, "flex": "1", "backgroundColor": "#2d3748"}),
                html.Button("▶ STEP", id="btn-step", n_clicks=0, style={**BUTTON_STYLE, "flex": "1"}),
            ]),

            html.Div(style={"marginTop": "24px"}, children=[
                html.Div("SET SIMULATION REPLAY BASE SPEED", style={"fontSize": "10px", "fontWeight": "600", "color": COLORS["text_dark"], "marginBottom": "10px"}),
                dcc.RadioItems(
                    id="radio-speed-base",
                    options=[
                        {"label": " FAST (250ms)", "value": "FAST"},
                        {"label": " NORMAL (1000ms)", "value": "NORMAL"},
                        {"label": " DEMO (1500ms)", "value": "DEMO"},
                    ],
                    value="DEMO",
                    style={"fontSize": "11px", "display": "flex", "flexDirection": "column", "gap": "6px"}
                )
            ]),

            # Speed Multipliers Slider
            html.Div(style={"marginTop": "20px"}, children=[
                html.Div("HARDWARE TIME DILATION SCALER", style={"fontSize": "9px", "fontWeight": "700", "color": COLORS["text_dark"], "marginBottom": "6px"}),
                dcc.Slider(
                    id="slider-time-warp",
                    min=0.5,
                    max=10.0,
                    step=0.5,
                    value=1.0,
                    marks={0.5: "0.5x", 1.0: "1x", 2.0: "2x", 5.0: "5x", 10.0: "10x"},
                    className="slider-warp"
                )
            ])
        ])
    ]),

    # --- ROW 5: EXPANSIVE 3D EARTH ORBITING RENDER ---
    html.Div(style=GRID_CHARTS, children=[
        html.Div(style={**CARD_STYLE, "gridColumn": "span 2"}, children=[
            html.Div(style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "12px"}, children=[
                html.Div("REAL-TIME CO-ALIGNMENT SAT TRACKER & EARTH GROUND PATH VISUALIZER", 
                         style={"fontSize": "13px", "fontWeight": "bold", "color": COLORS["accent_blue"], "letterSpacing": "1px"}),
                html.Span(id="current-coord-display", style={"fontSize": "11px", "fontFamily": "monospace", "color": COLORS["green"]})
            ]),
            dcc.Graph(id="earth-orbital-viz", style={"height": "480px"}, config={"scrollZoom": True})
        ])
    ])
])

# ==========================================
# 4. GAUGE & CHART PLOT IMPLEMENTATIONS
# ==========================================
def create_gauge_figure(value, min_val, max_val, label, unit, current_status):
    # Select color state
    if "CRITICAL" in current_status:
        indicator_color = COLORS["red"]
    elif "WARNING" in current_status:
        indicator_color = COLORS["orange"]
    else:
        indicator_color = COLORS["green"]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        number={
            'suffix': f" {unit}",
            'font': {'size': 20, 'color': COLORS["text"], 'family': 'sans-serif'},
            'valueformat': '.1f'
        },
        gauge={
            'axis': {'range': [min_val, max_val], 'tickwidth': 1, 'tickcolor': COLORS["text_dark"]},
            'bar': {'color': indicator_color},
            'bgcolor': '#0e1420',
            'borderwidth': 1,
            'bordercolor': COLORS["border_color"],
            'steps': [
                {'range': [min_val, max_val], 'color': 'rgba(0,0,0,0)'}
            ],
            'threshold': {
                'line': {'color': COLORS["accent_blue"], 'width': 2},
                'thickness': 0.75,
                'value': value
            }
        }
    ))

    fig.update_layout(
        margin={'t': 10, 'b': 10, 'l': 10, 'r': 10},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=140
    )
    return fig


# ==========================================
# 5. HIGH-FIDELITY EARTH VISUALIZATION (3D)
# ==========================================
def create_earth_figure(frame_idx):
    # Base geophysics coordinate model
    # Generating coordinates for smooth Earth sphere mesh
    lats = np.linspace(-np.pi/2, np.pi/2, 35)
    lons = np.linspace(-np.pi, np.pi, 35)
    lats, lons = np.meshgrid(lats, lons)
    
    # Calculate cartesian coordinates
    r_earth = 6371  # kilometers radius
    x = r_earth * np.cos(lats) * np.cos(lons)
    y = r_earth * np.cos(lats) * np.sin(lons)
    z = r_earth * np.sin(lats)

    # Continent maps (simplified vector outlines of major landmasses)
    features_data = []

    # Simple coordinate boundaries of landmasses to look like high-tech vector continents
    continents_lon = [
        # Americas
        [-80, -70, -60, -50, -40, -40, -50, -60, -70, -80, -90, -100, -120, -120, -100, -80],
        [-80, -70, -80], # South peak
        # Afro-Eurasia
        [10, 20, 30, 40, 50, 60, 80, 100, 120, 140, 130, 100, 80, 60, 40, 20, 0, -10, -10, 0, 10],
        # Australia
        [115, 125, 135, 145, 150, 140, 120, 115],
        # Antarctica
        [-180, 180, 180]
    ]
    continents_lat = [
        # Americas
        [5, -10, -20, -40, -50, -45, -30, -15, -5, 10, 15, 20, 35, 60, 50, 5],
        [-50, -55, -50],
        # Afro-Eurasia
        [10, 5, 15, 25, 15, 25, 30, 20, 30, 50, 60, 40, 10, -10, -30, -30, -10, 10, 30, 40, 10],
        # Australia
        [-25, -20, -15, -20, -30, -35, -30, -25],
        # Antarctica
        [-80, -85, -80]
    ]

    # Render Earth base wireframe/grid sphere mesh
    # Trace for water body representation
    sphere_trace = go.Surface(
        x=x, y=y, z=z,
        colorscale=[[0, '#0c1524'], [1, '#0e203d']],
        showscale=False,
        opacity=0.45,
        hoverinfo="skip"
    )

    # Orbit path parameters (polar orbits / flight dynamics)
    num_vals = 120
    orbit_t = np.linspace(0, 2 * np.pi, num_vals)
    # Give inclination of 65 degrees
    inc = np.radians(65)
    r_sat = r_earth + 850  # LEO Satellite Altitude ~850km
    
    sat_x = r_sat * np.cos(orbit_t)
    sat_y = r_sat * np.sin(orbit_t) * np.cos(inc)
    sat_z = r_sat * np.sin(orbit_t) * np.sin(inc)

    # Plot orbit path (glowing ion laser track)
    orbit_track = go.Scatter3d(
        x=sat_x, y=sat_y, z=sat_z,
        mode="lines",
        line=dict(color=COLORS["accent_blue"], width=3, dash="solid"),
        name="NOMINAL ORBIT TRACK",
        hoverinfo="skip"
    )

    # Earth continents (vector boundaries)
    continent_traces = []
    for lon, lat in zip(continents_lon, continents_lat):
        clon, clat = np.meshgrid(np.array(lon), np.array(lat))
        # Project land boundaries onto sphere
        cx = r_earth * np.cos(np.radians(lat)) * np.cos(np.radians(lon))
        cy = r_earth * np.cos(np.radians(lat)) * np.sin(np.radians(lon))
        cz = r_earth * np.sin(np.radians(lat))
        
        continent_traces.append(go.Scatter3d(
            x=cx, y=cy, z=cz,
            mode="lines+markers",
            marker=dict(size=1.5, color='#17b5ff'),
            line=dict(color='#00d2ff', width=1.5),
            showlegend=False,
            hoverinfo="skip"
        ))

    # Satellite Dynamic Marker positioning (Current Frame loop multiplier)
    current_angle = (frame_idx * (2 * np.pi / TOTAL_ROWS)) % (2 * np.pi)
    sat_curr_x = r_sat * np.cos(current_angle)
    sat_curr_y = r_sat * np.sin(current_angle) * np.cos(inc)
    sat_curr_z = r_sat * np.sin(current_angle) * np.sin(inc)

    # Active ground track marker progress mapping
    history_idx = frame_idx + 1
    track_angles = np.linspace(0, current_angle, history_idx)
    hist_x = r_sat * np.cos(track_angles)
    hist_y = r_sat * np.sin(track_angles) * np.cos(inc)
    hist_z = r_sat * np.sin(track_angles) * np.sin(inc)
    
    ground_track_history = go.Scatter3d(
        x=hist_x, y=hist_y, z=hist_z,
        mode="lines",
        line=dict(color=COLORS["green"], width=4),
        name="COMPLETED FLIGHTPATH TRACE",
        hoverinfo="skip"
    )

    # Dynamic Satellite marker
    sat_marker = go.Scatter3d(
        x=[sat_curr_x], y=[sat_curr_y], z=[sat_curr_z],
        mode="markers+text",
        marker=dict(size=10, color=COLORS["green"], symbol="circle", line=dict(color="#ffffff", width=2)),
        name="ACTIVE SATELLITE (LEO-SAT-109X)",
        text=["🛰️ LEO-SAT-109X"],
        textposition="top center",
        textfont=dict(size=11, color="#ffffff", family="Courier New")
    )

    # Ground Stations (Deep Space Network coordinates)
    # Goldstone, Canberra, Madrid positions projected
    gs_locations = {
        "NASA Goldstone (DSN-14)": (35.4, -116.8),
        "Canberra (DSN-43)": (-35.4, 148.9),
        "Madrid Comm Site (DSN-63)": (40.4, -4.2)
    }
    
    gs_x, gs_y, gs_z, gs_names = [], [], [], []
    for nm, (glat, glon) in gs_locations.items():
        grad_lat = np.radians(glat)
        grad_lon = np.radians(glon)
        gs_x.append(r_earth * np.cos(grad_lat) * np.cos(grad_lon))
        gs_y.append(r_earth * np.cos(grad_lat) * np.sin(grad_lon))
        gs_z.append(r_earth * np.sin(grad_lat))
        gs_names.append(nm)

    ground_stations = go.Scatter3d(
        x=gs_x, y=gs_y, z=gs_z,
        mode="markers+text",
        marker=dict(size=6, color=COLORS["orange"], symbol="diamond"),
        name="ACTIVE DEEP SPACE COMM GROUND STATIONS",
        text=gs_names,
        textposition="bottom center",
        textfont=dict(size=9, color=COLORS["text_dark"])
    )

    # Stellar background generation (deep stars)
    np.random.seed(42)  # Maintain static clean seed
    num_stars = 200
    star_theta = np.random.uniform(0, 2*np.pi, num_stars)
    star_phi = np.random.uniform(-np.pi/2, np.pi/2, num_stars)
    r_firmament = r_earth + 15000  # Space bubble radius
    
    stars_x = r_firmament * np.cos(star_phi) * np.cos(star_theta)
    stars_y = r_firmament * np.cos(star_phi) * np.sin(star_theta)
    stars_z = r_firmament * np.sin(star_phi)

    stars_trace = go.Scatter3d(
        x=stars_x, y=stars_y, z=stars_z,
        mode="markers",
        marker=dict(size=1.2, color='#ffffff', opacity=0.85),
        name="STELLAR STELLATION FIRMAMENT",
        showlegend=False,
        hoverinfo="skip"
    )

    # Assemble comprehensive 3D plot
    composite_data = [
        stars_trace,
        sphere_trace, 
        orbit_track, 
        ground_track_history, 
        sat_marker, 
        ground_stations
    ] + continent_traces

    # Camera rotation animation logic: base dynamic orbit viewing angle
    camera_t = (frame_idx * 0.015) % (2 * np.pi)
    cam_radius = 2.4 # zooming multiplier ratio
    
    fig = go.Figure(data=composite_data)
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            bgcolor="rgba(0,0,0,0)",
            aspectmode='data',
            camera=dict(
                eye=dict(
                    x=cam_radius * np.cos(camera_t), 
                    y=cam_radius * np.sin(camera_t), 
                    z=1.0
                )
            )
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin={'t': 0, 'b': 0, 'l': 0, 'r': 0},
        legend=dict(
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=0.01,
            font=dict(size=10, color=COLORS["text_dark"]),
            bgcolor="rgba(10, 15, 29, 0.7)",
            bordercolor=COLORS["border_color"],
            borderwidth=1
        ),
        showlegend=True
    )
    return fig


# ==========================================
# 6. REACTIVE CORE CALLBACKS (CONTROL MACHINE)
# ==========================================

# Controller 1: Toggle Playback Pause/Play Interlocking Speed
@app.callback(
    Output("playing-store", "data"),
    Input("btn-pause-play", "n_clicks"),
    State("playing-store", "data"),
    prevent_initial_call=False
)
def handle_play_pause_click(n, currently_playing):
    if n is None or n == 0:
        return True # Start running automatically out of the box
    return not currently_playing


# Controller 2: Button text dynamically updating
@app.callback(
    Output("btn-pause-play", "children"),
    Input("playing-store", "data")
)
def update_pause_button_label(is_playing):
    return "⏸ PAUSE" if is_playing else "▶ PLAY"


# Controller 3: Speed Controls and Multipliers mapping to Interval milliseconds
@app.callback(
    Output("replay-timer", "interval"),
    Output("replay-timer", "disabled"),
    Input("radio-speed-base", "value"),
    Input("slider-time-warp", "value"),
    Input("playing-store", "data")
)
def configure_interval_frequency(base_key, warp_val, is_playing):
    if not is_playing:
        return 500, True # Lock CPU refresh cycle when paused

    # Base lookup
    if base_key == "FAST":
        base_ms = FAST_BASE
    elif base_key == "NORMAL":
        base_ms = NORMAL_BASE
    else:  # DEMO default
        base_ms = DEMO_BASE

    adjusted_ms = int(base_ms / warp_val)
    # Floor frame limit to 50ms for performance stability
    adjusted_ms = max(50, adjusted_ms)
    return adjusted_ms, False


# Controller 4: Central Frame state counter management
@app.callback(
    Output("current-frame-store", "data"),
    Input("replay-timer", "n_intervals"),
    Input("btn-step", "n_clicks"),
    Input("btn-reset", "n_clicks"),
    State("current-frame-store", "data"),
    prevent_initial_call=False
)
def manage_state_frame_cursor(timer_ticks, step_clicks, reset_clicks, current_frame):
    ctx = callback_context
    if not ctx.triggered:
        return 0

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "btn-reset":
        return 0

    if trigger_id == "btn-step":
        if current_frame < TOTAL_ROWS - 1:
            return current_frame + 1
        return current_frame

    # Base Timer Increment
    if trigger_id == "replay-timer":
        if current_frame < TOTAL_ROWS - 1:
            return current_frame + 1
        else:
            return current_frame  # Cap at termination limit

    return current_frame


# Controller 5: Dynamic layout parameters updates
@app.callback(
    # Top metrics
    Output("mission-status-value", "children"),
    Output("mission-status-value", "style"),
    Output("mission-subtext", "children"),
    Output("health-score-value", "children"),
    Output("health-score-value", "style"),
    Output("health-subtext", "children"),
    
    # Storage details
    Output("replay-frame-display", "children"),
    Output("replay-progress-display", "children"),
    Output("replay-status-display", "children"),
    Output("replay-status-display", "style"),
    Output("replay-speed-display", "children"),
    Output("replay-eta-display", "children"),

    # Secondary text feedback gauges
    Output("temperature-value-text", "children"),
    Output("temperature-status-text", "children"),
    Output("temperature-status-text", "style"),
    Output("battery-value-text", "children"),
    Output("battery-status-text", "children"),
    Output("battery-status-text", "style"),
    Output("voltage-value-text", "children"),
    Output("voltage-status-text", "children"),
    Output("voltage-status-text", "style"),
    Output("fuel-value-text", "children"),
    Output("fuel-status-text", "children"),
    Output("fuel-status-text", "style"),

    # Gauges & Charts figures
    Output("temperature-gauge", "figure"),
    Output("battery-gauge", "figure"),
    Output("voltage-gauge", "figure"),
    Output("fuel-gauge", "figure"),
    Output("thermal-power-trends", "figure"),
    Output("bus-fuel-trends", "figure"),
    Output("earth-orbital-viz", "figure"),
    Output("current-coord-display", "children"),

    # Intelligence lists
    Output("active-fault-tbody", "children"),
    Output("alert-timeline-log", "children"),

    # Core states
    Input("current-frame-store", "data"),
    State("playing-store", "data"),
    State("radio-speed-base", "value"),
    State("slider-time-warp", "value")
)
def compute_dashboard_state(frame_idx, is_playing, val_speed_base, warp_val):
    frame_idx = min(frame_idx, TOTAL_ROWS - 1)
    
    # Slice arrays up to index
    df_sliced = df_master.iloc[:frame_idx + 1]
    latest_rec = df_master.iloc[frame_idx]

    # Telemetry actual values
    t_val = float(latest_rec["temperature"])
    b_val = float(latest_rec["battery"])
    v_val = float(latest_rec["voltage"])
    f_val = float(latest_rec["fuel"])

    t_stat = str(latest_rec["temp_status"])
    b_stat = str(latest_rec["battery_status"])
    v_stat = str(latest_rec["voltage_status"])
    f_stat = str(latest_rec["fuel_status"])

    # 1. Gauge configurations
    fig_temp = create_gauge_figure(t_val, 0.0, 75.0, "CHASSIS TEMPERATURE", LIMITS["temperature"]["unit"], t_stat)
    fig_batt = create_gauge_figure(b_val, 0.0, 100.0, "SOLID STATE SOC", LIMITS["battery"]["unit"], b_stat)
    fig_volt = create_gauge_figure(v_val, 20.0, 45.0, "REGULATED BUS VOLTAGE", LIMITS["voltage"]["unit"], v_stat)
    fig_fuel = create_gauge_figure(f_val, 0.0, 100.0, "PROPELLANT LEVEL", LIMITS["fuel"]["unit"], f_stat)

    # Determine dynamic active warnings state values
    anomaly_messages = []
    fault_counter = 0

    t_color = COLORS["green"]
    if "CRITICAL" in t_stat:
        t_color = COLORS["red"]; fault_counter += 1
        anomaly_messages.append(f"Temperature CRITICAL ANOMALY: {t_val}°C surpassed warning limit.")
    elif "WARNING" in t_stat:
        t_color = COLORS["orange"]; fault_counter += 1
        anomaly_messages.append(f"Temperature Alert: Heat sink levels elevated ({t_val}°C).")

    b_color = COLORS["green"]
    if "CRITICAL" in b_stat:
        b_color = COLORS["red"]; fault_counter += 1
        anomaly_messages.append(f"Storage SOC CRITICAL LOW: Battery reporting depleted cycle ({b_val}%).")
    elif "WARNING" in b_stat:
        b_color = COLORS["orange"]; fault_counter += 1
        anomaly_messages.append(f"Storage SOC Warning: Rapid discharging load cycle ({b_val}%).")

    v_color = COLORS["green"]
    if "CRITICAL" in v_stat:
        v_color = COLORS["red"]; fault_counter += 1
        anomaly_messages.append(f"Bus Power CRITICAL FLUCTUATION: {v_val}V exceeded power distribution safety margin.")
    elif "WARNING" in v_stat:
        v_color = COLORS["orange"]; fault_counter += 1
        anomaly_messages.append(f"Bus Power Warning: Fluctuations detected near safety limits ({v_val}V).")

    f_color = COLORS["green"]
    if "CRITICAL" in f_stat:
        f_color = COLORS["red"]; fault_counter += 1
        anomaly_messages.append(f"Propellant CRITICAL EMPTY: Critical dry pressure status reached.")
    elif "WARNING" in f_stat:
        f_color = COLORS["orange"]; fault_counter += 1
        anomaly_messages.append(f"Propellant Low warning: propellant reservoir low ({f_val}%).")

    # Math-defined health score
    # Subtraction of 10 points for each active Warning subsystem, 25 points for each Critical subsystem
    calculated_health = 100
    for stat in [t_stat, b_stat, v_stat, f_stat]:
        if "CRITICAL" in stat:
            calculated_health -= 25
        elif "WARNING" in stat:
            calculated_health -= 10
    calculated_health = max(0, calculated_health)

    # Health Text descriptions
    health_text_color = COLORS["green"]
    if calculated_health < 60:
        health_text_color = COLORS["red"]
        health_desc = "SEVERE: Emergency thermal/power recovery in progress"
    elif calculated_health < 90:
        health_text_color = COLORS["orange"]
        health_desc = "WARNING: System operational in degraded bypass state"
    else:
        health_desc = "System nominal. All loops reporting within limits"

    # Mission Status Text logic with simulation-complete injection state
    if frame_idx >= TOTAL_ROWS - 1:
        mission_status = "MISSION REPLAY COMPLETE"
        mission_status_color = COLORS["accent_blue"]
        mission_sub = "All recorded telemetry parsed successfully. Listening for Command Line reset."
    elif len(anomaly_messages) > 0:
        if calculated_health < 60:
            mission_status = "CRITICAL SUBSYSTEM FAILURE"
            mission_status_color = COLORS["red"]
            mission_sub = f"AUTOMATED BYPASS: {anomaly_messages[0]}"
        else:
            mission_status = "DEGRADED TELEMETRY DETECTED"
            mission_status_color = COLORS["orange"]
            mission_sub = f"PREDICTIVE AUTOPILOT ADJUST: {anomaly_messages[0]}"
    else:
        mission_status = "NOMINAL TELEMETRY FLOW"
        mission_status_color = COLORS["green"]
        mission_sub = "Active geostationary ground-telecomment telemetry channel connected."

    # 2. Dynamic playback properties
    prog_pct = int((frame_idx / (TOTAL_ROWS - 1)) * 100) if TOTAL_ROWS > 1 else 100
    frame_text = f"FRAME {frame_idx + 1} / {TOTAL_ROWS}"
    progress_text = f"{prog_pct}% COMPLETE"
    
    speed_text = f"SPEED: {val_speed_base} ({warp_val}x)"
    
    if frame_idx >= TOTAL_ROWS - 1:
        playback_state_label = "TASK FINISHED"
        playback_state_color = COLORS["accent_blue"]
    elif is_playing:
        playback_state_label = "REPLAY RUNNING"
        playback_state_color = COLORS["green"]
    else:
        playback_state_label = "REPLAY PAUSED"
        playback_state_color = COLORS["orange"]

    # Calculate ETA based on remaining frames and current speed config
    base_ms = FAST_BASE if val_speed_base == "FAST" else (NORMAL_BASE if val_speed_base == "NORMAL" else DEMO_BASE)
    warp_sec = (base_ms / warp_val) / 1000.0
    remaining_sec = int((TOTAL_ROWS - 1 - frame_idx) * warp_sec)
    eta_text = f"EST. ETA COMPLETE: {remaining_sec} Seconds" if remaining_sec > 0 else "TASK COPING: COMPLETE"

    # 3. Dynamic Interactive High-Performance Trend Plots
    # Chart A: Thermal & Power
    trend_thermal_power = go.Figure()
    # Sliced Data
    chart_x_stamps = [
        pd.to_datetime(ts).strftime("%H:%M:%S")
        for ts in df_sliced["timestamp"]
    ]

    # Temperature series
    trend_thermal_power.add_trace(go.Scatter(
        x=chart_x_stamps, y=df_sliced["temperature"],
        mode="lines",
        line=dict(color=COLORS["accent_blue"], width=2.5),
        name="Chassis Temp (°C)"
    ))
    # Battery series on side secondary Y axis
    trend_thermal_power.add_trace(go.Scatter(
        x=chart_x_stamps, y=df_sliced["battery"],
        mode="lines",
        line=dict(color=COLORS["green"], width=2, dash="dash"),
        name="Battery SOC (%)",
        yaxis="y2"
    ))

    trend_thermal_power.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(13, 19, 33, 0.65)',
        margin=dict(l=45, r=45, t=10, b=25),
        grid=dict(rows=1, columns=1),
        xaxis=dict(
            gridcolor=COLORS["border_color"], 
            tickfont=dict(color=COLORS["text_dark"], size=9),
            showgrid=True
        ),
        yaxis=dict(
            title=dict(
                text="Temperature (°C)",
                font=dict(
                    color=COLORS["accent_blue"],
                    size=10
                )
            ),
        tickfont=dict(
            color=COLORS["accent_blue"],
            size=9
        ),
        gridcolor=COLORS["border_color"]
    ),
        yaxis2=dict(
            title=dict(
                text="Battery (%)",
                font=dict(
                    color=COLORS["green"],
                    size=10
                )
            ),
            tickfont=dict(
                color=COLORS["green"],
                size=9
            ),
            overlaying="y",
            side="right"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=9, color=COLORS["text"]),
            bgcolor="rgba(0,0,0,0)"
        ),
        hovermode="x unified",
        showlegend=True
    )

    # Chart B: Voltage & Fuel Dynamics
    trend_volt_fuel = go.Figure()
    trend_volt_fuel.add_trace(go.Scatter(
        x=chart_x_stamps, y=df_sliced["voltage"],
        mode="lines",
        line=dict(color="#f44336", width=2.5),
        name="Bus Voltage (V)"
    ))
    trend_volt_fuel.add_trace(go.Scatter(
        x=chart_x_stamps, y=df_sliced["fuel"],
        mode="lines",
        line=dict(color=COLORS["orange"], width=2, dash="dot"),
        name="Propellant Fuel (%)",
        yaxis="y2"
    ))

    trend_volt_fuel.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(13, 19, 33, 0.65)',
        margin=dict(l=45, r=45, t=10, b=25),
        xaxis=dict(
            gridcolor=COLORS["border_color"], 
            tickfont=dict(color=COLORS["text_dark"], size=9),
            showgrid=True
        ),
        yaxis=dict(
            title=dict(
                text="Voltage (V)",
                font=dict(
                    color="#f44336",
                    size=10
                )
            ),
            tickfont=dict(
                color="#f44336",
                size=9
            ),
            gridcolor=COLORS["border_color"]
        ),
        yaxis2=dict(
            title=dict(
                text="Fuel (%)",
                font=dict(
                    color=COLORS["orange"],
                    size=10
                )
            ),
            tickfont=dict(
                color=COLORS["orange"],
                size=9
            ),
            overlaying="y",
            side="right"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=9, color=COLORS["text"]),
            bgcolor="rgba(0,0,0,0)"
        ),
        hovermode="x unified",
        showlegend=True
    )

    # 4. Generate beautiful 3D Earth visualization
    fig_earth = create_earth_figure(frame_idx)

    # Coordinate output formatting mapping orbital projection angles to geographic lats/lons
    inc_rad = np.radians(65)
    orbit_angle = (frame_idx * (2 * np.pi / TOTAL_ROWS)) % (2 * np.pi)
    
    # Simple conversion of orbit angular vector onto geodetic Latitude / Longitude
    geo_lat = np.degrees(np.arcsin(np.sin(orbit_angle) * np.sin(inc_rad)))
    geo_lon = np.degrees(orbit_angle) if geo_lat >= 0 else -1 * np.degrees(orbit_angle)
    # Wrap lon between -180 and 180
    geo_lon = ((geo_lon + 180) % 360) - 180
    
    coords_text = f"RADIAL ORBIT POS: {geo_lat:.3f}° N, {geo_lon:.3f}° E // ACC ALTI: 852.14 KM"

    # 5. Compile Active Fault Table contents dynamically
    fault_rows = []
    # Alert logging string generator accumulators
    alert_logs = []

    # Iterate matching historical timeline occurrences up to the current index
    for idx in range(frame_idx + 1):
        row_data = df_master.iloc[idx]
        ts_full = str(row_data["timestamp"])
        ts_clk = pd.to_datetime(ts_full).strftime("%H:%M:%S")
        
        # Check variables and generate row outputs
        for col_name, status_col, display_label in [
            ("temperature", "temp_status", "Chassis Heat Sink"),
            ("battery", "battery_status", "Power Cells SOC"),
            ("voltage", "voltage_status", "Regulated Bus Bus"),
            ("fuel", "fuel_status", "Propellant Reservoir")
        ]:
            s_val = str(row_data[status_col])
            v_curr = float(row_data[col_name])
            
            if "NOMINAL" not in s_val:
                # Add to fault row list
                fault_rows.append(html.Tr(style={
                    "borderBottom": f"1px solid {COLORS['border_color']}",
                    "backgroundColor": "#1d141e" if "CRITICAL" in s_val else "#1b1915"
                }, children=[
                    html.Td(f"FR-{idx}", style={"padding": "6px 8px", "fontWeight": "bold"}),
                    html.Td(ts_clk, style={"padding": "6px 8px"}),
                    html.Td(display_label, style={"padding": "6px 8px"}),
                    html.Td(f"{v_curr:.2f}", style={"padding": "6px 8px"}),
                    html.Td(s_val, style={"padding": "6px 8px", "color": COLORS["red"] if "CRITICAL" in s_val else COLORS["orange"], "fontWeight": "bold"}),
                ]))

        # Alert log timeline entries output format
        # Check transition states relative to previous frame
        t_prev = "NOMINAL" if idx == 0 else str(df_master.iloc[idx - 1]["temp_status"])
        b_prev = "NOMINAL" if idx == 0 else str(df_master.iloc[idx - 1]["battery_status"])
        v_prev = "NOMINAL" if idx == 0 else str(df_master.iloc[idx - 1]["voltage_status"])
        f_prev = "NOMINAL" if idx == 0 else str(df_master.iloc[idx - 1]["fuel_status"])

        # Trace temp transition log
        if t_stat != t_prev and idx == frame_idx:
            alert_logs.append(f"[{ts_clk}] EVENT ALERT: Temperature transition detected: {t_prev} -> {t_stat} (Curr: {t_val}°C)")
        
        if b_stat != b_prev and idx == frame_idx:
            alert_logs.append(f"[{ts_clk}] EVENT ALERT: Battery SOC transition detected: {b_prev} -> {b_stat} (Curr: {b_val}%)")

        if v_stat != v_prev and idx == frame_idx:
            alert_logs.append(f"[{ts_clk}] EVENT ALERT: Voltage Regulation transition detected: {v_prev} -> {v_stat} (Curr: {v_val}V)")

    # Build timeline diagnostic lines for scrolling box
    if len(fault_rows) == 0:
        fault_rows_content = [html.Tr(children=[
            html.Td("NO DETECTED TELESYSTEM COMPILATION FAULTS", colSpan=5, 
                    style={"padding": "20px", "textAlign": "center", "color": COLORS["green"], "fontWeight": "700"})
        ])]
    else:
        fault_rows_content = fault_rows

    # Populate vertical scrolling timelines
    timeline_lines = []
    # Build complete timeline history of triggers
    for idx in range(frame_idx + 1):
        row_d = df_master.iloc[idx]
        ts_val = pd.to_datetime(row_d["timestamp"]).strftime("%H:%M:%S")
        
        # Temp alert triggers
        r_temp_s = str(row_d["temp_status"])
        if "NOMINAL" not in r_temp_s:
            color_sel = COLORS["red"] if "CRITICAL" in r_temp_s else COLORS["orange"]
            timeline_lines.append(html.Div([
                html.Span(f"[{ts_val}] ", style={"color": COLORS["text_dark"]}),
                html.Span(f"◆ THERMAL ANOMALY INJECTED // CHASSIS TEMPERATURE: {row_d['temperature']}°C ({r_temp_s})", style={"color": color_sel})
            ]))

        # Battery triggers
        r_batt_s = str(row_d["battery_status"])
        if "NOMINAL" not in r_batt_s:
            color_sel = COLORS["red"] if "CRITICAL" in r_batt_s else COLORS["orange"]
            timeline_lines.append(html.Div([
                html.Span(f"[{ts_val}] ", style={"color": COLORS["text_dark"]}),
                html.Span(f"◆ ELECTRICAL STORAGE ALERT // BATTERY CONFIG SOC: {row_d['battery']}% ({r_batt_s})", style={"color": color_sel})
            ]))

        # Voltage triggers
        r_volt_s = str(row_d["voltage_status"])
        if "NOMINAL" not in r_volt_s:
            color_sel = COLORS["red"] if "CRITICAL" in r_volt_s else COLORS["orange"]
            timeline_lines.append(html.Div([
                html.Span(f"[{ts_val}] ", style={"color": COLORS["text_dark"]}),
                html.Span(f"◆ BUS REGULATION EXCEPTION // SURGE LEVEL: {row_d['voltage']}V ({r_volt_s})", style={"color": color_sel})
            ]))

    if len(timeline_lines) == 0:
        timeline_rendered_lines = [html.Div("• STATION COMM LINK ESTABLISHED // MONITOR LOG EMPTY NOMINAL STATS", style={"color": COLORS["green"]})]
    else:
        timeline_rendered_lines = timeline_lines[::-1] # Reverse chronology

    # Text formats for second-row values
    val_temp_text = f"{t_val:.1f} °C"
    val_batt_text = f"{b_val:.1f} %"
    val_volt_text = f"{v_val:.1f} V"
    val_fuel_text = f"{f_val:.1f} %"

    return (
        # Top KPI updates
        mission_status, {"fontSize": "22px", "fontWeight": "800", "marginTop": "10px", "color": mission_status_color}, mission_sub,
        str(calculated_health), {"fontSize": "32px", "fontWeight": "900", "color": health_text_color}, health_desc,
        
        # Playback states
        frame_text, progress_text, 
        playback_state_label, {"fontSize": "13px", "fontWeight": "700", "color": playback_state_color},
        speed_text, eta_text,

        # Secondary indicators labels text
        val_temp_text, t_stat, {"color": t_color},
        val_batt_text, b_stat, {"color": b_color},
        val_volt_text, v_stat, {"color": v_color},
        val_fuel_text, f_stat, {"color": f_color},

        # Figures
        fig_temp, fig_batt, fig_volt, fig_fuel,
        trend_thermal_power, trend_volt_fuel,
        fig_earth, coords_text,

        # Tables Content
        fault_rows_content,
        html.Div(timeline_rendered_lines)
    )


# ==========================================
# 7. SCRIPT ENTRYPOINT SYSTEM
# ==========================================
if __name__ == "__main__":
    print("------------------------------------------------------------")
    print("🛰️  SATELLITE HEALTH REPLAY SYSTEMS: DASH OVERLAY LIVE")
    print("🎯  OPERATING SATELLITE DEMONSTRATION AT PORT 3000")
    print("🌐  DEPLOYING WEB DASHBOARD ROUTERS VIA PLOTLY ENGINE")
    print("------------------------------------------------------------")

    app.run(
        host="0.0.0.0",
        port=3000,
        debug=False
    )