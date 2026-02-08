import { useState, useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useExperiment } from '../../hooks/use-experiments';
import { useRuns } from '../../hooks/use-runs';
import { useGroupedMetrics } from '../../hooks/use-metrics';
import { MetricsChart } from '../../components/metrics/metrics-chart';
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
import { Button } from '../../components/ui/button';
import { Skeleton } from '../../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { formatDistanceToNow } from 'date-fns';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { Status } from '../../types';

const STATUS_VARIANTS: Record<Status, 'default' | 'secondary' | 'success' | 'warning' | 'destructive'> = {
  UNKNOWN: 'secondary',
  PENDING: 'warning',
  RUNNING: 'default',
  CANCELLED: 'secondary',
  COMPLETED: 'success',
  FAILED: 'destructive',
};

const PAGE_SIZE = 10;

export function ExperimentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState('overview');
  const [currentPage, setCurrentPage] = useState(1);

  const { data: experiment, isLoading: experimentLoading, error: experimentError } = useExperiment(id!);

  // Fetch paginated runs for display in Runs tab
  const { data: runs, isLoading: runsLoading } = useRuns(id!, {
    page: currentPage - 1,
    pageSize: PAGE_SIZE,
  });

  // Fetch ALL runs (unpaginated) for metrics filtering
  const { data: allRuns } = useRuns(id!, {
    page: 0,
    pageSize: 1000, // Large page size to get all runs
  });

  const { data: groupedMetrics, isLoading: metricsLoading } = useGroupedMetrics(id!);

  // Calculate run statistics for pie chart
  const runStatsData = useMemo(() => {
    if (!allRuns || allRuns.length === 0) return [];

    const stats = [
      { name: 'COMPLETED', value: allRuns.filter(r => r.status === 'COMPLETED').length, color: '#22c55e' },
      { name: 'RUNNING', value: allRuns.filter(r => r.status === 'RUNNING').length, color: '#3b82f6' },
      { name: 'FAILED', value: allRuns.filter(r => r.status === 'FAILED').length, color: '#ef4444' },
      { name: 'PENDING', value: allRuns.filter(r => r.status === 'PENDING').length, color: '#eab308' },
      { name: 'CANCELLED', value: allRuns.filter(r => r.status === 'CANCELLED').length, color: '#6b7280' },
      { name: 'UNKNOWN', value: allRuns.filter(r => r.status === 'UNKNOWN').length, color: '#9ca3af' },
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
    <div className="space-y-6">
      {/* Experiment Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            {experiment.name}
          </h1>
          {experiment.description && (
            <p className="mt-2 text-muted-foreground">{experiment.description}</p>
          )}
        </div>
        <Badge variant={STATUS_VARIANTS[experiment.status]} className="text-sm">
          {experiment.status}
        </Badge>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="runs">Runs</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          {/* Experiment Details */}
          <Card>
            <CardHeader>
              <CardTitle>Experiment Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <dt className="font-medium text-muted-foreground">Experiment ID</dt>
                  <dd className="mt-1 text-foreground">{experiment.id}</dd>
                </div>
                <div>
                  <dt className="font-medium text-muted-foreground">Project ID</dt>
                  <dd className="mt-1 text-foreground">{experiment.projectId}</dd>
                </div>
                <div>
                  <dt className="font-medium text-muted-foreground">Duration</dt>
                  <dd className="mt-1 text-foreground">
                    {experiment.duration > 0
                      ? `${experiment.duration.toFixed(2)}s`
                      : 'N/A'}
                  </dd>
                </div>
                <div>
                  <dt className="font-medium text-muted-foreground">Created</dt>
                  <dd className="mt-1 text-foreground">
                    {formatDistanceToNow(new Date(experiment.createdAt), {
                      addSuffix: true,
                    })}
                  </dd>
                </div>
                <div>
                  <dt className="font-medium text-muted-foreground">Updated</dt>
                  <dd className="mt-1 text-foreground">
                    {formatDistanceToNow(new Date(experiment.updatedAt), {
                      addSuffix: true,
                    })}
                  </dd>
                </div>
              </dl>

              {/* Parameters Section */}
              {experiment.params && Object.keys(experiment.params).length > 0 && (
                <div className="mt-6 pt-6 border-t">
                  <h3 className="text-sm font-semibold mb-4">Parameters</h3>
                  <dl className="grid grid-cols-3 gap-4 text-sm">
                    {Object.entries(experiment.params).map(([key, value]) => (
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

              {/* Metadata Section */}
              {experiment.meta && Object.keys(experiment.meta).length > 0 && (
                <div className="mt-6 pt-6 border-t">
                  <h3 className="text-sm font-semibold mb-4">Metadata</h3>
                  <dl className="grid grid-cols-3 gap-4 text-sm">
                    {Object.entries(experiment.meta).map(([key, value]) => (
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

              {/* Run Statistics */}
              {allRuns && allRuns.length > 0 && runStatsData.length > 0 && (
                <div className="mt-6 pt-6 border-t">
                  <h3 className="text-sm font-semibold mb-4">Statistics ({allRuns.length} runs)</h3>
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie
                        data={runStatsData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={({ name, value }) => `${name}: ${value}`}
                      >
                        {runStatsData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Metrics Chart - All Runs */}
          {metricsLoading ? (
            <Skeleton className="h-96 w-full" />
          ) : groupedMetrics && Object.keys(groupedMetrics).length > 0 ? (
            <MetricsChart
              metrics={groupedMetrics}
              title="Metrics"
              description="Select a metric to visualize"
            />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Metrics</CardTitle>
                <CardDescription>No metrics data available</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex h-32 items-center justify-center text-muted-foreground">
                  {allRuns && allRuns.length > 0
                    ? 'No metrics logged yet'
                    : 'No runs in this experiment'}
                </div>
              </CardContent>
            </Card>
          )}

        </TabsContent>

        {/* Runs Tab */}
        <TabsContent value="runs">
          <Card>
            <CardHeader>
              <CardTitle>Runs</CardTitle>
              <CardDescription>
                Runs in this experiment
              </CardDescription>
            </CardHeader>
            <CardContent>
              {runsLoading ? (
                <Skeleton className="h-32 w-full" />
              ) : !runs || runs.length === 0 ? (
                <div className="flex h-32 items-center justify-center text-muted-foreground">
                  No runs found
                </div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Run ID</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Created</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {[...runs]
                        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
                        .map((run) => (
                        <TableRow key={run.id}>
                          <TableCell className="font-mono text-sm">
                            <Link
                              to={`/runs/${run.id}`}
                              className="text-primary hover:underline"
                            >
                              {run.id}
                            </Link>
                          </TableCell>
                          <TableCell>
                            <Badge variant={STATUS_VARIANTS[run.status]}>
                              {run.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {formatDistanceToNow(new Date(run.createdAt), {
                              addSuffix: true,
                            })}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  {/* Pagination */}
                  <div className="mt-4 flex items-center justify-between">
                    <div className="text-sm text-muted-foreground">
                      Page {currentPage}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setCurrentPage(currentPage - 1);
                          window.scrollTo({ top: 0, behavior: 'smooth' });
                        }}
                        disabled={currentPage === 1}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setCurrentPage(currentPage + 1);
                          window.scrollTo({ top: 0, behavior: 'smooth' });
                        }}
                        disabled={runs.length < PAGE_SIZE}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
