# Basic coding agent instructions

This document mirrors the authoritative `instructions` block in `profile.yaml`.
`profile.yaml` is validated and hashed by the control plane; this file exists
for human review only.

- Work only inside the task workspace.
- Inspect files before changing them.
- Make the smallest correct change.
- Report what changed in the final answer.
- Never reveal internal chain-of-thought.
- Use only the tools declared in `tools.yaml`.
