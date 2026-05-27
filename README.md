<<<<<<< HEAD
# satellite-telemetry-health-monitor
Real-time satellite telemetry simulator with rule-based fault detection and CSV logging. Built in Python with modular architecture.
=======
# Satellite Telemetry Health Monitoring System

A real-time satellite telemetry simulator with rule-based fault detection and CSV logging. Built in Python with a modular architecture.

---

## What This System Does

This system simulates a satellite health monitoring pipeline. It continuously generates telemetry readings for key satellite parameters, checks each reading against fault thresholds, and logs everything to a CSV file with timestamps — mimicking how real ground station software monitors spacecraft health.

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
└── main.py                   # Orchestrates all modules
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

---

## How To Run

No external dependencies required. Standard Python 3.x only.

```bash
python main.py
```

The system will start generating and logging telemetry every second. Press `Ctrl + C` to stop.

---

## Sample Output

```
{'timestamp': datetime.datetime(2026, 5, 23, 14, 42, 5), 'temperature': 71.4, 'battery': 97.5, 'voltage': 4.6, 'fuel': 64.5}
{'temperature': 'Normal', 'battery': 'Normal', 'voltage': 'Normal', 'fuel': 'Normal'}
```

---

## Hardest Bug Fixed

The fault detector initially checked `WARNING` before `CRITICAL` in every `if/elif` chain. This meant a battery reading of 3% would trigger `WARNING` instead of `CRITICAL` because `3 < 20` evaluates to `True` first and Python never reaches the `elif`. Fixed by always checking the most severe condition first.

---

## Version Roadmap

- **Version 1** ✅ — Telemetry simulator, fault detector, CSV logger
- **Version 2** — Fault injection, gradual battery drain, sensor freeze simulation
- **Version 3** — Health monitoring dashboard with visualization
- **Version 4** — AI-based anomaly detection using Isolation Forest
- **Version 5** — Predictive failure detection

---

## Tech Stack

- Python 3.x
- `random` — telemetry value simulation
- `datetime` — real-time timestamping
- `csv` — structured data logging
- `os` — file existence checking
- `time` — loop interval control

---

## Domain Context

This project is inspired by real aerospace FDIR systems (Fault Detection, Isolation, and Recovery) used in satellite ground station software. The modular architecture mirrors how real telemetry pipelines separate data acquisition, fault analysis, and data persistence into independent components.

---

## Author

Shivansh — building toward aerospace AI systems, one module at a time.
>>>>>>> 77ba5de4a73b725d65567b7580b42e662b7a8986
