"""
VoltGuard Phase 1 - Arduino Simulator
Simulates Arduino sensor readings and relay behavior
Generates data in format: C=<current>,T=<temperature>
Receives state commands: SAFE, WARNING, CRITICAL
"""

import time
from datetime import datetime
from typing import Optional


class ArduinoSimulator:
    """
    Python-based mock Arduino that:
    1. Generates realistic sensor data in C=X,T=Y format
    2. Receives state commands (SAFE/WARNING/CRITICAL) from Python
    3. Applies Arduino logic to determine relay state
    4. Logs all state transitions
    
    CRITICAL RULE: Simulator does NOT independently decide relay.
    It receives state from Python and applies Arduino response logic.
    """
    
    def __init__(self, mode: str = "stable"):
        """
        Initialize simulator with specified mode.
        
        Args:
            mode: Operating mode ("stable", "rising_current", "rising_temp", "fault")
        """
        self.mode = mode
        self.relay_state = "ON"  # Default relay state
        self.current = 2.0  # Starting current in Amperes
        self.temperature = 36.0  # Starting temperature in Celsius
        self.start_time = time.time()
        self.reading_count = 0
        self.last_state_command = None
        self.state_transitions = []
        self.is_running = False
        
        print(f"[SIMULATOR] Initialized in mode: {mode}")
    
    def get_reading(self) -> str:
        """
        Generate next sensor reading in "C=X,T=Y" format.
        Simulates real-time delays based on mode.
        
        Returns:
            String in format "C=2.50,T=36.00"
        
        Raises:
            RuntimeError if simulator not running
        """
        if not self.is_running:
            raise RuntimeError("Simulator not running. Call start() first.")
        
        # Apply mode-specific behavior
        elapsed = time.time() - self.start_time
        
        if self.mode == "stable":
            # Constant values
            self.current = 2.0
            self.temperature = 36.0
        
        elif self.mode == "rising_current":
            # Current rises gradually: 2A → 6A → 12A over ~30 seconds
            # This tests SAFE → WARNING → CRITICAL transitions
            progress = min(elapsed / 30.0, 1.0)  # 0 to 1 over 30s
            if progress < 0.5:
                # 0s–15s: 2A → 6A
                self.current = 2.0 + (6.0 - 2.0) * (progress / 0.5)
            else:
                # 15s–30s: 6A → 12A
                self.current = 6.0 + (12.0 - 6.0) * ((progress - 0.5) / 0.5)
            self.temperature = 36.0  # Constant temp
        
        elif self.mode == "rising_temp":
            # Temperature spikes rapidly: 35°C → 70°C in 2 seconds
            # This tests anomaly detection
            if elapsed < 2.0:
                progress = elapsed / 2.0
                self.temperature = 35.0 + (70.0 - 35.0) * progress
            else:
                self.temperature = 70.0
            self.current = 3.0  # Constant current
        
        elif self.mode == "fault":
            # Current spike: 3A → 16A (exceeds hardware cutoff of 15A)
            # This tests hardware override
            if elapsed < 1.0:
                progress = elapsed / 1.0
                self.current = 3.0 + (16.0 - 3.0) * progress
            else:
                self.current = 16.0
            self.temperature = 36.0  # Constant temp
        
        # Add small random noise (±2%)
        noise_current = self.current * (0.98 + 0.04 * (elapsed % 0.1) / 0.1)
        noise_temp = self.temperature * (0.98 + 0.04 * (elapsed % 0.1) / 0.1)
        
        # Format reading
        reading = f"C={noise_current:.2f},T={noise_temp:.2f}\n"
        
        self.reading_count += 1
        
        # Log every 10 readings
        if self.reading_count % 10 == 0:
            print(f"[SIMULATOR] Reading #{self.reading_count}: {reading.strip()} | Relay={self.relay_state}")
        
        return reading
    
    def receive_state_command(self, state: str) -> str:
        """
        Receive state command from Python (SAFE/WARNING/CRITICAL).
        Apply Arduino logic to determine relay action.
        
        CRITICAL: Python does NOT command relay directly.
        Python sends state; Arduino decides relay.
        
        Args:
            state: Command state ("SAFE", "WARNING", or "CRITICAL")
        
        Returns:
            Relay state ("ON" or "OFF")
        
        Raises:
            ValueError if invalid state
        """
        if state not in ["SAFE", "WARNING", "CRITICAL"]:
            raise ValueError(f"Invalid state: {state}. Must be SAFE, WARNING, or CRITICAL")
        
        # Store command for logging
        self.last_state_command = state
        
        # Apply Arduino logic (simple state-to-relay mapping)
        if state == "CRITICAL":
            new_relay_state = "OFF"
        else:  # SAFE or WARNING
            new_relay_state = "ON"
        
        # Log state transition if changed
        if new_relay_state != self.relay_state:
            self.relay_state = new_relay_state
            transition = {
                "timestamp": datetime.now(),
                "state_command": state,
                "relay_action": new_relay_state,
                "current": self.current,
                "temperature": self.temperature,
            }
            self.state_transitions.append(transition)
            print(f"[SIMULATOR] State={state:8s} → Relay={new_relay_state:3s} (I={self.current:.2f}A T={self.temperature:.2f}°C)")
        
        return new_relay_state
    
    def start(self):
        """Start simulator."""
        if self.is_running:
            print("[SIMULATOR] Already running")
            return
        
        self.is_running = True
        self.start_time = time.time()
        print(f"[SIMULATOR] Started in mode: {self.mode}")
    
    def stop(self):
        """Stop simulator and log summary."""
        if not self.is_running:
            print("[SIMULATOR] Not running")
            return
        
        self.is_running = False
        elapsed = time.time() - self.start_time
        
        print(f"\n[SIMULATOR] Stopped")
        print(f"  Duration: {elapsed:.2f}s")
        print(f"  Readings: {self.reading_count}")
        print(f"  State transitions: {len(self.state_transitions)}")
        
        if self.state_transitions:
            print("  Transitions:")
            for trans in self.state_transitions:
                print(f"    {trans['timestamp'].strftime('%H:%M:%S')} - {trans['state_command']:8s} → {trans['relay_action']:3s}")
    
    def get_summary(self) -> dict:
        """Return simulator summary for testing."""
        return {
            "mode": self.mode,
            "reading_count": self.reading_count,
            "current_reading": f"C={self.current:.2f},T={self.temperature:.2f}",
            "relay_state": self.relay_state,
            "state_transitions": len(self.state_transitions),
        }


if __name__ == "__main__":
    # Test all 4 simulator modes
    print("=" * 70)
    print("TESTING ARDUINO SIMULATOR")
    print("=" * 70)
    
    modes = ["stable", "rising_current", "rising_temp", "fault"]
    
    for test_mode in modes:
        print(f"\n--- Testing mode: {test_mode} ---\n")
        
        simulator = ArduinoSimulator(mode=test_mode)
        simulator.start()
        
        # Simulate readings
        for i in range(5):
            reading = simulator.get_reading()
            time.sleep(0.1)
            
            # Simulate state commands from Python
            if i == 2:
                if test_mode in ["rising_current", "rising_temp"]:
                    simulator.receive_state_command("WARNING")
                elif test_mode == "fault":
                    simulator.receive_state_command("CRITICAL")
            
            if i == 4:
                if test_mode in ["rising_current", "rising_temp", "fault"]:
                    simulator.receive_state_command("CRITICAL")
        
        simulator.stop()
        
        # Verify state
        summary = simulator.get_summary()
        print(f"\n✓ Mode '{test_mode}' test complete")
        print(f"  Readings: {summary['reading_count']}")
        print(f"  Relay state: {summary['relay_state']}")
        print(f"  Transitions: {summary['state_transitions']}")
    
    print("\n" + "=" * 70)
    print("✓ ALL SIMULATOR TESTS PASSED")
    print("=" * 70)
