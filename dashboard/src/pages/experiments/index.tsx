import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useTeamContext } from '../../context/team-context';
import { useProjects } from '../../hooks/use-projects';
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
import { Skeleton } from '../../components/ui/skeleton';
import { Button } from '../../components/ui/button';
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

export function ExperimentsPage() {
  const { selectedTeamId } = useTeamContext();
  const [statusFilter, setStatusFilter] = useState<Status | 'ALL'>('ALL');

  // Fetch all projects to get their experiments
  const { data: projects, isLoading: projectsLoading } = useProjects(
    selectedTeamId || '',
    { page: 0, pageSize: 1000, enabled: !!selectedTeamId }
  );

  // For now, we'll fetch experiments from the first project as an example
  // In production, you'd want a dedicated API endpoint to get all experiments
  const firstProjectId = projects?.[0]?.id || '';

  const { data: experiments, isLoading: experimentsLoading } = useExperiments(
    firstProjectId,
    { page: 0, pageSize: 100, enabled: !!firstProjectId }
  );

  // Filter and sort experiments
  const filteredExperiments = useMemo(() => {
    if (!experiments) return [];

    let filtered = [...experiments];

    // Apply status filter
    if (statusFilter !== 'ALL') {
      filtered = filtered.filter(exp => exp.status === statusFilter);
    }

    // Sort by creation time descending (newest first)
    filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return filtered;
  }, [experiments, statusFilter]);

  const isLoading = projectsLoading || experimentsLoading;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Experiments</h1>
        <p className="mt-2 text-muted-foreground">
          All experiments in your projects
        </p>
      </div>

      {/* Experiments List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>All Experiments</CardTitle>
              <CardDescription>
                Browse and manage experiments across projects
              </CardDescription>
            </div>
            {/* Status Filter */}
            <div className="flex gap-2">
              {(['ALL', 'COMPLETED', 'RUNNING', 'FAILED', 'PENDING', 'CANCELLED'] as const).map((status) => (
                <Button
                  key={status}
                  variant={statusFilter === status ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setStatusFilter(status)}
                >
                  {status}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !filteredExperiments || filteredExperiments.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              {statusFilter !== 'ALL' ? `No ${statusFilter} experiments found` : 'No experiments found'}
            </div>
          ) : (
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
                {filteredExperiments.map((experiment) => (
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
          )}
        </CardContent>
      </Card>
    </div>
  );
}
