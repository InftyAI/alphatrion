import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { useTeamContext } from '../../context/team-context';
import { useExperiments } from '../../hooks/use-experiments';
import { useLabelKeys } from '../../hooks/use-label-keys';
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
import { formatDistanceToNow } from 'date-fns';
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

export function ExperimentsPage() {
  const { selectedTeamId } = useTeamContext();
  const [statusFilter, setStatusFilter] = useState<Status | 'ALL'>('ALL');
  const [labelFilter, setLabelFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch experiments directly for the team
  const { data: experiments, isLoading } = useExperiments(
    selectedTeamId || '',
    { page: 0, pageSize: 1000, enabled: !!selectedTeamId }
  );

  // Fetch label keys from team
  const { data: labelKeys } = useLabelKeys(selectedTeamId || '', { enabled: !!selectedTeamId });

  // Build label options from team label keys
  const labelOptions = useMemo(() => {
    if (!labelKeys || labelKeys.length === 0) {
      return [{ value: 'ALL', label: 'All Labels' }];
    }

    return [
      { value: 'ALL', label: 'All Labels' },
      ...labelKeys.sort().map(key => ({
        value: key,
        label: key
      }))
    ];
  }, [labelKeys]);

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
          exp.labels?.some(label =>
            label.name.toLowerCase().includes(query) ||
            label.value.toLowerCase().includes(query)
          )
      );
    }

    // Apply status filter
    if (statusFilter !== 'ALL') {
      filtered = filtered.filter(exp => exp.status === statusFilter);
    }

    // Apply label filter (filter by label key name)
    if (labelFilter !== 'ALL') {
      filtered = filtered.filter(exp =>
        exp.labels?.some(label => label.name === labelFilter)
      );
    }

    // Sort by creation time descending (newest first)
    filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return filtered;
  }, [experiments, statusFilter, labelFilter, searchQuery]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">Experiments</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Browse and manage experiments
          </p>
        </div>

        {/* Filters */}
        <div className="flex gap-2 items-center">
          {/* Search Bar */}
          <div className="relative w-80">
            <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Search experiments..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 h-9 text-sm focus:bg-blue-50 focus:border-blue-300 focus-visible:ring-0"
            />
          </div>

          {/* Label Filter */}
          <Dropdown
            value={labelFilter}
            onChange={(value) => setLabelFilter(value)}
            options={labelOptions}
            className="w-48"
          />

          {/* Status Filter */}
          <Dropdown
            value={statusFilter}
            onChange={(value) => setStatusFilter(value as Status | 'ALL')}
            options={STATUS_OPTIONS}
            className="w-40"
          />
        </div>
      </div>

      {/* Experiments List */}
      <Card className="border-0 shadow-sm">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8">
              <Skeleton className="h-24 w-full" />
            </div>
          ) : !filteredExperiments || filteredExperiments.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
              {searchQuery.trim() ? 'No experiments match your search' : statusFilter !== 'ALL' ? `No ${statusFilter} experiments found` : 'No experiments found'}
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent border-b">
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">UUID</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Name</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Labels</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Status</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50 text-right">Duration</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50 text-right">Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredExperiments.map((experiment, idx) => (
                    <TableRow
                      key={experiment.id}
                      className="hover:bg-accent/50 transition-colors border-b last:border-0"
                    >
                      <TableCell className="py-3 text-sm font-mono">
                        <Link
                          to={`/experiments/${experiment.id}`}
                          className="text-blue-600 hover:text-blue-800 hover:underline font-medium transition-colors"
                        >
                          {experiment.id}
                        </Link>
                      </TableCell>
                      <TableCell className="py-3 text-sm font-medium text-foreground">
                        {experiment.name}
                      </TableCell>
                      <TableCell className="py-3 text-sm">
                        {experiment.labels && experiment.labels.length > 0 ? (
                          <div className="flex gap-1 flex-wrap">
                            {experiment.labels.map((label, idx) => (
                              <Badge key={idx} variant="outline" className="text-xs px-2 py-0.5 font-normal">
                                {label.name}: {label.value}
                              </Badge>
                            ))}
                          </div>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="py-3">
                        <Badge variant={STATUS_VARIANTS[experiment.status]} className="text-xs px-2.5 py-0.5 font-medium">
                          {experiment.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="py-3 text-sm text-foreground tabular-nums text-right">
                        {experiment.duration > 0
                          ? `${experiment.duration.toFixed(2)}s`
                          : '-'}
                      </TableCell>
                      <TableCell className="py-3 text-sm text-muted-foreground text-right">
                        {formatDistanceToNow(new Date(experiment.createdAt), {
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
    </div>
  );
}
