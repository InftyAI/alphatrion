import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import { useExperiment } from '../../hooks/use-experiments';
import { useRunDurations } from '../../hooks/use-run-statistics';
import { useRuns } from '../../hooks/use-runs';
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
  const [activeTab, setActiveTab] = useState('overview');

  const { data: experiment, isLoading: experimentLoading, error: experimentError } = useExperiment(id!);

  // Fetch run durations (includes both status and duration)
  const { data: runDurations } = useRunDurations(id!);

  // Fetch all runs for the iterations table
  const { data: runs, isLoading: runsLoading } = useRuns(id!, { pageSize: 1000 });

  // Calculate run statistics for pie chart - optimized to single pass
  const runStatsData = useMemo(() => {
    if (!runDurations || runDurations.length === 0) return [];

    // Single pass through the array instead of 6 separate filter operations
    const counts = runDurations.reduce((acc, run) => {
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
  }, [runDurations]);

  // Prepare iteration duration histogram data
  const { iterationHistogramData, iterationStats } = useMemo(() => {
    if (!runDurations || runDurations.length === 0) {
      return { iterationHistogramData: [], iterationStats: null };
    }

    // Get completed run durations
    const durations = runDurations
      .filter(run => run.status === 'COMPLETED' && run.duration > 0)
      .map(run => run.duration);

    if (durations.length === 0) {
      return { iterationHistogramData: [], iterationStats: null };
    }

    // Calculate statistics
    const mean = durations.reduce((sum, d) => sum + d, 0) / durations.length;
    const sorted = [...durations].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 === 0
      ? (sorted[mid - 1] + sorted[mid]) / 2
      : sorted[mid];

    // Detect and handle outliers using IQR method
    const sortedDurations = [...durations].sort((a, b) => a - b);
    const q1Index = Math.floor(sortedDurations.length * 0.25);
    const q3Index = Math.floor(sortedDurations.length * 0.75);
    const q1 = sortedDurations[q1Index];
    const q3 = sortedDurations[q3Index];
    const iqr = q3 - q1;
    const lowerBound = q1 - 1.5 * iqr;
    const upperBound = q3 + 1.5 * iqr;

    // Separate main data and outliers
    const mainData = durations.filter(d => d >= lowerBound && d <= upperBound);
    const outliers = durations.filter(d => d < lowerBound || d > upperBound);

    if (mainData.length === 0) {
      // All data are outliers, treat as normal
      const min = Math.min(...durations);
      const max = Math.max(...durations);
      const range = max - min;
      const numBins = Math.min(Math.max(5, Math.ceil(Math.sqrt(durations.length))), 15);
      const binSize = range / numBins;

      const bins: { range: string; count: number; minValue: number; maxValue: number }[] = [];
      for (let i = 0; i < numBins; i++) {
        const binMin = min + i * binSize;
        const binMax = min + (i + 1) * binSize;
        bins.push({
          range: `${formatDuration(binMin)}-${formatDuration(binMax)}`,
          count: 0,
          minValue: binMin,
          maxValue: binMax,
        });
      }

      durations.forEach(duration => {
        const binIndex = Math.min(Math.floor((duration - min) / binSize), numBins - 1);
        bins[binIndex].count++;
      });

      return {
        iterationHistogramData: bins.filter(bin => bin.count > 0),
        iterationStats: { mean, median },
      };
    }

    // Create bins for main data distribution
    const mainMin = Math.min(...mainData);
    const mainMax = Math.max(...mainData);
    const mainRange = mainMax - mainMin;

    // Determine number of bins
    let numBins: number;
    if (mainData.length < 10) {
      numBins = Math.min(5, mainData.length);
    } else if (mainData.length < 30) {
      numBins = Math.max(5, Math.min(Math.ceil(Math.sqrt(mainData.length)), 10));
    } else {
      numBins = Math.max(8, Math.min(Math.ceil(Math.log2(mainData.length)) + 1, 15));
    }

    const binSize = mainRange > 0 ? mainRange / numBins : 1;

    // Initialize bins for main data
    const bins: { range: string; count: number; minValue: number; maxValue: number; isOutlier?: boolean }[] = [];
    for (let i = 0; i < numBins; i++) {
      const binMin = mainMin + i * binSize;
      const binMax = mainMin + (i + 1) * binSize;
      bins.push({
        range: `${formatDuration(binMin)}-${formatDuration(binMax)}`,
        count: 0,
        minValue: binMin,
        maxValue: binMax,
      });
    }

    // Fill bins with main data
    mainData.forEach(duration => {
      const binIndex = Math.min(Math.floor((duration - mainMin) / binSize), numBins - 1);
      bins[binIndex].count++;
    });

    // Add outlier bin if there are outliers
    if (outliers.length > 0) {
      const outlierMin = Math.min(...outliers);
      const outlierMax = Math.max(...outliers);
      bins.push({
        range: outliers.length === 1
          ? `${formatDuration(outliers[0])} (outlier)`
          : `${formatDuration(outlierMin)}-${formatDuration(outlierMax)} (outliers)`,
        count: outliers.length,
        minValue: outlierMin,
        maxValue: outlierMax,
        isOutlier: true,
      });
    }

    // Filter out empty bins
    const nonEmptyBins = bins.filter(bin => bin.count > 0);

    return {
      iterationHistogramData: nonEmptyBins,
      iterationStats: { mean, median },
    };
  }, [runDurations]);

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
        <Badge variant={STATUS_VARIANTS[experiment.status]}>
          {experiment.status}
        </Badge>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="iterations">Iterations</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
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
              {runDurations && runDurations.length > 0 && runStatsData.length > 0 && (
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
                          ({runDurations.length} total)
                        </span>
                      </h4>
                      <ResponsiveContainer width="100%" height={280}>
                        <PieChart margin={{ top: 5, bottom: 10 }}>
                          <Pie
                            data={runStatsData}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="45%"
                            outerRadius={70}
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

                    {/* Iteration Duration Distribution Histogram */}
                    {iterationHistogramData.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium mb-3 text-muted-foreground">
                          Iteration Duration Distribution
                          {iterationStats && (
                            <span className="ml-2 text-xs font-normal">
                              • Avg: {formatDuration(iterationStats.mean)} • Med: {formatDuration(iterationStats.median)}
                            </span>
                          )}
                        </h4>
                        <ResponsiveContainer width="100%" height={320}>
                          <BarChart data={iterationHistogramData} margin={{ top: 55, right: 15, left: 5, bottom: 70 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                            <XAxis
                              dataKey="range"
                              label={{ value: 'Duration Range', position: 'insideBottom', offset: -48, style: { fontSize: '10px' } }}
                              tick={{ fontSize: '8px', angle: -45, textAnchor: 'end' }}
                              stroke="hsl(var(--muted-foreground))"
                              height={75}
                              interval={0}
                            />
                            <YAxis
                              label={{ value: 'Count', angle: -90, position: 'insideLeft', style: { fontSize: '10px' } }}
                              tick={{ fontSize: '9px' }}
                              stroke="hsl(var(--muted-foreground))"
                              allowDecimals={false}
                            />
                            <Tooltip
                              contentStyle={{
                                fontSize: '11px',
                                backgroundColor: 'hsl(var(--card))',
                                border: '1px solid hsl(var(--border))',
                                borderRadius: '6px',
                              }}
                              labelFormatter={(value) => `Duration: ${value}`}
                              formatter={(value: number) => [value, 'Iterations']}
                            />
                            <Bar dataKey="count" fill="#22c55e" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Iterations Tab */}
        <TabsContent value="iterations">
          <Card className="border-0 shadow-sm">
            <CardContent className="p-0">
              {runsLoading ? (
                <div className="p-8">
                  <Skeleton className="h-24 w-full" />
                </div>
              ) : !runs || runs.length === 0 ? (
                <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
                  No iterations found for this experiment
                </div>
              ) : (
                <div className="overflow-hidden rounded-lg">
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent border-b">
                        <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">UUID</TableHead>
                        <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Status</TableHead>
                        <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Duration</TableHead>
                        <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Created</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {runs.map((run) => (
                        <TableRow
                          key={run.id}
                          className="hover:bg-accent/50 transition-colors border-b last:border-0"
                        >
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
                          <TableCell className="py-3 text-sm font-mono">
                            {run.duration != null && run.duration > 0 ? formatDuration(run.duration) : '-'}
                          </TableCell>
                          <TableCell className="py-3 text-sm text-muted-foreground">
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
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
