# Satellite Telemetry Health Monitoring System

A real-time satellite telemetry simulator with rule-based fault detection, CSV logging, offline mission analysis, a live Mission Control dashboard, and (from V5 onward) a shared cross-version alerting system. Built in Python with a modular architecture, inspired by real aerospace FDIR systems (Fault Detection, Isolation, and Recovery).

---

## What This System Does

This system simulates a satellite health monitoring pipeline end to end:

- **Generates** simulated telemetry readings for key satellite parameters
- **Detects faults** against defined thresholds in real time
- **Logs** everything to CSV with timestamps, mimicking real ground station software
- **Analyzes** completed mission logs offline — fault events, subsystem health scores, mission timelines, full reports
- **Visualizes** live telemetry and mission history in a Streamlit Mission Control dashboard, with an optional Grafana telemetry wall
- **Alerts**, from V5 onward, through a shared alert bus that every future version (V5, V6, V7) writes into and the dashboard reads from — so new fault-detection logic plugs into the existing UI instead of requiring a new one each time

---

## System Architecture

```
satellite_telemetry/
│
├── simulator/
│   └── generator.py               # Generates simulated telemetry data
│
├── monitor/
│   └── fault_detector.py          # V1/V2 rule-based fault detection engine
│
├── logger/
│   └── telemetry_logger.py        # Logs telemetry + fault status to CSV
│
├── data/
│   └── telemetry_log.csv          # Auto-generated on first run
│
├── shared/
│   └── alert_bus.py               # write_alert() / read_alerts() — shared by V5, V6, V7 and the dashboard
│
├── Version_3/                     # Offline Telemetry Log Analyzer
│   ├── log_loader_file.py
│   ├── summary_statistics_file.py
│   ├── event_detection_file.py
│   ├── fault_statistics_file.py
│   ├── mission_timeline_file.py
│   ├── health_score_file.py
│   ├── generate_report_file.py
│   └── main.py
│
├── Version_4/                     # Streamlit Mission Control Dashboard
│   └── dashboard/
│       └── dashboard.py           # Live gauges, replay engine, orbit view, mission report, alerts tab
│
├── Version_5/                     # Advanced Rule-Based Fault Detection
│   ├── rules/
│   │   └── fault_rules.json       # Thresholds, direction, rate-of-change limits — no hardcoded logic
│   └── monitor/
│       ├── rule_engine.py         # Generic engine that evaluates any parameter from fault_rules.json
│       ├── state_machine.py       # Per-parameter NORMAL/WARNING/CRITICAL/RECOVERING lifecycle
│       ├── rate_of_change.py      # Trend-based detection (fast-dropping values before they cross a line)
│       └── compound_rules.py      # Correlated multi-parameter fault logic
│
├── Version_6/                     # Packet Communication Simulator (planned)
│
├── Version_7/                     # AI Anomaly Detection (planned)
│
└── main.py                        # Orchestrates simulator/monitor/logger modules
```

---

## Modules

### `simulator/generator.py`
Generates one telemetry snapshot per second using `random.uniform()` within realistic satellite parameter ranges. Parameters include temperature, battery, voltage, and fuel. Uses `datetime.now()` for real timestamps.

### `monitor/fault_detector.py` (V1/V2)
Receives a telemetry snapshot and checks each parameter against defined thresholds. Returns a fault status dictionary with `NORMAL`, `WARNING`, or `CRITICAL` for each parameter.

Original thresholds:

| Parameter        | WARNING | CRITICAL |
|-------------------|---------|----------|
| Temperature (°C)  | > 75    | > 90     |
| Battery (%)       | < 20    | < 10     |
| Voltage (V)       | < 3.5   | < 3.3    |
| Fuel (%)          | < 15    | < 5      |

### `logger/telemetry_logger.py`
Receives the telemetry snapshot and fault status dictionary. Writes one row per reading to `telemetry_log.csv` with full timestamps. Creates the file with headers on first run, then appends on every subsequent run.

---

## Version_3 — Telemetry Log Analyzer

Takes a completed telemetry CSV log and produces a full offline mission analysis:

- **`log_loader_file.py`** — loads and validates the CSV, checks for missing values, out-of-order timestamps, duplicates, and physically impossible sensor readings
- **`summary_statistics_file.py`** — computes mean, min, max, std deviation, rate of change, nominal percentage, and trend per parameter
- **`event_detection_file.py`** — scans for sustained threshold breaches (minimum 3 consecutive samples), classifies warning vs. critical, tracks recovery
- **`fault_statistics_file.py`** — aggregates fault counts, frequency, recovery rate, most-faulted parameter, longest fault duration, and severity distribution
- **`mission_timeline_file.py`** — builds a chronological event log from mission start to end
- **`health_score_file.py`** — scores Battery, Fuel, and Thermal subsystems (starting at 100, deducted per fault), and computes an Overall score bounded by the worst subsystem
- **`generate_report_file.py`** — writes `health_scores.json`, `mission_timeline.json`, `fault_log.csv`, and a human-readable `mission_report.txt`
- **`main.py`** — single entry point that runs the full V3 pipeline end to end

---

## Version_4 — Mission Control Dashboard ✅

A Streamlit dashboard (`dashboard.py`, ~630 lines) that brings the telemetry pipeline to life visually:

- **Tabbed layout** — Overview / Graphs / Mission Report
- **Frame-by-frame replay engine** — Reset, Pause, Step, 3 speed presets, auto-loop
- **Live gauges** matching the real `fault_detector.py` thresholds
- **Simulated 3D orbit tracker**
- **V3 report integration** — pulls in health scores, mission timeline, and fault stats directly
- **Smooth live updates** via `st.fragment(run_every=...)` + Plotly `transition`/`easing`
- **Alerts tab (from V5 onward)** — reads from `shared/alert_bus.py`, showing a live, filterable feed of alerts from every connected version, color-coded by severity with a source-version badge, plus an active-alerts counter in the sidebar

**Known-fixed issues:** full-page blink (fixed via `st.fragment`), blank buttons (fixed via plain-text labels + forced CSS), a fade-in CSS animation that backfired into rhythmic flicker (removed).

**Run:**
```bash
pip install streamlit plotly pandas
streamlit run dashboard.py
# or: python -m streamlit run dashboard.py   (if PATH issues)
```

---

## Version_5 — Advanced Rule-Based Fault Detection 🚧

V5 pushes rule-based fault detection as far as it can go before ML (V7) takes over — and integrates its output into the existing dashboard rather than building a new interface.

**Core upgrades over the V1/V2 detector:**

1. **Config-driven rule engine** — thresholds move out of hardcoded `if/elif` chains and into `fault_rules.json` (parameter, warning/critical thresholds, direction). `rule_engine.py` becomes generic: it reads rules instead of encoding them, permanently fixing the class of bug caused by hardcoded severity-check ordering.
2. **Per-parameter state machine** — each parameter moves through `NORMAL → WARNING → CRITICAL → RECOVERING → NORMAL` instead of being reclassified independently every second, adding hysteresis so boundary flickering doesn't spam fault toggles.
3. **Rate-of-change rules** — flags values trending dangerously even before they cross a threshold (e.g. battery still above the warning line but dropping fast).
4. **Compound/correlated fault rules** — a small set of hand-written rules for parameter combinations that are worse together than apart (e.g. high temperature + low voltage).
5. **Severity escalation over time** — a WARNING sustained past a duration limit auto-escalates to CRITICAL even without a raw threshold breach.

**Alert integration:** every rule trigger, state transition, and escalation writes a row into the shared alert bus (see below), which the V4 dashboard's Alerts tab already displays.

---

## Shared Alert Bus (V5, V6, V7 → Dashboard)

Instead of every future version building its own alert UI, V5 introduces one shared, append-only alert stream that V6 and V7 plug into later at zero extra dashboard cost.

**`shared/alert_bus.py`** exposes:
- `write_alert(...)` — used by any version to emit an alert
- `read_alerts(...)` — used by the dashboard to tail/query the feed

**Shared schema** (one row per alert):

```
timestamp, source_version, parameter, severity, rule_type, message, value, resolved_at
```

| Field | Meaning |
|---|---|
| `source_version` | `"V5"`, `"V6"`, `"V7"` — lets the dashboard badge/color-code origin |
| `rule_type` | `"threshold"`, `"rate_of_change"`, `"compound"`, `"packet_loss"`, `"anomaly_score"` — one field spans all versions' alert kinds |
| `resolved_at` | Nullable; distinguishes active vs. historical alerts and lets duration be computed |

**How later versions plug in:**
- **V6** (packet comms) — packet loss, out-of-order arrival, checksum/corruption failures write into the same bus with `rule_type="packet_loss"` etc.
- **V7** (AI anomaly detection) — anomaly-score threshold breaches write in with `rule_type="anomaly_score"`, `value` holding the score

Because the schema and the dashboard's Alerts tab are built once in V5, V6 and V7 only need to call `write_alert()` — no dashboard rework required.

---

## Version_6 — Packet Communication Simulator 🔜
Planned: simulates realistic ground-to-satellite / satellite-to-ground packet transmission, including loss, corruption, and out-of-order delivery, feeding faults into the shared alert bus.

## Version_7 — AI Anomaly Detection 🔜
Planned: replaces/augments static and rate-of-change rules with a learned model (e.g. rolling z-score or isolation forest) trained on telemetry history, flagging anomalies that don't cleanly fit a hand-written rule — feeding into the same shared alert bus.

---

## Telemetry Wall (Grafana) 🚧
A parallel, ops-style visualization layer, separate from the Streamlit dashboard:
- Docker Desktop → Grafana container using the `marcusolsson-csv-datasource` plugin, reading `telemetry_log.csv` directly (no database)
- Gauge panels (temperature/battery/voltage/fuel) with thresholds matching `fault_detector.py`
- Two time-series panels (temp+battery, voltage+fuel)
- Auto-refresh every 5–10s
- Kiosk-mode URL (`?kiosk`) for embedding
- Optional alerting → Discord/Slack/email contact points

Deferred: a fuller InfluxDB + Docker Compose pipeline with additional real parameters (propellant, propulsion), and public access via Cloudflare Tunnel.

---

## How To Run

**Live simulator (V1/V2):**
```bash
python main.py
```
Generates and logs telemetry every second. Press `Ctrl + C` to stop.

**Offline log analyzer (V3):**
```bash
cd Version_3
python main.py --file ../Version_1/data/telemetry_log.csv
```
Produces `health_scores.json`, `mission_timeline.json`, `fault_log.csv`, and `mission_report.txt`.

**Dashboard (V4):**
```bash
cd Version_4/dashboard
pip install streamlit plotly pandas
streamlit run dashboard.py
```

---

## Sample Output

**Live simulator:**
```
{'timestamp': datetime.datetime(2026, 5, 23, 14, 42, 5), 'temperature': 71.4, 'battery': 97.5, 'voltage': 4.6, 'fuel': 64.5}
{'temperature': 'Normal', 'battery': 'Normal', 'voltage': 'Normal', 'fuel': 'Normal'}
```

**V3 analyzer (fault_stats excerpt):**
```json
{"total_faults": 18, "faults_per_parameter": {"temperature": 15, "battery": 2, "fuel": 1, "voltage": 0},
"fault_frequency_per_hour": 0.189, "recovery_rate": 88.89, "most_faulted_parameter": "temperature",
"longest_fault_duration": 273413.95, "severity": {"warning": 12, "critical": 6}}
```

---

## Hardest Bugs Fixed

- **Severity check order (V1/V2)** — the fault detector initially checked WARNING before CRITICAL in every if/elif chain, so a battery reading of 3% triggered WARNING instead of CRITICAL because `3 < 20` evaluated `True` first and Python never reached the `elif`. Fixed by always checking the most severe condition first — and structurally eliminated in V5 by moving to a config-driven rule engine.
- **Timestamp JSON serialization (V3)** — `mission_timeline.json` failed with `TypeError: Object of type Timestamp is not JSON serializable`, since `pd.to_datetime()` converts the timestamp column into pandas `Timestamp` objects. Fixed by converting timestamps to strings before/during the JSON dump.
- **Empty event list guard (V3)** — building CSV fieldnames from `event_list[0].keys()` crashed with an `IndexError` on clean data with zero faults. Fixed with a length check before attempting the CSV write.
- **Streamlit full-page blink (V4)** — fixed via `st.fragment(run_every=...)` instead of full reruns.
- **Blank dashboard buttons (V4)** — fixed via plain-text labels + forced CSS.
- **Fade-in flicker (V4)** — a CSS fade-in animation caused rhythmic flicker on live updates; removed.

---

## Current Progress

- ✅ **V1** — Telemetry Monitoring System
- ✅ **V2** — Fault Injection Engine
- ✅ **V3** — Telemetry Log Analyzer (Log Loader, Summary Statistics, Event Detection, Fault Statistics, Mission Timeline, Health Score, Report Generator, `main.py` entry point — tested end to end on clean and fault-injected data)
- ✅ **V4** — Telemetry Visualization Dashboard (Streamlit, tabbed layout, replay engine, live gauges, simulated orbit tracker, V3 report integration)
- 🚧 **V5** — Advanced Rule-Based Fault Detection + shared alert bus integration into the V4 dashboard
- 🔜 **V6** — Packet Communication Simulator (feeds shared alert bus)
- 🔜 **V7** — AI Anomaly Detection (feeds shared alert bus)
- 🚧 **Grafana Telemetry Wall** — parallel ops-style visualization, Docker/WSL setup in progress

---

## Tech Stack

- **Python 3.x**
- `pandas` — telemetry data loading and analysis (V3+)
- `random` — telemetry value simulation
- `datetime` — real-time timestamping
- `csv` / `json` — structured data logging and reporting
- `argparse` — command-line interface
- `os`, `time` — file handling and loop interval control
- `streamlit`, `plotly` — Mission Control dashboard (V4+)
- `Docker`, `Grafana` (`marcusolsson-csv-datasource` plugin) — telemetry wall

---

## Domain Context

This project is inspired by real aerospace FDIR systems (Fault Detection, Isolation, and Recovery) used in satellite ground station software. The modular architecture mirrors how real telemetry pipelines separate data acquisition, fault analysis, and data persistence into independent components — and from V5 onward, a shared alerting layer that later fault-detection strategies (packet-level, then AI-based) plug into without requiring a new interface each time.

---

## Author

Shivansh — building toward aerospace AI systems, one module at a time.
