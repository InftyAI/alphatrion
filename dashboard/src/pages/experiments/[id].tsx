import { useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import { useExperiment } from '../../hooks/use-experiments';
import { useRunStatistics, useRunDurations } from '../../hooks/use-run-statistics';
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
import { formatDistanceToNow } from 'date-fns';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, ReferenceLine } from 'recharts';
import type { Status } from '../../types';
import { formatDuration } from '../../lib/format';

const STATUS_VARIANTS: Record<Status, 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'unknown' | 'info'> = {
  UNKNOWN: 'unknown',
  PENDING: 'warning',
  RUNNING: 'info',
  CANCELLED: 'secondary',
  COMPLETED: 'success',
  FAILED: 'destructive',
};

export function ExperimentDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: experiment, isLoading: experimentLoading, error: experimentError } = useExperiment(id!);

  // Fetch run statuses for statistics - optimized to only fetch status field
  const { data: runStatuses } = useRunStatistics(id!);

  // Fetch run durations for calculating average iteration time
  const { data: runDurations } = useRunDurations(id!);

  // Calculate run statistics for pie chart - optimized to single pass
  const runStatsData = useMemo(() => {
    if (!runStatuses || runStatuses.length === 0) return [];

    // Single pass through the array instead of 6 separate filter operations
    const counts = runStatuses.reduce((acc, run) => {
      acc[run.status] = (acc[run.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const stats = [
      { name: 'COMPLETED', value: counts.COMPLETED || 0, color: '#22c55e' },
      { name: 'RUNNING', value: counts.RUNNING || 0, color: '#3b82f6' },
      { name: 'FAILED', value: counts.FAILED || 0, color: '#ef4444' },
      { name: 'PENDING', value: counts.PENDING || 0, color: '#eab308' },
      { name: 'CANCELLED', value: counts.CANCELLED || 0, color: '#6b7280' },
      { name: 'UNKNOWN', value: counts.UNKNOWN || 0, color: '#a78bfa' },
    ];

    return stats.filter(s => s.value > 0);
  }, [runStatuses]);

  // Prepare iteration duration data for chart
  const iterationDurationData = useMemo(() => {
    if (!runDurations || runDurations.length === 0) return [];

    const completedRuns = runDurations
      .map((run, index) => ({
        iteration: index + 1,
        duration: run.status === 'COMPLETED' && run.duration > 0 ? run.duration : null,
        status: run.status,
      }))
      .filter(run => run.duration !== null);

    return completedRuns;
  }, [runDurations]);

  // Calculate statistics for display
  const iterationStats = useMemo(() => {
    if (iterationDurationData.length === 0) return null;

    const durations = iterationDurationData.map(d => d.duration!);
    const mean = durations.reduce((sum, d) => sum + d, 0) / durations.length;

    const sorted = [...durations].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 === 0
      ? (sorted[mid - 1] + sorted[mid]) / 2
      : sorted[mid];

    return { mean, median };
  }, [iterationDurationData]);

  if (experimentLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (experimentError || !experiment) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Error</CardTitle>
          <CardDescription>Failed to load experiment</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-destructive">
            {experimentError?.message || 'Experiment not found'}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Experiment Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-baseline gap-3">
              <h1 className="text-xl font-semibold tracking-tight text-foreground">
                {experiment.name}
              </h1>
              <Button
                variant="default"
                size="sm"
                className="h-6 px-2.5 text-xs bg-blue-500 hover:bg-blue-600 text-white"
                asChild
              >
                <Link to={`/experiments/${id}/tracker`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1">
                  <ExternalLink className="h-3 w-3" />
                  <span>Track Progress</span>
                </Link>
              </Button>
            </div>
            <p className="mt-0.5 text-muted-foreground font-mono text-sm">
              {experiment.id}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {runStatuses && runStatuses.length > 0 && (
            <div className="text-sm text-muted-foreground">
              <span className="font-medium">{runStatuses.length}</span> iterations
            </div>
          )}
          <Badge variant={STATUS_VARIANTS[experiment.status]}>
            {experiment.status}
          </Badge>
        </div>
      </div>

      {/* Experiment Details */}
      <Card>
            <CardContent className="p-4">
              <h3 className="text-base font-semibold mb-3">Details</h3>
              <dl className="grid grid-cols-4 gap-3 text-sm">
                {experiment.description && (
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Description</dt>
                    <dd className="mt-1.5 text-foreground text-sm">{experiment.description}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Duration</dt>
                  <dd className="mt-1.5 text-foreground text-sm">
                    {experiment.duration > 0
                      ? formatDuration(experiment.duration)
                      : '-'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Created</dt>
                  <dd className="mt-1.5 text-foreground text-sm">
                    {formatDistanceToNow(new Date(experiment.createdAt), {
                      addSuffix: true,
                    })}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Updated</dt>
                  <dd className="mt-1.5 text-foreground text-sm">
                    {formatDistanceToNow(new Date(experiment.updatedAt), {
                      addSuffix: true,
                    })}
                  </dd>
                </div>
              </dl>

              {/* Metadata Section */}
              {experiment.meta && Object.keys(experiment.meta).length > 0 && (
                <div className="mt-5 pt-5 border-t">
                  <h3 className="text-base font-semibold mb-3">Metadata</h3>
                  <dl className="grid grid-cols-4 gap-3 text-sm">
                    {Object.entries(experiment.meta).map(([key, value]) => (
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

              {/* Parameters Section */}
              {experiment.params && Object.keys(experiment.params).length > 0 && (
                <div className="mt-5 pt-5 border-t">
                  <h3 className="text-base font-semibold mb-3">Parameters</h3>
                  <dl className="grid grid-cols-4 gap-3 text-sm">
                    {Object.entries(experiment.params).map(([key, value]) => (
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

              {/* Statistics Section */}
              {runStatuses && runStatuses.length > 0 && runStatsData.length > 0 && (
                <div className="mt-5 pt-5 border-t">
                  <h3 className="text-base font-semibold mb-6">
                    Statistics
                  </h3>
                  <div className="grid grid-cols-2 gap-6">
                    {/* Iteration Status Pie Chart */}
                    <div>
                      <h4 className="text-sm font-medium mb-3 text-muted-foreground">
                        Iteration Status
                        <span className="ml-2 text-xs font-normal">
                          ({runStatuses.length} total)
                        </span>
                      </h4>
                      <ResponsiveContainer width="100%" height={240}>
                        <PieChart margin={{ top: 10, bottom: 5 }}>
                          <Pie
                            data={runStatsData}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="45%"
                            outerRadius={60}
                            label={({ name, value }) => `${name}: ${value}`}
                            style={{ fontSize: '10px' }}
                          >
                            {runStatsData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip
                            contentStyle={{
                              fontSize: '10px',
                              backgroundColor: 'hsl(var(--card))',
                              border: '1px solid hsl(var(--border))',
                              borderRadius: '6px',
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: '10px' }} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Iteration Duration Bar Chart */}
                    {iterationDurationData.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium mb-3 text-muted-foreground">
                          Iteration Duration
                          {iterationStats && (
                            <span className="ml-2 text-xs font-normal">
                              • Mean: {formatDuration(iterationStats.mean)} • Median: {formatDuration(iterationStats.median)}
                            </span>
                          )}
                        </h4>
                        <ResponsiveContainer width="100%" height={240}>
                          <BarChart data={iterationDurationData} margin={{ top: 10, right: 20, left: 10, bottom: 30 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                            <XAxis
                              dataKey="iteration"
                              label={{ value: 'Iteration', position: 'insideBottom', offset: -10, style: { fontSize: '11px' } }}
                              tick={{ fontSize: '10px' }}
                              stroke="hsl(var(--muted-foreground))"
                            />
                            <YAxis
                              label={{ value: 'Duration', angle: -90, position: 'insideLeft', style: { fontSize: '11px' } }}
                              tick={{ fontSize: '10px' }}
                              stroke="hsl(var(--muted-foreground))"
                              tickFormatter={(value) => formatDuration(value)}
                            />
                            <Tooltip
                              contentStyle={{
                                fontSize: '11px',
                                backgroundColor: 'hsl(var(--card))',
                                border: '1px solid hsl(var(--border))',
                                borderRadius: '6px',
                              }}
                              labelFormatter={(value) => `Iteration ${value}`}
                              formatter={(value: number) => [formatDuration(value), 'Duration']}
                            />
                            {iterationStats && (
                              <>
                                <ReferenceLine
                                  y={iterationStats.mean}
                                  stroke="#3b82f6"
                                  strokeDasharray="3 3"
                                  strokeWidth={2}
                                  label={{
                                    value: 'Mean',
                                    position: 'right',
                                    fontSize: '10px',
                                    fill: '#3b82f6',
                                    fontWeight: 600
                                  }}
                                />
                                <ReferenceLine
                                  y={iterationStats.median}
                                  stroke="#f59e0b"
                                  strokeDasharray="3 3"
                                  strokeWidth={2}
                                  label={{
                                    value: 'Median',
                                    position: 'right',
                                    fontSize: '10px',
                                    fill: '#f59e0b',
                                    fontWeight: 600
                                  }}
                                />
                              </>
                            )}
                            <Bar dataKey="duration" fill="#22c55e" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
    </div>
  );
}
