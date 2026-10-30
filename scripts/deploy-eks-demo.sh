#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT/infra/terraform"
REGION="${AWS_REGION:-us-east-1}"
NAMESPACE="withdrawal-soles"

for command in terraform aws kubectl docker; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "$command is required for the EKS demo" >&2
    exit 1
  fi
done

cd "$ROOT"

CLUSTER="$(terraform -chdir="$TF_DIR" output -raw eks_cluster_name)"
ECR="$(terraform -chdir="$TF_DIR" output -raw ecr_repository_url)"
RDS_ENDPOINT="$(terraform -chdir="$TF_DIR" output -raw rds_endpoint)"
DB_NAME="$(terraform -chdir="$TF_DIR" output -raw rds_database_name)"
DB_USER="$(sed -n 's/^db_username *= *"\(.*\)"/\1/p' "$TF_DIR/terraform.tfvars" || true)"
DB_USER="${DB_USER:-withdrawal}"
DB_PASSWORD="$(sed -n 's/^db_password *= *"\(.*\)"/\1/p' "$TF_DIR/terraform.tfvars")"

if [[ -z "$DB_PASSWORD" ]]; then
  echo "db_password not found in $TF_DIR/terraform.tfvars" >&2
  exit 1
fi

aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER"

echo "==> Waiting for both nodes to be Ready"
kubectl wait --for=condition=Ready nodes --all --timeout=600s

echo "==> Building and pushing image to ECR"
TAG="$(git rev-parse --short HEAD)"
IMAGE="$ECR:$TAG"
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "${ECR%%/*}" >/dev/null
docker build -t "$IMAGE" "$ROOT"
docker push "$IMAGE" >/dev/null

echo "==> Creating namespace and database secret"
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NAMESPACE" create secret generic withdrawal-db \
  --from-literal=url="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${RDS_ENDPOINT}/${DB_NAME}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "==> Applying mock dependencies"
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mock-dependencies
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mock-dependencies
  template:
    metadata:
      labels:
        app: mock-dependencies
    spec:
      containers:
        - name: mock-dependencies
          image: $IMAGE
          imagePullPolicy: Always
          command: ["uvicorn", "tools.mock_dependencies:app", "--host", "0.0.0.0", "--port", "8001"]
          ports:
            - containerPort: 8001
          readinessProbe:
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 5
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: mock-dependencies
  namespace: $NAMESPACE
spec:
  selector:
    app: mock-dependencies
  ports:
    - port: 8001
      targetPort: 8001
EOF

echo "==> Running database migrations"
kubectl -n "$NAMESPACE" delete job withdrawal-migrate --ignore-not-found >/dev/null
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: withdrawal-migrate
  namespace: $NAMESPACE
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: $IMAGE
          command: ["alembic", "upgrade", "head"]
          env:
            - name: WITHDRAWAL_SOLES_DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: withdrawal-db
                  key: url
EOF
kubectl -n "$NAMESPACE" wait --for=condition=complete job/withdrawal-migrate --timeout=600s

echo "==> Applying withdrawal-soles"
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: withdrawal-soles
  namespace: $NAMESPACE
spec:
  replicas: 2
  selector:
    matchLabels:
      app: withdrawal-soles
  template:
    metadata:
      labels:
        app: withdrawal-soles
    spec:
      containers:
        - name: withdrawal-soles
          image: $IMAGE
          imagePullPolicy: Always
          command: ["uvicorn", "withdrawal_soles.main:app", "--host", "0.0.0.0", "--port", "8000"]
          ports:
            - containerPort: 8000
          env:
            - name: WITHDRAWAL_SOLES_DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: withdrawal-db
                  key: url
            - name: WITHDRAWAL_SOLES_USER_SERVICE_URL
              value: "http://mock-dependencies:8001"
            - name: WITHDRAWAL_SOLES_TRANSACTION_SERVICE_URL
              value: "http://mock-dependencies:8001"
            - name: WITHDRAWAL_SOLES_BUSINESS_TIMEZONE
              value: "America/Lima"
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: withdrawal-soles
  namespace: $NAMESPACE
spec:
  selector:
    app: withdrawal-soles
  ports:
    - port: 80
      targetPort: 8000
EOF

echo "==> Waiting for application rollout"
kubectl -n "$NAMESPACE" rollout status deployment/withdrawal-soles --timeout=600s

echo "==> Pods and services"
kubectl -n "$NAMESPACE" get pods -o wide
kubectl -n "$NAMESPACE" get svc

echo "==> Open the app locally with:"
echo "kubectl -n $NAMESPACE port-forward svc/withdrawal-soles 18080:80"
echo "Then open http://localhost:18080/docs"
