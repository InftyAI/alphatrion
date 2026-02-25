# Enhanced Cloud IDE Plugin

The Cloud IDE plugin now supports two modes of operation: **Local Workspace** and **K8s Sandbox**, providing flexibility for different development and evaluation scenarios.

## Overview

The enhanced Cloud IDE integrates:
- **Local Workspace**: Direct access to the server's local filesystem
- **K8s Sandbox**: Isolated Kubernetes-based development environments

This dual-mode architecture allows users to choose the right environment for their needs while maintaining a unified interface.

## Architecture

```
alphatrion/plugins/workspace/
├── __init__.py              # Package exports
├── plugin.py                # Main plugin with both local and K8s APIs
├── k8s_pod.py              # Kubernetes pod management
└── k8s_terminal.py         # K8s terminal and file operations
```

## Modes

### 1. Local Workspace Mode

**Use Cases:**
- Development and debugging
- Quick file editing
- Direct access to server resources
- Local environment testing

**Features:**
- File tree browsing
- Code editor with syntax highlighting
- Local terminal execution
- Resource monitoring (CPU, memory, disk, GPU)
- File create/delete/rename operations

**API Endpoints:**
- `GET /api/plugins/cloud-ide/files/tree` - Get file tree
- `GET /api/plugins/cloud-ide/files/content` - Read file
- `POST /api/plugins/cloud-ide/files/save` - Save file
- `POST /api/plugins/cloud-ide/files/create` - Create file/directory
- `POST /api/plugins/cloud-ide/files/delete` - Delete file
- `POST /api/plugins/cloud-ide/files/rename` - Rename file
- `POST /api/plugins/cloud-ide/terminal/execute` - Execute command
- `GET /api/plugins/cloud-ide/environment/info` - Get environment info
- `GET /api/plugins/cloud-ide/environment/packages` - List packages
- `GET /api/plugins/cloud-ide/resources/status` - Get resource usage

### 2. K8s Sandbox Mode

**Use Cases:**
- Experiment evaluation in isolated environments
- Reproducible development environments
- Multi-user sandboxes
- Custom Docker image testing

**Features:**
- Deploy pods with custom Docker images
- Pod lifecycle management (deploy, status, delete)
- List all active sandbox pods
- Execute commands in pods
- Read/write files to pods
- Interactive terminal access via WebSocket
- Automatic pod labeling and organization

**API Endpoints:**
- `GET /api/plugins/cloud-ide/k8s/available` - Check K8s availability
- `POST /api/plugins/cloud-ide/k8s/pods/deploy` - Deploy a pod
- `GET /api/plugins/cloud-ide/k8s/pods/list` - List all pods
- `GET /api/plugins/cloud-ide/k8s/pods/{pod_name}/status` - Get pod status
- `DELETE /api/plugins/cloud-ide/k8s/pods/{pod_name}` - Delete pod
- `GET /api/plugins/cloud-ide/k8s/pods/{pod_name}/files/list` - List files in pod
- `POST /api/plugins/cloud-ide/k8s/pods/{pod_name}/files/read` - Read file from pod
- `POST /api/plugins/cloud-ide/k8s/pods/{pod_name}/files/write` - Write file to pod
- `POST /api/plugins/cloud-ide/k8s/pods/{pod_name}/terminal/execute` - Execute command
- `WS /api/plugins/cloud-ide/k8s/pods/{pod_name}/terminal` - WebSocket terminal

## Configuration

### Local Workspace

Set via plugin initialization config or environment variable:
```python
cloud_ide.initialize({
    "workspace_root": "/path/to/workspace"
})
```

Default: `~/alphatrion-workspace`

### K8s Sandbox

Requires one of:
1. **Kubeconfig file**:
   ```bash
   export K8S_KUBECONFIG=/path/to/kubeconfig
   ```

2. **GKE credentials**:
   ```bash
   export GKE_CLUSTER_ENDPOINT=<cluster-endpoint>
   export GKE_CLUSTER_CA=<base64-ca-cert>
   ```

3. **Default kubeconfig**: `~/.kube/config`

4. **In-cluster config**: Automatic when running inside K8s

Optional:
```bash
export K8S_NAMESPACE=default  # Namespace for sandbox pods
```

## Frontend UI

The Cloud IDE frontend provides:

### Mode Selector
- Switch between Local and K8s modes
- Visual indicators for K8s availability
- Automatic detection of K8s configuration

### Local Workspace View
- Click "Open Local IDE" to access the full local workspace interface
- Maintains all existing local workspace features

### K8s Sandbox View
- **Deploy Panel**: Create new sandbox pods with custom names and images
- **Active Pods List**: View all running sandboxes
  - Pod status indicators (ready, pending, failed)
  - Refresh individual pod status
  - Open pod workspace (future: integrated file browser)
  - Delete pods
- **Resource Configuration**: Default CPU/memory limits shown

## Usage Examples

### Deploy a Python Sandbox

```bash
curl -X POST http://localhost:8000/api/plugins/cloud-ide/k8s/pods/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-experiment",
    "image": "python:3.12-slim",
    "resources": {
      "requests": {"cpu": "100m", "memory": "256Mi"},
      "limits": {"cpu": "2", "memory": "4Gi"}
    }
  }'
```

Response:
```json
{
  "success": true,
  "pod_name": "cloud-ide-my-experiment"
}
```

### Check Pod Status

```bash
curl http://localhost:8000/api/plugins/cloud-ide/k8s/pods/cloud-ide-my-experiment/status
```

Response:
```json
{
  "pod_name": "cloud-ide-my-experiment",
  "phase": "Running",
  "ready": true,
  "status": "ready",
  "error": null
}
```

### Write File to Pod

```bash
curl -X POST http://localhost:8000/api/plugins/cloud-ide/k8s/pods/cloud-ide-my-experiment/files/write \
  -H "Content-Type: application/json" \
  -d '{
    "pod_name": "cloud-ide-my-experiment",
    "path": "/workspace/main.py",
    "content": "print(\"Hello from K8s!\")"
  }'
```

### Execute Command in Pod

```bash
curl -X POST http://localhost:8000/api/plugins/cloud-ide/k8s/pods/cloud-ide-my-experiment/terminal/execute \
  -H "Content-Type: application/json" \
  -d '{
    "command": "python /workspace/main.py"
  }'
```

Response:
```json
{
  "stdout": "Hello from K8s!\n",
  "stderr": "",
  "returncode": 0
}
```

### List All Active Sandboxes

```bash
curl http://localhost:8000/api/plugins/cloud-ide/k8s/pods/list
```

Response:
```json
{
  "pods": [
    {
      "name": "cloud-ide-my-experiment",
      "phase": "Running",
      "ready": true,
      "status": "ready",
      "created_at": "2024-02-24T10:30:00Z"
    }
  ]
}
```

### Interactive Terminal (WebSocket)

```javascript
const ws = new WebSocket(
  'ws://localhost:8000/api/plugins/cloud-ide/k8s/pods/cloud-ide-my-experiment/terminal'
);

ws.onopen = () => {
  console.log('Terminal connected');
  ws.send('ls -la\n');
  ws.send('python --version\n');
};

ws.onmessage = (event) => {
  console.log('Output:', event.data);
};
```

## Migration from Forked Project

The K8s functionality was migrated from the forked project with these changes:

1. **Integration**: Merged into Cloud IDE plugin instead of separate plugin
2. **Dual Mode**: Added local/K8s mode switcher
3. **Data Model**: Removed `trial_id` references (now uses `experiment_id`)
4. **Container Name**: Changed from "sandbox" to "workspace" for consistency
5. **Pod Prefix**: Changed from "sandbox-eval-" to "cloud-ide-"
6. **Pod Labels**: Changed purpose label from "evaluation" to "cloud-ide"
7. **Graceful Degradation**: K8s features fail gracefully if not configured

## Benefits

### Unified Interface
- Single plugin for both local and remote development
- Consistent API structure
- Shared UI components

### Flexibility
- Choose the right environment for each task
- Easy switching between modes
- No separate plugin management

### Scalability
- K8s provides automatic resource management
- Pods can be distributed across cluster nodes
- Isolated environments prevent conflicts

### Security
- Pods run in isolated namespaces
- Resource limits prevent resource exhaustion
- File access restricted to pod containers

## Future Enhancements

1. **Integrated Pod File Browser**
   - Show pod filesystem in the IDE
   - Edit pod files directly in the UI
   - Drag-and-drop file uploads

2. **Pod Templates**
   - Pre-configured templates for common languages
   - One-click deployment for Python, Node.js, Go, etc.

3. **Experiment Integration**
   - Launch sandbox from experiment detail page
   - Auto-deploy with experiment configuration
   - Link pod lifecycle to experiment lifecycle

4. **Persistent Volumes**
   - Optional PVC mounting for data persistence
   - Share data between pod restarts

5. **GPU Support**
   - NVIDIA GPU resource requests
   - GPU-enabled images for ML workloads

6. **Multi-Pod Environments**
   - Deploy multiple connected pods (e.g., app + database)
   - Service mesh integration

7. **Resource Quotas**
   - Namespace-level resource limits
   - Per-user quota management

8. **Auto-Cleanup**
   - TTL-based pod deletion
   - Automatic cleanup of failed pods

## Dependencies

- **kubernetes>=31.0.0**: K8s Python client (optional for K8s mode)
- **psutil>=7.0.0**: Resource monitoring (for local mode)
- **google-auth** (optional): For GKE authentication

## Security Considerations

1. **Namespace Isolation**: All pods deployed in configurable namespace
2. **Resource Limits**: Default CPU/memory limits prevent resource abuse
3. **Pod Labels**: All pods labeled with `purpose: cloud-ide` for tracking
4. **File Access**: Pod file operations sandboxed to container filesystem
5. **Network Policies**: Consider applying K8s NetworkPolicies to sandbox namespace
6. **RBAC**: Ensure service account has appropriate pod creation permissions

## Troubleshooting

### K8s Mode Not Available

**Symptom**: K8s mode shows as unavailable

**Solutions**:
1. Check K8s configuration:
   ```bash
   kubectl cluster-info
   ```

2. Verify environment variables:
   ```bash
   echo $K8S_KUBECONFIG
   echo $GKE_CLUSTER_ENDPOINT
   echo $GKE_CLUSTER_CA
   ```

3. Test K8s connectivity:
   ```bash
   curl http://localhost:8000/api/plugins/cloud-ide/k8s/available
   ```

### Pod Stuck in Pending

**Causes**:
- Insufficient cluster resources
- Image pull errors
- Node selector constraints

**Solutions**:
1. Check pod status:
   ```bash
   kubectl describe pod <pod-name>
   ```

2. Check node resources:
   ```bash
   kubectl top nodes
   ```

### Terminal Connection Fails

**Causes**:
- Pod not ready
- Container not running
- WebSocket connection issues

**Solutions**:
1. Verify pod is ready:
   ```bash
   curl http://localhost:8000/api/plugins/cloud-ide/k8s/pods/<pod-name>/status
   ```

2. Check pod logs:
   ```bash
   kubectl logs <pod-name>
   ```

3. Test with simple exec:
   ```bash
   kubectl exec <pod-name> -- echo "test"
   ```

## Summary

The enhanced Cloud IDE plugin provides a powerful, flexible development environment that combines the simplicity of local workspace editing with the scalability and isolation of Kubernetes sandboxes. Users can seamlessly switch between modes based on their needs, all within a unified interface.
