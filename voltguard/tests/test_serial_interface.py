import sys
from pathlib import Path


base_dir = Path(__file__).parent.parent
python_engine_dir = base_dir / "python-engine"
sys.path.insert(0, str(base_dir))
sys.path.insert(0, str(python_engine_dir))

from serial_interface import SimulatorSerialConnection, create_serial_connection


def test_simulator_connection_reads_data():
    conn = SimulatorSerialConnection(mode="stable")
    try:
        reading = conn.read_line()
        assert reading.startswith("C=")
        assert ",T=" in reading
    finally:
        conn.close()


def test_simulator_connection_accepts_state_commands():
    conn = SimulatorSerialConnection(mode="stable")
    try:
        conn.write_command("SAFE")
        conn.write_command("WARNING")
        conn.write_command("CRITICAL")
    finally:
        conn.close()


def test_factory_returns_simulator_connection():
    conn = create_serial_connection(use_simulator=True, mode="stable")
    try:
        assert conn.is_connected() is True
    finally:
        conn.close()
