# AGENTS.md

This repository uses a small, durable harness around a coding agent. OpenSpec
owns planning; the harness owns execution, state, verification, scope, and
session lifecycle. Keep this file short. Read the linked documents only when a
task needs them.

## Startup

Run this sequence at the start of every session:

1. `pwd` — confirm the repository root.
2. Read `context.md` — the project brief, service inventory, and domain rules.
3. Read `progress.md` — the last verified state and next step.
4. Read `feature_list.json` — the active feature and its verification.
5. `git log --oneline -5` — recent changes.
6. `./init.sh` — install, validate the harness, validate OpenSpec, run project checks.
7. If baseline verification fails, fix that before starting new work.

## Project context

This repository implements the `withdrawal-soles` microservice of a banking
platform. The platform language is Python 3.11+ with FastAPI, PostgreSQL 15,
SQLAlchemy 2.0 async, Alembic, Traefik v3, Docker Compose, pytest, GitHub
Actions, and Terraform on AWS. Architecture documentation lives in
`openspec/architecture/`. Read `context.md` before planning any change.

## Select work

- If the next feature has no OpenSpec change, create one with
  `/opsx-propose <change-name>`.
- If a change already exists, review it and use `/opsx-apply <change-name>`.
- Planning workflows create artifacts only. Do not edit project code during
  `/opsx-propose`, `/opsx-new`, or `/opsx-continue`.
- Work on exactly one feature and one change at a time. The active feature is
  the single entry in `feature_list.json` with status `in_progress`.
- Keep the feature's `change` field pointed at the active directory under
  `openspec/changes/`.

## Invariants

- The repository is the system of record. Chat history is not.
- A feature is `passing` only when the verification in its entry actually ran
  and evidence is recorded.
- Never weaken, skip, or rewrite verification to make work pass.
- Do not edit `openspec/specs/` directly. Archive a completed change to update
  the main specs.
- Keep changes inside the active feature scope. A blocker may justify a narrow
  supporting fix; record it in `progress.md`.
- Prefer durable repository artifacts over chat summaries.

## Read on demand

- `context.md` — project scope, service inventory, conventions, and domain rules.
- `openspec/architecture/` — system diagram, per-service ERDs, and contracts.
- `docs/harness.md` — the five subsystems and the files that implement them.
- `docs/workflow.md` — the OpenSpec + harness workflow, end to end.
- `docs/customize.md` — how to adopt this template for a new project.
- `openspec/config.yaml` — constraints for OpenSpec artifacts.
- `session-handoff.md` — compact state for the next session.
- `examples/sample-change/` — a reference change; it is not active.

## Definition of done

A feature is done only when all of the following are true:

- the behavior in `feature_list.json` is implemented;
- the verification steps for that feature actually ran;
- evidence is recorded in the `evidence` array;
- `./init.sh` passes from the current checkout;
- `progress.md` and `session-handoff.md` reflect the new state.

## End of session

Before ending a session:

1. Update `progress.md` with a new session entry.
2. Update `feature_list.json` status and evidence.
3. Update `session-handoff.md` if another session will continue.
4. Run `./init.sh` one last time.
5. Commit a safe, descriptive state.
6. Leave no half-finished work undocumented.
