import { useState, useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import { useProject } from '../../hooks/use-projects';
import { useExperiments } from '../../hooks/use-experiments';
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

const STATUS_VARIANTS: Record<Status, 'default' | 'secondary' | 'success' | 'warning' | 'destructive'> = {
  UNKNOWN: 'secondary',
  PENDING: 'warning',
  RUNNING: 'default',
  CANCELLED: 'secondary',
  COMPLETED: 'success',
  FAILED: 'destructive',
};

const PAGE_SIZE = 20;

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState('overview');
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<Status | 'ALL'>('ALL');

  const { data: project, isLoading: projectLoading, error: projectError } = useProject(id!);

  // Fetch paginated experiments for display
  const { data: experiments, isLoading: experimentsLoading, error: experimentsError } = useExperiments(id!, {
    page: currentPage - 1,
    pageSize: PAGE_SIZE,
    enabled: !!id,
  });

  // Fetch ALL experiments for statistics
  const { data: allExperiments } = useExperiments(id!, {
    page: 0,
    pageSize: 1000,
    enabled: !!id,
  });

  // Filter and sort experiments
  const filteredExperiments = useMemo(() => {
    if (!experiments) return [];

    let filtered = [...experiments];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (exp) =>
          exp.name?.toLowerCase().includes(query) ||
          exp.description?.toLowerCase().includes(query) ||
          exp.id?.toLowerCase().includes(query)
      );
    }

    // Apply status filter
    if (statusFilter !== 'ALL') {
      filtered = filtered.filter(exp => exp.status === statusFilter);
    }

    // Sort by creation time descending (newest first)
    filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return filtered;
  }, [experiments, searchQuery, statusFilter]);

  // Calculate experiment statistics for pie chart
  const experimentStatsData = useMemo(() => {
    if (!allExperiments || allExperiments.length === 0) return [];

    const stats = [
      { name: 'COMPLETED', value: allExperiments.filter(e => e.status === 'COMPLETED').length, color: '#22c55e' },
      { name: 'RUNNING', value: allExperiments.filter(e => e.status === 'RUNNING').length, color: '#3b82f6' },
      { name: 'FAILED', value: allExperiments.filter(e => e.status === 'FAILED').length, color: '#ef4444' },
      { name: 'PENDING', value: allExperiments.filter(e => e.status === 'PENDING').length, color: '#eab308' },
      { name: 'CANCELLED', value: allExperiments.filter(e => e.status === 'CANCELLED').length, color: '#6b7280' },
      { name: 'UNKNOWN', value: allExperiments.filter(e => e.status === 'UNKNOWN').length, color: '#9ca3af' },
    ];

    return stats.filter(s => s.value > 0);
  }, [allExperiments]);

  if (projectLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (projectError || !project) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Error</CardTitle>
          <CardDescription>Failed to load project</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-destructive">
            {projectError?.message || 'Project not found'}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Project Header */}
      <div>
        <h1 className="text-xl font-bold text-foreground">
          {project.name || 'Unnamed Project'}
        </h1>
        {project.description && (
          <p className="mt-1 text-sm text-muted-foreground">{project.description}</p>
        )}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="experiments">Experiments</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          {/* Project Details */}
          <Card>
            <CardContent className="p-4">
              <h3 className="text-sm font-semibold mb-3">Details</h3>
              <dl className="grid grid-cols-3 gap-3 text-sm">
                <div>
                  <dt className="text-xs text-muted-foreground font-medium">Project ID</dt>
                  <dd className="mt-1.5 text-foreground text-sm">{project.id}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground font-medium">Team ID</dt>
                  <dd className="mt-1.5 text-foreground text-sm">{project.teamId}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground font-medium">Created</dt>
                  <dd className="mt-1.5 text-foreground text-sm">
                    {formatDistanceToNow(new Date(project.createdAt), {
                      addSuffix: true,
                    })}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground font-medium">Updated</dt>
                  <dd className="mt-1.5 text-foreground text-sm">
                    {formatDistanceToNow(new Date(project.updatedAt), {
                      addSuffix: true,
                    })}
                  </dd>
                </div>
              </dl>

              {/* Metadata */}
              {project.meta && Object.keys(project.meta).length > 0 && (
                <div className="mt-5 pt-5 border-t">
                  <h3 className="text-sm font-semibold mb-3">Metadata</h3>
                  <dl className="grid grid-cols-3 gap-3 text-sm">
                    {Object.entries(project.meta).map(([key, value]) => (
                      <div key={key}>
                        <dt className="text-xs text-muted-foreground font-medium">{key}</dt>
                        <dd className="mt-1.5 text-foreground font-mono text-sm">
                          {JSON.stringify(value)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}

              {/* Experiment Statistics */}
              {allExperiments && allExperiments.length > 0 && experimentStatsData.length > 0 && (
                <div className="mt-5 pt-5 border-t">
                  <h3 className="text-sm font-semibold mb-3">Statistics ({allExperiments.length} experiments)</h3>
                  <ResponsiveContainer width="100%" height={160}>
                    <PieChart>
                      <Pie
                        data={experimentStatsData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={55}
                        label={({ name, value }) => `${name}: ${value}`}
                        style={{ fontSize: '12px' }}
                      >
                        {experimentStatsData.map((entry, index) => (
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
        </TabsContent>

        {/* Experiments Tab */}
        <TabsContent value="experiments" className="space-y-4">
          <Card>
            <CardContent className="p-4">
              {/* Search Bar and Status Filter */}
              <div className="flex gap-2 mb-3 items-center">
                {/* Search Bar */}
                <div className="relative w-64">
                  <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    placeholder="Search experiments..."
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

              {experimentsLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : experimentsError ? (
                <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3">
                  <p className="text-sm font-medium text-destructive">
                    Failed to load experiments
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {experimentsError.message}
                  </p>
                </div>
              ) : !experiments || experiments.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-24 text-center">
                  <p className="text-sm text-muted-foreground mb-1">No experiments found</p>
                  <p className="text-xs text-muted-foreground">
                    Create experiments using the AlphaTrion SDK
                  </p>
                </div>
              ) : filteredExperiments.length === 0 ? (
                <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
                  No experiments match your search
                </div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="h-10 text-sm font-medium">UUID</TableHead>
                        <TableHead className="h-10 text-sm font-medium">Name</TableHead>
                        <TableHead className="h-10 text-sm font-medium">Status</TableHead>
                        <TableHead className="h-10 text-sm font-medium">Duration</TableHead>
                        <TableHead className="h-10 text-sm font-medium">Created</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredExperiments.map((experiment) => (
                          <TableRow key={experiment.id}>
                            <TableCell className="py-3.5 font-mono text-sm">
                              <Link
                                to={`/experiments/${experiment.id}`}
                                className="text-primary hover:underline"
                              >
                                {experiment.id}
                              </Link>
                            </TableCell>
                            <TableCell className="py-3.5 text-sm text-muted-foreground">
                              {experiment.name}
                            </TableCell>
                            <TableCell className="py-3.5">
                              <Badge variant={STATUS_VARIANTS[experiment.status]} className="text-xs px-2 py-0.5">
                                {experiment.status}
                              </Badge>
                            </TableCell>
                            <TableCell className="py-3.5 text-sm text-muted-foreground">
                              {experiment.duration > 0
                                ? `${experiment.duration.toFixed(2)}s`
                                : '-'}
                            </TableCell>
                            <TableCell className="py-3.5 text-sm text-muted-foreground">
                              {formatDistanceToNow(new Date(experiment.createdAt), {
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
                        disabled={experiments.length < PAGE_SIZE}
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
