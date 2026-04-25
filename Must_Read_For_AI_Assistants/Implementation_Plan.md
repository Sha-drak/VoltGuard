AI Implementation Strategy — Execution Protocol
1. Clarification First

Before implementing anything:

Ask questions if requirements are unclear
Identify gaps or assumptions
Highlight potential issues or risks
2. Challenge Weak Logic
If user instructions are inefficient, risky, or incorrect:
explicitly point it out
suggest a better alternative
Do not blindly follow flawed instructions
3. Plan Before Code

Before writing any code:

Break task into steps
Present a clear execution plan
Save plan into a file (e.g., /docs/current_plan.md)
Wait for user approval before proceeding
4. Phase-Based Execution

All work must follow phases:

Define task
Plan steps
Get approval
Implement
Test
Mark as complete

No skipping phases

5. Small Unit Implementation
Implement one feature at a time
Avoid combining multiple features in one step
Each unit must be independently testable
6. Continuous Testing

After each step:

Run the code
Validate expected output
Fix errors before proceeding
7. Completion Tracking
Maintain a checklist of tasks
Mark each completed step clearly:
[✓] Sensor reading working
[✓] Serial communication working
[ ] AI model integration pending
8. Debugging Discipline

When errors occur:

Identify root cause
Explain issue clearly
Provide fix with reasoning
Retest after fix
9. No Assumptions About Environment
Always confirm:
file structure
port names (COM ports)
installed libraries
10. Code Output Standards

All generated code must be:

complete (no missing parts)
directly runnable
clearly structured
11. Integration Awareness

Before implementing new features:

consider impact on:
Arduino code
Python AI engine
Streamlit dashboard
12. Final Validation Rule

Before declaring any phase complete:

system must:
run without errors
produce expected output
integrate with existing components