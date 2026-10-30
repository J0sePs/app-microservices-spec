#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT/infra/terraform"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform is required to verify infra/terraform" >&2
  exit 1
fi

echo "==> terraform fmt -check"
terraform -chdir="$TF_DIR" fmt -check -recursive

echo "==> terraform init -backend=false"
terraform -chdir="$TF_DIR" init -backend=false -input=false -no-color >/dev/null

echo "==> terraform validate"
terraform -chdir="$TF_DIR" validate -no-color

echo "Terraform checks passed"
