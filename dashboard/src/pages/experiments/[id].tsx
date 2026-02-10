import { useState, useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Search } from 'lucide-react';
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
import { Input } from '../../components/ui/input';
import { Skeleton } from '../../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { formatDistanceToNow } from 'date-fns';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { Status } from '../../types';

const STATUS_VARIANTS: Record<Status, 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'unknown'> = {
  UNKNOWN: 'unknown',
  PENDING: 'warning',
  RUNNING: 'default',
  CANCELLED: 'secondary',
  COMPLETED: 'success',
  FAILED: 'destructive',
};

const PAGE_SIZE = 20;

export function ExperimentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState('overview');
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<Status | 'ALL'>('ALL');

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

  // Filter and sort runs
  const filteredRuns = useMemo(() => {
    if (!runs) return [];

    let filtered = [...runs];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (run) =>
          run.id?.toLowerCase().includes(query)
      );
    }

    // Apply status filter
    if (statusFilter !== 'ALL') {
      filtered = filtered.filter(run => run.status === statusFilter);
    }

    // Sort by creation time descending (newest first)
    filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return filtered;
  }, [runs, searchQuery, statusFilter]);

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
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            {experiment.name}
          </h1>
          {experiment.description && (
            <p className="mt-1 text-sm text-muted-foreground">{experiment.description}</p>
          )}
        </div>
        <Badge variant={STATUS_VARIANTS[experiment.status]}>
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
            <CardContent className="p-4">
              <h3 className="text-base font-semibold mb-3">Details</h3>
              <dl className="grid grid-cols-3 gap-3 text-sm">
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Experiment ID</dt>
                  <dd className="mt-1.5 text-foreground font-mono text-sm">{experiment.id}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Project ID</dt>
                  <dd className="mt-1.5 text-foreground font-mono text-sm">{experiment.projectId}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Duration</dt>
                  <dd className="mt-1.5 text-foreground text-sm">
                    {experiment.duration > 0
                      ? `${experiment.duration.toFixed(2)}s`
                      : 'N/A'}
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
                  <dl className="grid grid-cols-3 gap-3 text-sm">
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
                  <dl className="grid grid-cols-3 gap-3 text-sm">
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

              {/* Run Statistics */}
              {allRuns && allRuns.length > 0 && runStatsData.length > 0 && (
                <div className="mt-5 pt-5 border-t">
                  <h3 className="text-base font-semibold mb-6">Statistics ({allRuns.length} runs)</h3>
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
                        style={{ fontSize: '12px' }}
                      >
                        {runStatsData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend wrapperStyle={{ fontSize: '12px' }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Metrics Chart - All Runs */}
          {metricsLoading ? (
            <Skeleton className="h-80 w-full" />
          ) : groupedMetrics && Object.keys(groupedMetrics).length > 0 ? (
            <MetricsChart
              metrics={groupedMetrics}
              title="Metrics"
              description="Select a metric to visualize"
            />
          ) : (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Metrics</CardTitle>
                <CardDescription className="text-xs">No metrics data available</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
                  {allRuns && allRuns.length > 0
                    ? 'No metrics logged yet'
                    : 'No runs in this experiment'}
                </div>
              </CardContent>
            </Card>
          )}

        </TabsContent>

        {/* Runs Tab */}
        <TabsContent value="runs" className="space-y-4">
          <Card>
            <CardContent className="p-4">
              {/* Search Bar and Status Filter */}
              <div className="flex gap-2 mb-3 items-center">
                {/* Search Bar */}
                <div className="relative w-64">
                  <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    placeholder="Search runs..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-8 h-9 text-sm focus:bg-blue-50 focus:border-blue-300 focus-visible:ring-0"
                  />
                </div>

                {/* Status Filter */}
                <div className="flex gap-1">
                  {(['ALL', 'COMPLETED', 'RUNNING', 'FAILED', 'PENDING', 'CANCELLED'] as const).map((status) => (
                    <Button
                      key={status}
                      variant="outline"
                      size="sm"
                      onClick={() => setStatusFilter(status)}
                      className={`h-8 px-2.5 text-xs transition-colors ${
                        statusFilter === status
                          ? 'bg-blue-50 border-blue-300 text-blue-700 hover:bg-blue-100'
                          : 'bg-white hover:bg-gray-50'
                      }`}
                    >
                      {status}
                    </Button>
                  ))}
                </div>
              </div>

              {runsLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : !runs || runs.length === 0 ? (
                <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
                  No runs found
                </div>
              ) : filteredRuns.length === 0 ? (
                <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
                  No runs match your search
                </div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="h-10 text-xs font-medium uppercase tracking-wide text-muted-foreground">Run ID</TableHead>
                        <TableHead className="h-10 text-xs font-medium uppercase tracking-wide text-muted-foreground">Status</TableHead>
                        <TableHead className="h-10 text-xs font-medium uppercase tracking-wide text-muted-foreground">Created</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredRuns.map((run) => (
                          <TableRow key={run.id}>
                            <TableCell className="py-3.5 text-sm">
                              <Link
                                to={`/runs/${run.id}`}
                                className="font-mono text-primary font-medium hover:underline"
                              >
                                {run.id}
                              </Link>
                            </TableCell>
                            <TableCell className="py-3.5">
                              <Badge variant={STATUS_VARIANTS[run.status]} className="text-xs px-2 py-0.5">
                                {run.status}
                              </Badge>
                            </TableCell>
                            <TableCell className="py-3.5 text-sm text-foreground">
                              {formatDistanceToNow(new Date(run.createdAt), {
                                addSuffix: true,
                              })}
                            </TableCell>
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>

                  {/* Pagination */}
                  <div className="mt-3 flex items-center justify-between">
                    <div className="text-sm text-muted-foreground">
                      Page {currentPage}
                    </div>
                    <div className="flex gap-1.5">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setCurrentPage(currentPage - 1);
                          window.scrollTo({ top: 0, behavior: 'smooth' });
                        }}
                        disabled={currentPage === 1}
                        className="h-9 px-3 text-sm"
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
                        className="h-9 px-3 text-sm"
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
