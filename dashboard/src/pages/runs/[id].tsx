import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useRun } from '../../hooks/use-runs';
import { useArtifactContent } from '../../hooks/use-artifacts';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Skeleton } from '../../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { TraceTimeline } from '../../components/traces/trace-timeline';
import { ArtifactViewer } from '../../components/artifact-viewer';
import { formatDistanceToNow } from 'date-fns';
import { Eye } from 'lucide-react';
import type { Status } from '../../types';

const STATUS_VARIANTS: Record<Status, 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'unknown' | 'info'> = {
  UNKNOWN: 'unknown',
  PENDING: 'warning',
  RUNNING: 'info',
  CANCELLED: 'secondary',
  COMPLETED: 'success',
  FAILED: 'destructive',
};

export function RunDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: run, isLoading: runLoading, error: runError } = useRun(id!);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  // Get metrics and traces from the nested run data
  const runMetrics = run?.metrics || [];
  const traces = run?.spans || [];
  const metricsLoading = runLoading;
  const tracesLoading = runLoading;
  const tracesError = runError;

  // Check if execution result exists in metadata
  const executionResult = run?.meta?.execution_result as any;
  const hasExecutionResult = executionResult?.path && executionResult?.file_name;

  // Parse the path to extract the tag
  let artifactTag = '';
  if (hasExecutionResult) {
    let tag = executionResult.path;

    // If path contains ':', extract the part after the colon (the tag)
    if (tag.includes(':')) {
      tag = tag.split(':')[1];
    }

    // If path contains '/', it's a full path, extract just the tag part
    if (tag.includes('/')) {
      const parts = tag.split('/');
      tag = parts[parts.length - 1];
      if (tag.includes(':')) {
        tag = tag.split(':')[1];
      }
    }

    artifactTag = tag;
  }

  // Use the cached artifact content hook
  // Only fetch when dialog is open to avoid unnecessary requests
  // Repository name is just 'execution' - the backend prepends teamId
  const {
    data: artifactContent,
    isLoading: loadingArtifact,
    error: artifactError
  } = useArtifactContent(
    run?.teamId || '',
    artifactTag,
    'execution',
    dialogOpen && hasExecutionResult // Only fetch when dialog is open
  );

  const handleViewArtifact = () => {
    if (!hasExecutionResult || !run) return;
    setDialogOpen(true);
  };

  // Show error if artifact fetch fails
  if (artifactError && dialogOpen) {
    console.error('Failed to load artifact:', artifactError);
  }

  if (runLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (runError || !run) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Error</CardTitle>
          <CardDescription>Failed to load run</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-destructive">
            {runError?.message || 'Run not found'}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Run Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">
            Run Details
          </h1>
          <p className="mt-1 text-muted-foreground font-mono text-sm">
            {run.id}
          </p>
        </div>
        <Badge variant={STATUS_VARIANTS[run.status]}>
          {run.status}
        </Badge>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="traces">Traces</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          {/* Run Overview */}
          <Card>
        <CardContent className="p-4">
          <h3 className="text-base font-semibold mb-3">Overview</h3>
          <dl className="grid grid-cols-3 gap-3 text-sm">
            {hasExecutionResult && (
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Execution Result</dt>
                <dd className="mt-1.5 text-foreground text-sm">
                  <button
                    onClick={handleViewArtifact}
                    disabled={loadingArtifact}
                    className="inline-flex items-center gap-1.5 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    {executionResult.file_name}
                  </button>
                </dd>
              </div>
            )}
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Tokens</dt>
              <dd className="mt-1.5 text-foreground font-mono text-sm">
                {run.aggregatedTokens?.totalTokens !== undefined && run.aggregatedTokens.totalTokens > 0 ? (
                  <>
                    {Number(run.aggregatedTokens.totalTokens).toLocaleString()}
                    <span className="text-muted-foreground text-xs ml-1">
                      ({Number(run.aggregatedTokens.inputTokens || 0).toLocaleString()}↓ {Number(run.aggregatedTokens.outputTokens || 0).toLocaleString()}↑)
                    </span>
                  </>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Duration</dt>
              <dd className="mt-1.5 text-foreground font-mono text-sm">
                {run.duration !== undefined && run.duration > 0 ? (
                  `${run.duration.toFixed(2)}s`
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Created</dt>
              <dd className="mt-1.5 text-foreground text-sm">
                {formatDistanceToNow(new Date(run.createdAt), {
                  addSuffix: true,
                })}
              </dd>
            </div>
          </dl>


          {/* Metadata */}
          {run.meta && Object.keys(run.meta).filter(k => k !== 'execution_result').length > 0 && (
            <div className="mt-5 pt-5 border-t">
              <h3 className="text-base font-semibold mb-3">Metadata</h3>
              <dl className="grid grid-cols-3 gap-3 text-sm">
                {Object.entries(run.meta)
                  .filter(([key]) => key !== 'execution_result')
                  .map(([key, value]) => (
                    <div key={key} className="break-words">
                      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{key}</dt>
                      <dd className="mt-1.5 text-foreground font-mono text-sm break-all">
                        {typeof value === 'string' ? value : JSON.stringify(value)}
                      </dd>
                    </div>
                  ))}
              </dl>
            </div>
          )}
        </CardContent>
      </Card>

          {/* Metrics */}
          <Card>
            <CardContent className="p-4">
              <h3 className="text-base font-semibold mb-3">Metrics</h3>
              {metricsLoading ? (
                <Skeleton className="h-32 w-full" />
              ) : runMetrics.length === 0 ? (
                <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
                  No metrics logged for this run
                </div>
              ) : (
                <dl className="grid grid-cols-3 gap-3 text-sm">
                  {runMetrics.map((metric) => (
                    <div key={metric.id}>
                      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{metric.key}</dt>
                      <dd className="mt-1.5 text-foreground font-mono text-sm">{metric.value}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Traces Tab */}
        <TabsContent value="traces">
          {tracesLoading ? (
            <Card>
              <CardContent className="p-4">
                <Skeleton className="h-64 w-full" />
              </CardContent>
            </Card>
          ) : tracesError ? (
            <Card>
              <CardContent className="p-4">
                <div className="text-red-500">Error loading traces: {tracesError.message}</div>
              </CardContent>
            </Card>
          ) : traces && traces.length > 0 ? (
            <TraceTimeline spans={traces} />
          ) : (
            <Card>
              <CardContent className="p-4">
                <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
                  No traces available for this run
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Artifact Content Viewer */}
      <ArtifactViewer
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        artifactContent={artifactContent}
        isLoading={loadingArtifact}
        error={artifactError}
        title="Artifact Content"
        hideLineCount={true}
        hideCloseButton={true}
      />
    </div>
  );
}
