# Behavioral evaluations

These [scenarios](scenarios.json) exercise agent decisions, separate from Python tests. Run a case in a fresh agent context with only its prompt, required raw inputs and the installed skills. Do not disclose evaluation criteria to the acting agent. Save its actual artifacts and transcript in an isolated temporary workspace.

Evaluate observable behavior against each case after execution. Record passed, failed or not run for each expectation, including whether a renderer and target application were available. A simulated answer or plan is not a completed artifact test. For a baseline comparison, repeat with the same tools and inputs but without these skills.

No model account or evaluation API is required by the repository. Unit tests do not execute these cases. The repository's implementation validation report records which independent checks were actually performed.
