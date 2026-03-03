# High Availability ClickHouse Setup

This guide shows how to deploy a highly available ClickHouse cluster with 3 replicas and ClickHouse Keeper for coordination.

## Architecture

**High Availability Setup:**
- **3 ClickHouse replicas** - Data is replicated across all 3 nodes
- **3 ClickHouse Keeper nodes** - Consensus-based coordination (replaces ZooKeeper)
- **Pod Anti-Affinity** - Spreads pods across different nodes and availability zones
- **Persistent Storage** - Each pod has its own 100Gi gp3 volume
- **Auto-recovery** - Failed pods automatically restart and rejoin the cluster

## Prerequisites

1. **AWS EKS Cluster** with at least 3 worker nodes (preferably across different AZs)
2. **gp3 Storage Class** configured
3. **Sufficient resources** - Each ClickHouse pod needs 500m CPU / 2Gi RAM (request)
4. **kubectl** configured to access your cluster

## Deployment

### 1. Create gp3 Storage Class (if not exists)

```bash
kubectl apply -f ./helm-charts/clickhouse/storageclass-gp3.yaml
```

### 2. Deploy HA ClickHouse Cluster

```bash
kubectl apply -f ./helm-charts/clickhouse/clickhouse-ha.yaml
```

This will create:
- 3 ClickHouse Keeper pods (for coordination)
- 3 ClickHouse server pods (for data storage and processing)
- ConfigMap with cluster configuration
- Services for internal and external access

### 3. Wait for Deployment

```bash
# Watch pods come up (this may take 2-3 minutes)
kubectl get pods -n alphatrion -l app=clickhouse -w
kubectl get pods -n alphatrion -l app=clickhouse-keeper -w
```

Expected output:
```
clickhouse-keeper-0   1/1     Running
clickhouse-keeper-1   1/1     Running
clickhouse-keeper-2   1/1     Running
clickhouse-0          1/1     Running
clickhouse-1          1/1     Running
clickhouse-2          1/1     Running
```

### 4. Verify Cluster

```bash
# Check cluster status
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query "SELECT * FROM system.clusters WHERE cluster='alphatrion_cluster'"

# Check replication status
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query "SELECT * FROM system.replicas"

# Verify all nodes see each other
for i in 0 1 2; do
  echo "=== clickhouse-$i ==="
  kubectl exec -n alphatrion clickhouse-$i -- clickhouse-client --query "SELECT hostname(), version()"
done
```

## Creating Replicated Tables

When using the HA setup, create tables with the `ReplicatedMergeTree` engine:

```sql
-- Connect to any ClickHouse node
kubectl exec -it -n alphatrion clickhouse-0 -- clickhouse-client

-- Create a replicated table
CREATE TABLE alphatrion_traces.traces ON CLUSTER alphatrion_cluster
(
    trace_id String,
    span_id String,
    timestamp DateTime,
    duration_ms UInt32,
    service_name String
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/traces', '{replica}')
PARTITION BY toYYYYMM(timestamp)
ORDER BY (service_name, timestamp);

-- Verify table exists on all replicas
SELECT hostname(), database, name, engine FROM clusterAllReplicas('alphatrion_cluster', system.tables)
WHERE database = 'alphatrion_traces';
```

## Testing High Availability

### Test 1: Node Failure

```bash
# Delete one ClickHouse pod
kubectl delete pod -n alphatrion clickhouse-1

# Watch it automatically restart
kubectl get pods -n alphatrion -l app=clickhouse -w

# Verify data is still accessible
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query "SELECT count() FROM system.clusters WHERE cluster='alphatrion_cluster'"
```

### Test 2: Write Replication

```bash
# Write data to clickhouse-0
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query "INSERT INTO alphatrion_traces.traces VALUES ('trace1', 'span1', now(), 100, 'test-service')"

# Read from clickhouse-1 (should see the data)
kubectl exec -n alphatrion clickhouse-1 -- clickhouse-client --query "SELECT * FROM alphatrion_traces.traces"

# Read from clickhouse-2 (should also see the data)
kubectl exec -n alphatrion clickhouse-2 -- clickhouse-client --query "SELECT * FROM alphatrion_traces.traces"
```

### Test 3: Keeper Failover

```bash
# Delete one Keeper pod
kubectl delete pod -n alphatrion clickhouse-keeper-1

# Cluster should continue working (quorum is 2/3)
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query "SELECT 1"
```

## Monitoring

### Check Cluster Health

```bash
# Cluster info
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query "
SELECT
    cluster,
    shard_num,
    replica_num,
    host_name,
    port,
    is_local,
    errors_count
FROM system.clusters
WHERE cluster = 'alphatrion_cluster'"

# Replication queue
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query "
SELECT
    database,
    table,
    is_currently_executing,
    num_tries,
    last_exception
FROM system.replication_queue"

# Keeper status
for i in 0 1 2; do
  echo "=== keeper-$i ==="
  kubectl exec -n alphatrion clickhouse-keeper-$i -- sh -c 'echo mntr | nc localhost 2181'
done
```

### Resource Usage

```bash
# Check CPU and memory
kubectl top pods -n alphatrion -l app=clickhouse
kubectl top pods -n alphatrion -l app=clickhouse-keeper

# Check storage
kubectl get pvc -n alphatrion
```

## Scaling

### Scale ClickHouse Replicas

To add more replicas (within the same shard):

1. Update the StatefulSet:
```bash
kubectl scale statefulset clickhouse -n alphatrion --replicas=5
```

2. Update the cluster configuration in ConfigMap to include new replicas:
```yaml
<replica>
    <host>clickhouse-3.clickhouse.alphatrion.svc.cluster.local</host>
    <port>9000</port>
</replica>
<replica>
    <host>clickhouse-4.clickhouse.alphatrion.svc.cluster.local</host>
    <port>9000</port>
</replica>
```

3. Restart pods to pick up new config:
```bash
kubectl rollout restart statefulset clickhouse -n alphatrion
```

### Add Shards (Horizontal Partitioning)

For true horizontal scaling with data partitioning, you need to add shards. This requires:

1. Deploying additional StatefulSets for each shard
2. Updating the `remote_servers` configuration with multiple `<shard>` sections
3. Using Distributed tables to query across shards

See ClickHouse documentation for multi-shard setups.

## Backup and Restore

### Backup

```bash
# Create backup on all replicas
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query="BACKUP DATABASE alphatrion_traces TO Disk('backups', 'backup-$(date +%Y%m%d)')"

# Or use volume snapshots (recommended for large datasets)
# Create snapshots of all PVCs
for i in 0 1 2; do
  kubectl exec -n alphatrion clickhouse-$i -- sync
  # Then create AWS EBS snapshot of corresponding volume
done
```

### Restore

```bash
# Stop writes (optional)
kubectl scale statefulset clickhouse -n alphatrion --replicas=0

# Restore from backup
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query="RESTORE DATABASE alphatrion_traces FROM Disk('backups', 'backup-20240101')"

# Or restore from volume snapshot
# Restore PVCs from EBS snapshots, then restart pods
```

## Migration from Single Node

If you already have a single-node ClickHouse deployment:

### Option 1: Backup and Restore (Recommended)

```bash
# 1. Backup existing data
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query="BACKUP DATABASE alphatrion_traces TO Disk('backups', 'migration-backup')"

# 2. Export backup to local
kubectl exec -n alphatrion clickhouse-0 -- tar -czf /tmp/backup.tar.gz /var/lib/clickhouse/backups
kubectl cp alphatrion/clickhouse-0:/tmp/backup.tar.gz ./clickhouse-backup.tar.gz

# 3. Delete single-node deployment
kubectl delete -f ./helm-charts/clickhouse/clickhouse-statefulset.yaml
kubectl delete pvc -n alphatrion clickhouse-data-clickhouse-0

# 4. Deploy HA cluster
kubectl apply -f ./helm-charts/clickhouse/clickhouse-ha.yaml

# 5. Wait for cluster to be ready
kubectl wait --for=condition=ready pod -n alphatrion -l app=clickhouse --timeout=300s

# 6. Restore backup
kubectl cp ./clickhouse-backup.tar.gz alphatrion/clickhouse-0:/tmp/backup.tar.gz
kubectl exec -n alphatrion clickhouse-0 -- tar -xzf /tmp/backup.tar.gz -C /
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query="RESTORE DATABASE alphatrion_traces FROM Disk('backups', 'migration-backup')"
```

### Option 2: Direct Data Migration (Zero Downtime)

```bash
# 1. Deploy HA cluster alongside existing single node (use different namespace temporarily)
kubectl create namespace alphatrion-ha
# Edit clickhouse-ha.yaml to use alphatrion-ha namespace
kubectl apply -f ./helm-charts/clickhouse/clickhouse-ha.yaml

# 2. Use clickhouse-copier or remote() function to copy data
kubectl exec -n alphatrion-ha clickhouse-0 -- clickhouse-client --query="
INSERT INTO alphatrion_traces.traces
SELECT * FROM remote('clickhouse-0.clickhouse.alphatrion.svc.cluster.local:9000', 'alphatrion_traces', 'traces', 'alphatrion', 'alphatrion')"

# 3. Switch AlphaTrion connection to new cluster
# Update service discovery or change host in values.yaml

# 4. Delete old single-node deployment
kubectl delete -f ./helm-charts/clickhouse/clickhouse-statefulset.yaml
```

## Troubleshooting

### Pods Stuck in Pending

```bash
# Check PVC status
kubectl get pvc -n alphatrion

# Check node resources
kubectl describe nodes | grep -A 5 "Allocated resources"

# Check pod events
kubectl describe pod -n alphatrion clickhouse-0
```

### Replication Lag

```bash
# Check replication queue
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query "
SELECT
    database,
    table,
    is_currently_executing,
    num_tries,
    last_exception
FROM system.replication_queue
WHERE last_exception != ''"

# Force sync
kubectl exec -n alphatrion clickhouse-0 -- clickhouse-client --query "SYSTEM SYNC REPLICA alphatrion_traces.traces"
```

### Keeper Connection Issues

```bash
# Check Keeper logs
kubectl logs -n alphatrion clickhouse-keeper-0

# Test Keeper connectivity
kubectl exec -n alphatrion clickhouse-0 -- sh -c 'echo ruok | nc clickhouse-keeper-0.clickhouse-keeper.alphatrion.svc.cluster.local 2181'

# Check Keeper quorum
for i in 0 1 2; do
  echo "=== keeper-$i ==="
  kubectl exec -n alphatrion clickhouse-keeper-$i -- sh -c 'echo stat | nc localhost 2181'
done
```

### Split Brain

If you have quorum issues:

```bash
# Check Keeper leader
for i in 0 1 2; do
  echo "=== keeper-$i ==="
  kubectl exec -n alphatrion clickhouse-keeper-$i -- sh -c 'echo srvr | nc localhost 2181 | grep Mode'
done

# Should see: 1 leader, 2 followers
```

## Performance Tuning

### For High Throughput

Edit ConfigMap and increase:
```xml
<max_concurrent_queries>200</max_concurrent_queries>
<max_connections>2048</max_connections>
<background_pool_size>32</background_pool_size>
```

### For Large Datasets

```bash
# Increase storage
kubectl patch pvc clickhouse-data-clickhouse-0 -n alphatrion -p '{"spec":{"resources":{"requests":{"storage":"500Gi"}}}}'

# Adjust gp3 throughput
kubectl edit storageclass gp3
# Add: parameters.throughput: "500"
```

### Resource Allocation

```bash
# Update StatefulSet resources
kubectl edit statefulset clickhouse -n alphatrion

# Increase to:
resources:
  requests:
    cpu: 2000m
    memory: 8Gi
  limits:
    cpu: 4000m
    memory: 16Gi
```

## Security Considerations

1. **Change default password** - Update CLICKHOUSE_PASSWORD in the StatefulSet
2. **Use Kubernetes Secrets** - Store credentials in secrets instead of env vars
3. **Enable TLS** - Configure TLS for ClickHouse connections
4. **Network Policies** - Restrict traffic between pods
5. **RBAC** - Use ClickHouse users/roles for access control

Example with Secret:
```bash
kubectl create secret generic clickhouse-credentials \
  --namespace alphatrion \
  --from-literal=password='your-secure-password'

# Update StatefulSet to use secret
env:
- name: CLICKHOUSE_PASSWORD
  valueFrom:
    secretKeyRef:
      name: clickhouse-credentials
      key: password
```

## Cost Optimization

1. **Right-size resources** - Monitor actual usage and adjust requests/limits
2. **Use gp3 over gp2** - Better performance at lower cost
3. **Enable compression** - ClickHouse has excellent compression (already enabled by default)
4. **Data retention policies** - Implement TTL to automatically delete old data
5. **Spot instances** - Use spot instances for ClickHouse nodes in non-production

## Further Reading

- [ClickHouse Replication](https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/replication)
- [ClickHouse Keeper](https://clickhouse.com/docs/en/guides/sre/keeper/clickhouse-keeper)
- [ClickHouse Cluster](https://clickhouse.com/docs/en/architecture/cluster-deployment)
- [High Availability Best Practices](https://clickhouse.com/docs/en/guides/sre/ha)
