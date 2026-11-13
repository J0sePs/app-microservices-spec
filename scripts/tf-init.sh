#!/usr/bin/env bash
# Initialize a Terraform root module against the shared S3 backend.
#
# Usage: scripts/tf-init.sh <terraform|platform> [extra terraform init args]
#
# Requires TF_STATE_BUCKET (see scripts/bootstrap-tf-state.sh). AWS_REGION
# defaults to us-east-1. The script never passes -reconfigure or -force-copy:
# if a local state still exists, Terraform stops and asks for -migrate-state,
# so state is never discarded silently. One-time migration:
#
#   scripts/tf-init.sh terraform -migrate-state
#   scripts/tf-init.sh platform -migrate-state
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODULE="${1:-}"
if [[ $# -gt 0 ]]; then
  shift
fi

case "$MODULE" in
  terraform) KEY="withdrawal-soles/infra.tfstate" ;;
  platform) KEY="withdrawal-soles/platform.tfstate" ;;
  *)
    echo "usage: scripts/tf-init.sh <terraform|platform> [terraform init args]" >&2
    exit 2
    ;;
esac

if [[ -z "${TF_STATE_BUCKET:-}" ]]; then
  echo "TF_STATE_BUCKET is not set. Create the bucket with scripts/bootstrap-tf-state.sh" >&2
  exit 1
fi

REGION="${AWS_REGION:-us-east-1}"

echo "==> terraform init infra/$MODULE (s3://$TF_STATE_BUCKET/$KEY)"
terraform -chdir="$ROOT/infra/$MODULE" init -input=false -no-color \
  -backend-config="bucket=$TF_STATE_BUCKET" \
  -backend-config="key=$KEY" \
  -backend-config="region=$REGION" \
  -backend-config="encrypt=true" \
  -backend-config="use_lockfile=true" \
  "$@"
