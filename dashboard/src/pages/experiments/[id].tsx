import { useState, useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Search, ExternalLink } from 'lucide-react';
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
import { Dropdown } from '../../components/ui/dropdown';
import { Pagination } from '../../components/ui/pagination';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { formatDistanceToNow } from 'date-fns';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { Status } from '../../types';

const STATUS_VARIANTS: Record<Status, 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'unknown' | 'info'> = {
  UNKNOWN: 'unknown',
  PENDING: 'warning',
  RUNNING: 'info',
  CANCELLED: 'secondary',
  COMPLETED: 'success',
  FAILED: 'destructive',
};

const STATUS_OPTIONS = [
  { value: 'ALL', label: 'All Status' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'RUNNING', label: 'Running' },
  { value: 'FAILED', label: 'Failed' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'CANCELLED', label: 'Cancelled' },
];

const PAGE_SIZE = 10;

export function ExperimentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState('overview');
  const [currentPage, setCurrentPage] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<Status | 'ALL'>('ALL');

  const { data: experiment, isLoading: experimentLoading, error: experimentError } = useExperiment(id!);

  // Fetch paginated runs for display in Runs tab
  const { data: runs, isLoading: runsLoading } = useRuns(id!, {
    page: currentPage,
    pageSize: PAGE_SIZE,
  });

  // Fetch ALL runs (unpaginated) for metrics filtering
  const { data: allRuns } = useRuns(id!, {
    page: 0,
    pageSize: 1000, // Large page size to get all runs
  });

  const totalRuns = allRuns?.length || 0;
  const totalPages = Math.ceil(totalRuns / PAGE_SIZE);

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
          <h1 className="text-xl font-semibold tracking-tight text-foreground">
            {experiment.name}
          </h1>
          <p className="mt-0.5 text-muted-foreground font-mono text-sm">
            {experiment.id}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to={`/experiments/${id}/ide`} target="_blank" rel="noopener noreferrer">
            <Button variant="outline" size="sm">
              <ExternalLink className="h-4 w-4 mr-2" />
              Open in IDE
            </Button>
          </Link>
          <Badge variant={STATUS_VARIANTS[experiment.status]}>
            {experiment.status}
          </Badge>
        </div>
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
                      ? `${experiment.duration.toFixed(2)}s`
                      : '-'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Total Tokens</dt>
                  <dd className="mt-1.5 text-foreground font-mono text-sm">
                    {experiment.aggregatedTokens?.totalTokens !== undefined && experiment.aggregatedTokens.totalTokens > 0 ? (
                      <>
                        {Number(experiment.aggregatedTokens.totalTokens).toLocaleString()}
                        {experiment.aggregatedTokens.inputTokens !== undefined && experiment.aggregatedTokens.outputTokens !== undefined && (
                          <span className="text-muted-foreground text-xs ml-1">
                            ({Number(experiment.aggregatedTokens.inputTokens).toLocaleString()}↓ {Number(experiment.aggregatedTokens.outputTokens).toLocaleString()}↑)
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
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

          {/* Metrics Chart - All Runs */}
          {metricsLoading ? (
            <Skeleton className="h-80 w-full" />
          ) : groupedMetrics && Object.keys(groupedMetrics).length > 0 ? (
            <MetricsChart
              metrics={groupedMetrics}
              experimentId={id!}
              title="Metrics"
              description="Switch between timeline and Pareto analysis views"
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
            <CardContent className="p-0">
              {/* Search Bar and Status Filter */}
              <div className="flex gap-2 mb-3 items-center px-4 pt-4">
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
                <Dropdown
                  value={statusFilter}
                  onChange={(value) => setStatusFilter(value as Status | 'ALL')}
                  options={STATUS_OPTIONS}
                  className="w-40"
                />
              </div>

              {runsLoading ? (
                <div className="p-8">
                  <Skeleton className="h-24 w-full" />
                </div>
              ) : !runs || runs.length === 0 ? (
                <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
                  No runs found
                </div>
              ) : filteredRuns.length === 0 ? (
                <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
                  No runs match your search
                </div>
              ) : (
                <div className="overflow-hidden rounded-lg">
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent border-b">
                        <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">UUID</TableHead>
                        <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Status</TableHead>
                        <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50 text-right">Created</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredRuns.map((run) => (
                        <TableRow key={run.id} className="hover:bg-accent/50 transition-colors border-b last:border-0">
                          <TableCell className="py-3 text-sm font-mono">
                            <Link
                              to={`/runs/${run.id}`}
                              className="text-blue-600 hover:text-blue-800 hover:underline font-medium transition-colors"
                            >
                              {run.id}
                            </Link>
                          </TableCell>
                          <TableCell className="py-3">
                            <Badge variant={STATUS_VARIANTS[run.status]}>
                              {run.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="py-3 text-sm text-muted-foreground text-right">
                            {formatDistanceToNow(new Date(run.createdAt), {
                              addSuffix: true,
                            })}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {/* Pagination */}
              {!runsLoading && filteredRuns && filteredRuns.length > 0 && (
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  pageSize={PAGE_SIZE}
                  totalItems={totalRuns}
                  onPageChange={setCurrentPage}
                  itemName="runs"
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
