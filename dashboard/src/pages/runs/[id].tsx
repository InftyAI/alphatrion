import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Database } from 'lucide-react';
import { useRun } from '../../hooks/use-runs';
import { formatDuration } from '../../lib/format';
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
import { formatDistanceToNow } from 'date-fns';
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
  const navigate = useNavigate();

  const { data: run, isLoading: runLoading, error: runError } = useRun(id!);

  const [activeTab, setActiveTab] = useState('overview');

  // Get metrics and traces from the nested run data
  const runMetrics = run?.metrics || [];
  const traces = run?.spans || [];
  const metricsLoading = runLoading;
  const tracesLoading = runLoading;
  const tracesError = runError;

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
    <div className="space-y-2">
      {/* Run Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">
            Run Details
          </h1>
          <p className="mt-0.5 text-muted-foreground font-mono text-xs">
            {run.id}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/datasets?runId=${run.id}`)}
            className="h-8 gap-2"
          >
            <Database className="h-3.5 w-3.5" />
            Datasets
          </Button>
          <Badge variant={STATUS_VARIANTS[run.status]}>
            {run.status}
          </Badge>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="traces">Traces</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-2">
          {/* Run Overview */}
          <Card>
        <CardContent className="p-3">
          <h3 className="text-sm font-semibold mb-2">Overview</h3>
          <dl className="grid grid-cols-3 gap-2 text-sm">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Total Tokens</dt>
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
                  formatDuration(run.duration)
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
            <div className="mt-3 pt-3 border-t">
              <h3 className="text-sm font-semibold mb-2">Metadata</h3>
              <dl className="grid grid-cols-3 gap-2 text-sm">
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
            <CardContent className="p-3">
              <h3 className="text-sm font-semibold mb-2">Metrics</h3>
              {metricsLoading ? (
                <Skeleton className="h-32 w-full" />
              ) : runMetrics.length === 0 ? (
                <div className="flex h-24 items-center justify-center text-xs text-muted-foreground">
                  No metrics logged for this run
                </div>
              ) : (
                <dl className="grid grid-cols-3 gap-2 text-sm">
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
              <CardContent className="p-3">
                <Skeleton className="h-64 w-full" />
              </CardContent>
            </Card>
          ) : tracesError ? (
            <Card>
              <CardContent className="p-3">
                <div className="text-red-500 text-xs">Error loading traces: {tracesError.message}</div>
              </CardContent>
            </Card>
          ) : traces && traces.length > 0 ? (
            <TraceTimeline spans={traces} />
          ) : (
            <Card>
              <CardContent className="p-3">
                <div className="flex h-24 items-center justify-center text-xs text-muted-foreground">
                  No traces available for this run
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
