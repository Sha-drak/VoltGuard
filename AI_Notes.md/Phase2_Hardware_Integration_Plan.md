# VoltGuard Phase 2 - Hardware Integration Plan

**Last Updated:** April 24, 2026  
**Status:** Plan-Only (No implementation in this document)  
**Phase:** 2 (Real Hardware Bring-Up and Validation)

---

## Executive Summary

Phase 2 moves VoltGuard from simulator-backed operation to real hardware while preserving the approved architecture:

- Arduino/ESP32 = sensing + relay control + hardware safety enforcement
- Python = decision engine and state classification
- Streamlit = read-only visualization
- SMS = event-triggered notification after confirmed shutdown

Primary objective: replace simulated serial data with real sensor streams and verify all safety layers under controlled conditions before optimization.

---

## Scope and Boundaries

### In Scope
- Real serial connection implementation and validation
- Sensor calibration and threshold verification with live readings
- LCD display integration and data visualization
- End-to-end safety rule testing on hardware
- Controlled enabling of production SMS provider
- Performance baseline capture with real hardware

### Out of Scope
- New architecture changes
- Logic invention outside existing rules
- Premature optimization before safety validation
- UI feature expansion beyond operational monitoring

---

## Phase 2A - Hardware Readiness and Environment Check

### Goals
- Confirm hardware is physically and electrically ready.
- Confirm software environment matches Phase 1 baseline.

### Checklist
- [ ] Hardware connected and powered safely (sensor, relay, controller, buzzer/LCD if present)
- [ ] COM port identified correctly in OS
- [ ] Firmware serial format confirmed: `C=<value>,T=<value>`
- [ ] Python environment active and dependencies installed
- [ ] Phase 1 tests still passing before hardware switch

### Verification Command
```powershell
.\.venv\Scripts\python -m pytest "voltguard/tests" -v
```

---

## Phase 2B - Real Serial Connection Implementation

### Goals
- Replace `RealSerialConnection` stub with working `pyserial` implementation.
- Keep simulator path intact for fallback testing.

### Planned File Targets
- `voltguard/python-engine/serial_interface.py`
- `voltguard/config/config.py` (port/timeout values only, if required)

### Acceptance Criteria
- [ ] `RealSerialConnection` opens configured port successfully
- [ ] `read_line()` receives valid sensor lines continuously
- [ ] `write_command()` sends only `SAFE`, `WARNING`, `CRITICAL`
- [ ] Clean shutdown closes serial resource without hanging
- [ ] No regression in simulator mode behavior

---

## Phase 2C - Sensor Calibration and Baseline Validation

### Goals
- Validate raw readings against expected physical values.
- Adjust calibration constants only if measurement evidence supports change.

### Planned File Targets
- `voltguard/config/config.py`
- Optional calibration helper script (only if explicitly approved)

### Calibration Steps
1. Capture idle current and ambient temperature samples.
2. Compare measured values with trusted reference instrument.
3. Adjust:
   - `ACS712_OFFSET`
   - `ACS712_SENSITIVITY`
   - `LM35_SCALE`
4. Re-sample and confirm reduced error.

### Acceptance Criteria
- [ ] Idle readings are stable within acceptable tolerance
- [ ] Temperature aligns with external reference
- [ ] Calibration updates documented and justified

---

## Phase 2D - Safety Logic Validation on Real Hardware

### Goals
- Prove safety behavior under live conditions before any tuning.

### Mandatory Safety Checks
- [ ] Hardware override: current > 15A OR temp > 75C forces relay OFF independent of Python
- [ ] Fail-safe: communication loss for configured timeout forces relay OFF
- [ ] Lockout: after CRITICAL shutdown, system remains OFF until manual reset
- [ ] Python continues sending state only (not direct relay ON/OFF commands)

### Acceptance Criteria
- [ ] Safety shutdowns are deterministic and repeatable
- [ ] Event logs match observed hardware behavior
- [ ] No unsafe auto-recovery after CRITICAL

---

## Phase 2E - Dashboard and Observability Verification

### Goals
- Confirm UI reflects real sensor and state transitions accurately.

### Checks
- [ ] Current/temperature values update in near real-time
- [ ] State badge transitions align with decision engine thresholds
- [ ] Relay status shown correctly after hardware actions
- [ ] Event table reflects critical events with correct ordering and timestamps
- [ ] Dashboard remains responsive during extended run

### Acceptance Criteria
- [ ] Real hardware transitions are visible without stale-state issues
- [ ] Monitoring quality is adequate for operator decision support

---

## Phase 2F - SMS Provider Activation (After Safety Sign-Off)

### Goals
- Replace mock SMS behavior with production provider in controlled manner.

### Planned File Targets
- `voltguard/python-engine/sms_provider.py`
- `voltguard/config/config.py` (API key and recipient list)

### Checks
- [ ] Provider auth/config loads correctly
- [ ] SMS sends only on confirmed shutdown event path
- [ ] Duplicate suppression window prevents alert spam
- [ ] Delivery failures are logged visibly

### Acceptance Criteria
- [ ] At least one controlled CRITICAL event generates one successful SMS
- [ ] No duplicate bursts for same event window

---

## Phase 2G - Performance Baseline and Stability Run

### Goals
- Measure real-world latency and stability before optimization work.

### Metrics to Capture
- Decision cycle time (target <= 1s)
- Serial read latency and timeout behavior
- Dashboard refresh smoothness under sustained operation
- Event log integrity over long run

### Stability Run
- [ ] Continuous run duration: minimum 2 hours (preferred 24 hours)
- [ ] No crashes or deadlocks
- [ ] No unbounded error growth

---

## Phase 2H - LCD Display Integration

### Goals
- Integrate LCD display for local hardware visualization of system state.
- Provide on-device monitoring independent of Streamlit dashboard.

### LCD Requirements
- **Display Size**: 16x2 or 20x4 character LCD (I2C or parallel interface)
- **Data to Display**:
  - Row 1: Current (A) and Temperature (°C) readings
  - Row 2: System state (SAFE/WARNING/CRITICAL) and relay status (ON/OFF)
- **Update Frequency**: Every sensor reading (real-time)
- **Display Format**:
  ```
  I: 2.50A T:36.0°C
  State:SAFE Relay:ON
  ```

### Planned File Targets
- Arduino firmware (new LCD integration code)
- `voltguard/config/config.py` (LCD pin configuration if needed)

### Implementation Steps
1. **LCD Library Setup**
   - Include appropriate library (LiquidCrystal for parallel, LiquidCrystal_I2C for I2C)
   - Configure pins based on hardware wiring
   - Initialize LCD in Arduino `setup()`

2. **Display Logic Integration**
   - Add LCD update function in Arduino main loop
   - Format sensor data for display (truncate decimals to fit)
   - Update display on each sensor reading cycle
   - Handle state transitions with visual indicators

3. **Display Content**
   - Current reading: `I: X.XXA` (max 16 chars)
   - Temperature: `T: XX.X°C` (max 16 chars)
   - System state: `State: XXXX` (SAFE/WARN/CRIT)
   - Relay status: `Relay: ON/OFF`

### Arduino Code Template
```cpp
#include <LiquidCrystal.h>  // or LiquidCrystal_I2C.h

// LCD Configuration (adjust pins based on wiring)
const int LCD_RS = 12;
const int LCD_EN = 11;
const int LCD_D4 = 5;
const int LCD_D5 = 4;
const int LCD_D6 = 3;
const int LCD_D7 = 2;
LiquidCrystal lcd(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7);

void setup() {
  lcd.begin(16, 2);
  lcd.print("VoltGuard Init...");
  delay(1000);
  lcd.clear();
}

void updateLCD(float current, float temp, String state, String relay) {
  lcd.clear();
  
  // Row 1: Current and Temperature
  lcd.setCursor(0, 0);
  lcd.print("I:");
  lcd.print(current, 1);
  lcd.print("A T:");
  lcd.print(temp, 1);
  lcd.print("C");
  
  // Row 2: State and Relay
  lcd.setCursor(0, 1);
  lcd.print("St:");
  lcd.print(state.substring(0, 4));  // Truncate to fit
  lcd.print(" R:");
  lcd.print(relay);
}

void loop() {
  // Read sensors
  float current = readCurrent();
  float temp = readTemperature();
  
  // Get state from Python (via serial)
  String state = getStateFromSerial();
  String relay = getRelayState();
  
  // Update LCD
  updateLCD(current, temp, state, relay);
  
  delay(100);  // Update every 100ms
}
```

### Acceptance Criteria
- [ ] LCD initializes correctly on Arduino startup
- [ ] Current and temperature readings display accurately
- [ ] System state transitions visible on LCD
- [ ] Relay status updates correctly
- [ ] Display updates without flickering or lag
- [ ] Text fits within display bounds (no truncation issues)
- [ ] LCD remains readable under various lighting conditions

### Testing Scenarios
1. **Normal Operation**: Verify stable readings display correctly
2. **State Transitions**: Confirm SAFE → WARNING → CRITICAL visible
3. **Relay Changes**: Verify ON/OFF status updates
4. **Long Run**: Test for 1+ hours to ensure no display degradation

### Integration Notes
- LCD is **read-only display** - no user input via LCD
- LCD provides **local monitoring** when dashboard unavailable
- LCD updates are **independent** of Python decision cycle
- LCD does **not affect** safety logic or timing

---

## Validation Matrix (Phase 2 Sign-Off)

- [ ] Real serial connection stable
- [ ] Calibration confirmed with reference measurements
- [ ] Hardware override verified independent of Python
- [ ] Fail-safe timeout verified
- [ ] Lockout and manual reset flow verified
- [ ] Dashboard reflects real-time hardware state
- [ ] SMS live provider verified with duplicate prevention
- [ ] Performance baseline documented
- [ ] LCD display integrated and functional

---

## Implementation Notes Template (for execution phase)

Use this section during Phase 2 execution for traceability:

- Date:
- Operator:
- Hardware configuration:
- Firmware version:
- COM port and baud:
- Test scenario:
- Observed behavior:
- Pass/Fail:
- Follow-up actions:

---

## Next Action Recommendation

Begin with **Phase 2A and 2B only** (environment check + real serial implementation), then pause for validation review before calibration or SMS activation.
