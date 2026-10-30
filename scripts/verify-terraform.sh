#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform is required to verify infra/terraform and infra/platform" >&2
  exit 1
fi

for tf_dir in "$ROOT/infra/terraform" "$ROOT/infra/platform"; do
  echo "==> $(basename "$(dirname "$tf_dir")")/$(basename "$tf_dir")"
  echo "    terraform fmt -check"
  terraform -chdir="$tf_dir" fmt -check -recursive

  echo "    terraform init -backend=false"
  terraform -chdir="$tf_dir" init -backend=false -input=false -no-color >/dev/null

  echo "    terraform validate"
  terraform -chdir="$tf_dir" validate -no-color
done

echo "Terraform checks passed"
