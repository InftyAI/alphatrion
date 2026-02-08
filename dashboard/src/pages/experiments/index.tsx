import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { useTeamContext } from '../../context/team-context';
import { useProjects } from '../../hooks/use-projects';
import { useExperiments } from '../../hooks/use-experiments';
import {
  Card,
  CardContent,
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
import { Input } from '../../components/ui/input';
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
  const [searchQuery, setSearchQuery] = useState('');

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

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (exp) =>
          exp.name?.toLowerCase().includes(query) ||
          exp.description?.toLowerCase().includes(query) ||
          exp.id?.toLowerCase().includes(query) ||
          exp.projectId?.toLowerCase().includes(query)
      );
    }

    // Apply status filter
    if (statusFilter !== 'ALL') {
      filtered = filtered.filter(exp => exp.status === statusFilter);
    }

    // Sort by creation time descending (newest first)
    filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return filtered;
  }, [experiments, statusFilter, searchQuery]);

  const isLoading = projectsLoading || experimentsLoading;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-foreground">Experiments</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Browse and manage experiments
        </p>
      </div>

      {/* Experiments List */}
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

          {isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : !filteredExperiments || filteredExperiments.length === 0 ? (
            <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
              {searchQuery.trim() ? 'No experiments match your search' : statusFilter !== 'ALL' ? `No ${statusFilter} experiments found` : 'No experiments found'}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="h-10 text-sm font-medium">Name</TableHead>
                  <TableHead className="h-10 text-sm font-medium">Experiment ID</TableHead>
                  <TableHead className="h-10 text-sm font-medium">Project ID</TableHead>
                  <TableHead className="h-10 text-sm font-medium">Status</TableHead>
                  <TableHead className="h-10 text-sm font-medium">Duration</TableHead>
                  <TableHead className="h-10 text-sm font-medium">Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredExperiments.map((experiment) => (
                  <TableRow key={experiment.id}>
                    <TableCell className="py-3.5 text-sm text-muted-foreground">
                      {experiment.name}
                    </TableCell>
                    <TableCell className="py-3.5 font-mono text-sm">
                      <Link
                        to={`/experiments/${experiment.id}`}
                        className="text-primary hover:underline"
                      >
                        {experiment.id}
                      </Link>
                    </TableCell>
                    <TableCell className="py-3.5 font-mono text-sm">
                      <Link
                        to={`/projects/${experiment.projectId}`}
                        className="text-primary hover:underline"
                      >
                        {experiment.projectId}
                      </Link>
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
          )}
        </CardContent>
      </Card>
    </div>
  );
}
