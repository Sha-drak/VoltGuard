"""
VoltGuard Phase 1 - Data Structures
Defines critical data classes for sensor readings, system state, and anomaly detection
"""

from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from typing import List


@dataclass
class SensorReading:
    """
    Represents a single sensor reading from Arduino.
    
    Attributes:
        timestamp: datetime when reading was taken
        current: Current in Amperes
        temperature: Temperature in Celsius
    """
    timestamp: datetime
    current: float  # Amperes
    temperature: float  # Celsius
    
    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] I={self.current:.2f}A T={self.temperature:.2f}°C"


@dataclass
class SystemState:
    """
    Represents complete system state at a point in time.
    
    Attributes:
        state: System classification ("SAFE", "WARNING", or "CRITICAL")
        relay_status: Relay position ("ON" or "OFF")
        anomaly_detected: Boolean; True if anomaly detected
        hardware_override_triggered: Boolean; True if hardware override active
        current: Current reading in Amperes
        temperature: Temperature reading in Celsius
        timestamp: When this state was determined
    """
    state: str  # "SAFE", "WARNING", or "CRITICAL"
    relay_status: str  # "ON" or "OFF"
    anomaly_detected: bool
    hardware_override_triggered: bool
    current: float
    temperature: float
    timestamp: datetime
    
    def __str__(self):
        return f"State={self.state:8s} Relay={self.relay_status:3s} Anomaly={str(self.anomaly_detected):5s} I={self.current:.2f}A T={self.temperature:.2f}°C"


@dataclass
class AnomalyBuffer:
    """
    Ring buffer for tracking rate-of-change anomalies.
    Maintains a fixed-size window of sensor readings for calculating derivatives.
    
    Attributes:
        size: Maximum number of readings to keep
        readings: Deque of SensorReading objects
    """
    size: int = 5
    readings: deque = field(default_factory=deque)
    
    def __post_init__(self):
        """Initialize the deque with max length."""
        self.readings = deque(maxlen=self.size)
    
    def add(self, reading: SensorReading):
        """
        Add a sensor reading to the buffer.
        Automatically removes oldest reading if buffer is full.
        
        Args:
            reading: SensorReading to add
        """
        self.readings.append(reading)
    
    def get_current_rate(self) -> float:
        """
        Calculate rate of change of current in A/s.
        
        Returns:
            Current rate of change (A/s), or 0.0 if insufficient data
        """
        if len(self.readings) < 2:
            return 0.0
        
        # Get oldest and newest readings
        oldest = self.readings[0]
        newest = self.readings[-1]
        
        # Calculate time delta
        time_delta = (newest.timestamp - oldest.timestamp).total_seconds()
        if time_delta <= 0:
            return 0.0
        
        # Calculate current delta
        current_delta = newest.current - oldest.current
        
        # Return rate of change
        return current_delta / time_delta
    
    def get_temp_rate(self) -> float:
        """
        Calculate rate of change of temperature in °C/s.
        
        Returns:
            Temperature rate of change (°C/s), or 0.0 if insufficient data
        """
        if len(self.readings) < 2:
            return 0.0
        
        # Get oldest and newest readings
        oldest = self.readings[0]
        newest = self.readings[-1]
        
        # Calculate time delta
        time_delta = (newest.timestamp - oldest.timestamp).total_seconds()
        if time_delta <= 0:
            return 0.0
        
        # Calculate temperature delta
        temp_delta = newest.temperature - oldest.temperature
        
        # Return rate of change
        return temp_delta / time_delta
    
    def is_full(self) -> bool:
        """
        Check if buffer is at maximum capacity.
        
        Returns:
            True if buffer has max readings, False otherwise
        """
        return len(self.readings) == self.size
    
    def __len__(self):
        """Return number of readings in buffer."""
        return len(self.readings)
    
    def __str__(self):
        """String representation of buffer contents."""
        if len(self.readings) == 0:
            return "AnomalyBuffer[empty]"
        
        rates = f"I_rate={self.get_current_rate():.2f}A/s T_rate={self.get_temp_rate():.2f}°C/s"
        readings_str = " → ".join([f"I={r.current:.2f}A" for r in self.readings])
        return f"AnomalyBuffer[{len(self.readings)}/{self.size}] {readings_str} ({rates})"


@dataclass
class EventLogEntry:
    """
    Represents a single event log entry.
    
    Attributes:
        timestamp: When event occurred
        event_type: Type of event (STATE_CHANGE, SHUTDOWN, ANOMALY_DETECTED, TIMEOUT, MANUAL_RESET, SMS_SENT, etc.)
        state: System state at time of event
        relay: Relay status at time of event
        current: Current reading at time of event
        temperature: Temperature reading at time of event
        description: Optional descriptive text
    """
    timestamp: datetime
    event_type: str  # STATE_CHANGE, SHUTDOWN, ANOMALY_DETECTED, TIMEOUT, MANUAL_RESET, SMS_SENT, SMS_ALERT_TRIGGERED, etc.
    state: str
    relay: str
    current: float
    temperature: float
    description: str = ""
    
    def to_csv_row(self) -> str:
        """Convert to CSV row format."""
        return f"{self.timestamp.isoformat()},{self.event_type},{self.state},{self.relay},{self.current:.2f},{self.temperature:.2f},{self.description}\n"
    
    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.event_type:20s} State={self.state:8s} Relay={self.relay:3s}"


# Constants for event types
EVENT_TYPES = {
    "STATE_CHANGE": "System state changed",
    "SHUTDOWN": "System shutdown triggered",
    "ANOMALY_DETECTED": "Anomaly detected",
    "TIMEOUT": "Communication timeout",
    "MANUAL_RESET": "Manual reset performed",
    "SMS_SENT": "SMS alert sent",
    "SMS_ALERT_TRIGGERED": "SMS alert triggered",
    "HARDWARE_OVERRIDE_TRIGGERED": "Hardware override triggered",
    "LOCKOUT_TRIGGERED": "Lockout rule triggered",
}


if __name__ == "__main__":
    # Test: Create sample data structures
    print("Testing data structures...")
    
    # Test SensorReading
    reading = SensorReading(datetime.now(), 2.5, 36.0)
    print(f"✓ SensorReading: {reading}")
    
    # Test AnomalyBuffer
    buffer = AnomalyBuffer(size=5)
    import time
    for i in range(5):
        reading = SensorReading(datetime.now(), 2.0 + i * 0.5, 36.0 + i * 2)
        buffer.add(reading)
        time.sleep(0.1)
    print(f"✓ AnomalyBuffer: {buffer}")
    print(f"  Current rate: {buffer.get_current_rate():.2f} A/s")
    print(f"  Temp rate: {buffer.get_temp_rate():.2f} °C/s")
    
    # Test SystemState
    state = SystemState(
        state="SAFE",
        relay_status="ON",
        anomaly_detected=False,
        hardware_override_triggered=False,
        current=2.5,
        temperature=36.0,
        timestamp=datetime.now()
    )
    print(f"✓ SystemState: {state}")
    
    # Test EventLogEntry
    entry = EventLogEntry(
        timestamp=datetime.now(),
        event_type="STATE_CHANGE",
        state="SAFE",
        relay="ON",
        current=2.5,
        temperature=36.0,
        description="Initial state"
    )
    print(f"✓ EventLogEntry: {entry}")
    print(f"✓ CSV format: {entry.to_csv_row().strip()}")
    
    print("\n✓ All data structures working correctly!")
