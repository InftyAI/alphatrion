import { useState, useEffect } from 'react';
import {
  Laptop,
  Container,
  CheckCircle,
  XCircle,
  Clock,
  Play,
  Trash2,
  RefreshCw,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';

type WorkspaceMode = 'local' | 'k8s';

interface PodInfo {
  name: string;
  phase: string;
  ready: boolean;
  status: string;
  error?: string;
  created_at?: string;
}

export function WorkspacePage() {
  const [mode, setMode] = useState<WorkspaceMode>('local');
  const [k8sAvailable, setK8sAvailable] = useState<boolean | null>(null);
  const [pods, setPods] = useState<PodInfo[]>([]);
  const [selectedPod, setSelectedPod] = useState<string | null>(null);
  const [newPodName, setNewPodName] = useState('');
  const [newPodImage, setNewPodImage] = useState('python:3.12-slim');
  const [loading, setLoading] = useState(false);

  // Check K8s availability
  useEffect(() => {
    const checkK8s = async () => {
      try {
        const response = await fetch('/api/plugins/cloud-ide/k8s/available');
        const data = await response.json();
        setK8sAvailable(data.available);
      } catch (error) {
        console.error('Error checking K8s availability:', error);
        setK8sAvailable(false);
      }
    };

    checkK8s();
  }, []);

  // Load pods when in K8s mode
  useEffect(() => {
    if (mode === 'k8s' && k8sAvailable) {
      loadPods();
    }
  }, [mode, k8sAvailable]);

  const loadPods = async () => {
    try {
      const response = await fetch('/api/plugins/cloud-ide/k8s/pods/list');
      const data = await response.json();
      setPods(data.pods || []);
    } catch (error) {
      console.error('Error loading pods:', error);
    }
  };

  const deployPod = async () => {
    if (!newPodName || !newPodImage) {
      alert('Please provide pod name and image');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/plugins/cloud-ide/k8s/pods/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newPodName,
          image: newPodImage,
          resources: {
            requests: { cpu: '100m', memory: '256Mi' },
            limits: { cpu: '2', memory: '4Gi' },
          },
        }),
      });

      const data = await response.json();
      if (data.success) {
        alert(`Pod deployed: ${data.pod_name}`);
        setNewPodName('');
        await loadPods();
      }
    } catch (error) {
      console.error('Error deploying pod:', error);
      alert(`Error: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const deletePod = async (podName: string) => {
    if (!confirm(`Delete pod ${podName}?`)) return;

    try {
      const response = await fetch(`/api/plugins/cloud-ide/k8s/pods/${podName}`, {
        method: 'DELETE',
      });

      const data = await response.json();
      if (data.success) {
        alert('Pod deleted');
        await loadPods();
      }
    } catch (error) {
      console.error('Error deleting pod:', error);
      alert(`Error: ${error}`);
    }
  };

  const refreshPodStatus = async (podName: string) => {
    try {
      const response = await fetch(`/api/plugins/cloud-ide/k8s/pods/${podName}/status`);
      const data = await response.json();

      // Update pod in list
      setPods(pods.map(p => p.name === podName ? data : p));
    } catch (error) {
      console.error('Error refreshing pod status:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'pending':
      case 'running':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <XCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  // Open local workspace in new window
  const openLocalWorkspace = () => {
    // In production: /static/ide.html, in dev: use relative path
    const ideUrl = import.meta.env.DEV
      ? '/ide.html'
      : '/static/ide.html';
    window.open(ideUrl, '_blank', 'width=1400,height=900');
  };

  // Open pod workspace in new window
  const openPodWorkspace = (podName: string) => {
    setSelectedPod(podName);
    const ideUrl = import.meta.env.DEV
      ? `/ide.html?pod=${podName}`
      : `/static/ide.html?pod=${podName}`;
    window.open(ideUrl, '_blank', 'width=1400,height=900');
  };

  return (
    <div className="flex flex-col h-full p-6 gap-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Cloud IDE</h1>
        <p className="text-muted-foreground mt-1">
          Choose your development environment: local workspace or Kubernetes sandbox
        </p>
      </div>

      {/* Mode Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Workspace Mode</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Button
              variant={mode === 'local' ? 'default' : 'outline'}
              className="flex-1 gap-2"
              onClick={() => setMode('local')}
            >
              <Laptop className="h-5 w-5" />
              Local Workspace
            </Button>
            <Button
              variant={mode === 'k8s' ? 'default' : 'outline'}
              className="flex-1 gap-2"
              onClick={() => setMode('k8s')}
              disabled={k8sAvailable === false}
            >
              <Container className="h-5 w-5" />
              K8s Sandbox
              {k8sAvailable === false && (
                <Badge variant="secondary" className="ml-2">Unavailable</Badge>
              )}
            </Button>
          </div>
          {k8sAvailable === false && (
            <p className="text-sm text-muted-foreground mt-2">
              Kubernetes is not configured. Set K8S_KUBECONFIG or configure GKE credentials to enable sandbox mode.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Local Workspace Mode */}
      {mode === 'local' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Laptop className="h-5 w-5" />
              Local Workspace
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Work with files on the local server filesystem. Perfect for development and testing.
            </p>
            <Button onClick={openLocalWorkspace} className="gap-2">
              <Play className="h-4 w-4" />
              Open Local IDE
            </Button>
          </CardContent>
        </Card>
      )}

      {/* K8s Sandbox Mode */}
      {mode === 'k8s' && k8sAvailable && (
        <>
          {/* Deploy New Pod */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Container className="h-5 w-5" />
                Deploy New Sandbox
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-3">
                <Input
                  placeholder="Pod name (e.g., my-experiment)"
                  value={newPodName}
                  onChange={(e) => setNewPodName(e.target.value)}
                  className="flex-1"
                />
                <Input
                  placeholder="Docker image (e.g., python:3.12-slim)"
                  value={newPodImage}
                  onChange={(e) => setNewPodImage(e.target.value)}
                  className="flex-1"
                />
                <Button
                  onClick={deployPod}
                  disabled={loading || !newPodName || !newPodImage}
                  className="gap-2"
                >
                  <Play className="h-4 w-4" />
                  Deploy
                </Button>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                Default resources: 100m CPU / 256Mi memory (request), 2 CPU / 4Gi memory (limit)
              </p>
            </CardContent>
          </Card>

          {/* Active Pods */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Active Sandboxes</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={loadPods}
                  className="gap-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  Refresh
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {pods.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No active sandbox pods. Deploy one above to get started.
                </div>
              ) : (
                <div className="space-y-3">
                  {pods.map((pod) => (
                    <div
                      key={pod.name}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"
                    >
                      <div className="flex items-center gap-3 flex-1">
                        {getStatusIcon(pod.status)}
                        <div>
                          <p className="font-medium">{pod.name}</p>
                          <p className="text-sm text-muted-foreground">
                            Phase: {pod.phase} {pod.error && `(${pod.error})`}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <Badge variant={pod.ready ? 'default' : 'secondary'}>
                          {pod.status}
                        </Badge>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => refreshPodStatus(pod.name)}
                          title="Refresh status"
                        >
                          <RefreshCw className="h-4 w-4" />
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openPodWorkspace(pod.name)}
                          disabled={!pod.ready}
                          title="Open workspace"
                        >
                          <Play className="h-4 w-4" />
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deletePod(pod.name)}
                          title="Delete pod"
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* Usage Instructions */}
      <Card>
        <CardHeader>
          <CardTitle>About Cloud IDE</CardTitle>
        </CardHeader>
        <CardContent className="prose prose-sm max-w-none">
          <p>The Cloud IDE provides two modes of operation:</p>

          <h4 className="text-sm font-semibold mt-3 mb-1">Local Workspace</h4>
          <ul className="text-sm">
            <li>Edit files directly on the server filesystem</li>
            <li>Access to local terminal and environment</li>
            <li>Resource monitoring (CPU, memory, disk)</li>
            <li>Perfect for development and quick testing</li>
          </ul>

          <h4 className="text-sm font-semibold mt-3 mb-1">K8s Sandbox</h4>
          <ul className="text-sm">
            <li>Deploy isolated sandbox pods with custom Docker images</li>
            <li>Each pod runs in a separate Kubernetes container</li>
            <li>Ideal for experiment evaluation and reproducible environments</li>
            <li>Automatic cleanup and resource management</li>
          </ul>

          <p className="text-sm text-muted-foreground mt-4">
            <strong>Note:</strong> K8s Sandbox requires Kubernetes configuration via K8S_KUBECONFIG,
            GKE_CLUSTER_ENDPOINT/GKE_CLUSTER_CA environment variables, or in-cluster configuration.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
