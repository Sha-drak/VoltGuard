1. System Integrity First

All implementations must preserve the full pipeline:

Sensor Data → AI Decision → Hardware Action → User Feedback

No component should be built in isolation without integration consideration.

2. Do Not Break Core Architecture
Arduino = sensor reading + relay control + hardware alerts + safety enforcement
Python = decision engine (classification + anomaly detection)
Streamlit = visualization layer
SMS = notification layer (event-triggered only)

No reassignment of responsibilities unless explicitly approved.

3. Incremental Development Only
Build features in small, testable units
Do not generate large blocks of untested code
Each feature must run independently before integration
4. Real-Time Performance Constraint
Full system cycle must be ≤ 1 second
Avoid blocking operations (e.g., delays, heavy loops)
Ensure smooth Arduino ↔ Python communication
5. Serial Communication Standard
Arduino → Python:
C=<value>,T=<value>
Python → Arduino:
SAFE
WARNING
CRITICAL

No deviation without approval.

6. Safety Enforcement (Expanded — Non-Negotiable)
6.1 Hardware Override (Primary Layer)

Hardware must independently enforce:

IF current > 15A OR temp > 75°C → Relay OFF

This must function without Python involvement.

6.2 Fail-Safe Mechanism (Mandatory)
IF no signal from Python for 3 seconds → Relay OFF
6.3 Lockout Rule (Mandatory)
Once a CRITICAL shutdown occurs:
Relay remains OFF
System requires manual reset
No automatic recovery allowed
6.4 Relay Logic Standard
LOW  → Power ON  
HIGH → Power OFF
7. Code Clarity Over Cleverness
Use simple, readable logic
Avoid unnecessary abstraction
Comment only where necessary
8. No Silent Failures

All critical operations must:

Log errors
Output debug information (Serial / Console)

System must fail visibly, not silently.

9. UI Simplicity Rule

Streamlit UI must prioritize:

Clarity
Readability
Real-time feedback

Avoid unnecessary design complexity.

10. No Premature Optimization
Focus on working system first
Optimize only after full integration is complete
11. Single Source of Truth
Sensor data originates only from Arduino
AI decisions originate only from Python
UI reflects state — does not generate logic
SMS triggers only from confirmed CRITICAL shutdown events
12. Testing is Mandatory

Each module must be:

Executed
Validated
Confirmed working

Before progressing to the next phase.

🚨 Final Enforcement Layer

All implementations must guarantee:

Hardware override always supersedes AI
Communication failure triggers shutdown
CRITICAL state results in immediate power cutoff
System remains OFF after shutdown until reset
SMS alerts trigger only after confirmed shutdown
Real-time system responsiveness is maintained