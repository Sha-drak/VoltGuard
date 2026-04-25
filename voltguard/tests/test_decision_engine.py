import sys
from pathlib import Path
from datetime import datetime, timedelta


base_dir = Path(__file__).parent.parent
python_engine_dir = base_dir / "python-engine"
sys.path.insert(0, str(base_dir))
sys.path.insert(0, str(python_engine_dir))

from config.config import load_config
from data_structures import AnomalyBuffer, SensorReading
from decision_engine import (
    parse_serial_data,
    classify_state,
    detect_anomaly,
    apply_hardware_override,
    DecisionEngine,
)


def test_parse_serial_data_valid():
    current, temperature = parse_serial_data("C=2.50,T=36.00")
    assert current == 2.50
    assert temperature == 36.00


def test_parse_serial_data_invalid():
    try:
        parse_serial_data("BAD_FORMAT")
        assert False, "Expected ValueError for malformed input"
    except ValueError:
        assert True


def test_classify_state_boundaries():
    config = load_config()
    assert classify_state(4.9, 39.9, config) == "SAFE"
    assert classify_state(5.0, 39.0, config) == "WARNING"
    assert classify_state(3.0, 40.0, config) == "WARNING"
    assert classify_state(10.1, 55.0, config) == "CRITICAL"


def test_detect_anomaly_true_for_rapid_change():
    config = load_config()
    buffer = AnomalyBuffer(size=5)
    now = datetime.now()
    buffer.add(SensorReading(timestamp=now, current=1.0, temperature=30.0))
    buffer.add(SensorReading(timestamp=now + timedelta(seconds=0.5), current=4.0, temperature=30.0))
    assert detect_anomaly(buffer, config) is True


def test_apply_hardware_override():
    config = load_config()
    assert apply_hardware_override(16.0, 35.0, config) is True
    assert apply_hardware_override(10.0, 76.0, config) is True
    assert apply_hardware_override(10.0, 35.0, config) is False


def test_fail_safe_timeout():
    config = load_config()
    engine = DecisionEngine(config)
    engine.reset_fail_safe_timer()
    assert engine.check_fail_safe() is False
    engine.last_signal_timestamp = datetime.now() - timedelta(seconds=3.5)
    assert engine.check_fail_safe() is True
