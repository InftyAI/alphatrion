# AlphaTrion Helm Chart - Quick Start Guide

This guide will help you quickly deploy AlphaTrion on Kubernetes using Helm.

## Prerequisites

- Kubernetes cluster (1.19+)
- Helm 3.0+
- kubectl configured to access your cluster
- **PostgreSQL database** (external, version 12 or later)
- **ClickHouse database** (optional, for tracing - see [Quick ClickHouse Setup](#optional-clickhouse-setup))

## Quick Install (Local Development)

### 1. Build Docker Images

```bash
# Build backend image
docker build -t alphatrion-server:latest .

# Build dashboard image
docker build -t alphatrion-dashboard:latest ./dashboard
```

### 2. Load Images to Kubernetes (if using minikube/kind)

```bash
# For minikube
minikube image load alphatrion-server:latest
minikube image load alphatrion-dashboard:latest

# For kind
kind load docker-image alphatrion-server:latest
kind load docker-image alphatrion-dashboard:latest
```

### 3. Setup PostgreSQL Database

You need an external PostgreSQL database. For local development, you can quickly spin one up:

```bash
# Using Docker
docker run -d --name alphatrion-postgres \
  -e POSTGRES_DB=alphatrion \
  -e POSTGRES_USER=alphatrion \
  -e POSTGRES_PASSWORD=alphatr1on \
  -p 5432:5432 \
  postgres:16-alpine

# Or using Kubernetes
kubectl run postgres --image=postgres:16-alpine \
  --env="POSTGRES_DB=alphatrion" \
  --env="POSTGRES_USER=alphatrion" \
  --env="POSTGRES_PASSWORD=alphatr1on" \
  --port=5432

kubectl expose pod postgres --port=5432 --target-port=5432
```

### 4. Install Helm Chart

```bash
# Install with PostgreSQL connection
helm install alphatrion ./helm-charts/alphatrion \
  -f ./helm-charts/alphatrion/values-dev.yaml \
  --set postgresql.host=postgres \
  --set postgresql.password=alphatr1on
```

**Note:** If using Docker PostgreSQL from your host, use `host.docker.internal` or your host IP instead of `postgres`.

### 5. Wait for Pods to Start

```bash
kubectl get pods -l app.kubernetes.io/name=alphatrion -w
```

### 6. Initialize AlphaTrion

```bash
kubectl exec -it deploy/alphatrion-server -- alphatrion init \
  --username admin \
  --email admin@example.com
```

Save the `USER_ID` and `TEAM_ID` from the output.

### 7. Access the Dashboard

```bash
kubectl port-forward svc/alphatrion-dashboard 8080:80
```

Visit http://localhost:8080 in your browser.

## Optional: ClickHouse Setup

If you want to enable tracing support with ClickHouse, you have two options:

### Option A: Single Node (Development/Testing)

```bash
# 1. Create gp3 storage class (AWS only)
kubectl apply -f ./helm-charts/clickhouse/storageclass-gp3.yaml

# 2. Deploy single-node ClickHouse
kubectl apply -f ./helm-charts/clickhouse/clickhouse-statefulset.yaml

# 3. Verify
kubectl get pods -n alphatrion -l app=clickhouse
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query "SELECT version()"
```

### Option B: High Availability (Production)

For production workloads with automatic failover and data replication:

```bash
# 1. Create gp3 storage class (AWS only)
kubectl apply -f ./helm-charts/clickhouse/storageclass-gp3.yaml

# 2. Deploy HA cluster (3 replicas + 3 keeper nodes)
./helm-charts/clickhouse/deploy-ha.sh

# Or manually:
kubectl apply -f ./helm-charts/clickhouse/clickhouse-ha.yaml
```

See [HA Setup Guide](./clickhouse/HA-SETUP.md) for detailed instructions and migration guide.

### Connect AlphaTrion to ClickHouse

```bash
helm upgrade alphatrion ./helm-charts/alphatrion \
  -f ./helm-charts/alphatrion/values-with-clickhouse.yaml
```

For more details, see the [ClickHouse deployment guide](./clickhouse/README.md).

## Common Operations

### View Logs

```bash
# Backend logs
kubectl logs -l app.kubernetes.io/component=server -f

# Dashboard logs
kubectl logs -l app.kubernetes.io/component=dashboard -f

# Migration logs
kubectl logs job/alphatrion-migration
```

### Access Backend API

```bash
kubectl port-forward svc/alphatrion-server 8000:8000
curl http://localhost:8000/health
```

### Access PostgreSQL

```bash
# If using Kubernetes PostgreSQL pod
kubectl port-forward pod/postgres 5432:5432
psql -h localhost -U alphatrion -d alphatrion
# Password: alphatr1on (dev default)

# If using Docker PostgreSQL
psql -h localhost -U alphatrion -d alphatrion
# Password: alphatr1on (dev default)
```

### Upgrade Release

```bash
helm upgrade alphatrion ./helm-charts/alphatrion -f ./helm-charts/alphatrion/values-dev.yaml
```

### Uninstall

```bash
helm uninstall alphatrion

# Optionally delete PostgreSQL (if you created it for dev)
kubectl delete pod postgres
kubectl delete svc postgres

# Or if using Docker
docker stop alphatrion-postgres
docker rm alphatrion-postgres
```

## Production Deployment

For production, use `values-prod.yaml` and customize it:

1. Update image repositories to your registry
2. Configure your production PostgreSQL connection
3. Enable ClickHouse for tracing
4. Enable Docker Registry for artifacts
5. Configure Ingress with TLS
6. Set up proper secrets management

```bash
# Copy and customize production values
cp helm-charts/alphatrion/values-prod.yaml my-prod-values.yaml
# Edit my-prod-values.yaml with your PostgreSQL host and other settings

# Create secret for PostgreSQL password
kubectl create secret generic alphatrion-postgres-credentials \
  --from-literal=password=your-secure-password

# Install
helm install alphatrion ./helm-charts/alphatrion -f my-prod-values.yaml
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/name=alphatrion

# Describe pod for events
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name>
```

### Database Connection Issues

```bash
# Check if PostgreSQL is ready
kubectl get pods -l app.kubernetes.io/name=postgresql

# Check migration job logs
kubectl logs job/alphatrion-migration

# Test database connection
kubectl exec -it deploy/alphatrion-server -- sh -c 'python -c "import os; print(os.getenv(\"ALPHATRION_METADATA_DB_URL\"))"'
```

### Migration Failures

```bash
# View migration logs
kubectl logs job/alphatrion-migration

# If you need to re-run migrations
kubectl delete job alphatrion-migration
helm upgrade alphatrion ./helm-charts/alphatrion
```

## Using AlphaTrion in Your Application

After initialization, use AlphaTrion in your Python code:

```python
import alphatrion as alpha

# Initialize with your USER_ID from the init command
alpha.init(user_id='<YOUR_USER_ID>')

# Create an experiment
experiment = alpha.create_experiment(
    name="my-experiment",
    description="My first experiment"
)

# Track your GenAI application
# ... your code here ...
```

## Next Steps

- Read the full [README.md](alphatrion/README.md) for detailed configuration options
- Check the [values.yaml](alphatrion/values.yaml) for all available settings
- Review [values-dev.yaml](alphatrion/values-dev.yaml) and [values-prod.yaml](alphatrion/values-prod.yaml) for environment-specific examples

## Support

- Documentation: https://github.com/InftyAI/alphatrion
- Issues: https://github.com/InftyAI/alphatrion/issues
