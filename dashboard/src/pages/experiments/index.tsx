import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Search, Trash2 } from 'lucide-react';
import { useTeamContext } from '../../context/team-context';
import { useExperiments } from '../../hooks/use-experiments';
import { useDeleteExperiments } from '../../hooks/use-experiment-mutations';
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
import { Button } from '../../components/ui/button';
import { Checkbox } from '../../components/ui/checkbox';
import { Skeleton } from '../../components/ui/skeleton';
import { Dropdown } from '../../components/ui/dropdown';
import { MultiSelectDropdown } from '../../components/ui/multi-select-dropdown';
import { Pagination } from '../../components/ui/pagination';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';
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

// Predefined color palette for label keys (20 distinct colors)
const LABEL_COLORS = [
  { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300' },
  { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300' },
  { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-300' },
  { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-300' },
  { bg: 'bg-pink-100', text: 'text-pink-700', border: 'border-pink-300' },
  { bg: 'bg-cyan-100', text: 'text-cyan-700', border: 'border-cyan-300' },
  { bg: 'bg-indigo-100', text: 'text-indigo-700', border: 'border-indigo-300' },
  { bg: 'bg-teal-100', text: 'text-teal-700', border: 'border-teal-300' },
  { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-300' },
  { bg: 'bg-rose-100', text: 'text-rose-700', border: 'border-rose-300' },
  { bg: 'bg-violet-100', text: 'text-violet-700', border: 'border-violet-300' },
  { bg: 'bg-lime-100', text: 'text-lime-700', border: 'border-lime-300' },
  { bg: 'bg-fuchsia-100', text: 'text-fuchsia-700', border: 'border-fuchsia-300' },
  { bg: 'bg-emerald-100', text: 'text-emerald-700', border: 'border-emerald-300' },
  { bg: 'bg-sky-100', text: 'text-sky-700', border: 'border-sky-300' },
  { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-300' },
  { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300' },
  { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-300' },
  { bg: 'bg-zinc-100', text: 'text-zinc-700', border: 'border-zinc-300' },
  { bg: 'bg-stone-100', text: 'text-stone-700', border: 'border-stone-300' },
];

const PAGE_SIZE = 10;

export function ExperimentsPage() {
  const { selectedTeamId } = useTeamContext();
  const [statusFilter, setStatusFilter] = useState<Status | 'ALL'>('ALL');
  const [labelFilters, setLabelFilters] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(0);
  const [selectedExperiments, setSelectedExperiments] = useState<Set<string>>(new Set());
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const deleteExperimentsMutation = useDeleteExperiments();

  // Fetch team info for total count
  const { data: team } = useTeam(selectedTeamId || '', { enabled: !!selectedTeamId });

  // Fetch experiments directly for the team
  const { data: experiments, isLoading } = useExperiments(
    selectedTeamId || '',
    { page: currentPage, pageSize: PAGE_SIZE, enabled: !!selectedTeamId }
  );

  const totalExperiments = team?.totalExperiments || 0;
  const totalPages = Math.ceil(totalExperiments / PAGE_SIZE);

  // Create a stable color mapping for label keys (no collisions)
  const labelKeyColorMap = useMemo(() => {
    if (!experiments || experiments.length === 0) {
      return new Map<string, typeof LABEL_COLORS[0]>();
    }

    const uniqueKeys = new Set<string>();
    experiments.forEach(exp => {
      exp.labels?.forEach(label => {
        uniqueKeys.add(label.name);
      });
    });

    const sortedKeys = Array.from(uniqueKeys).sort();
    const colorMap = new Map<string, typeof LABEL_COLORS[0]>();

    sortedKeys.forEach((key, index) => {
      colorMap.set(key, LABEL_COLORS[index % LABEL_COLORS.length]);
    });

    return colorMap;
  }, [experiments]);

  // Build label options grouped by key, showing all unique values per key
  const labelOptions = useMemo(() => {
    if (!experiments || experiments.length === 0) {
      return [];
    }

    // Collect labels by key
    const labelsByKey = new Map<string, Set<string>>();

    experiments.forEach(exp => {
      exp.labels?.forEach(label => {
        if (!labelsByKey.has(label.name)) {
          labelsByKey.set(label.name, new Set());
        }
        labelsByKey.get(label.name)!.add(label.value);
      });
    });

    // Build options grouped by key
    const options: { value: string; label: string; group: string }[] = [];

    Array.from(labelsByKey.entries())
      .sort(([keyA], [keyB]) => keyA.localeCompare(keyB))
      .forEach(([key, values]) => {
        // Add "Any" option for this key
        options.push({
          value: `${key}:*`,
          label: `(Any ${key})`,
          group: key
        });

        // Add specific value options
        Array.from(values)
          .sort()
          .forEach(value => {
            options.push({
              value: `${key}:${value}`,
              label: value,
              group: key
            });
          });
      });

    return options;
  }, [experiments]);

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

    // Apply label filters (AND logic - experiment must match ALL selected labels)
    if (labelFilters.length > 0) {
      filtered = filtered.filter(exp => {
        // Check if experiment matches ALL selected label filters
        return labelFilters.every(filter => {
          const [labelName, labelValue] = filter.split(':', 2);

          if (labelValue === '*') {
            // "key:*" means any experiment with this key
            return exp.labels?.some(label => label.name === labelName);
          } else {
            // "key:value" means exact match
            return exp.labels?.some(label =>
              label.name === labelName && label.value === labelValue
            );
          }
        });
      });
    }

    // Sort by creation time descending (newest first)
    filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return filtered;
  }, [experiments, statusFilter, labelFilters, searchQuery]);

  // Check if all filtered experiments are selected
  const allSelected = filteredExperiments.length > 0 &&
    filteredExperiments.every(exp => selectedExperiments.has(exp.id));

  // Toggle select all
  const handleSelectAll = () => {
    if (allSelected) {
      setSelectedExperiments(new Set());
    } else {
      setSelectedExperiments(new Set(filteredExperiments.map(exp => exp.id)));
    }
  };

  // Toggle individual experiment selection
  const handleSelectExperiment = (experimentId: string) => {
    const newSelected = new Set(selectedExperiments);
    if (newSelected.has(experimentId)) {
      newSelected.delete(experimentId);
    } else {
      newSelected.add(experimentId);
    }
    setSelectedExperiments(newSelected);
  };

  // Handle delete confirmation
  const handleDeleteClick = () => {
    if (selectedExperiments.size === 0) return;
    setShowDeleteDialog(true);
  };

  // Handle delete confirmation
  const handleDeleteConfirm = async (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();

    if (selectedExperiments.size === 0) return;

    try {
      const result = await deleteExperimentsMutation.mutateAsync(Array.from(selectedExperiments));
      console.log(`Successfully deleted ${result} experiments`);
      setSelectedExperiments(new Set());
      setShowDeleteDialog(false);
    } catch (error) {
      console.error('Failed to delete experiments:', error);
      alert('Failed to delete experiments. Please try again.');
    }
  };

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
              className="pl-8 h-9 text-[13px] font-medium focus:bg-blue-50 focus:border-blue-300 focus-visible:ring-0"
            />
          </div>

          {/* Label Filter */}
          <MultiSelectDropdown
            values={labelFilters}
            onChange={(values) => setLabelFilters(values)}
            options={labelOptions}
            className="w-64"
            placeholder="Filter by labels..."
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
              {searchQuery.trim() || statusFilter !== 'ALL' || labelFilters.length > 0
                ? 'No experiments match your filters'
                : 'No experiments found'}
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent border-b">
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">
                      <div className="flex items-center gap-2">
                        <Checkbox
                          checked={allSelected}
                          onChange={handleSelectAll}
                          aria-label="Select all experiments"
                        />
                        {selectedExperiments.size > 0 && (
                          <button
                            onClick={handleDeleteClick}
                            disabled={deleteExperimentsMutation.isPending}
                            className="inline-flex items-center justify-center h-6 w-6 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors disabled:opacity-50 disabled:pointer-events-none"
                            title={`Delete ${selectedExperiments.size} ${selectedExperiments.size === 1 ? 'experiment' : 'experiments'}`}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">ID</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Name</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Labels</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50">Status</TableHead>
                    <TableHead className="h-11 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/50 text-right">Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredExperiments.map((experiment, idx) => (
                    <TableRow
                      key={experiment.id}
                      className="hover:bg-accent/50 transition-colors border-b last:border-0"
                    >
                      <TableCell className="py-3">
                        <Checkbox
                          checked={selectedExperiments.has(experiment.id)}
                          onChange={() => handleSelectExperiment(experiment.id)}
                          aria-label={`Select experiment ${experiment.name}`}
                        />
                      </TableCell>
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
                            {experiment.labels.map((label, idx) => {
                              const colors = labelKeyColorMap.get(label.name) || LABEL_COLORS[0];
                              return (
                                <Badge
                                  key={idx}
                                  variant="outline"
                                  className={`text-xs px-2 py-0.5 font-normal ${colors.bg} ${colors.text} ${colors.border}`}
                                >
                                  {label.name}: {label.value}
                                </Badge>
                              );
                            })}
                          </div>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="py-3">
                        <Badge variant={STATUS_VARIANTS[experiment.status]}>
                          {experiment.status}
                        </Badge>
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

          {/* Pagination */}
          {filteredExperiments && filteredExperiments.length > 0 && (
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              pageSize={PAGE_SIZE}
              totalItems={totalExperiments}
              onPageChange={setCurrentPage}
              itemName="experiments"
            />
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent className="pointer-events-auto sm:max-w-[440px]">
          <DialogHeader className="space-y-3">
            <DialogTitle className="text-lg font-semibold text-foreground">
              Delete {selectedExperiments.size === 1 ? 'Experiment' : 'Experiments'}
            </DialogTitle>
            <DialogDescription className="text-sm text-muted-foreground leading-relaxed">
              You are about to delete <span className="font-medium text-foreground">{selectedExperiments.size}</span> {selectedExperiments.size === 1 ? 'experiment' : 'experiments'}.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setShowDeleteDialog(false);
              }}
              disabled={deleteExperimentsMutation.isPending}
              className="h-9"
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteExperimentsMutation.isPending}
              className="h-9"
            >
              {deleteExperimentsMutation.isPending ? (
                <>
                  <span className="mr-2">Deleting...</span>
                  <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-solid border-current border-r-transparent"></span>
                </>
              ) : (
                <>
                  <Trash2 className="h-3.5 w-3.5 mr-2" />
                  Delete
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
