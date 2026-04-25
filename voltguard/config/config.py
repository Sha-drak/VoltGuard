"""
VoltGuard Phase 1 - Unified Configuration Module
Single Source of Truth for all system thresholds and calibration values
"""

# ============================================================================
# SENSOR CALIBRATION (ACS712 20A version + LM35 temperature sensor)
# ============================================================================

ACS712_OFFSET = 2.5  # Volts (midpoint for 0A reading)
ACS712_SENSITIVITY = 0.100  # V/A (100mV per Ampere for 20A version)

LM35_SCALE = 100  # Multiplier after voltage conversion (10mV per °C → ×100)

# ============================================================================
# FIXED THRESHOLD MODEL (SINGLE SOURCE OF TRUTH)
# Do NOT modify thresholds without explicit approval
# ============================================================================

# SAFE state: current < 5A AND temperature < 40°C
THRESHOLD_SAFE_CURRENT = 5.0  # Amperes
THRESHOLD_SAFE_TEMP = 40.0  # Celsius

# WARNING state: current 5–10A OR temperature 40–60°C
THRESHOLD_WARNING_CURRENT_MIN = 5.0  # Amperes
THRESHOLD_WARNING_CURRENT_MAX = 10.0  # Amperes
THRESHOLD_WARNING_TEMP_MIN = 40.0  # Celsius
THRESHOLD_WARNING_TEMP_MAX = 60.0  # Celsius

# CRITICAL state: current > 10A OR temperature > 60°C
THRESHOLD_CRITICAL_CURRENT = 10.0  # Amperes
THRESHOLD_CRITICAL_TEMP = 60.0  # Celsius

# HARDWARE CUTOFF (Arduino independent enforcement)
# Relay OFF if current > 15A OR temperature > 75°C
THRESHOLD_HARDWARE_CUTOFF_CURRENT = 15.0  # Amperes
THRESHOLD_HARDWARE_CUTOFF_TEMP = 75.0  # Celsius

# ============================================================================
# SERIAL COMMUNICATION CONFIGURATION
# ============================================================================

SERIAL_BAUD_RATE = 9600  # Standard for Arduino Uno
SERIAL_PORT = "COM3"  # Default; will be configurable in Phase 2
SERIAL_TIMEOUT = 2.0  # Seconds; timeout for read operations

# Decision cycle timing
DECISION_CYCLE_MAX_TIME = 1.0  # Seconds (max time for one complete cycle)

# ============================================================================
# SMS CONFIGURATION (Arkesel API)
# Empty/placeholder for Phase 1; will be populated in Phase 2
# ============================================================================

ARKESEL_API_KEY = ""  # Set during Phase 2 with actual API key
ARKESEL_PHONE_NUMBERS = []  # Configurable; empty for Phase 1 testing
SMS_DUPLICATE_PREVENTION_WINDOW = 60  # Seconds (prevent duplicate alerts)

# ============================================================================
# ANOMALY DETECTION CONFIGURATION
# Rate-of-change based detection using ring buffer
# ============================================================================

ANOMALY_BUFFER_SIZE = 5  # Number of readings to track for rate calc
ANOMALY_CURRENT_RATE_THRESHOLD = 2.0  # Amperes per second
ANOMALY_TEMP_RATE_THRESHOLD = 5.0  # Celsius per second

# ============================================================================
# FAIL-SAFE TIMEOUT CONFIGURATION
# ============================================================================

FAIL_SAFE_TIMEOUT = 3.0  # Seconds of no communication triggers shutdown

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

EVENT_LOG_FILE = "logs/events.csv"  # Path to event log CSV
LOG_LEVEL = "DEBUG"  # DEBUG, INFO, WARNING, ERROR

# ============================================================================
# HELPER FUNCTION: Load and validate config
# ============================================================================

def load_config():
    """
    Load configuration and validate critical values.
    Returns dict with all configuration constants.
    
    Raises:
        ValueError if critical configuration is invalid
    """
    config = {
        # Calibration
        "ACS712_OFFSET": ACS712_OFFSET,
        "ACS712_SENSITIVITY": ACS712_SENSITIVITY,
        "LM35_SCALE": LM35_SCALE,
        
        # Thresholds
        "THRESHOLD_SAFE_CURRENT": THRESHOLD_SAFE_CURRENT,
        "THRESHOLD_SAFE_TEMP": THRESHOLD_SAFE_TEMP,
        "THRESHOLD_WARNING_CURRENT_MIN": THRESHOLD_WARNING_CURRENT_MIN,
        "THRESHOLD_WARNING_CURRENT_MAX": THRESHOLD_WARNING_CURRENT_MAX,
        "THRESHOLD_WARNING_TEMP_MIN": THRESHOLD_WARNING_TEMP_MIN,
        "THRESHOLD_WARNING_TEMP_MAX": THRESHOLD_WARNING_TEMP_MAX,
        "THRESHOLD_CRITICAL_CURRENT": THRESHOLD_CRITICAL_CURRENT,
        "THRESHOLD_CRITICAL_TEMP": THRESHOLD_CRITICAL_TEMP,
        "THRESHOLD_HARDWARE_CUTOFF_CURRENT": THRESHOLD_HARDWARE_CUTOFF_CURRENT,
        "THRESHOLD_HARDWARE_CUTOFF_TEMP": THRESHOLD_HARDWARE_CUTOFF_TEMP,
        
        # Serial
        "SERIAL_BAUD_RATE": SERIAL_BAUD_RATE,
        "SERIAL_PORT": SERIAL_PORT,
        "SERIAL_TIMEOUT": SERIAL_TIMEOUT,
        "DECISION_CYCLE_MAX_TIME": DECISION_CYCLE_MAX_TIME,
        
        # SMS
        "ARKESEL_API_KEY": ARKESEL_API_KEY,
        "ARKESEL_PHONE_NUMBERS": ARKESEL_PHONE_NUMBERS,
        "SMS_DUPLICATE_PREVENTION_WINDOW": SMS_DUPLICATE_PREVENTION_WINDOW,
        
        # Anomaly Detection
        "ANOMALY_BUFFER_SIZE": ANOMALY_BUFFER_SIZE,
        "ANOMALY_CURRENT_RATE_THRESHOLD": ANOMALY_CURRENT_RATE_THRESHOLD,
        "ANOMALY_TEMP_RATE_THRESHOLD": ANOMALY_TEMP_RATE_THRESHOLD,
        
        # Fail-Safe
        "FAIL_SAFE_TIMEOUT": FAIL_SAFE_TIMEOUT,
        
        # Logging
        "EVENT_LOG_FILE": EVENT_LOG_FILE,
        "LOG_LEVEL": LOG_LEVEL,
    }
    
    # Validate critical thresholds (boundaries can overlap)
    if THRESHOLD_SAFE_CURRENT > THRESHOLD_WARNING_CURRENT_MIN:
        raise ValueError("SAFE current threshold must be <= WARNING threshold")
    
    if THRESHOLD_WARNING_CURRENT_MAX > THRESHOLD_CRITICAL_CURRENT:
        raise ValueError("WARNING current threshold must be <= CRITICAL threshold")
    
    if THRESHOLD_CRITICAL_CURRENT > THRESHOLD_HARDWARE_CUTOFF_CURRENT:
        raise ValueError("CRITICAL threshold must be <= HARDWARE_CUTOFF threshold")
    
    if THRESHOLD_SAFE_TEMP > THRESHOLD_WARNING_TEMP_MIN:
        raise ValueError("SAFE temp threshold must be <= WARNING threshold")
    
    if THRESHOLD_WARNING_TEMP_MAX > THRESHOLD_CRITICAL_TEMP:
        raise ValueError("WARNING temp threshold must be <= CRITICAL threshold")
    
    if THRESHOLD_CRITICAL_TEMP > THRESHOLD_HARDWARE_CUTOFF_TEMP:
        raise ValueError("CRITICAL temp threshold must be <= HARDWARE_CUTOFF threshold")
    
    return config


if __name__ == "__main__":
    # Test: Load and print config
    try:
        cfg = load_config()
        print("✓ Configuration loaded successfully")
        print("\nThresholds:")
        print(f"  SAFE:     Current < {cfg['THRESHOLD_SAFE_CURRENT']}A AND Temp < {cfg['THRESHOLD_SAFE_TEMP']}°C")
        print(f"  WARNING:  Current {cfg['THRESHOLD_WARNING_CURRENT_MIN']}–{cfg['THRESHOLD_WARNING_CURRENT_MAX']}A OR Temp {cfg['THRESHOLD_WARNING_TEMP_MIN']}–{cfg['THRESHOLD_WARNING_TEMP_MAX']}°C")
        print(f"  CRITICAL: Current > {cfg['THRESHOLD_CRITICAL_CURRENT']}A OR Temp > {cfg['THRESHOLD_CRITICAL_TEMP']}°C")
        print(f"  HARDWARE: Current > {cfg['THRESHOLD_HARDWARE_CUTOFF_CURRENT']}A OR Temp > {cfg['THRESHOLD_HARDWARE_CUTOFF_TEMP']}°C")
        print("\nCalibration:")
        print(f"  ACS712 Offset: {cfg['ACS712_OFFSET']}V")
        print(f"  ACS712 Sensitivity: {cfg['ACS712_SENSITIVITY']}V/A")
        print(f"  LM35 Scale: {cfg['LM35_SCALE']}")
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
