# ClickHouse Deployment for AlphaTrion

This directory contains configuration for deploying ClickHouse separately from AlphaTrion using Kubernetes StatefulSets with the official ClickHouse image.

**Two deployment options:**

| Feature | Single Node | High Availability |
|---------|------------|-------------------|
| **Replicas** | 1 ClickHouse pod | 3 ClickHouse pods + 3 Keeper pods |
| **Data Redundancy** | ❌ No | ✅ Yes (3x replicated) |
| **Automatic Failover** | ❌ No | ✅ Yes |
| **Resource Usage** | 500m CPU / 2Gi RAM | 2.1 CPU / 8.5Gi RAM total |
| **Storage** | 100Gi | 300Gi total (100Gi × 3) |
| **Use Case** | Development, Testing | Production |
| **Setup Complexity** | Simple | Moderate |
| **File** | `clickhouse-statefulset.yaml` | `clickhouse-ha.yaml` |

For HA setup, see **[High Availability Setup Guide](HA-SETUP.md)**.

---

## Single Node Deployment (Quick Start)

### Prerequisites

1. **AWS EKS Cluster** with the EBS CSI driver installed
2. **gp3 Storage Class** configured
3. **kubectl** configured to access your cluster

## Installation

### 1. Create gp3 Storage Class

```bash
kubectl apply -f ./helm-charts/clickhouse/storageclass-gp3.yaml
```

### 2. Create Namespace (if not exists)

```bash
kubectl create namespace alphatrion
```

### 3. Deploy ClickHouse

```bash
kubectl apply -f ./helm-charts/clickhouse/clickhouse-statefulset.yaml
```

### 4. Verify Deployment

```bash
# Check pod
kubectl get pods -n alphatrion -l app=clickhouse

# Check PVC
kubectl get pvc -n alphatrion

# Check service
kubectl get svc -n alphatrion clickhouse

# Test ClickHouse
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query "SELECT version()"
```

## Configuration

The deployment is configured via `clickhouse-statefulset.yaml`:

### Storage

- **Storage Class**: gp3
- **Size**: 100Gi
- **Access Mode**: ReadWriteOnce

To change storage size, edit the StatefulSet:

```yaml
volumeClaimTemplates:
- metadata:
    name: clickhouse-data
  spec:
    storageClassName: gp3
    resources:
      requests:
        storage: 200Gi  # Change size here
```

For custom gp3 IOPS/throughput, update `storageclass-gp3.yaml`:

```yaml
parameters:
  type: gp3
  iops: "3000"
  throughput: "250"
```

### Authentication

Default credentials (defined in clickhouse-statefulset.yaml):
- **Username**: alphatrion
- **Password**: alphatrion (⚠️ Change in production!)

To change credentials, update the env vars in the StatefulSet:

```yaml
env:
- name: CLICKHOUSE_USER
  value: "your-username"
- name: CLICKHOUSE_PASSWORD
  value: "your-secure-password"
```

Or use a Kubernetes Secret:

```yaml
env:
- name: CLICKHOUSE_PASSWORD
  valueFrom:
    secretKeyRef:
      name: clickhouse-credentials
      key: password
```

### Resources

Current resource limits:

```yaml
resources:
  requests:
    cpu: 500m
    memory: 2Gi
  limits:
    cpu: 2000m
    memory: 4Gi
```

Adjust based on your workload requirements.

## Connecting AlphaTrion

After deploying ClickHouse, update your AlphaTrion `values.yaml`:

```yaml
clickhouse:
  enabled: true
  host: "clickhouse.alphatrion.svc.cluster.local"
  port: 8123
  database: alphatrion_traces
  username: alphatrion
  password: "alphatrion"  # or use existingSecret
  initTables: false

server:
  env:
    enableTracing: true
```

Or use the provided values file:

```bash
helm upgrade alphatrion ./helm-charts/alphatrion \
  -f ./helm-charts/alphatrion/values-with-clickhouse.yaml
```

## Accessing ClickHouse

### Port Forward

```bash
kubectl port-forward -n alphatrion clickhouse-0 8123:8123
```

Then access via HTTP:
```bash
curl http://localhost:8123
```

### Using clickhouse-client

```bash
kubectl exec -it -n alphatrion clickhouse-0 -- clickhouse-client
```

Example queries:

```sql
-- List databases
SHOW DATABASES;

-- Use alphatrion_traces database
USE alphatrion_traces;

-- List tables
SHOW TABLES;
```

## Scaling

To scale ClickHouse (single node only in this simple setup):

```bash
kubectl scale statefulset clickhouse -n alphatrion --replicas=1
```

Note: For multi-node clustering with replication, you'll need to configure ZooKeeper/ClickHouse Keeper and update the ClickHouse configuration files.

## Upgrading

To upgrade to a newer ClickHouse version, edit the StatefulSet and change the image tag:

```yaml
containers:
- name: clickhouse
  image: clickhouse/clickhouse-server:24.8-alpine  # Update version
```

Then apply the changes:

```bash
kubectl apply -f ./helm-charts/clickhouse/clickhouse-statefulset.yaml
```

## Uninstallation

```bash
# Delete the StatefulSet and Service
kubectl delete -f ./helm-charts/clickhouse/clickhouse-statefulset.yaml

# Delete PVC if needed (⚠️ This deletes all data!)
kubectl delete pvc -n alphatrion clickhouse-data-clickhouse-0
```

## Backup and Restore

### Backup

```bash
# Create a backup
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query="BACKUP DATABASE alphatrion_traces TO Disk('backups', 'backup-$(date +%Y%m%d)')"

# Or use kubectl cp to copy data
kubectl cp alphatrion/clickhouse-0:/var/lib/clickhouse ./clickhouse-backup
```

### Restore

```bash
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query="RESTORE DATABASE alphatrion_traces FROM Disk('backups', 'backup-20240101')"
```

## Troubleshooting

### Check ClickHouse logs

```bash
kubectl logs -n alphatrion clickhouse-0 -f
```

### Pod not starting

```bash
# Check pod events
kubectl describe pod -n alphatrion clickhouse-0

# Check PVC events
kubectl describe pvc -n alphatrion clickhouse-data-clickhouse-0
```

### Storage issues

```bash
# Check PVC status
kubectl get pvc -n alphatrion

# Check storage class
kubectl get storageclass gp3

# Check if gp3 storage class exists
kubectl describe storageclass gp3
```

If gp3 storage class doesn't exist, create it:

```bash
kubectl apply -f ./helm-charts/clickhouse/storageclass-gp3.yaml
```

### Connection issues

```bash
# Test connectivity from another pod
kubectl run -it --rm test --image=curlimages/curl --restart=Never -- \
  curl http://clickhouse.alphatrion.svc.cluster.local:8123

# Check service endpoints
kubectl get endpoints -n alphatrion clickhouse
```

## Performance Tuning

1. **Increase gp3 throughput** in `storageclass-gp3.yaml`:
   ```yaml
   parameters:
     throughput: "500"  # Up to 1000 MiB/s
   ```

2. **Increase resources** in `clickhouse-statefulset.yaml`:
   ```yaml
   resources:
     requests:
       cpu: 2000m
       memory: 8Gi
     limits:
       cpu: 4000m
       memory: 16Gi
   ```

3. **Use node selectors** for specific instance types:
   ```yaml
   nodeSelector:
     node.kubernetes.io/instance-type: m5.2xlarge
   ```

## Cost Optimization

- gp3 provides better performance at lower cost than gp2
- Right-size storage based on actual usage
- Consider using spot instances for non-production
- Monitor and adjust resource requests/limits based on actual usage
