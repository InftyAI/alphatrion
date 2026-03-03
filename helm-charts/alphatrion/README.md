# AlphaTrion Helm Chart

This Helm chart deploys AlphaTrion, an open-source framework for GenAI applications, on Kubernetes.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- **External PostgreSQL database** (version 12 or later recommended)

## Installing the Chart

Install the chart with your PostgreSQL configuration:

```bash
helm install alphatrion ./helm-charts/alphatrion \
  --set server.image.repository=alphatrion-server \
  --set server.image.tag=latest \
  --set dashboard.image.repository=alphatrion-dashboard \
  --set dashboard.image.tag=latest \
  --set postgresql.host=your-postgres-host \
  --set postgresql.password=your-postgres-password
```

## Building Docker Images

Before installing the Helm chart, you need to build and push the Docker images:

### Server Image

```bash
docker build -t alphatrion-server:latest .
# If using a remote registry:
# docker tag alphatrion-server:latest your-registry/alphatrion-server:latest
# docker push your-registry/alphatrion-server:latest
```

### Dashboard Image

```bash
docker build -t alphatrion-dashboard:latest ./dashboard
# If using a remote registry:
# docker tag alphatrion-dashboard:latest your-registry/alphatrion-dashboard:latest
# docker push your-registry/alphatrion-dashboard:latest
```

## Configuration

The following table lists the configurable parameters of the AlphaTrion chart and their default values.

### ServerConfiguration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `server.image.repository` | Serverimage repository | `alphatrion-server` |
| `server.image.tag` | Serverimage tag | `latest` |
| `server.image.pullPolicy` | Serverimage pull policy | `IfNotPresent` |
| `server.replicaCount` | Number of backend replicas | `2` |
| `server.resources.requests.cpu` | ServerCPU request | `500m` |
| `server.resources.requests.memory` | Servermemory request | `512Mi` |
| `server.resources.limits.cpu` | ServerCPU limit | `1000m` |
| `server.resources.limits.memory` | Servermemory limit | `1Gi` |
| `server.service.type` | Serverservice type | `ClusterIP` |
| `server.service.port` | Serverservice port | `8000` |
| `server.env.logLevel` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `INFO` |
| `server.env.autoCleanup` | Auto cleanup old records | `true` |
| `server.env.enableTracing` | Enable tracing with ClickHouse | `false` |
| `server.env.enableArtifactStorage` | Enable artifact storage | `false` |

### Dashboard Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `dashboard.image.repository` | Dashboard image repository | `alphatrion-dashboard` |
| `dashboard.image.tag` | Dashboard image tag | `latest` |
| `dashboard.image.pullPolicy` | Dashboard image pull policy | `IfNotPresent` |
| `dashboard.replicaCount` | Number of dashboard replicas | `2` |
| `dashboard.resources.requests.cpu` | Dashboard CPU request | `100m` |
| `dashboard.resources.requests.memory` | Dashboard memory request | `128Mi` |
| `dashboard.resources.limits.cpu` | Dashboard CPU limit | `500m` |
| `dashboard.resources.limits.memory` | Dashboard memory limit | `256Mi` |
| `dashboard.service.type` | Dashboard service type | `ClusterIP` |
| `dashboard.service.port` | Dashboard service port | `80` |

### PostgreSQL Configuration (Required)

AlphaTrion requires an external PostgreSQL database. Configure the connection details below:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable PostgreSQL connection | `true` |
| `postgresql.host` | PostgreSQL host (required) | `""` |
| `postgresql.port` | PostgreSQL port | `5432` |
| `postgresql.database` | PostgreSQL database name | `alphatrion` |
| `postgresql.username` | PostgreSQL username | `alphatrion` |
| `postgresql.password` | PostgreSQL password | `""` |
| `postgresql.existingSecret` | Existing secret for PostgreSQL password (recommended) | `""` |
| `postgresql.initTables` | Automatically initialize database tables | `false` |

### Ingress Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.annotations` | Ingress annotations | `{}` |
| `ingress.hosts[0].host` | Hostname | `alphatrion.local` |
| `ingress.tls` | TLS configuration | `[]` |

### ClickHouse Configuration (Optional)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `clickhouse.enabled` | Enable ClickHouse integration | `false` |
| `clickhouse.host` | ClickHouse host | `""` |
| `clickhouse.port` | ClickHouse port | `8123` |
| `clickhouse.database` | ClickHouse database | `alphatrion_tracing` |
| `clickhouse.username` | ClickHouse username | `default` |
| `clickhouse.password` | ClickHouse password | `""` |

### Docker Registry Configuration (Optional)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `registry.enabled` | Enable Docker Registry integration | `false` |
| `registry.url` | Registry URL | `""` |
| `registry.insecure` | Use HTTP instead of HTTPS | `false` |
| `registry.username` | Registry username | `""` |
| `registry.password` | Registry password | `""` |

## PostgreSQL Database Setup

AlphaTrion requires an external PostgreSQL database (version 12 or later). You must configure the database connection during installation:

### Using Password (Development)

```bash
helm install alphatrion ./helm-charts/alphatrion \
  --set postgresql.host=my-postgres.example.com \
  --set postgresql.password=mypassword
```

### Using Existing Secret (Production - Recommended)

First, create a secret with your PostgreSQL password:

```bash
kubectl create secret generic alphatrion-postgres-credentials \
  --from-literal=password=your-secure-password
```

Then install with the secret reference:

```bash
helm install alphatrion ./helm-charts/alphatrion \
  --set postgresql.host=my-postgres.example.com \
  --set postgresql.existingSecret=alphatrion-postgres-credentials
```

## Enabling Ingress

To expose AlphaTrion via Ingress:

```bash
helm install alphatrion ./helm-charts/alphatrion \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=alphatrion.example.com \
  --set ingress.tls[0].secretName=alphatrion-tls \
  --set ingress.tls[0].hosts[0]=alphatrion.example.com
```

## Initializing AlphaTrion

After installation, initialize AlphaTrion with a user and team:

```bash
kubectl exec -it deploy/alphatrion-server -- alphatrion init \
  --username admin \
  --email admin@example.com
```

This will output a `USER_ID` and `TEAM_ID` that you can use in your GenAI applications.

## Accessing the Dashboard

### Via Port-Forward (Default)

```bash
kubectl port-forward svc/alphatrion-dashboard 8080:80
```

Then visit http://localhost:8080

### Via Ingress

If you enabled ingress, visit the configured hostname (e.g., https://alphatrion.example.com)

## Upgrading

To upgrade the release:

```bash
helm upgrade alphatrion ./helm-charts/alphatrion \
  -f custom-values.yaml
```

## Uninstalling

To uninstall/delete the release:

```bash
helm uninstall alphatrion
```

This removes all the Kubernetes components associated with the chart and deletes the release.

**Note:** Your external PostgreSQL database is not affected by the uninstall. You'll need to manually clean up the database if desired.

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -l app.kubernetes.io/name=alphatrion
```

### View ServerLogs

```bash
kubectl logs -l app.kubernetes.io/component=server -f
```

### View Dashboard Logs

```bash
kubectl logs -l app.kubernetes.io/component=dashboard -f
```

### View Migration Logs

```bash
kubectl logs job/alphatrion-migration
```

### Check Database Connection

```bash
# Replace YOUR_POSTGRES_HOST and YOUR_PASSWORD with your actual values
kubectl run postgresql-client --rm --tty -i --restart='Never' \
  --image postgres:16-alpine \
  --env="PGPASSWORD=YOUR_PASSWORD" \
  -- psql --host YOUR_POSTGRES_HOST -U alphatrion -d alphatrion
```

## Advanced Configuration

For advanced configuration options, see the `values.yaml` file or run:

```bash
helm show values ./helm-charts/alphatrion
```

## License

This chart is licensed under the Apache License 2.0.
