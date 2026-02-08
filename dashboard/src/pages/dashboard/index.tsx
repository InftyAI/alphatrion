import { useTeamContext } from '../../context/team-context';
import { useTeam } from '../../hooks/use-teams';
import { useTeamExperiments } from '../../hooks/use-team-experiments';
import {
  Card,
  CardContent,
} from '../../components/ui/card';
import { Skeleton } from '../../components/ui/skeleton';
import { ExperimentsTimelineChart } from '../../components/dashboard/experiments-timeline-chart';
import { ExperimentsStatusChart } from '../../components/dashboard/experiments-status-chart';

export function DashboardPage() {
  const { selectedTeamId } = useTeamContext();

  const { data: team, isLoading: teamLoading } = useTeam(selectedTeamId || '');

  const { data: teamExperiments, isLoading: experimentsLoading } = useTeamExperiments(
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
          {teamLoading ? (
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
                  {team?.totalProjects || 0}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-muted-foreground">Experiments</dt>
                <dd className="mt-1 text-3xl font-bold text-foreground">
                  {team?.totalExperiments || 0}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-muted-foreground">Runs</dt>
                <dd className="mt-1 text-3xl font-bold text-foreground">
                  {team?.totalRuns || 0}
                </dd>
              </div>
            </dl>
          )}
        </CardContent>
      </Card>

      {/* Experiments Charts */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Status Distribution Pie Chart */}
        <Card>
          <CardContent className="p-6 pt-6">
            {experimentsLoading ? (
              <Skeleton className="h-80 w-full" />
            ) : teamExperiments && teamExperiments.length > 0 ? (
              <ExperimentsStatusChart experiments={teamExperiments} />
            ) : (
              <div className="flex h-80 items-center justify-center text-muted-foreground">
                No experiments data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Timeline Chart */}
        <Card>
          <CardContent className="p-6 pt-6">
            {experimentsLoading ? (
              <Skeleton className="h-80 w-full" />
            ) : teamExperiments && teamExperiments.length > 0 ? (
              <ExperimentsTimelineChart experiments={teamExperiments} />
            ) : (
              <div className="flex h-80 items-center justify-center text-muted-foreground">
                No experiments data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
