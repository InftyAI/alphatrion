import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { useTeamContext } from '../../context/team-context';
import { useExperiments } from '../../hooks/use-experiments';
import { useRuns } from '../../hooks/use-runs';
import { useTeam } from '../../hooks/use-teams';
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
import { Dropdown } from '../../components/ui/dropdown';
import { Pagination } from '../../components/ui/pagination';
import { formatDistanceToNow } from 'date-fns';
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

const STATUS_OPTIONS = [
  { value: 'ALL', label: 'All Status' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'RUNNING', label: 'Running' },
  { value: 'FAILED', label: 'Failed' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'CANCELLED', label: 'Cancelled' },
];

const PAGE_SIZE = 10;

export function RunsPage() {
  const { selectedTeamId } = useTeamContext();
  const [statusFilter, setStatusFilter] = useState<Status | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(0);

  // Fetch team info for total count
  const { data: team } = useTeam(selectedTeamId || '', { enabled: !!selectedTeamId });

  // Fetch experiments directly for the team
  const { data: experiments, isLoading: experimentsLoading } = useExperiments(
    selectedTeamId || '',
    { page: 0, pageSize: 1000, enabled: !!selectedTeamId }
  );

  // Fetch runs from the first experiment (temporary solution)
  // TODO: Add a backend query to fetch all runs for a team
  const firstExperimentId = experiments?.[0]?.id || '';

  const { data: runs, isLoading: runsLoading } = useRuns(
    firstExperimentId,
    { page: currentPage, pageSize: PAGE_SIZE, enabled: !!firstExperimentId }
  );

  const totalRuns = team?.totalRuns || 0;
  const totalPages = Math.ceil(totalRuns / PAGE_SIZE);

  // Filter and sort runs
  const filteredRuns = useMemo(() => {
    if (!runs) return [];

    let filtered = [...runs];

    // Apply search filter (search by run ID or experiment ID)
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (run) =>
          run.id?.toLowerCase().includes(query) ||
          run.experimentId?.toLowerCase().includes(query)
      );
    }

    // Apply status filter
    if (statusFilter !== 'ALL') {
      filtered = filtered.filter(run => run.status === statusFilter);
    }

    // Sort by creation time descending (newest first)
    filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return filtered;
  }, [runs, statusFilter, searchQuery]);

  const isLoading = experimentsLoading || runsLoading;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">Runs</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Monitor execution runs with token usage and performance metrics
          </p>
        </div>

        {/* Filters */}
        <div className="flex gap-2 items-center">
          {/* Search Bar */}
          <div className="relative w-80">
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
      </div>

      {/* Runs List */}
      <Card className="border-0 shadow-sm">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8">
              <Skeleton className="h-24 w-full" />
            </div>
          ) : !filteredRuns || filteredRuns.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
              {searchQuery.trim() ? 'No runs match your search' : statusFilter !== 'ALL' ? `No ${statusFilter} runs found` : 'No runs found'}
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent border-b">
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Run ID</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Status</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Tokens</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Duration</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Experiment</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRuns.map((run) => {
                    const totalTokens = run.aggregatedTokens?.totalTokens || 0;
                    const inputTokens = run.aggregatedTokens?.inputTokens || 0;
                    const outputTokens = run.aggregatedTokens?.outputTokens || 0;

                    return (
                      <TableRow
                        key={run.id}
                        className="hover:bg-accent/50 transition-colors border-b last:border-0"
                      >
                        <TableCell className="py-3 text-sm font-mono">
                          <Link
                            to={`/runs/${run.id}`}
                            className="text-blue-600 hover:text-blue-800 hover:underline font-medium transition-colors"
                            title={run.id}
                          >
                            {run.id.substring(0, 8)}...
                          </Link>
                        </TableCell>
                        <TableCell className="py-3">
                          <Badge variant={STATUS_VARIANTS[run.status]}>
                            {run.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="py-3 text-sm font-mono">
                          {totalTokens > 0 ? (
                            <div className="flex flex-col">
                              <span className="font-semibold">{totalTokens.toLocaleString()}</span>
                              <span className="text-xs text-muted-foreground">
                                {inputTokens.toLocaleString()}↓ {outputTokens.toLocaleString()}↑
                              </span>
                            </div>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="py-3 text-sm font-mono">
                          {run.duration > 0 ? (
                            formatDuration(run.duration)
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="py-3 text-sm font-mono">
                          {run.experimentId ? (
                            <Link
                              to={`/experiments/${run.experimentId}`}
                              className="text-blue-600 hover:text-blue-800 hover:underline font-medium transition-colors"
                              title={run.experimentId}
                            >
                              {run.experimentId.substring(0, 8)}...
                            </Link>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="py-3 text-sm text-muted-foreground">
                          {formatDistanceToNow(new Date(run.createdAt), {
                            addSuffix: true,
                          })}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Pagination */}
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            pageSize={PAGE_SIZE}
            totalItems={totalRuns}
            onPageChange={setCurrentPage}
            itemName="runs"
          />
        </CardContent>
      </Card>
    </div>
  );
}
