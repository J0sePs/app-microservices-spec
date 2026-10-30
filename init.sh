#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: Node.js 20+ is required because the harness validator uses Node." >&2
  exit 1
fi

PM="npm"
if [ -f pnpm-lock.yaml ]; then
  PM="pnpm"
elif [ -f yarn.lock ]; then
  PM="yarn"
elif [ -f bun.lockb ] || [ -f bun.lock ]; then
  PM="bun"
fi

echo "==> Repository: $PWD"
echo "==> Package manager: $PM"

if [ "${SKIP_INSTALL:-0}" = "1" ]; then
  echo "==> Dependency install skipped (SKIP_INSTALL=1)"
elif [ -n "${INSTALL_CMD:-}" ]; then
  echo "==> Installing dependencies (INSTALL_CMD)"
  bash -c "$INSTALL_CMD"
elif [ -f package-lock.json ]; then
  echo "==> Installing dependencies (npm ci)"
  npm ci
elif [ -f pnpm-lock.yaml ]; then
  echo "==> Installing dependencies (pnpm install --frozen-lockfile)"
  pnpm install --frozen-lockfile
elif [ -f yarn.lock ]; then
  echo "==> Installing dependencies (yarn install --frozen-lockfile)"
  yarn install --frozen-lockfile
elif [ -f bun.lockb ] || [ -f bun.lock ]; then
  echo "==> Installing dependencies (bun install --frozen-lockfile)"
  bun install --frozen-lockfile
elif [ -f package.json ]; then
  echo "==> Installing dependencies (npm install)"
  npm install
else
  echo "==> No package manifest found; skipping dependency install"
fi

echo "==> Running verification"
bash scripts/verify.sh

START_CMD="${START_CMD:-}"
if [ -z "$START_CMD" ] && [ -f package.json ]; then
  if node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts.dev ? 0 : 1)"; then
    START_CMD="$PM run dev"
  fi
fi

if [ -n "$START_CMD" ]; then
  echo "==> Startup command: $START_CMD"
  if [ "${RUN_START_COMMAND:-0}" = "1" ]; then
    echo "==> Starting the app"
    exec bash -c "$START_CMD"
  fi
  echo "Set RUN_START_COMMAND=1 to launch it."
else
  echo "==> No startup command configured."
fi
