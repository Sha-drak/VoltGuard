# VoltGuard Phase 1 - Software & Simulator

## Overview
VoltGuard Phase 1 is a software-only implementation of the electrical safety pipeline:

Sensor Data -> AI Decision -> Hardware Action (simulated) -> User Feedback

This build includes:
- Arduino simulator (`C=X,T=Y` stream)
- Python decision engine (SAFE/WARNING/CRITICAL + anomaly checks)
- Streamlit dashboard (read-only monitoring)
- SMS abstraction layer (mock provider for Phase 1)

## Project Structure
`voltguard/` contains all runtime modules:
- `arduino-simulator/simulator.py`
- `python-engine/decision_engine.py`
- `python-engine/serial_interface.py`
- `python-engine/data_structures.py`
- `python-engine/sms_provider.py`
- `python-engine/main.py`
- `streamlit-dashboard/dashboard.py`
- `config/config.py`
- `tests/`
- `logs/events.csv` (created/updated at runtime)

## Prerequisites
- Python 3.13+
- Virtual environment at `.venv`
- Dependencies:
  - `streamlit`
  - `pytest`
  - `pyserial`
  - `requests`
  - `plotly`

## Installation
From the repository root:

```powershell
cd "c:\Users\user\Desktop\VoltGuard"
.\.venv\Scripts\Activate.ps1
pip install streamlit pytest pyserial requests plotly
```

## Run The Dashboard
From repo root:

```powershell
.\.venv\Scripts\python -m streamlit run "voltguard/streamlit-dashboard/dashboard.py"
```

## Run Demo Scenarios
From repo root:

```powershell
.\.venv\Scripts\python "voltguard/python-engine/main.py" --demo 0 --duration 30
.\.venv\Scripts\python "voltguard/python-engine/main.py" --demo 1 --duration 40
.\.venv\Scripts\python "voltguard/python-engine/main.py" --demo 2 --duration 10
.\.venv\Scripts\python "voltguard/python-engine/main.py" --demo 3 --duration 10
```

Demo modes:
- `0`: stable
- `1`: rising_current
- `2`: rising_temp
- `3`: fault

## Run Tests
From repo root:

```powershell
.\.venv\Scripts\python -m pytest "voltguard/tests" -v
```

## Logs
Event logs are written to:

`voltguard/logs/events.csv`

## Phase 2 Preparation
When hardware is available:
- replace simulator connection with `RealSerialConnection`
- configure real serial port in `config/config.py`
- wire `ArkeselSMSProvider` API call implementation
