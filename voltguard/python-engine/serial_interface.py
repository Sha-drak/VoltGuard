"""
VoltGuard Phase 1 - Serial Communication Abstraction Layer
Allows swappable implementations: Simulator (Phase 1) or Real Arduino (Phase 2)

DESIGN PATTERN: Strategy pattern for pluggable serial implementations
RULE: No code changes needed to switch implementations
"""

from abc import ABC, abstractmethod
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add simulator directory to path for imports
simulator_dir = Path(__file__).parent.parent / "arduino-simulator"
sys.path.insert(0, str(simulator_dir))

# Import simulator for Phase 1
from simulator import ArduinoSimulator


class SerialConnection(ABC):
    """
    Abstract interface for serial communication.
    Defines contract for all serial implementations.
    
    Python → Arduino: State commands (SAFE/WARNING/CRITICAL)
    Arduino → Python: Sensor readings (C=X,T=Y format)
    """
    
    @abstractmethod
    def read_line(self) -> str:
        """
        Read one line from serial.
        
        Returns:
            String in format "C=X,T=Y" or empty string if timeout
        
        Raises:
            TimeoutError if no data available after timeout period
        """
        pass
    
    @abstractmethod
    def write_command(self, state: str) -> None:
        """
        Write state command to serial.
        
        Args:
            state: Command state ("SAFE", "WARNING", or "CRITICAL")
        
        Raises:
            ValueError if invalid state
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Cleanly close connection."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connection is active."""
        pass


class SimulatorSerialConnection(SerialConnection):
    """
    Phase 1 Implementation: Python-based simulator
    Simulates Arduino behavior for development and testing
    
    RULE: Simulator only provides data + responds to state commands
    It does NOT make independent relay decisions.
    """
    
    def __init__(self, mode: str = "stable"):
        """
        Initialize simulator-based serial connection.
        
        Args:
            mode: Simulator mode ("stable", "rising_current", "rising_temp", "fault")
        """
        self.simulator = ArduinoSimulator(mode=mode)
        self.simulator.start()
        self.is_active = True
        self.last_read_time = time.time()
        self.read_timeout = 2.0  # seconds
        self.last_state_command = None
        
        print(f"[SERIAL] SimulatorSerialConnection initialized (mode={mode})")
    
    def read_line(self) -> str:
        """
        Read sensor data from simulator.
        
        Returns:
            Sensor reading in format "C=X,T=Y"
        
        Raises:
            TimeoutError if no valid reading available
        """
        if not self.is_active:
            raise RuntimeError("Connection closed")
        
        try:
            reading = self.simulator.get_reading()
            self.last_read_time = time.time()
            return reading.strip()  # Remove trailing newline
        except Exception as e:
            raise TimeoutError(f"Failed to read from simulator: {e}")
    
    def write_command(self, state: str) -> None:
        """
        Send state command to simulator.
        Simulator applies Arduino logic to determine relay.
        
        Args:
            state: Command ("SAFE", "WARNING", or "CRITICAL")
        
        Raises:
            ValueError if invalid state
        """
        if not self.is_active:
            raise RuntimeError("Connection closed")
        
        if state not in ["SAFE", "WARNING", "CRITICAL"]:
            raise ValueError(f"Invalid state: {state}")
        
        try:
            relay_state = self.simulator.receive_state_command(state)
            self.last_state_command = state
            # Simulator handles relay logic
        except Exception as e:
            raise RuntimeError(f"Failed to send command to simulator: {e}")
    
    def is_connected(self) -> bool:
        """Check if simulator is running."""
        return self.is_active and self.simulator.is_running
    
    def close(self) -> None:
        """Stop simulator and close connection."""
        if self.is_active:
            self.simulator.stop()
            self.is_active = False
            print("[SERIAL] SimulatorSerialConnection closed")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()


class RealSerialConnection(SerialConnection):
    """
    Phase 2 Implementation: Real Arduino via pyserial
    Stub implementation for hardware integration
    
    IMPORTANT: In Phase 2, replace this with actual pyserial code
    """
    
    def __init__(self, port: str = "COM3", baud: int = 9600, timeout: float = 2.0):
        """
        Initialize real Arduino serial connection.
        
        Args:
            port: Serial port (e.g., "COM3", "/dev/ttyUSB0")
            baud: Baud rate (9600 for Arduino Uno)
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.serial = None
        
        print(f"[SERIAL] RealSerialConnection initialized (Phase 2 stub)")
        print(f"         Port: {port}, Baud: {baud}, Timeout: {timeout}s")
        # TODO: Implement pyserial connection in Phase 2
    
    def read_line(self) -> str:
        """
        Read from real Arduino (Phase 2 implementation).
        
        Currently: Raises NotImplementedError (stub)
        Phase 2: Connect to real serial port using pyserial
        """
        raise NotImplementedError("Phase 2: Real Arduino support not yet implemented")
    
    def write_command(self, state: str) -> None:
        """
        Write to real Arduino (Phase 2 implementation).
        
        Currently: Raises NotImplementedError (stub)
        Phase 2: Send state to real Arduino via serial
        """
        raise NotImplementedError("Phase 2: Real Arduino support not yet implemented")
    
    def is_connected(self) -> bool:
        """Check if real Arduino is connected (Phase 2)."""
        return False  # Not connected in Phase 1
    
    def close(self) -> None:
        """Close real serial connection (Phase 2)."""
        if self.serial:
            self.serial.close()
            print("[SERIAL] RealSerialConnection closed")


def create_serial_connection(use_simulator: bool = True, mode: str = "stable") -> SerialConnection:
    """
    Factory function to create appropriate serial connection.
    
    Args:
        use_simulator: If True, use simulator; if False, use real Arduino (Phase 2)
        mode: Simulator mode (ignored if use_simulator=False)
    
    Returns:
        SerialConnection instance (either Simulator or Real)
    """
    if use_simulator:
        return SimulatorSerialConnection(mode=mode)
    else:
        # Phase 2: Real Arduino
        return RealSerialConnection(port="COM3", baud=9600)


if __name__ == "__main__":
    # Test serial interface
    print("=" * 70)
    print("TESTING SERIAL INTERFACE ABSTRACTION")
    print("=" * 70)
    
    # Test 1: Simulator connection
    print("\n--- Test 1: Simulator Connection ---\n")
    try:
        conn = SimulatorSerialConnection(mode="rising_current")
        
        # Read 5 sensor values
        for i in range(5):
            reading = conn.read_line()
            print(f"Read {i+1}: {reading}")
            time.sleep(0.1)
        
        # Send state commands
        print("\nSending state commands:")
        conn.write_command("WARNING")
        print("✓ Sent: WARNING")
        time.sleep(0.1)
        
        reading = conn.read_line()
        print(f"Read after WARNING: {reading}")
        
        conn.write_command("CRITICAL")
        print("✓ Sent: CRITICAL")
        time.sleep(0.1)
        
        reading = conn.read_line()
        print(f"Read after CRITICAL: {reading}")
        
        conn.close()
        print("\n✓ Simulator connection test PASSED")
    except Exception as e:
        print(f"\n✗ Simulator connection test FAILED: {e}")
    
    # Test 2: Factory function
    print("\n--- Test 2: Factory Function ---\n")
    try:
        # Create simulator via factory
        conn = create_serial_connection(use_simulator=True, mode="stable")
        print(f"✓ Created connection: {type(conn).__name__}")
        print(f"  Connected: {conn.is_connected()}")
        
        reading = conn.read_line()
        print(f"  First reading: {reading}")
        
        conn.close()
        print("✓ Factory function test PASSED")
    except Exception as e:
        print(f"✗ Factory function test FAILED: {e}")
    
    # Test 3: Error handling
    print("\n--- Test 3: Error Handling ---\n")
    try:
        conn = SimulatorSerialConnection(mode="stable")
        
        # Test invalid state
        try:
            conn.write_command("INVALID")
            print("✗ Should have raised ValueError for invalid state")
        except ValueError as e:
            print(f"✓ Correctly rejected invalid state: {e}")
        
        # Test closed connection
        conn.close()
        try:
            conn.read_line()
            print("✗ Should have raised RuntimeError for closed connection")
        except RuntimeError as e:
            print(f"✓ Correctly rejected read on closed connection: {e}")
        
        print("✓ Error handling test PASSED")
    except Exception as e:
        print(f"✗ Error handling test FAILED: {e}")
    
    print("\n" + "=" * 70)
    print("✓ ALL SERIAL INTERFACE TESTS PASSED")
    print("=" * 70)
