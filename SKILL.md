---
name: learning
description: Explicit-use project learning mode for lightweight supplemental teaching. Use only when the user explicitly invokes learning by name to toggle the current project's learning mode, or when a project AGENTS.md learning-managed block instructs Codex to read this skill for read-only state recovery.
---

# Learning

`learning` is a lightweight project learning mode. It explains why work is being done at natural task boundaries, without turning the task into a course.

## Entry Routing

First identify why this skill was loaded:

- **Explicit user invocation**: the user directly named `learning` through `/learning`, `$learning`, or a skill chip. Read [references/toggle.md](references/toggle.md), toggle the project state, confirm the new state briefly, then stop.
- **Project AGENTS read-only recovery**: a `learning-managed` block in the project's `AGENTS.md` instructed Codex to read this skill. Run `scripts/learning_state.py status --project <project>`. If `enabled` is not `1`, stop. If `enabled` is `1`, read [references/active-mode.md](references/active-mode.md), then read `<project>/.codex/learning/NOTES.md`.

Reading this skill from project `AGENTS.md` is not an explicit invocation and must not create, toggle, or change learning state.

## Hard Boundaries

- Explicit invocation is the only path that creates or toggles `state.json`.
- Project state and project memory live under `<project>/.codex/learning/`.
- `state.json` contains only `enabled`.
- `.codex/learning/` is personal project memory; script-managed writes keep it ignored by Git when the project is a Git repository.
- `NOTES.md` records stable teaching preferences only.
- Task quality stays primary. Learning explains and compresses existing judgment; it must not drive solution choice, expand scope, or reduce validation quality.

## Resources

- `scripts/learning_state.py`: manage project state, project memory, `.gitignore`, and the project `AGENTS.md` managed block.
- [references/toggle.md](references/toggle.md): explicit invocation workflow.
- [references/active-mode.md](references/active-mode.md): behavior while learning mode is enabled.
