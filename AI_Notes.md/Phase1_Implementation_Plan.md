# VoltGuard Phase 1 - Software & Simulator Implementation Plan

**Last Updated:** April 24, 2026  
**Status:** Ready for Execution  
**Phase:** 1 (Software-Only, No Hardware Required)

---

## Executive Summary

Build a complete software-based VoltGuard system with a Python-based sensor simulator. Phase 1 delivers:
- Arduino simulator (generates mock serial data in `C=X,T=Y` format)
- Python decision engine with threshold classification and anomaly detection
- Streamlit dashboard (read-only real-time visualization)
- SMS integration layer (non-functional; placeholder for Phase 2)

All components work together deterministically for demo before swapping in real hardware in Phase 2.

---

## 🔧 CRITICAL ARCHITECTURAL CORRECTIONS APPLIED

**Core Principle:** Arduino = Authority over Power | Python = Intelligence | Streamlit = Visibility

**Key Fixes:**
- ✅ Relay commands: Python sends ONLY state (SAFE/WARNING/CRITICAL) — not ON/OFF
- ✅ Hardware override: Arduino enforces independently; Python mirrors for logs only
- ✅ Simulator: Only sends data + responds to state; makes no independent relay decisions
- ✅ Streamlit threading: Controlled loop with timer-based refresh; no uncontrolled threads
- ✅ SMS trigger: Depends on CRITICAL state from Python only; not relay state
- ✅ Decision cycle: Simplified — classify, check fail-safe/lockout, send state, Arduino decides
- ✅ Scenarios: Updated to reflect Python→state, Arduino→relay architecture

---

## Execution Steps

### **Phase 1A: Foundation & Project Structure** (Parallel Tasks)

#### Status: ✅ COMPLETE

**Verification:**
- [x] Project directories created: `/arduino-simulator`, `/python-engine`, `/streamlit-dashboard`, `/config`, `/tests`, `/logs`
- [x] Config module (`config/config.py`) created and tested
  - Loads successfully with all thresholds validated
  - Single source of truth for all calibration and threshold values
  - Output: ✓ Configuration loaded successfully
- [x] Data structures (`python-engine/data_structures.py`) created and tested
  - SensorReading: Working ✓
  - AnomalyBuffer: Working ✓ (rate calculations verified: 4.98 A/s, 19.92 °C/s)
  - SystemState: Working ✓
  - EventLogEntry: Working ✓ (CSV serialization verified)
  - Output: ✓ All data structures working correctly!

#### 1. Create Project Directory Structure
```
/voltguard (at c:\Users\user\Desktop\VoltGuard\)
├── /arduino-simulator/
│   └── simulator.py
├── /python-engine/
│   ├── decision_engine.py
│   ├── serial_interface.py
│   ├── data_structures.py
│   └── main.py
├── /streamlit-dashboard/
│   └── dashboard.py
├── /config/
│   └── config.py
├── /tests/
│   ├── test_decision_engine.py
│   ├── test_serial_interface.py
│   └── test_scenarios.py
├── /logs/
│   └── (events.csv created at runtime)
└── README.md
```

**Verification:** All directories created; structure visible in file explorer

#### 2. Create Unified Config Module (`config/config.py`)
**Contents:**
```python
# Sensor Calibration (ACS712 20A version)
ACS712_OFFSET = 2.5  # Volts
ACS712_SENSITIVITY = 0.100  # V/A

# Temperature Sensor (LM35)
LM35_SCALE = 100  # multiplier after voltage conversion

# Fixed Threshold Model (SINGLE SOURCE OF TRUTH)
THRESHOLD_SAFE_CURRENT = 5.0  # A
THRESHOLD_SAFE_TEMP = 40.0  # °C
THRESHOLD_WARNING_CURRENT_MAX = 10.0  # A
THRESHOLD_WARNING_TEMP_MAX = 60.0  # °C
THRESHOLD_CRITICAL_CURRENT = 10.0  # A
THRESHOLD_CRITICAL_TEMP = 60.0  # °C
THRESHOLD_HARDWARE_CUTOFF_CURRENT = 15.0  # A
THRESHOLD_HARDWARE_CUTOFF_TEMP = 75.0  # °C

# Serial Configuration
SERIAL_BAUD_RATE = 9600
SERIAL_PORT = "COM3"  # Will be configurable; default for Arduino Uno
DECISION_CYCLE_MAX_TIME = 1.0  # seconds

# SMS Configuration (Phase 2)
ARKESEL_API_KEY = ""  # Set during Phase 2
ARKESEL_PHONE_NUMBERS = []  # Configurable; empty for Phase 1 testing
SMS_DUPLICATE_PREVENTION_WINDOW = 60  # seconds

# Anomaly Detection
ANOMALY_BUFFER_SIZE = 5  # Ring buffer for rate-of-change
ANOMALY_CURRENT_RATE_THRESHOLD = 2.0  # A/s
ANOMALY_TEMP_RATE_THRESHOLD = 5.0  # °C/s

# Fail-Safe Timeout
FAIL_SAFE_TIMEOUT = 3.0  # seconds of no communication triggers shutdown
```

**Verification:** Config loads without errors; all values accessible as constants from other modules

#### 3. Define Data Structures (`python-engine/data_structures.py`)
**Classes:**
```python
from dataclasses import dataclass
from datetime import datetime
from collections import deque

@dataclass
class SensorReading:
    timestamp: datetime
    current: float  # Amperes
    temperature: float  # Celsius

@dataclass
class SystemState:
    state: str  # "SAFE", "WARNING", "CRITICAL"
    relay_status: str  # "ON", "OFF"
    anomaly_detected: bool
    current: float
    temperature: float
    timestamp: datetime

class AnomalyBuffer:
    """Ring buffer for tracking rate-of-change."""
    def __init__(self, size: int = 5):
        self.readings = deque(maxlen=size)
    
    def add(self, reading: SensorReading):
        self.readings.append(reading)
    
    def get_current_rate(self) -> float:
        """Calculate current rate of change (A/s)."""
        # Returns rate or 0 if insufficient data
    
    def get_temp_rate(self) -> float:
        """Calculate temperature rate of change (°C/s)."""
        # Returns rate or 0 if insufficient data
```

**Verification:** Structures instantiate correctly; can serialize/deserialize; anomaly buffer calculates rates

---

### **Phase 1B: Arduino Simulator & Serial Interface** (Single-Threaded Serial Emulation)

#### Status: ✅ COMPLETE

**Verification:**
- [x] Arduino Simulator (`arduino-simulator/simulator.py`) created and tested
  - All 4 modes working: stable, rising_current, rising_temp, fault
  - Output: ✓ ALL SIMULATOR TESTS PASSED (5 readings per mode verified)
- [x] Serial Interface Abstraction (`python-engine/serial_interface.py`) created and tested
  - Abstract interface working; SimulatorSerialConnection functional
  - Factory pattern enables swappable implementations
  - Output: ✓ ALL SERIAL INTERFACE TESTS PASSED (simulator connection, factory, error handling verified)

#### 4. Build Python-Based Arduino Simulator (`arduino-simulator/simulator.py`) — CORRECTED

**Features (CORRECTED):**
- Generates sensor data in format: `C=<current>,T=<temperature>\n`
- Operating modes:
  - `"stable"` — constant values (baseline demo)
  - `"rising_current"` — current trends upward 2A → 6A → 12A (tests SAFE → WARNING → CRITICAL)
  - `"rising_temp"` — temperature trends upward 35°C → 70°C in 2s (tests anomaly detection)
  - `"fault"` — current spikes to 16A (tests hardware override)
- Simulates real-time delays (e.g., one reading every 0.5s)
- **Receives state commands from Python (SAFE/WARNING/CRITICAL)** — NOT ON/OFF
- **Applies Arduino logic: mirrors state to relay + enforces hardware override**
- Outputs relay state changes to log

**Interface (CORRECTED):**
```python
class ArduinoSimulator:
    def __init__(self, mode: str = "stable"):
        self.relay_state = "ON"  # Default relay state
    
    def get_reading(self) -> str:
        # Returns next sensor reading in "C=X,T=Y" format
    
    def receive_state_command(self, state: str) -> str:
        """
        CORRECTED: Receives ONLY state (SAFE/WARNING/CRITICAL) from Python.
        Applies Arduino logic to determine relay.
        Returns: "ON" or "OFF"
        """
        # Apply Arduino logic
        if state == "CRITICAL":
            self.relay_state = "OFF"
        else:
            self.relay_state = "ON"
        return self.relay_state
    
    def stop(self):
        pass
```

**CRITICAL:** Simulator does NOT independently decide relay. It receives state from Python and applies Arduino response logic.

#### 5. Create Serial Communication Abstraction Layer (`python-engine/serial_interface.py`)

**Design Pattern:** Strategy pattern for swappable implementations

```python
from abc import ABC, abstractmethod

class SerialConnection(ABC):
    """Abstract interface for serial communication."""
    
    @abstractmethod
    def read_line(self) -> str:
        # Read one line from serial; returns "C=X,T=Y" or raises TimeoutError
        pass
    
    @abstractmethod
    def write_command(self, state: str):
        # Write ONLY state: "SAFE", "WARNING", or "CRITICAL" (NOT relay ON/OFF)
        # Arduino decides relay action based on state
        pass
    
    @abstractmethod
    def close(self):
        # Cleanly close connection
        pass

class RealSerialConnection(SerialConnection):
    """Real Arduino via pyserial (Phase 2)."""
    def __init__(self, port: str, baud: int):
        # Connect to real Arduino
    
    # Implement abstract methods using pyserial

class SimulatorSerialConnection(SerialConnection):
    """Python-based simulator (Phase 1)."""
    def __init__(self):
        self.simulator = ArduinoSimulator(mode="stable")
    
    # Implement abstract methods using simulator
```

**Verification:** Both implementations instantiate correctly; can switch by changing one import statement; serial data flows correctly in both modes

---

### **Phase 1C: Python Decision Engine** (Input: Serial Data → Output: System State)

#### Status: ✅ COMPLETE

**Verification:**
- [x] Data Parser (`parse_serial_data()`) - Parses "C=X,T=Y" format; handles invalid inputs
- [x] Threshold Classification (`classify_state()`) - SAFE/WARNING/CRITICAL logic verified; all boundaries tested
- [x] Anomaly Detection (`detect_anomaly()`) - Rate-of-change analysis working
- [x] Hardware Override Logic (`apply_hardware_override()`) - Mirrors Arduino safety (logging only)
- [x] Fail-Safe Timeout (`check_fail_safe()`) - 3-second timeout detection working
- [x] Lockout Management (`trigger_lockout()`, `reset_lockout_manual()`) - Prevents auto-recovery
- [x] DecisionEngine class - Full stateful coordination working
- [x] Main Decision Cycle (`run_decision_cycle()`) - Integrates all logic; cycle time <500ms verified
- [x] Main Application (`python-engine/main.py`) - Complete integration tested
- [x] Integration Tests - 4 scenarios tested:
  - Stable operation: 30 cycles, all SAFE, relay ON
  - Rising current: SAFE → WARNING (5A) → CRITICAL (10A) transitions verified
  - Relay correctly goes OFF on CRITICAL
  - Lockout mechanism activated and holding

#### 6. Data Parser (`python-engine/decision_engine.py` — method: `parse_serial_data`)
**Function:**
```python
def parse_serial_data(raw_line: str) -> tuple[float, float]:
    """
    Parse "C=<current>,T=<temperature>" format.
    Returns: (current, temperature)
    Raises: ValueError if malformed
    """
    # Example: "C=2.50,T=36.00" → (2.50, 36.00)
    # Handles: trailing whitespace, missing fields, invalid formats
```

**Verification:** Parse 100+ valid inputs correctly; handle 10+ malformed inputs without crashing; log errors

#### 7. Threshold-Based Classification (`classify_state` function)
**Logic:**
```python
def classify_state(current: float, temperature: float) -> str:
    """
    Apply fixed thresholds (from config).
    Returns: "SAFE", "WARNING", or "CRITICAL"
    """
    if current < 5.0 and temperature < 40.0:
        return "SAFE"
    elif (5.0 <= current <= 10.0) or (40.0 <= temperature <= 60.0):
        return "WARNING"
    elif current > 10.0 or temperature > 60.0:
        return "CRITICAL"
```

**Verification:** Test all boundary cases:
- SAFE boundaries: (4.9A, 39.9°C), (5.0A, 40.0°C), (5.1A, 40.1°C)
- WARNING boundaries: (5.0A, 40.0°C), (10.0A, 60.0°C), (10.1A, 60.1°C)
- CRITICAL boundaries: (10.0A, 60.0°C), (10.1A, 60.1°C)
- Test 15 cases total; all return correct state

#### 8. Anomaly Detection (Rate-of-Change Based)
**Logic:**
```python
def detect_anomaly(anomaly_buffer: AnomalyBuffer, current_threshold: float = 2.0, temp_threshold: float = 5.0) -> bool:
    """
    Flag anomaly if rate-of-change exceeds threshold over buffer window.
    Returns: True if (current_rate > 2 A/s) OR (temp_rate > 5°C/s), else False
    """
    current_rate = anomaly_buffer.get_current_rate()
    temp_rate = anomaly_buffer.get_temp_rate()
    
    if current_rate > current_threshold or temp_rate > temp_threshold:
        return True
    return False
```

**Verification:** 
- Rapid current spike (0 → 2A in 0.5s) detected as anomaly
- Gradual rise (0 → 2A in 5s) not flagged as anomaly
- Temperature spike test: 35°C → 70°C in 2s flagged; slow rise not

#### 9. Hardware Override Logic — CORRECTED
**Function:**
```python
def apply_hardware_override(current: float, temperature: float) -> bool:
    """
    CORRECTED: Mirror Arduino safety logic (for visibility/logging only).
    Returns True if hardware SHOULD cut power.
    
    CRITICAL: Python does NOT enforce relay shutdown.
    Arduino enforces this independently.
    """
    return current > 15.0 or temperature > 75.0
```

**Verification:** 
- Direct threshold test works correctly
- Python logs when hardware override WOULD trigger
- Arduino independently enforces if thresholds exceeded
- No single point of failure; AI cannot bypass hardware safety

#### 10. Fail-Safe Timeout Logic
**Function:**
```python
class DecisionEngine:
    def __init__(self):
        self.last_message_time = None
        self.fail_safe_threshold = 3.0  # seconds
    
    def check_fail_safe(self) -> bool:
        """
        Returns: True if more than 3 seconds since last valid message.
        If True, relay should be forced OFF.
        """
        if self.last_message_time is None:
            return False
        elapsed = datetime.now() - self.last_message_time
        return elapsed.total_seconds() > self.fail_safe_threshold
    
    def reset_fail_safe_timer(self):
        """Called on each valid message received."""
        self.last_message_time = datetime.now()
```

**Verification:** 
- Simulate 3-second communication loss; relay goes OFF
- Resume communication; timer resets
- Behavior logged in event log

#### 11. Lockout Rule Enforcement
**Function:**
```python
class DecisionEngine:
    def __init__(self):
        self.locked_out = False
        self.lockout_timestamp = None
    
    def trigger_lockout(self):
        """Called when CRITICAL shutdown occurs."""
        self.locked_out = True
        self.lockout_timestamp = datetime.now()
    
    def try_manual_reset(self) -> bool:
        """
        Returns: True if reset successful, False if still locked.
        TODO: Implement manual reset trigger (e.g., button in dashboard or serial command).
        """
        # For Phase 1, reset requires explicit command
        # Log event if reset attempted during lockout
        self.locked_out = False
        return True
    
    def get_relay_state(self) -> str:
        """
        Returns: "OFF" if locked out, otherwise normal state.
        """
        if self.locked_out:
            return "OFF"
        # Return normal state based on classification
```

**Verification:** After shutdown, cannot recover automatically; manual reset works; state persists

#### 12. Main Decision Loop (`run_decision_cycle` function) — CORRECTED
**Execution:**
```python
def run_decision_cycle(serial_conn: SerialConnection, 
                        config: dict, 
                        anomaly_buffer: AnomalyBuffer,
                        event_log: list) -> SystemState:
    """
    Full decision cycle (target: ≤ 500ms per cycle).
    
    CORRECTED STEPS:
    1. Read sensor data from serial
    2. Parse current & temperature
    3. Update anomaly buffer
    4. Apply threshold classification
    5. Check fail-safe timeout (override to CRITICAL if no signal)
    6. Check lockout rule (override to CRITICAL if locked)
    7. Send ONLY state (SAFE/WARNING/CRITICAL) to Arduino/simulator
    8. Arduino/simulator decides relay action
    9. Log state change if state changed
    10. If state is CRITICAL, trigger SMS
    11. Return SystemState object
    """
    # Pseudocode (CORRECTED):
    # raw_data = serial_conn.read_line()  # "C=2.50,T=36.00"
    # current, temp = parse_serial_data(raw_data)
    # anomaly_buffer.add(SensorReading(...))
    # state = classify_state(current, temp)
    # anomaly_detected = detect_anomaly(anomaly_buffer)
    # 
    # # Override to CRITICAL if fail-safe triggered
    # if check_fail_safe():
    #     state = "CRITICAL"
    #     log_event("TIMEOUT", ...)
    # 
    # # Override to CRITICAL if locked out
    # if locked_out:
    #     state = "CRITICAL"
    # 
    # # Send ONLY state; Arduino decides relay
    # serial_conn.write_command(state)  # Send state, not relay command
    # 
    # # Trigger SMS if CRITICAL (Arduino will enforce relay OFF)
    # if state == "CRITICAL":
    #     trigger_sms_alert(current, temp)
    #     trigger_lockout()  # Prevent auto-recovery
    # 
    # # Log mirror of hardware override for visibility
    # if apply_hardware_override(current, temp):
    #     log_event("HARDWARE_OVERRIDE_TRIGGERED", ...)
    # 
    # return SystemState(state, relay_status, anomaly_detected, current, temp, timestamp)
```

**Verification:** 
- Full loop executes in < 500ms
- Python sends ONLY state to Arduino
- Arduino enforces relay + hardware override
- SMS triggers on CRITICAL state (from Python)
- Lockout mechanism prevents auto-recovery
- All events logged for audit trail

---

### **Phase 1D: Streamlit Dashboard** (Read-Only Visualization)

#### Status: ✅ COMPLETE

**Verification:**
- [x] Dashboard startup verified successfully (`streamlit run streamlit-dashboard/dashboard.py`)
- [x] Read-only visualization components implemented (state, relay, anomaly, thresholds, event log)
- [x] Controlled refresh loop active (no persistent background threads)
- [x] Integration with `VoltGuardApplication` validated after import-path alignment
- [x] Phase 1D syntax checks passed for dashboard and integrated engine modules

#### 13. Dashboard Structure (`streamlit-dashboard/dashboard.py`)
**UI Elements:**
- **Real-time Gauges:** Current (0–20A), Temperature (0–100°C)
- **State Indicator:** Color-coded badge (SAFE=green, WARNING=yellow, CRITICAL=red)
- **Relay Status:** ON (green) / OFF (red) with text "Power ON" or "Power OFF"
- **Anomaly Flag:** "Yes" (red) / "No" (green) with timestamp if detected
- **Threshold Display (Read-Only):**
  - SAFE: Current < 5A AND Temp < 40°C
  - WARNING: Current 5–10A OR Temp 40–60°C
  - CRITICAL: Current > 10A OR Temp > 60°C
  - HARDWARE CUTOFF: Current > 15A OR Temp > 75°C
- **Event Log Table:** Columns: Timestamp, Event Type, State, Relay, Current, Temp
  - Rows: STATE_CHANGE, SHUTDOWN, ANOMALY_DETECTED, TIMEOUT, MANUAL_RESET events

**Verification:** All elements render; no errors on startup; read-only (no sliders/buttons for control)

#### 14. Background Integration (`dashboard.py` — threading model) — CORRECTED
**Design (CORRECTED for Safety):**
```python
import streamlit as st
import time

# Initialize session state
if "system_state" not in st.session_state:
    st.session_state.system_state = None
    st.session_state.event_log = []
    st.session_state.decision_engine = DecisionEngine()
    st.session_state.serial_conn = SimulatorSerialConnection()
    st.session_state.last_update_time = time.time()

# CORRECTED: Replace uncontrolled background thread with controlled loop
# Option 1: Use st.experimental_rerun() with delay
def decision_update_loop():
    """Run one decision cycle per dashboard refresh."""
    try:
        state = run_decision_cycle(st.session_state.serial_conn, ...)
        st.session_state.system_state = state
        # Append to event_log if state changed
        elapsed = time.time() - st.session_state.last_update_time
        if elapsed >= 1.0:  # Refresh every 1 second
            st.session_state.last_update_time = time.time()
            st.rerun()  # Trigger refresh
    except Exception as e:
        st.error(f"Decision engine error: {e}")

# Call decision update once per render
decision_update_loop()

# Main dashboard renders system_state and event_log
if st.session_state.system_state:
    st.metric("Current", f"{st.session_state.system_state.current:.2f} A")
    st.metric("Temperature", f"{st.session_state.system_state.temperature:.2f} °C")
    st.metric("State", st.session_state.system_state.state)
    # ... render other elements
else:
    st.info("Initializing...")

# Auto-refresh every 1 second
time.sleep(1)
st.rerun()
```

**Verification:** 
- Dashboard updates every 1–2 seconds (controlled interval)
- No uncontrolled background threads
- State reflects decision engine
- No resource leaks or instability
- Safe for production

#### 15. Event Logging
**Function:**
```python
def log_event(event_type: str, state: str, relay: str, current: float, temp: float, event_log: list):
    """
    Append timestamped event to log.
    Event types: STATE_CHANGE, SHUTDOWN, ANOMALY_DETECTED, TIMEOUT, MANUAL_RESET
    """
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "state": state,
        "relay": relay,
        "current": current,
        "temperature": temp
    }
    event_log.append(event)
    # Also write to CSV: /logs/events.csv
    with open("logs/events.csv", "a") as f:
        f.write(f"{event['timestamp']},{event['event_type']},{event['state']},{event['relay']},{event['current']},{event['temperature']}\n")
```

**Verification:** 10 events generated; logged to memory and CSV; timestamps correct; at least 20+ entries by end of Phase 1F

---

### **Phase 1E: SMS Integration Layer** (Non-Functional Until Phase 2)

#### Status: ✅ COMPLETE

**Verification:**
- [x] `python-engine/sms_provider.py` created with `SMSProvider`, `ArkeselSMSProvider` stub, and `MockSMSProvider`
- [x] Decision engine SMS trigger path integrated via helper functions
- [x] Duplicate prevention window uses config value (`SMS_DUPLICATE_PREVENTION_WINDOW`)
- [x] Fault scenario runtime test executed with mock SMS output confirmation

#### 16. SMS Provider Abstraction (`python-engine/sms_provider.py`)
**Interface:**
```python
from abc import ABC, abstractmethod

class SMSProvider(ABC):
    """Abstract SMS provider."""
    
    @abstractmethod
    def send_alert(self, phone_number: str, message_body: str) -> bool:
        """Send SMS alert; returns True if sent, False if failed."""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if API keys are set and provider is ready."""
        pass

class ArkeselSMSProvider(SMSProvider):
    """Arkesel API implementation (Phase 2)."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Store API key
    
    def send_alert(self, phone_number: str, message_body: str) -> bool:
        """Send SMS via Arkesel API."""
        # TODO: Implement actual API call in Phase 2
        # For Phase 1, return True (mock success)
        return True
    
    def is_configured(self) -> bool:
        return bool(self.api_key)

class MockSMSProvider(SMSProvider):
    """Mock SMS provider for Phase 1 testing."""
    
    def send_alert(self, phone_number: str, message_body: str) -> bool:
        print(f"[MOCK SMS] To: {phone_number}\nMessage: {message_body}")
        return True
    
    def is_configured(self) -> bool:
        return True  # Always ready for testing
```

**Verification:** Can instantiate; methods callable without errors; mock provider logs SMS to console/file

#### 17. SMS Trigger Logic (CORRECTED)
**Function:**
```python
def should_send_sms(current_state: str, last_sms_timestamp: datetime = None, duplicate_window: int = 60) -> bool:
    """
    CORRECTED: Determine if SMS should be sent.
    
    Trigger condition:
    - Current state is CRITICAL (ONLY — don't wait for relay confirmation from Python)
    - No SMS sent in last 60 seconds (prevent duplicates)
    
    CRITICAL: Do NOT depend on relay_status from Python.
    Arduino decides relay; Python only knows its own decision.
    
    Returns: True if SMS should be sent, False otherwise
    """
    if current_state != "CRITICAL":
        return False
    
    if last_sms_timestamp is None:
        return True  # First alert
    
    elapsed = (datetime.now() - last_sms_timestamp).total_seconds()
    return elapsed > duplicate_window

def format_sms_message(current: float, temperature: float, timestamp: datetime) -> str:
    """
    Format SMS alert message.
    
    Returns:
    ⚠️ ALERT: Critical Electrical Condition Detected
    Current: {current}A
    Temperature: {temperature}°C
    Action: Power Supply Turned OFF
    Time: {timestamp}
    """
    return f"""⚠️ ALERT: Critical Electrical Condition Detected
Current: {current:.2f}A
Temperature: {temperature:.2f}°C
Action: Power Supply Turned OFF
Time: {timestamp.strftime('%H:%M:%S')}"""
```

**Verification:** SMS trigger logic correct; duplicate prevention works; message format valid

#### 18. Integrate SMS into Decision Engine (CORRECTED)
**Code:**
```python
class DecisionEngine:
    def __init__(self, sms_provider: SMSProvider):
        self.sms_provider = sms_provider
        self.last_sms_timestamp = None
        self.sms_phone_numbers = [""]  # Empty for Phase 1; will be populated from config in Phase 2
    
    def trigger_sms_alert(self, current: float, temperature: float):
        """
        CORRECTED: Called when CRITICAL state detected (not relay state).
        Arduino will enforce relay OFF; Python triggers SMS on state only.
        """
        if not should_send_sms(self.current_state, self.last_sms_timestamp):
            return
        
        message = format_sms_message(current, temperature, datetime.now())
        for phone in self.sms_phone_numbers:
            if phone:
                success = self.sms_provider.send_alert(phone, message)
                if success:
                    self.last_sms_timestamp = datetime.now()
                    log_event("SMS_SENT", self.current_state, current, temperature, self.event_log)
        
        # Log SMS event even if no recipients configured
        log_event("SMS_ALERT_TRIGGERED", self.current_state, current, temperature, self.event_log)

# In run_decision_cycle:
# if state == "CRITICAL":  # Trigger on state, not relay
#     self.trigger_sms_alert(current, temperature)
```

**Verification:** 
- SMS triggered on CRITICAL state from Python only
- Not dependent on relay state (which Arduino controls)
- Duplicate prevention works (60s window)
- Event logged for audit
- Decouples SMS from hardware relay state

---

### **Phase 1F: Integration & Testing** (Run 6 Scenarios)

#### Status: ✅ COMPLETE

**Verification:**
- [x] `tests/test_decision_engine.py` implemented
- [x] `tests/test_serial_interface.py` implemented
- [x] `tests/test_scenarios.py` implemented
- [x] Scenario coverage includes stable, rising current, rising temperature, fault, fail-safe timeout, and lockout reset paths
- [x] Test suite passes: `pytest voltguard/tests -v` → `15 passed`

#### 19. Scenario 0: System Baseline (No Errors)
**Setup:** Simulator mode "stable"; stable readings
**Steps:**
1. Start simulator
2. Start Python decision engine connected to simulator
3. Start Streamlit dashboard
4. Run for 30 seconds

**Verification:**
- [ ] Dashboard updates with stable readings
- [ ] State remains "SAFE" throughout
- [ ] Relay status "ON"
- [ ] No anomalies detected
- [ ] Event log shows initial state only
- [ ] No errors in console

#### 20. Scenario 1: Rising Current (SAFE → WARNING → CRITICAL)
**Setup:** Simulator mode "rising_current"
**Expected Behavior:**
- Current increases: 2A → 6A → 12A over ~30 seconds
- Temperature constant: 36°C

**Steps:**
1. Run scenario
2. Monitor state transitions
3. Check relay commands sent

**Verification:**
- [ ] State transitions: SAFE → WARNING (at 5A) → CRITICAL (at 10A)
- [ ] Each transition logged with timestamp
- [ ] Relay behavior correct:
  - SAFE: relay ON
  - WARNING: relay ON
  - CRITICAL: relay OFF
- [ ] Event log shows: STATE_CHANGE events for each transition

#### 21. Scenario 2: Temperature Spike (Anomaly Detection + CRITICAL)
**Setup:** Simulator mode "rising_temp"
**Expected Behavior:**
- Temperature spikes: 35°C → 70°C in 2 seconds
- Current stable: 3A

**Steps:**
1. Run scenario
2. Watch for anomaly flag
3. Monitor CRITICAL state

**Verification:**
- [ ] Anomaly detected within 1 second of spike (flagged: True)
- [ ] CRITICAL state triggered (temp > 60°C)
- [ ] Relay forced OFF
- [ ] Event log shows: ANOMALY_DETECTED, STATE_CHANGE, SHUTDOWN
- [ ] SMS triggered (if phone numbers configured)

#### 22. Scenario 3: Hardware Override (Current Spike = Immediate Shutdown) — CORRECTED
**Setup:** Simulator mode "fault"
**Expected Behavior:**
- Current jumps: 3A → 16A (exceeds 15A hardware cutoff)
- Temperature: 36°C

**Steps:**
1. Run scenario
2. Check state classification
3. Verify Arduino enforces shutdown

**Verification:**
- [ ] Python classifies state as CRITICAL (current > 10A)
- [ ] Python sends CRITICAL state to Arduino/simulator
- [ ] Arduino/simulator enforces relay OFF (due to CRITICAL state + hardware threshold)
- [ ] Event log shows: STATE_CHANGE to CRITICAL, HARDWARE_OVERRIDE_TRIGGERED (Python mirrors logic), SMS_ALERT_TRIGGERED
- [ ] SMS sent (CRITICAL state detected)
- [ ] Lockout triggered (prevents auto-recovery)

#### 23. Scenario 4: Fail-Safe Timeout (Communication Loss) — CORRECTED
**Setup:** Simulator pauses for 3+ seconds
**Expected Behavior:**
- System detects no data for 3 seconds
- Python overrides state to CRITICAL
- Arduino enforces relay OFF (safety mechanism)

**Steps:**
1. Start normal operation (state: SAFE, relay: ON)
2. Stop simulator feed at 5 seconds
3. At 3-second mark, Python triggers fail-safe
4. Resume simulator

**Verification:**
- [ ] Timeout detected at 3-second mark
- [ ] Python sets state = CRITICAL (fail-safe override)
- [ ] Python sends CRITICAL to Arduino/simulator
- [ ] Relay status shows "OFF" in dashboard (Arduino enforces)
- [ ] Event log shows: TIMEOUT event, STATE_CHANGE to CRITICAL
- [ ] Communication resumes; lockout prevents auto-recovery (must reset manually)
- [ ] After manual reset, system can return to normal

#### 24. Scenario 5: Lockout Enforcement (Manual Reset Required)
**Setup:** Trigger CRITICAL shutdown (Scenario 1 or 3)
**Expected Behavior:**
- After shutdown, relay remains OFF
- Cannot auto-recovery; requires manual reset

**Steps:**
1. Trigger CRITICAL state
2. Verify relay OFF
3. Try to send "SAFE" command (should stay OFF)
4. Send manual reset command
5. Verify recovery

**Verification:**
- [ ] After CRITICAL shutdown, relay stays OFF
- [ ] Despite new readings showing SAFE conditions, relay remains OFF (lockout active)
- [ ] Manual reset command processed
- [ ] After reset, relay can go back ON
- [ ] Event log shows: LOCKOUT events + MANUAL_RESET

---

### **Phase 1G: Documentation** (Parallel with Testing)

#### Status: ✅ COMPLETE

**Verification:**
- [x] Root `README.md` created with setup, run, test, and logs instructions
- [x] Phase handoff notes for hardware integration included
- [x] Implementation notes added: `AI_Notes.md/Phase1E_1F_1G_Implementation_Notes.md`

#### 25. Create Implementation Documentation

**README.md:**
```markdown
# VoltGuard Phase 1 - Software & Simulator

## Quick Start

### Prerequisites
- Python 3.8+
- pip packages: streamlit, pyserial (Phase 2 only)

### Installation
1. Clone/create project structure
2. Install dependencies: `pip install streamlit`
3. Run simulator: `python arduino-simulator/simulator.py --mode stable`
4. Run dashboard: `streamlit run streamlit-dashboard/dashboard.py`

### Modes
- `stable` — Constant readings (baseline)
- `rising_current` — Current trends upward
- `rising_temp` — Temperature spike
- `fault` — Current spike (hardware override test)

### Configuration
Edit `config/config.py` to adjust:
- Calibration values (ACS712_OFFSET, ACS712_SENSITIVITY, LM35_SCALE)
- Thresholds (SAFE, WARNING, CRITICAL, HARDWARE_CUTOFF)
- Fail-safe timeout (FAIL_SAFE_TIMEOUT)
- Anomaly detection sensitivity (ANOMALY_*_THRESHOLD)

### Testing
Run integration tests: `python -m pytest tests/test_scenarios.py -v`

### Logs
Event logs written to `/logs/events.csv`
```

**Architecture Diagram:**
```
┌─────────────────────────────────────────────────────────────┐
│                    VOLTGUARD PHASE 1                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Arduino Simulator (simulator.py)                           │
│  [Generates C=X,T=Y serial data]                            │
│           ↓                                                 │
│  Serial Interface Abstraction (serial_interface.py)         │
│  [SimulatorSerialConnection | RealSerialConnection]         │
│           ↓                                                 │
│  Python Decision Engine (decision_engine.py)                │
│  ├─ Parser: "C=X,T=Y" → current, temp                      │
│  ├─ Classifier: threshold-based state                       │
│  ├─ Anomaly Detection: rate-of-change                       │
│  ├─ Hardware Override: current > 15A OR temp > 75°C         │
│  ├─ Fail-Safe Timeout: no signal for 3s → override to CRITICAL │
│  ├─ Lockout Rule: manual reset required after shutdown      │
│  └─ SMS Trigger: CRITICAL state → alert                    │
│           ↓                                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Streamlit Dashboard (dashboard.py)                      │ │
│  ├─ Real-time gauges (current, temp)                       │ │
│  ├─ State indicator (SAFE/WARNING/CRITICAL)                │ │
│  ├─ Relay status (ON/OFF)                                  │ │
│  ├─ Anomaly flag                                           │ │
│  ├─ Thresholds display (read-only)                         │ │
│  └─ Event log table                                        │ │
│  └─ SMS Alerts                                             │ │
│           ↓                                                 │
│  /logs/events.csv (timestamped event log)                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Config Migration Guide (for Phase 2):**
```markdown
## Phase 2 Configuration Steps

### When Hardware Arrives

1. **Update Serial Configuration**
   - Change `SERIAL_PORT` from "COM3" to your Arduino port (e.g., "COM5")
   - Verify Arduino baud rate matches `SERIAL_BAUD_RATE = 9600`

2. **Swap Serial Implementation**
   - In `decision_engine.py`, change:
     ```python
     from serial_interface import SimulatorSerialConnection
     # TO
     from serial_interface import RealSerialConnection
     ```

3. **Calibrate Sensors**
   - Run calibration script: `python calibrate_sensors.py`
   - Update `config.py` with actual sensor values:
     - ACS712_OFFSET (typically 2.5V)
     - ACS712_SENSITIVITY (depends on model)
     - LM35_SCALE (typically 100)

4. **Test Individual Sensors**
   - `python tests/test_sensors.py --sensor current`
   - `python tests/test_sensors.py --sensor temperature`

5. **Adjust Thresholds (if needed)**
   - Monitor real readings under normal conditions
   - Update thresholds if necessary:
     - THRESHOLD_SAFE_CURRENT, THRESHOLD_SAFE_TEMP, etc.

6. **Enable SMS Integration**
   - Set `ARKESEL_API_KEY` in `config.py`
   - Add phone numbers to `ARKESEL_PHONE_NUMBERS`
   - Test SMS delivery: `python tests/test_sms.py`

7. **Run Full System Test**
   - Execute `python tests/test_scenarios.py` with real hardware
   - Verify all 6 scenarios pass with real data
```

**Verification:** New developer can:
- Run Phase 1 from README without additional help
- Migrate Phase 1 code to Phase 2 following config guide
- Understand data flow from architecture diagram

---

## Key Functions to Implement

| Function | Location | Purpose |
|----------|----------|---------|
| `load_config()` | `config/config.py` | Load all thresholds & calibration |
| `classify_state(current, temp)` | `python-engine/decision_engine.py` | SAFE\|WARNING\|CRITICAL classification |
| `detect_anomaly(buffer)` | `python-engine/decision_engine.py` | Rate-of-change anomaly detection |
| `apply_hardware_override(current, temp)` | `python-engine/decision_engine.py` | Mirror Arduino logic (visibility/logging only) |
| `check_fail_safe()` | `python-engine/decision_engine.py` | Timeout detection (3s no signal) |
| `run_decision_cycle()` | `python-engine/decision_engine.py` | Main loop (≤1s per cycle) |
| `parse_serial_data(raw_line)` | `python-engine/decision_engine.py` | Parse "C=X,T=Y" format |
| `SerialConnection` abstract class | `python-engine/serial_interface.py` | Interface for swappable implementations |
| `ArduinoSimulator` | `arduino-simulator/simulator.py` | Python-based mock Arduino |
| `SMSProvider` abstract class | `python-engine/sms_provider.py` | Abstract SMS interface |
| `should_send_sms()` | `python-engine/sms_provider.py` | Trigger logic + duplicate prevention |

---

## Phase 1 Acceptance Criteria

- [ ] All 25 steps completed
- [ ] System runs 60 seconds without crashes or errors
- [ ] All 6 test scenarios pass (baseline through lockout)
- [ ] Event log contains 20+ timestamped entries with correct event types
- [ ] Dashboard updates smoothly (1–2s refresh rate)
- [ ] SMS layer in place and callable (non-functional; placeholder for Phase 2)
- [ ] Code documented with inline comments
- [ ] README allows new developer to run system independently
- [ ] Config guide enables Phase 2 hardware migration without major refactoring
- [ ] All tests pass: `pytest tests/ -v`

---

## Implementation Notes

### Design Principles
1. **Simulator-first**: Build complete software system before hardware integration
2. **Fixed thresholds**: Hardcoded in config for deterministic demo behavior
3. **Abstract serial interface**: Enables simulator ↔ hardware swap without code changes
4. **Single decision cycle**: All logic runs in ≤1s cycle; deterministic timing
5. **Ring buffer anomalies**: Efficient rate-of-change detection (5 readings only)
6. **SMS as abstraction layer**: Phase 1 placeholder; Phase 2 integration ready

### Threading Model (Streamlit) — CORRECTED
- Use `streamlit.session_state` for shared state
- **NO persistent background threads** (causes instability in Streamlit)
- Decision engine runs once per render cycle
- UI refresh controlled using `st.rerun()` with 1–2s delay
- Ensures stability and prevents race conditions

### Simulator Realism
- Add 2–5% random sensor noise to mimic real data
- Test code accounts for ±0.1A/±0.5°C variance
- Modes cycle through predefined patterns for reproducibility

### Event Persistence
- Phase 1: Write events to CSV (simple, queryable)
- Phase 2 (optional): Upgrade to SQLite or cloud logging if needed

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Serial communication lag | Use non-blocking reads; timeout after 100ms |
| Dashboard not updating | Verify background thread is running; check Streamlit cache settings |
| Simulator not realistic | Add noise; validate against expected sensor ranges |
| Hardware thresholds inconsistent | Define once in config.py; import everywhere |
| SMS duplicates | Implement 60s prevention window per logic |
| Lockout never resets | Require explicit manual reset command; log all attempts |

---

## Next Steps (After Phase 1)

1. **Phase 2 Hardware Integration**
   - Replace `SimulatorSerialConnection` with `RealSerialConnection`
   - Calibrate sensors against reference equipment
   - Test real thresholds under actual load conditions
   - Enable SMS alerts with Arkesel API keys

2. **Phase 3 Scenarios & Optimization**
   - Run full demo scenarios with hardware
   - Optimize for responsiveness (target: ≤500ms decision cycle)
   - Stress-test (run for 24+ hours; monitor for memory leaks)
   - Document calibration for production deployment

---

**Last Updated:** April 24, 2026  
**Status:** Ready to Begin Phase 1 Implementation
