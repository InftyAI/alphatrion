import { useTeamContext } from '../../context/team-context';
import { useStatistics } from '../../hooks/use-statistics';
import { useTeamRuns } from '../../hooks/use-team-runs';
import {
  Card,
  CardContent,
} from '../../components/ui/card';
import { Skeleton } from '../../components/ui/skeleton';
import { RunsTimelineChart } from '../../components/dashboard/runs-timeline-chart';

export function DashboardPage() {
  const { selectedTeamId } = useTeamContext();

  const { data: statistics, isLoading: statisticsLoading } = useStatistics(
    selectedTeamId || '',
    { enabled: !!selectedTeamId }
  );

  const { data: teamRuns, isLoading: runsLoading } = useTeamRuns(
    selectedTeamId || '',
    { enabled: !!selectedTeamId }
  );

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
          {statisticsLoading ? (
            <div className="grid grid-cols-3 gap-4">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : (
            <dl className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <dt className="font-medium text-muted-foreground">Projects</dt>
                <dd className="mt-1 text-3xl font-bold text-foreground">
                  {statistics?.totalProjects || 0}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-muted-foreground">Experiments</dt>
                <dd className="mt-1 text-3xl font-bold text-foreground">
                  {statistics?.totalExperiments || 0}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-muted-foreground">Runs</dt>
                <dd className="mt-1 text-3xl font-bold text-foreground">
                  {statistics?.totalRuns || 0}
                </dd>
              </div>
            </dl>
          )}
        </CardContent>
      </Card>

      {/* Runs Timeline Chart */}
      <Card>
        <CardContent className="p-6 pt-6">
          {runsLoading ? (
            <Skeleton className="h-80 w-full" />
          ) : teamRuns && teamRuns.length > 0 ? (
            <RunsTimelineChart runs={teamRuns} />
          ) : (
            <div className="flex h-80 items-center justify-center text-muted-foreground">
              No runs data available
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
