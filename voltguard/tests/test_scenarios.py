import sys
import time
from pathlib import Path
from datetime import datetime, timedelta


base_dir = Path(__file__).parent.parent
python_engine_dir = base_dir / "python-engine"
sys.path.insert(0, str(base_dir))
sys.path.insert(0, str(python_engine_dir))

from main import VoltGuardApplication
from config.config import load_config
from decision_engine import DecisionEngine


def run_cycles(app: VoltGuardApplication, count: int, delay: float = 0.2):
    states = []
    for _ in range(count):
        state = app.run_decision_cycle()
        if state:
            states.append(state.state)
        time.sleep(delay)
    return states


def test_scenario_stable_stays_safe():
    app = VoltGuardApplication(use_simulator=True, simulator_mode="stable")
    try:
        states = run_cycles(app, count=8)
        assert len(states) > 0
        assert all(state == "SAFE" for state in states)
    finally:
        app.stop()


def test_scenario_rising_current_reaches_critical():
    app = VoltGuardApplication(use_simulator=True, simulator_mode="rising_current")
    try:
        states = run_cycles(app, count=55, delay=0.5)
        assert "WARNING" in states
        assert "CRITICAL" in states
    finally:
        app.stop()


def test_scenario_fault_triggers_critical_and_lockout():
    app = VoltGuardApplication(use_simulator=True, simulator_mode="fault")
    try:
        states = run_cycles(app, count=8)
        assert "CRITICAL" in states
        assert app.decision_engine.locked_out is True
    finally:
        app.stop()


def test_scenario_rising_temp_triggers_anomaly_and_critical():
    app = VoltGuardApplication(use_simulator=True, simulator_mode="rising_temp")
    try:
        anomaly_seen = False
        critical_seen = False
        for _ in range(12):
            state = app.run_decision_cycle()
            if state:
                anomaly_seen = anomaly_seen or state.anomaly_detected
                critical_seen = critical_seen or (state.state == "CRITICAL")
            time.sleep(0.3)

        assert anomaly_seen is True
        assert critical_seen is True
    finally:
        app.stop()


def test_scenario_fail_safe_timeout_forces_critical():
    config = load_config()
    engine = DecisionEngine(config)
    engine.last_signal_timestamp = datetime.now() - timedelta(seconds=config["FAIL_SAFE_TIMEOUT"] + 1)
    assert engine.check_fail_safe() is True


def test_scenario_lockout_requires_manual_reset():
    config = load_config()
    engine = DecisionEngine(config)
    engine.trigger_lockout()
    assert engine.locked_out is True
    reset_ok = engine.reset_lockout_manual()
    assert reset_ok is True
    assert engine.locked_out is False
