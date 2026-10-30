#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

FAILED=0

run_step() {
  local label="$1"
  shift

  echo
  echo "==> $label"
  if "$@"; then
    echo "PASS: $label"
  else
    echo "FAIL: $label" >&2
    FAILED=1
  fi
}

PM="npm"
if [ -f pnpm-lock.yaml ]; then
  PM="pnpm"
elif [ -f yarn.lock ]; then
  PM="yarn"
elif [ -f bun.lockb ] || [ -f bun.lock ]; then
  PM="bun"
fi

echo "==> Repository: $PWD"

run_step "Harness structure (five subsystems)" node scripts/validate-harness.mjs

if [ "${SKIP_OPENSPEC:-0}" = "1" ]; then
  echo
  echo "==> OpenSpec validation skipped (SKIP_OPENSPEC=1)"
elif command -v openspec >/dev/null 2>&1; then
  run_step "OpenSpec validation" openspec validate --all --strict
else
  echo
  echo "FAIL: OpenSpec CLI not found. Install it with:" >&2
  echo "      npm install --global @fission-ai/openspec" >&2
  echo "      Or set SKIP_OPENSPEC=1 to skip this check." >&2
  FAILED=1
fi

PROJECT_VERIFY_CMD="${VERIFY_CMD:-}"
if [ -z "$PROJECT_VERIFY_CMD" ] && [ -f package.json ] && command -v node >/dev/null 2>&1; then
  if node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts.verify ? 0 : 1)"; then
    PROJECT_VERIFY_CMD="$PM run verify"
  elif node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts.test ? 0 : 1)"; then
    PROJECT_VERIFY_CMD="$PM test"
  fi
fi

if [ -n "$PROJECT_VERIFY_CMD" ]; then
  run_step "Project verification" bash -c "$PROJECT_VERIFY_CMD"
else
  echo
  echo "==> No project verification command found; skipping"
  echo "    Set VERIFY_CMD or add a package.json verify/test script."
fi

echo
if [ "$FAILED" -ne 0 ]; then
  echo "VERIFICATION FAILED"
  exit 1
fi

echo "VERIFICATION PASSED"
