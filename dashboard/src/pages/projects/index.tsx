import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
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
import { Input } from '../../components/ui/input';
import { Skeleton } from '../../components/ui/skeleton';
import { formatDistanceToNow } from 'date-fns';

export function ProjectsPage() {
  // Get selected team from context
  const { selectedTeamId } = useTeamContext();
  const [searchQuery, setSearchQuery] = useState('');

  const { data: projects, isLoading, error } = useProjects(selectedTeamId || '', {
    page: 0,
    pageSize: 100,
    enabled: !!selectedTeamId, // Only fetch projects if we have a team ID
  });

  // Filter projects based on search query
  const filteredProjects = useMemo(() => {
    if (!projects) return [];

    let filtered = [...projects];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (project) =>
          project.name?.toLowerCase().includes(query) ||
          project.description?.toLowerCase().includes(query) ||
          project.id?.toLowerCase().includes(query)
      );
    }

    // Sort by creation time descending
    filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return filtered;
  }, [projects, searchQuery]);

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
          The list of projects for the selected team. Click to view more details.
        </p>
      </div>

      <Card>
        <CardContent className="p-3 pt-3">
          {/* Search Bar */}
          <div className="mb-4 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search projects by name, UUID, or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          {!projects || projects.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              No projects found
            </div>
          ) : filteredProjects.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              No projects match your search
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>UUID</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Updated</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredProjects.map((project) => (
                      <TableRow key={project.id}>
                        <TableCell className="font-mono text-sm">
                          <Link
                            to={`/projects/${project.id}`}
                            className="text-primary hover:underline"
                          >
                            {project.id}
                          </Link>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {project.name || 'Unnamed Project'}
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
