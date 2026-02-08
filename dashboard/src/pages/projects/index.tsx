import { Link } from 'react-router-dom';
import { useTeamContext } from '../../context/team-context';
import { useProjects } from '../../hooks/use-projects';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';
import { Skeleton } from '../../components/ui/skeleton';
import { formatDistanceToNow } from 'date-fns';

export function ProjectsPage() {
  // Get selected team from context
  const { selectedTeamId } = useTeamContext();

  const { data: projects, isLoading, error } = useProjects(selectedTeamId || '', {
    page: 0,
    pageSize: 100,
    enabled: !!selectedTeamId, // Only fetch projects if we have a team ID
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!selectedTeamId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No Team Selected</CardTitle>
          <CardDescription>Please select a team from the dropdown above</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Use the team switcher in the header to select a team.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Error</CardTitle>
          <CardDescription>Failed to load projects</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-destructive">{error.message}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Projects</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your AI experiment projects
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          {!projects || projects.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              No projects found
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Updated</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {[...projects]
                    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
                    .map((project) => (
                    <TableRow key={project.id}>
                      <TableCell>
                        <Link
                          to={`/projects/${project.id}`}
                          className="font-medium text-primary hover:underline"
                        >
                          {project.name || 'Unnamed Project'}
                        </Link>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {project.description || '-'}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDistanceToNow(new Date(project.createdAt), {
                          addSuffix: true,
                        })}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDistanceToNow(new Date(project.updatedAt), {
                          addSuffix: true,
                        })}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
