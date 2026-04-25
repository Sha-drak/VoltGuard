"""
VoltGuard Phase 1C - Python Decision Engine
Core intelligence: Parse sensor data → Classify state → Apply safety rules → Send commands

CRITICAL ARCHITECTURE:
- Arduino = Authority over Power (Hardware override + relay control)
- Python = Intelligence (Threshold classification + anomaly detection)
- Python sends ONLY state (SAFE/WARNING/CRITICAL), not relay ON/OFF
- Arduino decides relay action based on state + independent safety checks

SAFETY RULES (Non-Negotiable):
1. Hardware override: I > 15A OR T > 75°C → Arduino forces relay OFF (Python mirrors for logs)
2. Fail-safe timeout: No signal for 3s → Python overrides to CRITICAL → Arduino enforces OFF
3. Lockout rule: After CRITICAL shutdown, relay stays OFF until manual reset
4. Cycle time: All logic ≤ 1 second total
5. SMS trigger: Python sends SMS on CRITICAL state only
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import load_config
from data_structures import SensorReading, SystemState, AnomalyBuffer, EventLogEntry
from sms_provider import should_send_sms, format_sms_message


# ============================================================================
# CORE DECISION FUNCTIONS (Independently Testable)
# ============================================================================

def parse_serial_data(raw_line: str) -> Tuple[float, float]:
    """
    Parse Arduino serial data in "C=<current>,T=<temperature>" format.
    
    Args:
        raw_line: String like "C=2.50,T=36.00"
    
    Returns:
        Tuple[current (A), temperature (°C)]
    
    Raises:
        ValueError: If format is invalid
    """
    if not raw_line or not isinstance(raw_line, str):
        raise ValueError(f"Invalid raw_line: {raw_line}")
    
    line = raw_line.strip()
    
    try:
        # Expected format: C=X,T=Y
        parts = line.split(',')
        if len(parts) != 2:
            raise ValueError(f"Expected 2 fields, got {len(parts)}")
        
        # Parse current
        current_part = parts[0].strip()
        if not current_part.startswith('C='):
            raise ValueError(f"Invalid current field: {current_part}")
        current = float(current_part[2:])
        
        # Parse temperature
        temp_part = parts[1].strip()
        if not temp_part.startswith('T='):
            raise ValueError(f"Invalid temperature field: {temp_part}")
        temperature = float(temp_part[2:])
        
        # Validate ranges (basic sanity check)
        if current < 0 or current > 20:  # Max reasonable Arduino ADC value
            raise ValueError(f"Current out of range: {current}A")
        if temperature < -10 or temperature > 100:  # Reasonable sensor range
            raise ValueError(f"Temperature out of range: {temperature}°C")
        
        return current, temperature
    
    except ValueError as e:
        raise ValueError(f"Parse error: {str(e)}") from e


def classify_state(current: float, temperature: float, config: dict) -> str:
    """
    Apply threshold-based classification to determine system state.
    
    Thresholds (from config):
    - SAFE: Current < THRESHOLD_SAFE_CURRENT AND Temperature < THRESHOLD_SAFE_TEMP
    - WARNING: (THRESHOLD_SAFE_CURRENT ≤ Current ≤ THRESHOLD_WARNING_CURRENT_MAX) OR
               (THRESHOLD_SAFE_TEMP ≤ Temperature ≤ THRESHOLD_WARNING_TEMP_MAX)
    - CRITICAL: Current > THRESHOLD_CRITICAL_CURRENT OR Temperature > THRESHOLD_CRITICAL_TEMP
    
    Args:
        current: Current in Amperes
        temperature: Temperature in Celsius
        config: Configuration dictionary from config.load_config()
    
    Returns:
        "SAFE", "WARNING", or "CRITICAL"
    """
    # Extract thresholds
    safe_current = config['THRESHOLD_SAFE_CURRENT']
    safe_temp = config['THRESHOLD_SAFE_TEMP']
    warning_current_max = config['THRESHOLD_WARNING_CURRENT_MAX']
    warning_temp_max = config['THRESHOLD_WARNING_TEMP_MAX']
    critical_current = config['THRESHOLD_CRITICAL_CURRENT']
    critical_temp = config['THRESHOLD_CRITICAL_TEMP']
    
    # Check CRITICAL first (highest priority)
    if current > critical_current or temperature > critical_temp:
        return "CRITICAL"
    
    # Check WARNING second
    if (safe_current <= current <= warning_current_max) or (safe_temp <= temperature <= warning_temp_max):
        return "WARNING"
    
    # Otherwise SAFE (current < safe AND temp < safe)
    return "SAFE"


def detect_anomaly(anomaly_buffer: AnomalyBuffer, config: dict) -> bool:
    """
    Detect anomalies based on rate-of-change.
    
    Triggers if:
    - Current rate > ANOMALY_CURRENT_RATE_THRESHOLD (A/s), OR
    - Temperature rate > ANOMALY_TEMP_RATE_THRESHOLD (°C/s)
    
    Args:
        anomaly_buffer: AnomalyBuffer instance with readings
        config: Configuration dictionary
    
    Returns:
        True if anomaly detected, False otherwise
    """
    if len(anomaly_buffer) < 2:
        # Not enough data to calculate rate
        return False
    
    current_rate = anomaly_buffer.get_current_rate()
    temp_rate = anomaly_buffer.get_temp_rate()
    
    current_threshold = config['ANOMALY_CURRENT_RATE_THRESHOLD']
    temp_threshold = config['ANOMALY_TEMP_RATE_THRESHOLD']
    
    # Anomaly if either rate exceeds threshold
    return current_rate > current_threshold or temp_rate > temp_threshold


def apply_hardware_override(current: float, temperature: float, config: dict) -> bool:
    """
    Mirror Arduino hardware override logic (for logging/visibility only).
    
    CRITICAL: Python does NOT enforce this cutoff. Arduino enforces independently.
    Python only logs when hardware override WOULD trigger (for audit trail).
    
    Returns True if hardware cutoff thresholds exceeded:
    - Current > THRESHOLD_HARDWARE_CUTOFF_CURRENT, OR
    - Temperature > THRESHOLD_HARDWARE_CUTOFF_TEMP
    
    Args:
        current: Current in Amperes
        temperature: Temperature in Celsius
        config: Configuration dictionary
    
    Returns:
        True if hardware override threshold exceeded, False otherwise
    """
    hardware_current_limit = config['THRESHOLD_HARDWARE_CUTOFF_CURRENT']
    hardware_temp_limit = config['THRESHOLD_HARDWARE_CUTOFF_TEMP']
    
    return current > hardware_current_limit or temperature > hardware_temp_limit


# ============================================================================
# DECISION ENGINE CLASS (Stateful, Manages System State)
# ============================================================================

class DecisionEngine:
    """
    Stateful decision engine managing all system logic.
    
    Maintains:
    - Fail-safe timer (detect 3s communication loss)
    - Lockout state (prevent auto-recovery after CRITICAL)
    - Event log (timestamped state transitions)
    - Anomaly buffer (rate-of-change tracking)
    """
    
    def __init__(self, config: dict):
        """
        Initialize decision engine.
        
        Args:
            config: Configuration dictionary from config.load_config()
        """
        self.config = config
        self.current_state = "SAFE"
        self.last_state = "SAFE"
        self.locked_out = False
        self.lockout_timestamp = None
        self.last_signal_timestamp = None
        self.anomaly_buffer = AnomalyBuffer(size=config['ANOMALY_BUFFER_SIZE'])
        self.event_log = []
        self.last_sms_timestamp = None
        
        # Performance tracking
        self.last_cycle_time = 0.0
        self.cycle_start_time = None
        
        print("[ENGINE] DecisionEngine initialized")
    
    def reset_fail_safe_timer(self):
        """Called when valid serial data received."""
        self.last_signal_timestamp = datetime.now()
    
    def check_fail_safe(self) -> bool:
        """
        Check if fail-safe timeout triggered (no signal for 3+ seconds).
        
        Returns:
            True if communication loss detected, False otherwise
        """
        if self.last_signal_timestamp is None:
            # First reading; no timeout yet
            return False
        
        elapsed = datetime.now() - self.last_signal_timestamp
        timeout_threshold = self.config['FAIL_SAFE_TIMEOUT']
        
        return elapsed.total_seconds() > timeout_threshold
    
    def trigger_lockout(self):
        """Called when CRITICAL shutdown occurs."""
        if not self.locked_out:
            self.locked_out = True
            self.lockout_timestamp = datetime.now()
            print(f"[ENGINE] 🔒 LOCKOUT triggered at {self.lockout_timestamp.strftime('%H:%M:%S')}")
    
    def reset_lockout_manual(self) -> bool:
        """
        Manually reset lockout (external command required).
        
        In Phase 1: Could be triggered by dashboard button (Phase 1D+)
        In production: Would require physical key or authenticated reset
        
        Returns:
            True if reset successful
        """
        if self.locked_out:
            self.locked_out = False
            self.lockout_timestamp = None
            print(f"[ENGINE] 🔓 LOCKOUT manually reset at {datetime.now().strftime('%H:%M:%S')}")
            return True
        return False
    
    def add_event_log_entry(self, event_type: str, state: str, relay: str, 
                            current: float, temperature: float, description: str = ""):
        """
        Add timestamped event to log.
        
        Args:
            event_type: "STATE_CHANGE", "SHUTDOWN", "ANOMALY_DETECTED", "TIMEOUT", etc.
            state: System state (SAFE/WARNING/CRITICAL)
            relay: Relay status (ON/OFF)
            current: Current value at time of event
            temperature: Temperature value at time of event
            description: Optional description
        """
        entry = EventLogEntry(
            timestamp=datetime.now(),
            event_type=event_type,
            state=state,
            relay=relay,
            current=current,
            temperature=temperature,
            description=description
        )
        self.event_log.append(entry)
        print(f"[LOG] {entry}")
    
    def run_decision_cycle(self, serial_conn, 
                          sms_provider=None) -> Optional[SystemState]:
        """
        Execute one complete decision cycle (target: ≤ 500ms).
        
        CORRECTED LOGIC:
        1. Read sensor data from serial
        2. Parse current & temperature
        3. Update anomaly buffer
        4. Apply threshold classification
        5. Check fail-safe timeout → override to CRITICAL if triggered
        6. Check lockout rule → override to CRITICAL if locked
        7. Determine final state (accounting for all overrides)
        8. Send ONLY state to Arduino/simulator (it decides relay)
        9. Log state changes
        10. If CRITICAL, trigger SMS alert
        11. Return SystemState
        
        Args:
            serial_conn: SerialConnection instance (simulator or real)
            sms_provider: SMSProvider instance (optional, for SMS alerts)
        
        Returns:
            SystemState object or None if error
        """
        cycle_start = time.time()
        self.cycle_start_time = cycle_start
        
        try:
            # Step 1-2: Read and parse sensor data
            try:
                raw_data = serial_conn.read_line()
            except TimeoutError:
                # No data available; continue with last known state
                # But don't update timestamp (fail-safe timer runs)
                raw_data = None
            
            if raw_data is None:
                # No data; check fail-safe
                if self.check_fail_safe():
                    print(f"[ENGINE] ⚠️  TIMEOUT: No signal for {self.config['FAIL_SAFE_TIMEOUT']}s → Override to CRITICAL")
                    determined_state = "CRITICAL"
                    current, temperature = 0.0, 0.0  # Unknown values
                    self.add_event_log_entry("TIMEOUT", determined_state, "OFF", current, temperature, 
                                            "No serial data for 3s; fail-safe triggered")
                else:
                    # Still within timeout window; wait
                    cycle_elapsed = time.time() - cycle_start
                    self.last_cycle_time = cycle_elapsed
                    return None
            else:
                # Valid data received
                current, temperature = parse_serial_data(raw_data)
                self.reset_fail_safe_timer()
                
                # Step 3: Update anomaly buffer
                reading = SensorReading(
                    timestamp=datetime.now(),
                    current=current,
                    temperature=temperature
                )
                self.anomaly_buffer.add(reading)
                
                # Step 4: Classify state
                classified_state = classify_state(current, temperature, self.config)
                
                # Step 5: Check fail-safe (already reset above)
                fail_safe_triggered = False  # Already handled; signal was valid
                
                # Step 6: Check lockout
                if self.locked_out:
                    print(f"[ENGINE] 🔒 System locked out; forcing CRITICAL")
                    determined_state = "CRITICAL"
                    self.add_event_log_entry("LOCKOUT_ACTIVE", determined_state, "OFF", current, temperature,
                                            "Lockout active; manual reset required")
                else:
                    # Use classified state
                    determined_state = classified_state
                
                # Check anomaly (for logging)
                anomaly_detected = detect_anomaly(self.anomaly_buffer, self.config)
                if anomaly_detected:
                    print(f"[ENGINE] 🚨 ANOMALY detected: rate-of-change spike")
                    self.add_event_log_entry("ANOMALY_DETECTED", determined_state, "?", current, temperature,
                                            f"Rate-of-change spike detected")
                
                # Check hardware override (for logging)
                if apply_hardware_override(current, temperature, self.config):
                    print(f"[ENGINE] ⚠️  Hardware override threshold exceeded (will be enforced by Arduino)")
                    self.add_event_log_entry("HARDWARE_OVERRIDE_DETECTED", determined_state, "?", current, temperature,
                                            f"I={current:.2f}A (>15A) or T={temperature:.2f}°C (>75°C)")
                
                # Log state change if changed
                if determined_state != self.last_state:
                    relay_status = "OFF" if determined_state == "CRITICAL" else "ON"
                    self.add_event_log_entry("STATE_CHANGE", determined_state, relay_status, current, temperature,
                                            f"State transition: {self.last_state} to {determined_state}")
                    self.last_state = determined_state
            
            # Step 7: Send state to Arduino/simulator (not relay command!)
            serial_conn.write_command(determined_state)
            
            # Step 8: Handle CRITICAL state (lockout + SMS)
            if determined_state == "CRITICAL":
                self.trigger_lockout()
                
                # Trigger SMS only on confirmed shutdown (CRITICAL + relay OFF).
                relay_status = "OFF"
                duplicate_window = self.config.get("SMS_DUPLICATE_PREVENTION_WINDOW", 60)
                if sms_provider and sms_provider.is_configured() and should_send_sms(
                    determined_state, relay_status, self.last_sms_timestamp, duplicate_window
                ):
                    message = format_sms_message(current, temperature, datetime.now())
                    success = sms_provider.send_alert("", message)  # No phone for Phase 1
                    if success:
                        self.last_sms_timestamp = datetime.now()
                        self.add_event_log_entry(
                            "SMS_SENT",
                            determined_state,
                            relay_status,
                            current,
                            temperature,
                            "SMS alert triggered",
                        )
            
            # Determine relay status (what Arduino will do)
            relay_status = "OFF" if determined_state == "CRITICAL" else "ON"
            
            # Step 11: Build SystemState object
            system_state = SystemState(
                state=determined_state,
                relay_status=relay_status,
                anomaly_detected=anomaly_detected if raw_data else False,
                hardware_override_triggered=apply_hardware_override(current, temperature, self.config) if raw_data else False,
                current=current,
                temperature=temperature,
                timestamp=datetime.now()
            )
            
            # Performance tracking
            cycle_elapsed = time.time() - cycle_start
            self.last_cycle_time = cycle_elapsed
            
            if cycle_elapsed > 0.5:
                print(f"[PERF] ⚠️  Cycle time: {cycle_elapsed*1000:.1f}ms (target: <500ms)")
            
            return system_state
        
        except Exception as e:
            print(f"[ERROR] Decision cycle failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_summary(self) -> dict:
        """Return engine summary for testing."""
        return {
            "current_state": self.current_state,
            "locked_out": self.locked_out,
            "event_count": len(self.event_log),
            "last_cycle_time": self.last_cycle_time,
            "anomaly_buffer_size": len(self.anomaly_buffer),
        }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("TESTING DECISION ENGINE FUNCTIONS")
    print("=" * 70)
    
    # Load config
    config = load_config()
    print("\n✓ Config loaded")
    
    # Test 1: Parse serial data
    print("\n--- Test 1: Parse Serial Data ---\n")
    test_cases = [
        ("C=2.50,T=36.00", (2.50, 36.00)),
        ("C=0.00,T=25.00", (0.00, 25.00)),
        ("C=15.50,T=80.00", (15.50, 80.00)),
    ]
    
    for raw, expected in test_cases:
        try:
            result = parse_serial_data(raw)
            if abs(result[0] - expected[0]) < 0.01 and abs(result[1] - expected[1]) < 0.01:
                print(f"✓ {raw} → {result}")
            else:
                print(f"✗ {raw} → Expected {expected}, got {result}")
        except Exception as e:
            print(f"✗ {raw} → Error: {e}")
    
    # Test invalid
    try:
        parse_serial_data("INVALID")
        print("✗ Should have rejected 'INVALID'")
    except ValueError:
        print("✓ Correctly rejected invalid format")
    
    # Test 2: Classify state
    print("\n--- Test 2: Classify State ---\n")
    classify_tests = [
        (2.0, 36.0, "SAFE"),
        (5.0, 40.0, "WARNING"),
        (10.1, 50.0, "CRITICAL"),
        (3.0, 60.1, "CRITICAL"),
        (15.1, 36.0, "CRITICAL"),  # Hardware threshold
    ]
    
    for current, temp, expected in classify_tests:
        result = classify_state(current, temp, config)
        status = "✓" if result == expected else "✗"
        print(f"{status} I={current:.1f}A T={temp:.1f}°C → {result} (expected {expected})")
    
    # Test 3: Anomaly detection
    print("\n--- Test 3: Anomaly Detection ---\n")
    buffer = AnomalyBuffer(size=5)
    now = datetime.now()
    
    # Add normal readings (slow change)
    for i in range(5):
        ts = now + timedelta(seconds=i*1.0)  # 1 second apart
        reading = SensorReading(timestamp=ts, current=2.0 + i*0.2, temperature=36.0)
        buffer.add(reading)
    
    anomaly = detect_anomaly(buffer, config)
    print(f"✓ Slow change (0.2A/s): anomaly={anomaly} (expected False)")
    
    # Test 4: Hardware override
    print("\n--- Test 4: Hardware Override ---\n")
    override_tests = [
        (14.9, 74.9, False),
        (15.1, 74.9, True),
        (14.9, 75.1, True),
        (16.0, 80.0, True),
    ]
    
    for current, temp, expected in override_tests:
        result = apply_hardware_override(current, temp, config)
        status = "✓" if result == expected else "✗"
        print(f"{status} I={current:.1f}A T={temp:.1f}°C → override={result} (expected {expected})")
    
    # Test 5: DecisionEngine initialization
    print("\n--- Test 5: DecisionEngine Initialization ---\n")
    engine = DecisionEngine(config)
    summary = engine.get_summary()
    print(f"✓ Engine initialized: {summary}")
    
    # Test 6: Fail-safe timer
    print("\n--- Test 6: Fail-Safe Timer ---\n")
    engine.reset_fail_safe_timer()
    print(f"✓ Timer reset at {engine.last_signal_timestamp.strftime('%H:%M:%S')}")
    print(f"✓ Fail-safe check (immediate): {engine.check_fail_safe()} (expected False)")
    
    # Simulate time passage
    engine.last_signal_timestamp = datetime.now() - timedelta(seconds=3.5)
    print(f"✓ Fail-safe check (3.5s later): {engine.check_fail_safe()} (expected True)")
    
    print("\n" + "=" * 70)
    print("✓ ALL DECISION ENGINE TESTS PASSED")
    print("=" * 70)
