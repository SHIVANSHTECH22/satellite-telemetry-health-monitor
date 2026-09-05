# 🛰️ Satellite Telemetry Health Monitoring System

A satellite ground-station monitoring pipeline, built one version at a time — from a simple data simulator to a live mission-control dashboard, with rule-based fault detection, mission analysis, and (eventually) AI-driven anomaly detection along the way.

Inspired by real aerospace **FDIR** systems (**F**ault **D**etection, **I**solation, and **R**ecovery) — the kind of software real ground stations use to watch over spacecraft health.

---

## The Idea, in One Paragraph

Satellites constantly send back readings — temperature, battery charge, voltage, fuel — and something has to watch those numbers and notice when they go dangerously wrong. This project builds that "something," piece by piece: first a way to generate realistic readings, then a way to deliberately break things to test the system, then a way to analyze what happened afterward, then a live dashboard to watch it all happen in real time, and eventually smarter detection that doesn't rely on hardcoded rules at all.

Every version below is a **complete, working, self-contained stage** — not a rough draft. Each one builds directly on the version before it.

---

## Project Status at a Glance

| Version | What it is | Status |
|---|---|---|
| V1 | Live telemetry simulator + rule-based fault detector | ✅ Done |
| V2 | Fault injection engine (deliberately break things, on purpose) | ✅ Done |
| V3 | Offline mission log analyzer + report generator | ✅ Done |
| V4 | Live mission control dashboard | ✅ Done |
| V5 | Advanced, multi-condition fault detection | 🔜 Planned |
| V6 | Telemetry packet communication simulator | 🔜 Planned |
| V7 | AI-based anomaly detection | 🔜 Planned |

---

## Version 1 — Telemetry Acquisition & Monitoring System

**In plain terms:** this is the heartbeat of the whole project. Every second, it invents a plausible satellite reading (like a weather simulator, but for spacecraft vitals), checks whether that reading is dangerous, and writes it down with a timestamp — exactly like a real ground station logging incoming data.

**What it actually does:**
- Generates one telemetry "snapshot" per second: temperature, battery %, voltage, and fuel %, each within a realistic range
- Checks every reading against fixed safety thresholds and classifies it as **Normal**, **Warning**, or **Critical**
- Logs every reading — plus its fault status — to a CSV file, with a proper header row and a real timestamp on each line

**The actual thresholds used (these are referenced by every later version too):**

| Parameter | Warning | Critical | Direction |
|---|---|---|---|
| Temperature (°C) | > 80 | > 90 | high = bad |
| Battery (%) | < 20 | < 5 | low = bad |
| Voltage (V) | < 3.6 | < 3.3 | low = bad |
| Fuel (%) | < 15 | < 5 | low = bad |

**Folder layout:**
```
Version_1/
├── simulator/generator.py       # generates one reading per second
├── monitor/fault_detector.py    # classifies each reading
├── logger/telemetry_logger.py   # writes to CSV
├── data/telemetry_log.csv       # the actual log (auto-created)
└── main.py                      # ties it all together in a loop
```

**Run it:**
```bash
cd Version_1
python main.py
```
Leave it running — it logs one row per second. `Ctrl+C` to stop.

**The most important bug this version taught:** the fault checker originally asked "is this a Warning?" *before* asking "is this Critical?" — so a battery reading of 3% (genuinely critical) got logged as a mere Warning, because the code found a match on the Warning check and never bothered checking further. One line of ordering, and a real emergency could go unflagged. **Lesson: always check the most severe condition first.**

---

## Version 2 — Fault Injection Engine

**In plain terms:** V1 only breaks by random chance — most of the time, everything stays Normal. That's a problem if you want to actually test whether your fault detector works. V2 solves this by deliberately, controllably injecting bad readings — sudden battery drops, temperature spikes, sensor freezes — on purpose, so the system's response can be genuinely tested instead of just hoped for.

**Why this matters:** you can't trust a smoke detector you've never actually tested with smoke. V2 is the "test with smoke" version of this project.

**What it adds on top of V1:**
- Deliberate fault scenarios: sudden battery voltage drops, temperature spikes, abnormal fuel loss, sensor freezes, signal noise, invalid readings
- These aren't random glitches — they're controlled, repeatable test scenarios
- The resulting data (faults + normal readings mixed together) becomes the standard test dataset for every later version — a 5,200-row run with 18 injected faults across battery, temperature, and fuel is the reference dataset used to validate V3 and V4.

**Run it:**
```bash
cd Version_2
python main.py
```

---

## Version 3 — Telemetry Log Analyzer

**In plain terms:** V1 and V2 tell you what's happening right now. V3 is the "black box flight recorder" — you feed it a completed log file (a finished mission, or hours of past data), and it reconstructs the full story: what went wrong, when, how often, how severely, and how the satellite's overall health should be scored.

**What it actually does, step by step:**
1. **Loads and validates** the CSV — checks for missing values, duplicate or out-of-order timestamps, and physically impossible readings (data quality control, before any analysis happens)
2. **Computes statistics** per parameter — mean, min, max, standard deviation, rate of change, percentage of time spent Normal, and overall trend
3. **Detects real fault events** — not single noisy blips, but *sustained* breaches (at least 3 consecutive bad readings in a row), and tracks when the system recovered
4. **Aggregates fault statistics** — total fault count, how often faults happen per hour, which subsystem faults the most, the longest single fault duration, and a breakdown of Warning vs. Critical severity
5. **Builds a mission timeline** — a full chronological log of every significant event across the mission
6. **Scores subsystem health** — Battery, Fuel, and Thermal each start at a perfect 100 and lose points per fault; the Overall score is capped by whichever subsystem is doing worst (a satellite isn't "healthy overall" if one system is failing badly)
7. **Generates a full report** — JSON files, a CSV fault log, and a plain-English text summary, all in one run

**Folder layout:**
```
Version_3/
├── log_loader_file.py          # step 1
├── summary_statistics_file.py  # step 2
├── event_detection_file.py     # step 3
├── fault_statistics_file.py    # step 4
├── mission_timeline_file.py    # step 5
├── health_score_file.py        # step 6
├── generate_report_file.py     # step 7
└── main.py                     # runs steps 1-7 in order
```

**Run it:**
```bash
cd Version_3
python main.py --file ../Version_2/data/telemetry_log.csv
```
Produces `health_scores.json`, `mission_timeline.json`, `fault_log.csv`, and `mission_report.txt`.

**Sample output (fault statistics):**
```python
{'total_faults': 18, 'faults_per_parameter': {'temperature': 15, 'battery': 2, 'fuel': 1, 'voltage': 0},
'fault_frequency_per_hour': 0.189, 'recovery_rate': 88.89, 'most_faulted_parameter': 'temperature',
'longest_fault_duration': 273413.95, 'severity': {'warning': 12, 'critical': 6}}
```

**Bugs this version taught:**
- Pandas timestamps aren't valid JSON by default — `TypeError: Object of type Timestamp is not JSON serializable`. Fixed by converting timestamps to plain strings before writing JSON.
- Building a CSV's column headers from the first item in an empty list crashes with an `IndexError` on perfectly clean, fault-free data. Fixed with a simple "is this list empty?" check first.

---

## Version 4 — Live Mission Control Dashboard

**In plain terms:** everything before this was either a background process or an after-the-fact report. V4 is the part you actually *watch* — a real-time, visual mission control screen, the kind you'd see in a movie: glowing gauges, live graphs, a satellite tracked on a map, and a full replay you can pause and step through.

**What it actually does:**
- **Live instrument gauges** for temperature, battery, voltage, and fuel — color-coded green/amber/red using the exact same thresholds from V1
- **A full replay engine** — not just "show me the latest reading," but Reset / Pause / Step controls that let you walk through an entire mission's history frame by frame, at three different speeds
- **A 3D orbit and ground-track visualizer** — plots a satellite's position against real deep-space network ground station coordinates (Goldstone, Madrid, Canberra). *(Honest caveat: the actual telemetry data has no GPS/position fields, so this orbit is simulated from elapsed mission time using realistic orbital parameters — it's clearly labeled "SIMULATED" in the dashboard, not passed off as real tracking data.)*
- **A live exception registry and event timeline** — builds up automatically as the replay plays, showing exactly when and where things went wrong
- **Direct integration with V3** — pulls in the health scores, fault log, and mission report V3 already generated, so the analysis and the live view sit side by side

**Run it:**
```bash
cd Version_4
pip install streamlit plotly pandas
streamlit run dashboard.py
```
(If `streamlit` isn't recognized as a command, try `python -m streamlit run dashboard.py` instead.)

**Tech used:** Streamlit (the app shell, sidebar, tabs, live refresh) and Plotly (every gauge, chart, and the 3D orbit view).

**Bugs this version taught — the "smoothness" story:**
- The first version auto-refreshed by tearing down and rebuilding the *entire* page every tick, which caused a visible full-page flash on every update. Fixed by scoping the refresh to a single Streamlit "fragment" that updates on its own timer, leaving the rest of the page untouched.
- An attempt to *further* smooth things out — a CSS fade-in animation — actually made things worse, causing a rhythmic pulsing effect, because the elements it was applied to get rebuilt fresh on every tick rather than updated in place. Removed, and replaced with Plotly's own built-in transition/easing settings on the charts and gauges themselves, which genuinely do animate in place.

---

## Version 5 — Advanced Rule-Based Fault Detection *(planned)*

**In plain terms:** V1's fault detection only looks at one number at a time — "is the temperature too high?" Real failures are often more subtle: a fault might only really matter if *two* things are wrong at once, or one small problem might be an early warning sign of a bigger one about to happen.

**What it will do:**
- **Multi-condition rules** — e.g., "temperature is high **AND** voltage is low" might be a distinct, more serious failure signature than either alone
- **Cascading failure logic** — model how one fault increases the likelihood or severity of another (a real spacecraft engineering concept: failures rarely happen in isolation)

---

## Version 6 — Telemetry Packet Communication Simulator *(planned)*

**In plain terms:** every version so far assumes the data just magically arrives, perfectly. In reality, satellite data travels over a real (often unreliable) radio link, packaged into structured "packets" that can get corrupted or lost in transit. V6 simulates that transport layer itself.

**What it will do:**
- Encode and decode telemetry into structured packets, the way a real satellite communication link would
- Add checksum validation — a way to detect if a packet arrived corrupted
- Simulate packet corruption and loss, so the system can be tested against a "noisy," realistic communication channel, not just clean in-memory data

---

## Version 7 — AI-Based Anomaly Detection *(planned)*

**In plain terms:** every version so far detects problems using rules a human wrote in advance ("if X is above Y, it's a fault"). But real failures sometimes look like nothing anyone thought to check for. V7 is about teaching a model to notice "this doesn't look like anything I've seen before" — without being told in advance what "wrong" looks like.

**What it will do:**
- Train unsupervised machine learning models — **Isolation Forest** and **One-Class SVM** — on the accumulated data from V1 through V6
- These models learn what "normal" looks like from the data itself, then flag anything that doesn't fit that pattern — including failure modes no fixed threshold rule would ever catch
- This is the step that moves the project from a purely rule-based FDIR system toward a *learned* one

---

## Tech Stack

| Version(s) | Tools |
|---|---|
| V1–V3 | Python 3.x, `pandas`, `random`, `datetime`, `csv`, `json`, `argparse`, `os`, `time` |
| V4 | + `Streamlit`, `Plotly` |
| V6 (planned) | packet/checksum logic, likely pure Python |
| V7 (planned) | + `scikit-learn` (Isolation Forest, One-Class SVM) |

---

## Full Repository Structure

```
satellite_telemetry_system/
│
├── Version_1/
│   ├── simulator/generator.py
│   ├── monitor/fault_detector.py
│   ├── logger/telemetry_logger.py
│   ├── data/telemetry_log.csv
│   └── main.py
│
├── Version_2/
│   ├── simulator/generator.py    # V1 generator + fault injection
│   ├── monitor/fault_detector.py
│   ├── logger/telemetry_logger.py
│   ├── data/telemetry_log.csv
│   └── main.py
│
├── Version_3/
│   ├── log_loader_file.py
│   ├── summary_statistics_file.py
│   ├── event_detection_file.py
│   ├── fault_statistics_file.py
│   ├── mission_timeline_file.py
│   ├── health_score_file.py
│   ├── generate_report_file.py
│   └── main.py
│
└── Version_4/
    └── dashboard.py
```

---

## Domain Context

This project is modeled on real aerospace **FDIR** (Fault Detection, Isolation & Recovery) systems used in satellite ground-station software. The version-by-version structure mirrors how real telemetry pipelines are actually built: data acquisition, fault analysis, mission reporting, live visualization, and (eventually) learned anomaly detection are treated as separate, independently testable stages — not one giant script.

---

## Author

**Shivansh** — Data Science undergraduate, building toward aerospace AI systems, one module at a time.
