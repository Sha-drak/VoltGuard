1. Executive Overview

This project delivers a real-time intelligent electrical monitoring and protection system that detects abnormal power conditions and automatically prevents damage by cutting off supply.

The system integrates:

Embedded hardware (Arduino/ESP32) for sensing and control
Python-based decision engine for classification and anomaly detection
Streamlit dashboard for real-time monitoring
SMS alert system for user notification
Core Output Flow:

Data → Decision → Hardware Shutdown → User Notification

2. Problem Statement

Electrical systems fail due to:

Overcurrent
Overheating
Irregular electrical patterns

Traditional systems:

React only to extreme thresholds
Cannot detect early anomalies
Provide no real-time visibility or alerts
3. Solution Approach

This system introduces:

Continuous monitoring of electrical parameters
Rule-based + anomaly-assisted decision logic
Hardware-enforced safety shutdown (independent of AI)
Real-time dashboard visualization
Event-triggered SMS alerts
4. System Architecture
4.1 Hardware Layer (Arduino / ESP32)
Components:
Current Sensor (ACS712)
Temperature Sensor (LM35 or equivalent)
Relay Module
Buzzer
LCD Display
Responsibilities:
Read and calibrate sensor data
Send formatted data via serial
Execute relay switching
Trigger buzzer and LCD updates
Enforce hardware safety override (highest priority)
Execute fail-safe shutdown if communication is lost
4.2 AI Processing Layer (Python)
Responsibilities:
Read real-time sensor data via serial
Parse values (current, temperature)
Classify system state:
SAFE
WARNING
CRITICAL
Perform anomaly detection (pattern-based, not just thresholds)
Send control commands back to Arduino
4.3 Visualization Layer (Streamlit Dashboard)
Displays:
Live current and temperature
System state (SAFE / WARNING / CRITICAL)
Relay status (ON / OFF)
Event logs (timestamped)
4.4 Notification Layer (SMS Alerts)
Trigger Condition (Corrected):

SMS is sent when:

System enters CRITICAL state AND relay is turned OFF
Message includes:
Current
Temperature
System state
Action taken (Power OFF)
Timestamp
SMS Provider:
Arkesel API
5. Data Flow Pipeline (Corrected)
Sensors → Arduino → Serial → Python → Decision → Arduino Relay
                                              ↓
                                      Streamlit Dashboard
                                              ↓
                                           SMS Alert
6. Standardized Threshold Model (MANDATORY)
SAFE:     current < 5A   AND temp < 40°C
WARNING:  current 5–10A  OR  temp 40–60°C
CRITICAL: current > 10A  OR  temp > 60°C

HARDWARE CUTOFF:
current > 15A OR temp > 75°C
7. Safety Logic (Corrected — Non-Negotiable)
7.1 Hardware Override (Primary Safety Layer)

System must cut power regardless of AI:

IF current > 15A OR temp > 75°C → Relay OFF
7.2 Fail-Safe Mechanism (Added)
IF no signal from Python for 3 seconds → Relay OFF
7.3 Lockout Rule (Added)
Once CRITICAL shutdown occurs:
System remains OFF
Requires manual reset
7.4 Relay Logic Standard
LOW  → Power ON  
HIGH → Power OFF
8. Technical Implementation Strategy (Reinforced)
Phase 1 — Hardware Setup
Configure sensors
Output stable readings:
C=2.50,T=36.00
Phase 2 — Serial Communication
Establish Arduino ↔ Python link
Validate continuous data stream
Phase 3 — Decision Logic
Implement threshold classification
Add anomaly detection (rate-of-change based)
Phase 4 — Control Loop
Send state (SAFE/WARNING/CRITICAL) to Arduino
Arduino executes relay logic
Phase 5 — Safety Enforcement
Implement:
Hardware override
Fail-safe timeout
Lockout mechanism
Phase 6 — Dashboard (Streamlit)
Real-time charts
State indicators
Event logs
Phase 7 — SMS Integration
Trigger only on:
CRITICAL + Relay OFF
Prevent duplicate alerts
9. SMS Alert System (Corrected)
Trigger Rule

Send SMS only when:

CRITICAL state is confirmed
Relay has been turned OFF
Message Format
⚠️ ALERT: Critical Electrical Condition Detected
Current: 11.2A
Temperature: 67°C
Action: Power Supply Turned OFF
Time: 14:32:10
Constraints
Send once per event
Reset required before next alert
Provider
Arkesel API
Credentials stored securely (env variables)
10. Phone Number Management (Unchanged — Valid)
Config file (config.json)
Streamlit subscription option
Hybrid approach recommended
Validation Rules:
Must include country code
No duplicates
Secure storage
🚨 FINAL SYSTEM RULES (ENFORCED)
Hardware override always supersedes AI
Loss of communication triggers shutdown
CRITICAL state must cut power immediately
System must not auto-recover after shutdown
SMS must trigger only after confirmed shutdown
Dashboard reflects real-time system state