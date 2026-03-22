import { useState, useMemo } from 'react';
import { useTeamContext } from '../../context/team-context';
import { useTeam } from '../../hooks/use-teams';
import { useTeamExperiments } from '../../hooks/use-team-experiments';
import { useDailyTokenUsage } from '../../hooks/use-token-usage';
import { useModelDistributions } from '../../hooks/use-model-distributions';
import {
  Card,
  CardContent,
} from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Skeleton } from '../../components/ui/skeleton';
import { ExperimentsTimelineChart } from '../../components/dashboard/experiments-timeline-chart';
import { ExperimentsStatusChart } from '../../components/dashboard/experiments-status-chart';
import { DailyTokenUsageChart } from '../../components/dashboard/daily-token-usage-chart';
import { ModelDistributionChart } from '../../components/dashboard/model-distribution-chart';
import { subDays, subMonths } from 'date-fns';
import { FlaskConical, Coins, Bot, MessagesSquare } from 'lucide-react';

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

  // Get days for selected time range
  const days = TIME_RANGE_OPTIONS.find((opt) => opt.value === timeRange)?.days || 30;

  const { data: dailyTokenUsage, isLoading: tokenUsageLoading } = useDailyTokenUsage(
    selectedTeamId || '',
    days
  );

  const { data: modelDistributions, isLoading: modelDistributionsLoading } = useModelDistributions(
    selectedTeamId || ''
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
    <div className="space-y-2">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">Dashboard</h1>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Overview of your team's experiments and activity
        </p>
      </div>

      {/* Overview Section */}
      <div>
        <h2 className="text-sm font-semibold text-foreground mb-1.5">Overview</h2>
      </div>

      {/* Overview Metrics */}
      {teamLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2">
          {/* Total Experiments */}
          <Card>
            <CardContent className="p-2.5">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-[10px] font-medium text-muted-foreground">EXPERIMENTS</p>
                  <p className="text-base font-bold tabular-nums text-foreground">{team?.totalExperiments || 0}</p>
                </div>
                <div className="p-1.5 bg-purple-100 rounded-lg">
                  <FlaskConical className="h-3.5 w-3.5 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Total Agents */}
          <Card>
            <CardContent className="p-2.5">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-[10px] font-medium text-muted-foreground">AGENTS</p>
                  <p className="text-base font-bold tabular-nums text-foreground">{team?.totalAgents || 0}</p>
                </div>
                <div className="p-1.5 bg-blue-100 rounded-lg">
                  <Bot className="h-3.5 w-3.5 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Total Sessions */}
          <Card>
            <CardContent className="p-2.5">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-[10px] font-medium text-muted-foreground">SESSIONS</p>
                  <p className="text-base font-bold tabular-nums text-foreground">{team?.totalSessions || 0}</p>
                </div>
                <div className="p-1.5 bg-green-100 rounded-lg">
                  <MessagesSquare className="h-3.5 w-3.5 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Total Tokens */}
          <Card>
            <CardContent className="p-2.5">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-[10px] font-medium text-muted-foreground">TOKENS</p>
                  <p className="text-base font-bold tabular-nums text-foreground">
                    {(team?.aggregatedTokens?.totalTokens || 0).toLocaleString()}
                    <span className="text-muted-foreground text-[10px] ml-1 font-normal">
                      ({(team?.aggregatedTokens?.inputTokens || 0).toLocaleString()}↓ {(team?.aggregatedTokens?.outputTokens || 0).toLocaleString()}↑)
                    </span>
                  </p>
                </div>
                <div className="p-1.5 bg-orange-100 rounded-lg">
                  <Coins className="h-3.5 w-3.5 text-orange-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Experiments Charts */}
      <div className="space-y-2">
        {/* Time Range Selector */}
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">Activity</h2>
          <div className="flex gap-1">
            {TIME_RANGE_OPTIONS.map((option) => (
              <Button
                key={option.value}
                variant="outline"
                size="sm"
                onClick={() => setTimeRange(option.value)}
                className={`h-7 px-2 text-[11px] transition-colors ${timeRange === option.value
                    ? 'bg-blue-50 border-blue-300 text-blue-700 hover:bg-blue-100'
                    : 'bg-white hover:bg-gray-50'
                  }`}
              >
                {option.label}
              </Button>
            ))}
          </div>
        </div>

        {/* First Row: Experiments Charts */}
        <div className="grid gap-2 md:grid-cols-2">
          {/* Status Distribution Pie Chart */}
          <Card>
            <CardContent className="p-3">
              {experimentsLoading ? (
                <Skeleton className="h-60 w-full" />
              ) : (
                <ExperimentsStatusChart experiments={filteredExperiments || []} />
              )}
            </CardContent>
          </Card>

          {/* Timeline Chart */}
          <Card>
            <CardContent className="p-3">
              {experimentsLoading ? (
                <Skeleton className="h-60 w-full" />
              ) : (
                <ExperimentsTimelineChart experiments={filteredExperiments || []} timeRange={timeRange} />
              )}
            </CardContent>
          </Card>
        </div>

        {/* Second Row: Model Distribution and Token Usage */}
        <div className="grid gap-2 md:grid-cols-2">
          {/* Model Distribution Pie Chart */}
          <Card>
            <CardContent className="p-3">
              {modelDistributionsLoading ? (
                <Skeleton className="h-60 w-full" />
              ) : (
                <ModelDistributionChart data={modelDistributions || []} />
              )}
            </CardContent>
          </Card>

          {/* Token Usage Chart */}
          <Card>
            <CardContent className="p-3">
              {tokenUsageLoading ? (
                <Skeleton className="h-60 w-full" />
              ) : dailyTokenUsage ? (
                <DailyTokenUsageChart data={dailyTokenUsage} timeRange={timeRange} />
              ) : (
                <div className="flex items-center justify-center h-60 text-xs text-muted-foreground">
                  No token usage data available for this time range
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
