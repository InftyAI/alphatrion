import { useState, useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
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

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState('overview');
  const [currentPage, setCurrentPage] = useState(1);

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
    <div className="space-y-6">
      {/* Project Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">
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
        <CardContent className="pt-6">
          <h3 className="text-sm font-semibold mb-4">Details</h3>
          <dl className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <dt className="font-medium text-muted-foreground">Project ID</dt>
              <dd className="mt-1 text-foreground">{project.id}</dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Team ID</dt>
              <dd className="mt-1 text-foreground">{project.teamId}</dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Created</dt>
              <dd className="mt-1 text-foreground">
                {formatDistanceToNow(new Date(project.createdAt), {
                  addSuffix: true,
                })}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Updated</dt>
              <dd className="mt-1 text-foreground">
                {formatDistanceToNow(new Date(project.updatedAt), {
                  addSuffix: true,
                })}
              </dd>
            </div>
          </dl>

          {/* Metadata */}
          {project.meta && Object.keys(project.meta).length > 0 && (
            <div className="mt-6 pt-6 border-t">
              <h3 className="text-sm font-semibold mb-4">Metadata</h3>
              <dl className="grid grid-cols-3 gap-4 text-sm">
                {Object.entries(project.meta).map(([key, value]) => (
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

          {/* Experiment Statistics */}
          {allExperiments && allExperiments.length > 0 && experimentStatsData.length > 0 && (
            <div className="mt-6 pt-6 border-t">
              <h3 className="text-sm font-semibold mb-4">Statistics ({allExperiments.length} experiments)</h3>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={experimentStatsData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ name, value }) => `${name}: ${value}`}
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
        <TabsContent value="experiments">
          <Card>
        <CardContent className="pt-6">
          {experimentsLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : experimentsError ? (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
              <p className="text-sm font-medium text-destructive">
                Failed to load experiments
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {experimentsError.message}
              </p>
            </div>
          ) : !experiments || experiments.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-center">
              <p className="text-muted-foreground mb-2">No experiments found</p>
              <p className="text-sm text-muted-foreground">
                Create experiments using the AlphaTrion SDK
              </p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {[...experiments]
                    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
                    .map((experiment) => (
                    <TableRow key={experiment.id}>
                      <TableCell>
                        <Link
                          to={`/experiments/${experiment.id}`}
                          className="font-medium text-primary hover:underline"
                        >
                          {experiment.name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant={STATUS_VARIANTS[experiment.status]}>
                          {experiment.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {experiment.duration > 0
                          ? `${experiment.duration.toFixed(2)}s`
                          : '-'}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDistanceToNow(new Date(experiment.createdAt), {
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
                    disabled={experiments.length < PAGE_SIZE}
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
