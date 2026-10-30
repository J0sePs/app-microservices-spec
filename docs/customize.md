# Adopt This Template

This repository is a template. After creating your project from it, spend ten
minutes replacing the template-specific state with your own.

## 1. Create the project

Use the GitHub **Use this template** button, or clone the repository:

```bash
git clone https://github.com/J0sePs/openspec-opencode-template.git my-project
cd my-project
rm -rf .git
git init -b main
```

## 2. Install the prerequisites

- Node.js 20 or newer
- The OpenSpec CLI:

```bash
npm install --global @fission-ai/openspec
```

- OpenCode, or another coding agent that reads `AGENTS.md`
- Git

## 3. Rename the project

Edit `feature_list.json`:

```json
{
  "project": "my-project",
  "last_updated": "YYYY-MM-DD"
}
```

Edit the title and description in `README.md`. Remove the template badges you
do not need.

## 4. Configure the commands

`init.sh` auto-detects npm, pnpm, yarn, and bun from lockfiles. If your project
uses another stack, set the commands explicitly:

```bash
INSTALL_CMD="make setup" \
VERIFY_CMD="make test" \
START_CMD="make run" \
./init.sh
```

You can also put the commands in your shell profile, a `.envrc`, or a project
task runner. The contract is simple:

- `INSTALL_CMD` installs dependencies.
- `VERIFY_CMD` proves the project works.
- `START_CMD` starts the app or development server.
- `SKIP_INSTALL=1` skips dependency installation.
- `RUN_START_COMMAND=1` launches the start command after verification.

`scripts/verify.sh` also auto-detects a `package.json` `verify` or `test`
script. Prefer a dedicated `verify` script that runs lint, type checks, and
tests.

## 5. Replace the feature list

The template ships with four `harness-*` maintenance features. They describe
the template itself. Replace them with your product's features:

1. Delete the `harness-*` entries.
2. Add one feature with status `not_started`.
3. Give it a user-visible behavior and concrete verification steps.
4. Keep the `change` field `null` until you create an OpenSpec change.

Start with one feature. A feature list with twenty aspirational entries is
harder to use than a list with three real ones.

## 6. Update the OpenSpec context

Edit `openspec/config.yaml`:

- Replace the template context with your project's constraints.
- Keep the English-only rule if you want all artifacts in English.
- Keep the "one active feature" and "evidence before passing" rules.
- Adjust the artifact rules for your domain.

The `context` field is injected into every propose/apply workflow. Use it for
constraints the agent cannot infer from the code, not for a full project
description.

## 7. Set the first change

Create your first change:

```text
/opsx-propose add-first-feature
```

Review the generated proposal, specs, design, and tasks. Then add the matching
feature to `feature_list.json` with:

```json
"status": "in_progress",
"change": "add-first-feature"
```

Run:

```bash
./init.sh
```

## 8. Clean up the template

Optional, but recommended for a product repository:

- Remove `examples/sample-change/` if you do not want a reference change.
- Remove `CLAUDE.md` if you do not use Claude Code.
- Remove `.opencode/` if you use a different agent and do not need the
  `/opsx-*` commands.
- Keep `AGENTS.md`, `feature_list.json`, `progress.md`, `session-handoff.md`,
  `init.sh`, `scripts/verify.sh`, and `openspec/config.yaml`. They are the
  harness.

## 9. Verify the adoption

Run the full gate:

```bash
./init.sh
```

You should see:

```text
Result: 5/5 subsystems passed, ... checks passed.
VERIFICATION PASSED
```

If a check fails, read the failure line. The validator names the missing file
or the inconsistent field.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `OpenSpec CLI not found` | The CLI is not installed | `npm install -g @fission-ai/openspec` |
| `feature_list.json ... invalid JSON` | A trailing comma or unquoted value | Fix the JSON and rerun |
| `is passing but has no evidence` | A feature was marked done without proof | Run the verification and add evidence, or mark it `blocked` |
| `is in_progress but has no change name` | The feature is not linked to a change | Create the change and set the `change` field |
| `points to missing openspec/changes/...` | The change name is wrong or the change was archived | Fix the name or set the feature to `passing` |
| `found 2 active changes` | Two changes are in flight | Archive or remove one before continuing |
| `is not executable` | The script lost its executable bit | `chmod +x init.sh scripts/verify.sh` |

## What not to change

The five subsystem files are the contract:

- `AGENTS.md` — instructions
- `feature_list.json` and `progress.md` — state
- `init.sh` and `scripts/verify.sh` — verification
- `openspec/changes/<change>/tasks.md` — scope
- `session-handoff.md` — lifecycle

You can change their contents, but keep their jobs. If you remove one, the
corresponding failure mode comes back.
