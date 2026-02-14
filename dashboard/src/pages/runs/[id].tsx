import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useRun } from '../../hooks/use-runs';
import { useMetrics } from '../../hooks/use-metrics';
import { useArtifactContent } from '../../hooks/use-artifacts';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Skeleton } from '../../components/ui/skeleton';
import { formatDistanceToNow } from 'date-fns';
import { Eye, Copy, Check } from 'lucide-react';
import type { Status } from '../../types';

const STATUS_VARIANTS: Record<Status, 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'unknown'> = {
  UNKNOWN: 'unknown',
  PENDING: 'warning',
  RUNNING: 'default',
  CANCELLED: 'secondary',
  COMPLETED: 'success',
  FAILED: 'destructive',
};

export function RunDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: run, isLoading: runLoading, error: runError } = useRun(id!);
  const { data: metrics, isLoading: metricsLoading } = useMetrics(run?.experimentId || '');

  const [dialogOpen, setDialogOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  // Filter metrics for this specific run
  const runMetrics = metrics?.filter(m => m.runId === id) || [];

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
  const {
    data: artifactContent,
    isLoading: loadingArtifact,
    error: artifactError
  } = useArtifactContent(
    run?.teamId || '',
    run?.projectId || '',
    artifactTag,
    'execution',
    dialogOpen && hasExecutionResult // Only fetch when dialog is open
  );

  const handleViewArtifact = () => {
    if (!hasExecutionResult || !run) return;
    setCopied(false);
    setDialogOpen(true);
  };

  // Show error if artifact fetch fails
  if (artifactError && dialogOpen) {
    console.error('Failed to load artifact:', artifactError);
  }

  const handleCopy = () => {
    if (artifactContent?.content) {
      navigator.clipboard.writeText(artifactContent.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatContent = () => {
    if (!artifactContent) return '';

    const { content, filename, contentType } = artifactContent;

    // Try to parse and format JSON
    if (contentType === 'application/json' || filename.endsWith('.json')) {
      try {
        const parsed = JSON.parse(content);
        return JSON.stringify(parsed, null, 2);
      } catch {
        return content;
      }
    }

    return content;
  };

  const getLanguageClass = () => {
    if (!artifactContent) return '';

    const { filename, contentType } = artifactContent;

    if (contentType === 'application/json' || filename.endsWith('.json')) {
      return 'language-json';
    }
    return '';
  };

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
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
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

      {/* Run Details */}
      <Card>
        <CardContent className="p-4">
          <h3 className="text-base font-semibold mb-3">Details</h3>
          <dl className="grid grid-cols-3 gap-3 text-sm">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Execution Result</dt>
              <dd className="mt-1.5 text-foreground text-sm">
                {hasExecutionResult ? (
                  <button
                    onClick={handleViewArtifact}
                    disabled={loadingArtifact}
                    className="inline-flex items-center gap-1.5 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    {executionResult.file_name}
                  </button>
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
          {run.meta && Object.keys(run.meta).length > 0 && (
            <div className="mt-5 pt-5 border-t">
              <h3 className="text-base font-semibold mb-3">Metadata</h3>
              <dl className="grid grid-cols-3 gap-3 text-sm">
                {Object.entries(run.meta).map(([key, value]) => (
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

      {/* Artifact Content Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[85vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <DialogTitle className="text-base">Artifact Content</DialogTitle>
                <DialogDescription className="text-xs font-mono mt-1 truncate">
                  {artifactContent?.filename || 'Loading...'}
                </DialogDescription>
              </div>
              {artifactContent && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopy}
                  className="ml-2 h-8 flex-shrink-0"
                >
                  {copied ? (
                    <>
                      <Check className="h-3.5 w-3.5 mr-1.5" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5 mr-1.5" />
                      Copy
                    </>
                  )}
                </Button>
              )}
            </div>
          </DialogHeader>
          <div className="flex-1 overflow-auto border rounded-md bg-slate-950 dark:bg-slate-950">
            {loadingArtifact && !artifactContent ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-slate-400 text-sm">Loading artifact...</div>
              </div>
            ) : artifactError ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-red-400 text-sm">Failed to load artifact</div>
              </div>
            ) : (
              <pre className={`text-xs p-4 overflow-auto text-slate-50 ${getLanguageClass()}`}>
                <code className="text-slate-50">{formatContent()}</code>
              </pre>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
