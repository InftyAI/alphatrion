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
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          An overview of your projects, experiments, and runs.
        </p>
      </div>

      {/* Overview Metrics */}
      {teamLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Total Projects */}
          <Card className="overflow-hidden">
            <CardContent className="p-0">
              <div className="flex items-center justify-between p-6 bg-gradient-to-br from-blue-50 to-blue-100/50">
                <div>
                  <p className="text-sm font-medium text-blue-600 whitespace-nowrap">Total Projects</p>
                  <p className="text-3xl font-bold text-blue-900 mt-2">{team?.totalProjects || 0}</p>
                </div>
                <div className="p-3 bg-blue-500 rounded-xl">
                  <FolderKanban className="h-6 w-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Total Experiments */}
          <Card className="overflow-hidden">
            <CardContent className="p-0">
              <div className="flex items-center justify-between p-6 bg-gradient-to-br from-purple-50 to-purple-100/50">
                <div>
                  <p className="text-sm font-medium text-purple-600 whitespace-nowrap">Total Experiments</p>
                  <p className="text-3xl font-bold text-purple-900 mt-2">{team?.totalExperiments || 0}</p>
                </div>
                <div className="p-3 bg-purple-500 rounded-xl">
                  <FlaskConical className="h-6 w-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Total Runs */}
          <Card className="overflow-hidden">
            <CardContent className="p-0">
              <div className="flex items-center justify-between p-6 bg-gradient-to-br from-green-50 to-green-100/50">
                <div>
                  <p className="text-sm font-medium text-green-600 whitespace-nowrap">Total Runs</p>
                  <p className="text-3xl font-bold text-green-900 mt-2">{team?.totalRuns || 0}</p>
                </div>
                <div className="p-3 bg-green-500 rounded-xl">
                  <Play className="h-6 w-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

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
