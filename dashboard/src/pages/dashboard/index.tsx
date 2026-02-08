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
import { FolderKanban, FlaskConical, Play } from 'lucide-react';

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
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Overview of your projects, experiments, and runs
        </p>
      </div>

      {/* Overview Metrics */}
      {teamLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Total Projects */}
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Projects</p>
                  <p className="text-2xl font-bold text-foreground">{team?.totalProjects || 0}</p>
                </div>
                <div className="p-2.5 bg-blue-100 rounded-lg">
                  <FolderKanban className="h-5 w-5 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Total Experiments */}
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Experiments</p>
                  <p className="text-2xl font-bold text-foreground">{team?.totalExperiments || 0}</p>
                </div>
                <div className="p-2.5 bg-purple-100 rounded-lg">
                  <FlaskConical className="h-5 w-5 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Total Runs */}
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Runs</p>
                  <p className="text-2xl font-bold text-foreground">{team?.totalRuns || 0}</p>
                </div>
                <div className="p-2.5 bg-green-100 rounded-lg">
                  <Play className="h-5 w-5 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Experiments Charts */}
      <div className="space-y-5">
        {/* Time Range Selector */}
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-foreground">Activity</h2>
          <div className="flex gap-1.5">
            {TIME_RANGE_OPTIONS.map((option) => (
              <Button
                key={option.value}
                variant="outline"
                size="sm"
                onClick={() => setTimeRange(option.value)}
                className={`h-8 px-3 transition-colors ${
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

        <div className="grid gap-5 md:grid-cols-2">
          {/* Status Distribution Pie Chart */}
          <Card>
            <CardContent className="p-5">
              {experimentsLoading ? (
                <Skeleton className="h-72 w-full" />
              ) : filteredExperiments && filteredExperiments.length > 0 ? (
                <ExperimentsStatusChart experiments={filteredExperiments} />
              ) : (
                <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
                  No experiments data available for this time range
                </div>
              )}
            </CardContent>
          </Card>

          {/* Timeline Chart */}
          <Card>
            <CardContent className="p-5">
              {experimentsLoading ? (
                <Skeleton className="h-72 w-full" />
              ) : filteredExperiments && filteredExperiments.length > 0 ? (
                <ExperimentsTimelineChart experiments={filteredExperiments} timeRange={timeRange} />
              ) : (
                <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
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
