# Session Handoff

## Verified Now

- `arch-001`, `withdrawal-001`, `infra-001`, `platform-001`, `wallet-001`, and
  `security-001` are `passing` with evidence; `cicd-001` is `in_progress` with
  the active change `openspec/changes/cicd-eks-deploy`.
- `./init.sh` passes with 5/5 harness subsystems and 16/16 checks (106 tests).
- **The AWS practice stack was deployed, verified, and destroyed on
  2026-11-13.** No billable cloud resources remain:
  - `infra/platform`: `Destroy complete! Resources: 10 destroyed`
    (Traefik, namespaces, app/mock deployments, services, secret, migration
    Job, Ingress, Classic LoadBalancer).
  - `infra/terraform`: `Destroy complete! Resources: 44 destroyed`
    (EKS, node group, RDS, ECR, VPC, NAT, subnets, IAM, security groups).
  - Both S3-backed Terraform states are empty; outputs are empty.
  - AWS sweep in `us-east-1`: no EKS clusters, RDS instances, running EC2
    instances, available NAT gateways, ELB/ALB, ECR repositories, tagged VPCs,
    EBS volumes, or `/aws/eks/app-nube-2-dev` log groups.
  - The S3 state bucket `s3://app-nube-2-tfstate-205346659030` is kept on
    purpose (versioned, encrypted, private; negligible cost).
  - The only remaining Elastic IP, `32.199.142.201`, is tagged
    `machupicchu-eip` and unrelated to this stack.
- Before teardown, the deployed API passed the full contract check on the
  CI-rolled image: 11/11 (debit 25000 → 24000 cents, reversal restored 25000).
- The local Docker Compose stack remains available; `localhost:8080` serves the
  API through Traefik.

## Changed This Session

- `scripts/deploy-eks-demo.sh` accepts an optional `WALLET_SERVICE_URL`
  override (already committed earlier in the day).
- `progress.md`, `feature_list.json`, and `session-handoff.md` record the
  deployment and the teardown.

## Broken Or Unverified

- `cicd-001` stays `in_progress`: the GitHub Actions deploy job targets the EKS
  cluster that no longer exists. Unset the `EKS_DEPLOY_ENABLED` repository
  variable while the stack is down, or re-create the stack before the next push
  to `main`.
- The published wallet `http://52.67.162.209` is unreachable (TCP timeout on
  port 80). Deployments should use the in-cluster mock
  (`WALLET_MOCK_ENABLED=true` or `WALLET_SERVICE_URL`) until it is back.
- The gateway was public with no edge authentication; the service trusts
  `X-User-Id`, so it was practice-only.
- The development JWT secret is shared by all services. Production must inject
  a strong secret in every deployment.
- The real users-service and wallet URLs are not published; both used the
  in-cluster mock.

## Next Best Step

1. Keep billing at zero: nothing else needs destroying. Optionally verify:

   ```bash
   export TF_STATE_BUCKET=app-nube-2-tfstate-205346659030 AWS_REGION=us-east-1
   ./scripts/tf-init.sh terraform && terraform -chdir=infra/terraform state list
   aws eks list-clusters --region us-east-1
   aws rds describe-db-instances --region us-east-1 --query 'DBInstances[].DBInstanceIdentifier'
   ```

2. Disable the deploy job while the cluster is down:

   ```bash
   gh variable delete EKS_DEPLOY_ENABLED --repo J0sePs/app-microservices-spec
   ```

3. Finish `cicd-eks-deploy`: re-create the stack for a practice run, confirm the
   SHA and `latest` tags and the rollout in `withdrawal-soles`, then archive the
   change.

4. Redeploy when a practice run is needed:

   ```bash
   export TF_STATE_BUCKET=app-nube-2-tfstate-205346659030 AWS_REGION=us-east-1
   ./scripts/tf-init.sh terraform
   terraform -chdir=infra/terraform apply
   WALLET_SERVICE_URL=http://traefik.traefik.svc.cluster.local ./scripts/deploy-eks-demo.sh
   ```

## Commands

```bash
./init.sh
make verify
make openapi-check
openspec validate --all --strict

# Wallet and auth simulation
.venv/bin/python scripts/simulate_wallet_integration.py --mode simulate
.venv/bin/python scripts/simulate_wallet_integration.py --mode live

# HTTP contract check against a running service
.venv/bin/python scripts/wallet_contract_check.py --base-url http://localhost:8080 --wallet-url http://localhost:8080
.venv/bin/python scripts/wallet_contract_check.py --base-url http://<gateway> --wallet-url http://<gateway>

# Local stack
docker compose up -d --build
curl http://localhost:8080/health
curl http://localhost:8080/docs

# AWS deployment (S3 state backend)
export TF_STATE_BUCKET=app-nube-2-tfstate-205346659030 AWS_REGION=us-east-1
./scripts/tf-init.sh terraform
terraform -chdir=infra/terraform apply
WALLET_SERVICE_URL=http://traefik.traefik.svc.cluster.local ./scripts/deploy-eks-demo.sh
terraform -chdir=infra/platform output -raw gateway_url

# AWS teardown
./scripts/destroy-eks-demo.sh
```
