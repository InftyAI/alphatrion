import { useState, useMemo } from 'react';
import { useTeamContext } from '../../context/team-context';
import { useTeam } from '../../hooks/use-teams';
import { useTeamExperiments } from '../../hooks/use-team-experiments';
import {
  Card,
  CardContent,
} from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Skeleton } from '../../components/ui/skeleton';
import { ExperimentsTimelineChart } from '../../components/dashboard/experiments-timeline-chart';
import { ExperimentsStatusChart } from '../../components/dashboard/experiments-status-chart';
import { subDays, subMonths } from 'date-fns';

type TimeRange = '7days' | '1month' | '3months';

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string; days: number }[] = [
  { value: '7days', label: '7 Days', days: 7 },
  { value: '1month', label: '1 Month', days: 30 },
  { value: '3months', label: '3 Months', days: 90 },
];

export function DashboardPage() {
  const { selectedTeamId } = useTeamContext();
  const [timeRange, setTimeRange] = useState<TimeRange>('7days');

  const { data: team, isLoading: teamLoading } = useTeam(selectedTeamId || '');

  const { data: teamExperiments, isLoading: experimentsLoading } = useTeamExperiments(
    selectedTeamId || '',
    { enabled: !!selectedTeamId }
  );

  // Filter experiments based on selected time range
  const filteredExperiments = useMemo(() => {
    if (!teamExperiments) return [];

    const now = new Date();
    const startDate =
      timeRange === '7days'
        ? subDays(now, 7)
        : timeRange === '1month'
        ? subMonths(now, 1)
        : subMonths(now, 3);

    return teamExperiments.filter((exp) => {
      const expDate = new Date(exp.createdAt);
      return expDate >= startDate && expDate <= now;
    });
  }, [teamExperiments, timeRange]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          An overview of your projects, experiments, and runs.
        </p>
      </div>

      {/* Overview */}
      <Card>
        <CardContent className="p-6 pt-6">
          <h3 className="text-sm font-semibold mb-4">Overview</h3>
          {teamLoading ? (
            <div className="grid grid-cols-3 gap-6">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : (
            <dl className="grid grid-cols-3 gap-6 text-sm">
              <div className="flex flex-col">
                <dt className="font-medium text-muted-foreground whitespace-nowrap">Projects</dt>
                <dd className="mt-2 text-3xl font-bold text-foreground">
                  {team?.totalProjects || 0}
                </dd>
              </div>
              <div className="flex flex-col">
                <dt className="font-medium text-muted-foreground whitespace-nowrap">Experiments</dt>
                <dd className="mt-2 text-3xl font-bold text-foreground">
                  {team?.totalExperiments || 0}
                </dd>
              </div>
              <div className="flex flex-col">
                <dt className="font-medium text-muted-foreground whitespace-nowrap">Runs</dt>
                <dd className="mt-2 text-3xl font-bold text-foreground">
                  {team?.totalRuns || 0}
                </dd>
              </div>
            </dl>
          )}
        </CardContent>
      </Card>

      {/* Experiments Charts */}
      <div className="space-y-4">
        {/* Time Range Selector */}
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Experiments Overview</h3>
          <div className="flex gap-2">
            {TIME_RANGE_OPTIONS.map((option) => (
              <Button
                key={option.value}
                variant="outline"
                size="sm"
                onClick={() => setTimeRange(option.value)}
                className={`transition-colors ${
                  timeRange === option.value
                    ? 'bg-blue-50 border-blue-300 text-blue-700 hover:bg-blue-100'
                    : 'bg-white hover:bg-gray-50'
                }`}
              >
                {option.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Status Distribution Pie Chart */}
          <Card>
            <CardContent className="p-6 pt-6">
              {experimentsLoading ? (
                <Skeleton className="h-80 w-full" />
              ) : filteredExperiments && filteredExperiments.length > 0 ? (
                <ExperimentsStatusChart experiments={filteredExperiments} />
              ) : (
                <div className="flex h-80 items-center justify-center text-muted-foreground">
                  No experiments data available for this time range
                </div>
              )}
            </CardContent>
          </Card>

          {/* Timeline Chart */}
          <Card>
            <CardContent className="p-6 pt-6">
              {experimentsLoading ? (
                <Skeleton className="h-80 w-full" />
              ) : filteredExperiments && filteredExperiments.length > 0 ? (
                <ExperimentsTimelineChart experiments={filteredExperiments} timeRange={timeRange} />
              ) : (
                <div className="flex h-80 items-center justify-center text-muted-foreground">
                  No experiments data available for this time range
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
