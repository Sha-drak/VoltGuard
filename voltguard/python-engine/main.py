"""
VoltGuard Phase 1C - Main Application Entry Point
Integrates: Serial Interface → Decision Engine → Event Logging

This module:
1. Initializes all components (config, serial, decision engine)
2. Runs the main decision loop
3. Handles state persistence and event logging
4. Prepares for Streamlit dashboard integration (Phase 1D)
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import load_config
from data_structures import SensorReading, SystemState, AnomalyBuffer, EventLogEntry
from decision_engine import DecisionEngine
from serial_interface import create_serial_connection
from sms_provider import MockSMSProvider


class VoltGuardApplication:
    """
    Main VoltGuard application controller.
    Orchestrates: Serial comm → Decision engine → Event logging → Dashboard ready
    """
    
    def __init__(self, use_simulator: bool = True, simulator_mode: str = "stable", 
                 enable_logging: bool = True):
        """
        Initialize application.
        
        Args:
            use_simulator: If True, use Python simulator; if False, real Arduino (Phase 2)
            simulator_mode: Simulator mode if use_simulator=True ("stable", "rising_current", etc.)
            enable_logging: If True, write events to /logs/events.csv
        """
        print("\n" + "="*70)
        print("VOLTGUARD PHASE 1 - INITIALIZING")
        print("="*70 + "\n")
        
        # Load configuration
        print("[APP] Loading configuration...")
        self.config = load_config()
        print("[APP] ✓ Configuration loaded\n")
        
        # Initialize serial connection
        print(f"[APP] Initializing serial connection (simulator={use_simulator}, mode={simulator_mode})...")
        self.serial_conn = create_serial_connection(use_simulator=use_simulator, mode=simulator_mode)
        print("[APP] ✓ Serial connection ready\n")
        
        # Initialize decision engine
        print("[APP] Initializing decision engine...")
        self.decision_engine = DecisionEngine(self.config)
        print("[APP] ✓ Decision engine ready\n")
        
        # Initialize SMS provider (phase 1: mock)
        self.sms_provider = MockSMSProvider()
        
        # Event logging
        self.enable_logging = enable_logging
        self.log_file = Path(__file__).parent.parent / "logs" / "events.csv"
        
        if self.enable_logging:
            # Create logs directory if needed
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize CSV header
            if not self.log_file.exists():
                with open(self.log_file, 'w') as f:
                    f.write("timestamp,event_type,state,relay,current,temperature,description\n")
                print(f"[APP] ✓ Event log initialized: {self.log_file}\n")
            else:
                print(f"[APP] ✓ Event log exists: {self.log_file}\n")
        
        # State tracking
        self.last_state = "SAFE"
        self.cycle_count = 0
        self.start_time = datetime.now()
        self.error_count = 0
    
    def log_event_to_csv(self, event: EventLogEntry):
        """Write event to CSV log file."""
        if not self.enable_logging:
            return
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(event.to_csv_row() + "\n")
        except Exception as e:
            print(f"[ERROR] Failed to write event log: {e}")
            self.error_count += 1
    
    def run_decision_cycle(self) -> Optional[SystemState]:
        """
        Execute one decision cycle.
        
        Returns:
            SystemState object or None if error
        """
        self.cycle_count += 1
        
        try:
            # Run decision engine cycle
            system_state = self.decision_engine.run_decision_cycle(self.serial_conn, self.sms_provider)
            
            # Log events from decision engine
            if system_state:
                for event in self.decision_engine.event_log:
                    if not hasattr(event, '_logged'):
                        self.log_event_to_csv(event)
                        event._logged = True
            
            return system_state
        
        except Exception as e:
            print(f"[ERROR] Decision cycle failed: {e}")
            self.error_count += 1
            import traceback
            traceback.print_exc()
            return None
    
    def get_system_state(self) -> Optional[SystemState]:
        """Get current system state (for dashboard use)."""
        # This would be called by Streamlit dashboard
        return self.run_decision_cycle()
    
    def get_event_log(self) -> list:
        """Return event log for dashboard display."""
        return self.decision_engine.event_log
    
    def manual_reset(self) -> bool:
        """Manually reset system after lockout."""
        return self.decision_engine.reset_lockout_manual()
    
    def stop(self):
        """Cleanly shutdown application."""
        print(f"\n[APP] Shutting down...")
        
        elapsed = datetime.now() - self.start_time
        print(f"[APP] Runtime: {elapsed.total_seconds():.1f}s")
        print(f"[APP] Cycles: {self.cycle_count}")
        print(f"[APP] Errors: {self.error_count}")
        print(f"[APP] Events logged: {len(self.decision_engine.event_log)}")
        
        # Close serial connection
        if self.serial_conn:
            self.serial_conn.close()
        
        print("[APP] ✓ Shutdown complete\n")
    
    def get_summary(self) -> dict:
        """Return application summary."""
        return {
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "cycles": self.cycle_count,
            "errors": self.error_count,
            "events": len(self.decision_engine.event_log),
            "current_state": self.decision_engine.current_state,
            "locked_out": self.decision_engine.locked_out,
        }


# ============================================================================
# TESTING & DEMO MODES
# ============================================================================

def demo_stable_operation(duration_seconds: int = 30):
    """
    Demo: Stable operation baseline (no issues)
    """
    print("\n" + "="*70)
    print("DEMO 1: STABLE OPERATION (30 seconds)")
    print("="*70 + "\n")
    
    app = VoltGuardApplication(use_simulator=True, simulator_mode="stable")
    
    start_time = time.time()
    while time.time() - start_time < duration_seconds:
        state = app.run_decision_cycle()
        if state:
            print(f"[DEMO] Cycle #{app.cycle_count}: {state.state:8s} | I={state.current:.2f}A | T={state.temperature:.2f}°C | Relay={state.relay_status}")
        time.sleep(0.5)
    
    app.stop()
    print(f"\n✓ Demo completed. Check /logs/events.csv for event log.")


def demo_rising_current(duration_seconds: int = 40):
    """
    Demo: Rising current (SAFE → WARNING → CRITICAL)
    """
    print("\n" + "="*70)
    print("DEMO 2: RISING CURRENT (SAFE → WARNING → CRITICAL)")
    print("="*70 + "\n")
    
    app = VoltGuardApplication(use_simulator=True, simulator_mode="rising_current")
    
    start_time = time.time()
    while time.time() - start_time < duration_seconds:
        state = app.run_decision_cycle()
        if state:
            print(f"[DEMO] Cycle #{app.cycle_count}: {state.state:8s} | I={state.current:.2f}A | T={state.temperature:.2f}°C | Relay={state.relay_status}")
        time.sleep(0.5)
    
    app.stop()
    print(f"\n✓ Demo completed. Check /logs/events.csv for state transitions.")


def demo_temperature_spike(duration_seconds: int = 10):
    """
    Demo: Temperature spike (tests anomaly detection)
    """
    print("\n" + "="*70)
    print("DEMO 3: TEMPERATURE SPIKE (Anomaly Detection)")
    print("="*70 + "\n")
    
    app = VoltGuardApplication(use_simulator=True, simulator_mode="rising_temp")
    
    start_time = time.time()
    while time.time() - start_time < duration_seconds:
        state = app.run_decision_cycle()
        if state:
            anomaly_flag = "🚨 ANOMALY" if state.anomaly_detected else "OK"
            print(f"[DEMO] Cycle #{app.cycle_count}: {state.state:8s} | I={state.current:.2f}A | T={state.temperature:.2f}°C | {anomaly_flag}")
        time.sleep(0.5)
    
    app.stop()
    print(f"\n✓ Demo completed. Anomaly detection should have triggered.")


def demo_fault_condition(duration_seconds: int = 10):
    """
    Demo: Fault condition (hardware override test)
    """
    print("\n" + "="*70)
    print("DEMO 4: FAULT CONDITION (Hardware Override)")
    print("="*70 + "\n")
    
    app = VoltGuardApplication(use_simulator=True, simulator_mode="fault")
    
    start_time = time.time()
    while time.time() - start_time < duration_seconds:
        state = app.run_decision_cycle()
        if state:
            print(f"[DEMO] Cycle #{app.cycle_count}: {state.state:8s} | I={state.current:.2f}A | T={state.temperature:.2f}°C | Relay={state.relay_status}")
        time.sleep(0.5)
    
    app.stop()
    print(f"\n✓ Demo completed. Hardware override should have been detected.")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    """
    Run demo scenarios to verify complete integration.
    """
    
    import argparse
    
    parser = argparse.ArgumentParser(description="VoltGuard Phase 1C Main Application")
    parser.add_argument("--demo", type=int, default=0, 
                       help="Run demo scenario (0=stable, 1=rising_current, 2=rising_temp, 3=fault)")
    parser.add_argument("--duration", type=int, default=30, 
                       help="Demo duration in seconds")
    
    args = parser.parse_args()
    
    if args.demo == 0:
        demo_stable_operation(args.duration)
    elif args.demo == 1:
        demo_rising_current(args.duration)
    elif args.demo == 2:
        demo_temperature_spike(args.duration)
    elif args.demo == 3:
        demo_fault_condition(args.duration)
    else:
        print(f"Unknown demo: {args.demo}")
        print("Usage: python main.py --demo 0|1|2|3 [--duration SECONDS]")
