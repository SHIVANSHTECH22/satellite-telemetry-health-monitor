# Satellite Telemetry Health Monitoring System

A real-time satellite telemetry simulator with rule-based fault detection and CSV logging. Built in Python with a modular architecture.

---

## What This System Does

This system simulates a satellite health monitoring pipeline. It continuously generates telemetry readings for key satellite parameters, checks each reading against fault thresholds, and logs everything to a CSV file with timestamps — mimicking how real ground station software monitors spacecraft health.

V3 extends this into an offline analysis engine: it takes a completed telemetry log, detects sustained fault events, computes fault statistics, builds a mission timeline, scores subsystem health, and generates a full mission report.

---

## System Architecture

```
satellite_telemetry/
│
├── simulator/
│   └── generator.py          # Generates simulated telemetry data
│
├── monitor/
│   └── fault_detector.py     # Rule-based fault detection engine
│
├── logger/
│   └── telemetry_logger.py   # Logs telemetry + fault status to CSV
│
├── data/
│   └── telemetry_log.csv     # Auto-generated on first run
│
├── Version_3/
│   ├── log_loader_file.py          # CSV loading, validation, quality checks
│   ├── summary_statistics_file.py  # Per-parameter statistics
│   ├── event_detection_file.py     # Threshold breach / fault detection
│   ├── fault_statistics_file.py    # Aggregate fault metrics
│   ├── mission_timeline_file.py    # Chronological mission event log
│   ├── health_score_file.py        # Subsystem health scoring
│   ├── generate_report_file.py     # JSON, CSV, and text report generation
│   └── main.py                     # Orchestrates all V3 modules
│
└── main.py                   # Orchestrates simulator/monitor/logger modules
```

---

## Modules

### simulator/generator.py
Generates one telemetry snapshot per second using `random.uniform()` within realistic satellite parameter ranges. Parameters include temperature, battery, voltage, and fuel. Uses `datetime.now()` for real timestamps.

### monitor/fault_detector.py
Receives a telemetry snapshot and checks each parameter against defined thresholds. Returns a fault status dictionary with `NORMAL`, `WARNING`, or `CRITICAL` for each parameter.

Thresholds used:

| Parameter | WARNING | CRITICAL |
|---|---|---|
| Temperature (°C) | > 75 | > 90 |
| Battery (%) | < 20 | < 10 |
| Voltage (V) | < 3.5 | < 3.3 |
| Fuel (%) | < 15 | < 5 |

### logger/telemetry_logger.py
Receives the telemetry snapshot and fault status dictionary. Writes one row per reading to `telemetry_log.csv` with full timestamps. Creates the file with headers on first run, then appends on every subsequent run.

### Version_3/ — Telemetry Log Analyzer
Takes a completed telemetry CSV log and produces a full offline mission analysis:

- **log_loader_file.py** — loads and validates the CSV, checks for missing values, out-of-order timestamps, duplicates, and physically impossible sensor readings.
- **summary_statistics_file.py** — computes mean, min, max, std deviation, rate of change, nominal percentage, and trend per parameter.
- **event_detection_file.py** — scans for sustained threshold breaches (minimum 3 consecutive samples), classifies warning vs. critical, tracks recovery.
- **fault_statistics_file.py** — aggregates fault counts, frequency, recovery rate, most-faulted parameter, longest fault duration, and severity distribution.
- **mission_timeline_file.py** — builds a chronological event log from mission start to end.
- **health_score_file.py** — scores Battery, Fuel, and Thermal subsystems (starting at 100, deducted per fault), and computes an Overall score bounded by the worst subsystem.
- **generate_report_file.py** — writes `health_scores.json`, `mission_timeline.json`, `fault_log.csv`, and a human-readable `mission_report.txt`.
- **main.py** — single entry point that runs the full V3 pipeline end to end.

---

## How To Run

No external dependencies required beyond `pandas`. Standard Python 3.x otherwise.

**Live simulator (V1/V2):**
```bash
python main.py
```
The system will start generating and logging telemetry every second. Press `Ctrl + C` to stop.

**Offline log analyzer (V3):**
```bash
cd Version_3
python main.py --file ../Version_1/data/telemetry_log.csv
```
Produces `health_scores.json`, `mission_timeline.json`, `fault_log.csv`, and `mission_report.txt` in the `Version_3` folder.

---

## Sample Output

**Live simulator:**
```
{'timestamp': datetime.datetime(2026, 5, 23, 14, 42, 5), 'temperature': 71.4, 'battery': 97.5, 'voltage': 4.6, 'fuel': 64.5}
{'temperature': 'Normal', 'battery': 'Normal', 'voltage': 'Normal', 'fuel': 'Normal'}
```

**V3 analyzer (fault_stats excerpt):**
```
{'total_faults': 18, 'faults_per_parameter': {'temperature': 15, 'battery': 2, 'fuel': 1, 'voltage': 0},
'fault_frequency_per_hour': 0.189, 'recovery_rate': 88.89, 'most_faulted_parameter': 'temperature',
'longest_fault_duration': 273413.95, 'severity': {'warning': 12, 'critical': 6}}
```

---

## Hardest Bugs Fixed

**Severity check order (V1/V2):** the fault detector initially checked `WARNING` before `CRITICAL` in every `if/elif` chain. This meant a battery reading of 3% would trigger `WARNING` instead of `CRITICAL` because `3 < 20` evaluates to `True` first and Python never reaches the `elif`. Fixed by always checking the most severe condition first.

**Timestamp JSON serialization (V3):** `mission_timeline.json` failed with `TypeError: Object of type Timestamp is not JSON serializable`, since `pd.to_datetime()` converts the timestamp column into pandas `Timestamp` objects, which the `json` module doesn't know how to serialize. Fixed by converting timestamps to strings before/during the JSON dump.

**Empty event list guard (V3):** building CSV fieldnames from `event_list[0].keys()` would crash with an `IndexError` on clean data with zero faults. Fixed with a length check before attempting the CSV write.

---

## Current Progress

- ✅ V1 — Telemetry Monitoring System
- ✅ V2 — Fault Injection Engine
- ✅ V3 — Telemetry Log Analyzer
  - ✅ Log Loader
  - ✅ Summary Statistics
  - ✅ Event Detection
  - ✅ Fault Statistics
  - ✅ Mission Timeline
  - ✅ Health Score
  - ✅ Report Generator (JSON, CSV, and text outputs)
  - ✅ main.py entry point
  - ✅ Tested end-to-end on clean (V1) and fault-injected (V2) data
- 🔜 V4 — Telemetry Visualization Dashboard
- 🔜 V5 — Advanced Rule-Based Fault Detection
- 🔜 V6 — Packet Communication Simulator
- 🔜 V7 — AI Anomaly Detection

---

## Tech Stack

- Python 3.x
- `pandas` — telemetry data loading and analysis (V3)
- `random` — telemetry value simulation
- `datetime` — real-time timestamping
- `csv` — structured data logging and reporting
- `json` — structured report output
- `argparse` — command-line interface
- `os` — file existence checking
- `time` — loop interval control

---

## Domain Context

This project is inspired by real aerospace FDIR systems (Fault Detection, Isolation, and Recovery) used in satellite ground station software. The modular architecture mirrors how real telemetry pipelines separate data acquisition, fault analysis, and data persistence into independent components.

---

## Author

Shivansh — building toward aerospace AI systems, one module at a time.
