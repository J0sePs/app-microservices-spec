# Sample OpenSpec Change

This directory is a complete, read-only reference for the OpenSpec artifacts
created by `/opsx-propose`. It is **not** an active change: it lives outside
`openspec/changes/`, so `openspec list` ignores it.

Use it to see how a change maps to the harness:

| OpenSpec artifact | Harness counterpart |
| --- | --- |
| `proposal.md` | Why the feature exists |
| `specs/service-health/spec.md` | Behavior contract |
| `design.md` | Technical decisions |
| `tasks.md` | Implementation checklist |
| A `feature_list.json` entry | Acceptance state and evidence |

To turn it into a real change:

1. Copy this directory to `openspec/changes/add-health-endpoint/`.
2. Remove this `README.md`.
3. Add a matching feature to `feature_list.json` with
   `"change": "add-health-endpoint"` and `"status": "in_progress"`.
4. Run `/opsx-apply add-health-endpoint`.

The example is intentionally small and language-agnostic. It is a reference,
not a requirement.
