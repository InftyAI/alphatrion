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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';
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
    <div className="space-y-6">
      {/* Run Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
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
        <CardContent className="p-6 pt-6">
          <h3 className="text-sm font-semibold mb-4">Details</h3>
          <dl className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <dt className="font-medium text-muted-foreground">Run ID</dt>
              <dd className="mt-1 text-foreground font-mono">{run.id}</dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Experiment ID</dt>
              <dd className="mt-1 text-foreground font-mono">{run.experimentId}</dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Project ID</dt>
              <dd className="mt-1 text-foreground font-mono">{run.projectId}</dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Team ID</dt>
              <dd className="mt-1 text-foreground font-mono">{run.teamId}</dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Created</dt>
              <dd className="mt-1 text-foreground">
                {formatDistanceToNow(new Date(run.createdAt), {
                  addSuffix: true,
                })}
              </dd>
            </div>
          </dl>

          {/* Metadata */}
          {run.meta && Object.keys(run.meta).length > 0 && (
            <div className="mt-6 pt-6 border-t">
              <h3 className="text-sm font-semibold mb-4">Metadata</h3>
              <dl className="grid grid-cols-3 gap-4 text-sm">
                {Object.entries(run.meta).map(([key, value]) => (
                  <div key={key}>
                    <dt className="font-medium text-muted-foreground">{key}</dt>
                    <dd className="mt-1 text-foreground font-mono text-sm">
                      {JSON.stringify(value)}
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
        <CardHeader>
          <CardTitle>Metrics</CardTitle>
          <CardDescription>
            Metrics logged during this run
          </CardDescription>
        </CardHeader>
        <CardContent>
          {metricsLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : runMetrics.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              No metrics logged for this run
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Key</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runMetrics.map((metric) => (
                  <TableRow key={metric.id}>
                    <TableCell className="font-medium">{metric.key}</TableCell>
                    <TableCell className="font-mono">{metric.value}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDistanceToNow(new Date(metric.createdAt), {
                        addSuffix: true,
                      })}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
