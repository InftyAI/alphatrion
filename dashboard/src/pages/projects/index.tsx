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
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Skeleton } from '../../components/ui/skeleton';
import { formatDistanceToNow } from 'date-fns';

const PAGE_SIZE = 20;

export function ProjectsPage() {
  // Get selected team from context
  const { selectedTeamId } = useTeamContext();
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');

  const { data: projects, isLoading, error } = useProjects(selectedTeamId || '', {
    page: currentPage - 1,
    pageSize: PAGE_SIZE,
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
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Projects</h1>
      </div>

      <Card>
        <CardContent className="p-4">
          {/* Search Bar */}
          <div className="flex gap-2 mb-3 items-center">
            <div className="relative w-64">
              <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                placeholder="Search projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 h-9 text-sm focus:bg-blue-50 focus:border-blue-300 focus-visible:ring-0"
              />
            </div>
          </div>

          {!projects || projects.length === 0 ? (
            <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
              No projects found
            </div>
          ) : filteredProjects.length === 0 ? (
            <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
              No projects match your search
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="h-10 text-xs font-medium uppercase tracking-wide text-muted-foreground">UUID</TableHead>
                    <TableHead className="h-10 text-xs font-medium uppercase tracking-wide text-muted-foreground">Name</TableHead>
                    <TableHead className="h-10 text-xs font-medium uppercase tracking-wide text-muted-foreground">Description</TableHead>
                    <TableHead className="h-10 text-xs font-medium uppercase tracking-wide text-muted-foreground">Created</TableHead>
                    <TableHead className="h-10 text-xs font-medium uppercase tracking-wide text-muted-foreground">Updated</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredProjects.map((project) => (
                      <TableRow key={project.id}>
                        <TableCell className="py-3.5 font-mono text-sm">
                          <Link
                            to={`/projects/${project.id}`}
                            className="text-primary font-medium hover:underline"
                          >
                            {project.id}
                          </Link>
                        </TableCell>
                        <TableCell className="py-3.5 text-sm text-foreground">
                          {project.name || 'Unnamed Project'}
                        </TableCell>
                        <TableCell className="py-3.5 text-sm text-muted-foreground">
                          {project.description || '-'}
                        </TableCell>
                        <TableCell className="py-3.5 text-sm text-foreground">
                          {formatDistanceToNow(new Date(project.createdAt), {
                            addSuffix: true,
                          })}
                        </TableCell>
                        <TableCell className="py-3.5 text-sm text-foreground">
                          {formatDistanceToNow(new Date(project.updatedAt), {
                            addSuffix: true,
                          })}
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              <div className="mt-3 flex items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  Page {currentPage}
                </div>
                <div className="flex gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setCurrentPage(currentPage - 1);
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    disabled={currentPage === 1}
                    className="h-9 px-3 text-sm"
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setCurrentPage(currentPage + 1);
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    disabled={projects.length < PAGE_SIZE}
                    className="h-9 px-3 text-sm"
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
