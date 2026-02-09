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
import { FolderKanban, FlaskConical, Play, Building2 } from 'lucide-react';

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
    <div className="space-y-3">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-foreground">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Overview of your projects, experiments, and runs
        </p>
      </div>

      {/* Team Info */}
      {teamLoading ? (
        <Skeleton className="h-16 w-full" />
      ) : team ? (
        <Card>
          <CardContent className="p-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-2.5">
                <div className="flex items-center gap-1.5">
                  <Building2 className="h-3.5 w-3.5 text-blue-600" />
                  <h3 className="text-sm font-semibold text-foreground">{team.name || 'Unnamed Team'}</h3>
                </div>
                <span className="text-xs text-muted-foreground font-mono">{team.id}</span>
              </div>
              {team.description && (
                <p className="mt-0.5 text-xs text-muted-foreground">{team.description}</p>
              )}
            </div>
            {team.meta && Object.keys(team.meta).length > 0 && (
              <div className="mt-2.5 pt-2.5 border-t space-y-2">
                <h4 className="text-xs font-semibold text-foreground">Metadata</h4>
                <dl className="grid grid-cols-3 gap-2.5">
                  {Object.entries(team.meta).map(([key, value]) => (
                    <div key={key}>
                      <dt className="text-xs text-muted-foreground font-medium">{key}</dt>
                      <dd className="mt-1 text-foreground font-mono text-xs truncate">
                        {typeof value === 'string' ? value : JSON.stringify(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

      {/* Overview Section */}
      <div>
        <h2 className="text-lg font-semibold text-foreground mb-2">Overview</h2>
      </div>

      {/* Overview Metrics */}
      {teamLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
          {/* Total Projects */}
          <Card>
            <CardContent className="p-3">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-xs text-muted-foreground">Projects</p>
                  <p className="text-lg font-bold text-foreground">{team?.totalProjects || 0}</p>
                </div>
                <div className="p-1.5 bg-blue-100 rounded-lg">
                  <FolderKanban className="h-3.5 w-3.5 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Total Experiments */}
          <Card>
            <CardContent className="p-3">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-xs text-muted-foreground">Experiments</p>
                  <p className="text-lg font-bold text-foreground">{team?.totalExperiments || 0}</p>
                </div>
                <div className="p-1.5 bg-purple-100 rounded-lg">
                  <FlaskConical className="h-3.5 w-3.5 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Total Runs */}
          <Card>
            <CardContent className="p-3">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-xs text-muted-foreground">Runs</p>
                  <p className="text-lg font-bold text-foreground">{team?.totalRuns || 0}</p>
                </div>
                <div className="p-1.5 bg-green-100 rounded-lg">
                  <Play className="h-3.5 w-3.5 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Experiments Charts */}
      <div className="space-y-3">
        {/* Time Range Selector */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Activity</h2>
          <div className="flex gap-1">
            {TIME_RANGE_OPTIONS.map((option) => (
              <Button
                key={option.value}
                variant="outline"
                size="sm"
                onClick={() => setTimeRange(option.value)}
                className={`h-8 px-2.5 text-xs transition-colors ${
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

        <div className="grid gap-3 md:grid-cols-2">
          {/* Status Distribution Pie Chart */}
          <Card>
            <CardContent className="p-4">
              {experimentsLoading ? (
                <Skeleton className="h-56 w-full" />
              ) : filteredExperiments && filteredExperiments.length > 0 ? (
                <ExperimentsStatusChart experiments={filteredExperiments} />
              ) : (
                <div className="flex h-56 items-center justify-center text-sm text-muted-foreground">
                  No experiments data available for this time range
                </div>
              )}
            </CardContent>
          </Card>

          {/* Timeline Chart */}
          <Card>
            <CardContent className="p-4">
              {experimentsLoading ? (
                <Skeleton className="h-56 w-full" />
              ) : filteredExperiments && filteredExperiments.length > 0 ? (
                <ExperimentsTimelineChart experiments={filteredExperiments} timeRange={timeRange} />
              ) : (
                <div className="flex h-56 items-center justify-center text-sm text-muted-foreground">
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
