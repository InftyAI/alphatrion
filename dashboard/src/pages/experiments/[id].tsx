import { useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import { useExperiment } from '../../hooks/use-experiments';
import { useRuns } from '../../hooks/use-runs';
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
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
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

  // Fetch ALL runs for statistics
  const { data: allRuns } = useRuns(id!, {
    page: 0,
    pageSize: 1000, // Large page size to get all runs
  });

  // Calculate run statistics for pie chart
  const runStatsData = useMemo(() => {
    if (!allRuns || allRuns.length === 0) return [];

    const stats = [
      { name: 'COMPLETED', value: allRuns.filter(r => r.status === 'COMPLETED').length, color: '#22c55e' },
      { name: 'RUNNING', value: allRuns.filter(r => r.status === 'RUNNING').length, color: '#3b82f6' },
      { name: 'FAILED', value: allRuns.filter(r => r.status === 'FAILED').length, color: '#ef4444' },
      { name: 'PENDING', value: allRuns.filter(r => r.status === 'PENDING').length, color: '#eab308' },
      { name: 'CANCELLED', value: allRuns.filter(r => r.status === 'CANCELLED').length, color: '#6b7280' },
      { name: 'UNKNOWN', value: allRuns.filter(r => r.status === 'UNKNOWN').length, color: '#a78bfa' },
    ];

    return stats.filter(s => s.value > 0);
  }, [allRuns]);

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
                <Link to={`/experiments/${id}/ide`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1">
                  <ExternalLink className="h-3 w-3" />
                  <span>Open in IDE</span>
                </Link>
              </Button>
            </div>
          </div>
        </div>
        <Badge variant={STATUS_VARIANTS[experiment.status]}>
          {experiment.status}
        </Badge>
      </div>

      {/* Experiment Details */}
      <Card>
            <CardContent className="p-4">
              <h3 className="text-base font-semibold mb-3">Details</h3>
              <dl className="grid grid-cols-4 gap-3 text-sm">
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">UUID</dt>
                  <dd className="mt-1.5 text-foreground font-mono text-sm break-all">{experiment.id}</dd>
                </div>
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

              {/* Iteration Statistics */}
              {allRuns && allRuns.length > 0 && runStatsData.length > 0 && (
                <div className="mt-5 pt-5 border-t">
                  <h3 className="text-base font-semibold mb-6">Statistics ({allRuns.length} iterations)</h3>
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart margin={{ top: 20, bottom: 5 }}>
                      <Pie
                        data={runStatsData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="48%"
                        outerRadius={48}
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
              )}
            </CardContent>
          </Card>
    </div>
  );
}
