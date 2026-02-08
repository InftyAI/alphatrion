import { useParams } from 'react-router-dom';
import { useRun } from '../../hooks/use-runs';
import { useMetrics } from '../../hooks/use-metrics';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { formatDistanceToNow } from 'date-fns';
import type { Status } from '../../types';

const STATUS_VARIANTS: Record<Status, 'default' | 'secondary' | 'success' | 'warning' | 'destructive'> = {
  UNKNOWN: 'secondary',
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

  // Filter metrics for this specific run
  const runMetrics = metrics?.filter(m => m.runId === id) || [];

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
          <h1 className="text-xl font-bold text-foreground">
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
          <h3 className="text-sm font-semibold mb-3">Details</h3>
          <dl className="grid grid-cols-3 gap-3 text-sm">
            <div>
              <dt className="text-xs text-muted-foreground font-medium">Run ID</dt>
              <dd className="mt-1.5 text-foreground font-mono text-sm">{run.id}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground font-medium">Experiment ID</dt>
              <dd className="mt-1.5 text-foreground font-mono text-sm">{run.experimentId}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground font-medium">Project ID</dt>
              <dd className="mt-1.5 text-foreground font-mono text-sm">{run.projectId}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground font-medium">Team ID</dt>
              <dd className="mt-1.5 text-foreground font-mono text-sm">{run.teamId}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground font-medium">Created</dt>
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
              <h3 className="text-sm font-semibold mb-3">Metadata</h3>
              <dl className="grid grid-cols-3 gap-3 text-sm">
                {Object.entries(run.meta).map(([key, value]) => (
                  <div key={key}>
                    <dt className="text-xs text-muted-foreground font-medium">{key}</dt>
                    <dd className="mt-1.5 text-foreground font-mono text-sm">
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
          <h3 className="text-sm font-semibold mb-3">Metrics</h3>
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
                  <dt className="text-xs text-muted-foreground font-medium">{metric.key}</dt>
                  <dd className="mt-1.5 text-foreground font-mono text-sm">{metric.value}</dd>
                </div>
              ))}
            </dl>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
