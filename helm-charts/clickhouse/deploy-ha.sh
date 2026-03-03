#!/bin/bash
set -e

NAMESPACE="alphatrion"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "ClickHouse HA Deployment"
echo "=========================================="
echo ""

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo "❌ Namespace '$NAMESPACE' does not exist. Creating it..."
    kubectl create namespace "$NAMESPACE"
    echo "✅ Namespace created"
else
    echo "✅ Namespace '$NAMESPACE' exists"
fi

# Check if gp3 storage class exists
if ! kubectl get storageclass gp3 &> /dev/null; then
    echo ""
    echo "❌ Storage class 'gp3' not found. Creating it..."
    kubectl apply -f "$SCRIPT_DIR/storageclass-gp3.yaml"
    echo "✅ Storage class created"
else
    echo "✅ Storage class 'gp3' exists"
fi

echo ""
echo "Deploying ClickHouse HA cluster..."
echo "This will create:"
echo "  - 3 ClickHouse Keeper pods (coordination layer)"
echo "  - 3 ClickHouse Server pods (data layer)"
echo "  - Persistent storage: 30Gi for Keepers + 300Gi for servers"
echo ""

# Check if single-node deployment exists
if kubectl get statefulset clickhouse -n "$NAMESPACE" &> /dev/null; then
    echo ""
    echo "⚠️  WARNING: Found existing single-node ClickHouse deployment!"
    echo ""
    echo "You have two options:"
    echo "  1. Delete the single-node deployment (DELETES ALL DATA)"
    echo "  2. Cancel and migrate data first (see HA-SETUP.md)"
    echo ""
    read -p "Delete existing deployment? (yes/no): " confirm
    if [[ "$confirm" == "yes" ]]; then
        echo "Deleting single-node deployment..."
        kubectl delete -f "$SCRIPT_DIR/clickhouse-statefulset.yaml" || true
        read -p "Delete PVC and ALL DATA? (yes/no): " confirm_data
        if [[ "$confirm_data" == "yes" ]]; then
            kubectl delete pvc -n "$NAMESPACE" clickhouse-data-clickhouse-0 || true
            echo "✅ Existing deployment deleted"
        fi
    else
        echo "❌ Deployment cancelled. Please migrate data first."
        echo "See: $SCRIPT_DIR/HA-SETUP.md"
        exit 1
    fi
fi

# Deploy HA cluster
echo ""
echo "Applying HA configuration..."
kubectl apply -f "$SCRIPT_DIR/clickhouse-ha.yaml"

echo ""
echo "Waiting for ClickHouse Keeper pods to be ready..."
echo "(This may take 1-2 minutes)"
kubectl wait --for=condition=ready pod \
    -l app=clickhouse-keeper \
    -n "$NAMESPACE" \
    --timeout=300s || echo "⚠️  Keeper pods not ready yet, continuing..."

echo ""
echo "Waiting for ClickHouse pods to be ready..."
echo "(This may take 2-3 minutes)"
kubectl wait --for=condition=ready pod \
    -l app=clickhouse \
    -n "$NAMESPACE" \
    --timeout=300s || echo "⚠️  ClickHouse pods not ready yet"

echo ""
echo "=========================================="
echo "Deployment Status"
echo "=========================================="
echo ""

echo "Keeper Pods:"
kubectl get pods -n "$NAMESPACE" -l app=clickhouse-keeper

echo ""
echo "ClickHouse Pods:"
kubectl get pods -n "$NAMESPACE" -l app=clickhouse

echo ""
echo "Persistent Volumes:"
kubectl get pvc -n "$NAMESPACE"

echo ""
echo "=========================================="
echo "Verifying Cluster"
echo "=========================================="

# Wait a bit more for services to fully start
sleep 10

# Check cluster status
echo ""
echo "Cluster Configuration:"
kubectl exec -n "$NAMESPACE" clickhouse-0 -- clickhouse-client --query \
    "SELECT cluster, shard_num, replica_num, host_name FROM system.clusters WHERE cluster='alphatrion_cluster'" \
    2>/dev/null || echo "⚠️  Cluster not fully ready yet"

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Verify cluster health:"
echo "   kubectl exec -n $NAMESPACE clickhouse-0 -- clickhouse-client --query \"SELECT * FROM system.clusters WHERE cluster='alphatrion_cluster'\""
echo ""
echo "2. Create replicated tables:"
echo "   kubectl exec -it -n $NAMESPACE clickhouse-0 -- clickhouse-client"
echo "   Then run: CREATE TABLE ... ENGINE = ReplicatedMergeTree(...)"
echo ""
echo "3. Connect AlphaTrion to the cluster:"
echo "   helm upgrade alphatrion ./helm-charts/alphatrion \\"
echo "     -f ./helm-charts/alphatrion/values-with-clickhouse.yaml"
echo ""
echo "4. Monitor the cluster:"
echo "   kubectl get pods -n $NAMESPACE -w"
echo ""
echo "For detailed HA setup guide, see: $SCRIPT_DIR/HA-SETUP.md"
echo ""
