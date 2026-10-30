# OpenSpec

This directory is managed by the OpenSpec CLI.

- `config.yaml` — project context and per-artifact rules.
- `specs/` — durable capability specs. Do not edit these directly; archive a
  completed change to update them.
- `changes/` — in-flight changes. Keep at most one active change.
- `changes/archive/` — completed changes.

Common commands:

```bash
openspec list                 # active changes
openspec list --specs         # durable capabilities
openspec show <name>          # show a change or spec
openspec validate --all --strict
```

The agent-facing workflow is documented in `docs/workflow.md`.
