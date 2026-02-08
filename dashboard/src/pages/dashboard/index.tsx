import { useTeamContext } from '../../context/team-context';
import { useProjects } from '../../hooks/use-projects';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import { Skeleton } from '../../components/ui/skeleton';
import {
  FolderKanban,
  FlaskConical,
  Play,
} from 'lucide-react';

export function DashboardPage() {
  const { selectedTeamId } = useTeamContext();

  const { data: projects, isLoading: projectsLoading } = useProjects(
    selectedTeamId || '',
    { page: 0, pageSize: 1000, enabled: !!selectedTeamId }
  );

  const totalProjects = projects?.length || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
        <p className="mt-2 text-muted-foreground">
          Overview and statistics
        </p>
      </div>

      {/* Statistics Grid */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Projects</CardTitle>
            <FolderKanban className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {projectsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{totalProjects}</div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              In selected team
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Experiments</CardTitle>
            <FlaskConical className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-muted-foreground">-</div>
            <p className="text-xs text-muted-foreground mt-1">
              Requires backend aggregation
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
            <Play className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-muted-foreground">-</div>
            <p className="text-xs text-muted-foreground mt-1">
              Requires backend aggregation
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
