import { useTeamContext } from '../../context/team-context';
import { useStatistics } from '../../hooks/use-statistics';
import { useProjects } from '../../hooks/use-projects';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import { Skeleton } from '../../components/ui/skeleton';
import {
  FolderKanban,
  FlaskConical,
  Play,
  TrendingUp,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export function DashboardPage() {
  const { selectedTeamId } = useTeamContext();

  const { data: statistics, isLoading: statisticsLoading } = useStatistics(
    selectedTeamId || '',
    { enabled: !!selectedTeamId }
  );

  const { data: recentProjects, isLoading: projectsLoading } = useProjects(
    selectedTeamId || '',
    { page: 0, pageSize: 5, enabled: !!selectedTeamId }
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Monitor your experiments and track progress across all projects
        </p>
      </div>

      {/* Statistics Grid */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Projects
              </CardTitle>
            </div>
            <FolderKanban className="h-5 w-5 text-blue-500" />
          </CardHeader>
          <CardContent>
            {statisticsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-3xl font-bold text-foreground">
                {statistics?.totalProjects || 0}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Experiments
              </CardTitle>
            </div>
            <FlaskConical className="h-5 w-5 text-purple-500" />
          </CardHeader>
          <CardContent>
            {statisticsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-3xl font-bold text-foreground">
                {statistics?.totalExperiments || 0}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Runs
              </CardTitle>
            </div>
            <Play className="h-5 w-5 text-green-500" />
          </CardHeader>
          <CardContent>
            {statisticsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-3xl font-bold text-foreground">
                {statistics?.totalRuns || 0}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Projects */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Recent Projects</CardTitle>
              <CardDescription className="mt-1">
                Quick access to your latest projects
              </CardDescription>
            </div>
            <Link
              to="/projects"
              className="text-sm text-primary hover:underline font-medium"
            >
              View all →
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          {projectsLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : !recentProjects || recentProjects.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FolderKanban className="h-12 w-12 text-muted-foreground mb-3" />
              <p className="text-muted-foreground">No projects yet</p>
              <p className="text-sm text-muted-foreground mt-1">
                Create your first project using the AlphaTrion SDK
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentProjects.map((project) => (
                <Link
                  key={project.id}
                  to={`/projects/${project.id}`}
                  className="block p-4 rounded-lg border hover:bg-accent transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h3 className="font-semibold text-foreground">
                        {project.name || 'Unnamed Project'}
                      </h3>
                      {project.description && (
                        <p className="text-sm text-muted-foreground mt-1 line-clamp-1">
                          {project.description}
                        </p>
                      )}
                    </div>
                    <TrendingUp className="h-4 w-4 text-muted-foreground ml-4" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
