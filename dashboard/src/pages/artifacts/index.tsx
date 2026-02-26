import { useState } from 'react';
import { useTags, useArtifactContent } from '../../hooks/use-artifacts';
import { useProjects } from '../../hooks/use-projects';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';
import { Skeleton } from '../../components/ui/skeleton';
import { useTeamContext } from '../../context/team-context';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import {
  FileText,
  Database,
  ChevronDown,
  ChevronRight,
  Search,
  Layers,
  ChevronLeft,
  Eye,
  Copy,
  Check,
} from 'lucide-react';

interface ArtifactSectionProps {
  teamId: string;
  projectId: string;
  repoType: 'execution' | 'checkpoint';
  icon: React.ReactNode;
  title: string;
  color: string;
}

function ArtifactSection({
  teamId,
  projectId,
  repoType,
  icon,
  title,
  color,
}: ArtifactSectionProps) {
  const { data: tags, isLoading } = useTags(teamId, projectId, repoType);
  const [isOpen, setIsOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedTag, setSelectedTag] = useState<string>('');
  const [copied, setCopied] = useState(false);
  const itemsPerPage = 10;

  // Use cached artifact content - only fetch when dialog is open and tag is selected
  const {
    data: artifactContent,
    isLoading: loadingArtifact,
    error: artifactError
  } = useArtifactContent(
    teamId,
    projectId,
    selectedTag,
    repoType,
    dialogOpen && Boolean(selectedTag)
  );

  const handleViewArtifact = (tag: string) => {
    setCopied(false);
    setSelectedTag(tag);
    setDialogOpen(true);
  };

  // Show error if artifact fetch fails
  if (artifactError && dialogOpen) {
    console.error('Failed to load artifact:', artifactError);
  }

  const handleCopy = () => {
    if (artifactContent?.content) {
      navigator.clipboard.writeText(artifactContent.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatContent = () => {
    if (!artifactContent) return '';

    const { content, filename, contentType } = artifactContent;

    // Try to parse and format JSON
    if (contentType === 'application/json' || filename.endsWith('.json')) {
      try {
        const parsed = JSON.parse(content);
        return JSON.stringify(parsed, null, 2);
      } catch {
        return content;
      }
    }

    return content;
  };

  const getLanguageClass = () => {
    if (!artifactContent) return '';

    const { filename, contentType } = artifactContent;

    if (contentType === 'application/json' || filename.endsWith('.json')) {
      return 'language-json';
    }
    return '';
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-2 rounded border bg-card">
        {icon}
        <div className="flex-1">
          <div className="text-xs font-medium">{title}</div>
          <Skeleton className="h-3 w-20 mt-0.5" />
        </div>
      </div>
    );
  }

  const totalPages = tags ? Math.ceil(tags.length / itemsPerPage) : 0;
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const displayTags = tags?.slice(startIndex, endIndex);
  const hasPagination = tags && tags.length > itemsPerPage;

  return (
    <div className="rounded border bg-card hover:bg-accent/50 transition-colors self-start">
      <button
        className="w-full flex items-center gap-2 p-2 text-left"
        onClick={() => setIsOpen(!isOpen)}
      >
        {icon}
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium">{title}</div>
          <div className="text-xs text-muted-foreground">
            {!tags || tags.length === 0 ? (
              'No artifacts'
            ) : (
              `${tags.length} item${tags.length === 1 ? '' : 's'}`
            )}
          </div>
        </div>
        {tags && tags.length > 0 && (
          <>
            <Badge variant="secondary" className={`${color} text-xs h-5 px-1.5`}>
              {tags.length}
            </Badge>
            {isOpen ? (
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
            )}
          </>
        )}
      </button>

      {isOpen && tags && tags.length > 0 && (
        <div className="px-2 pb-2">
          <div className="h-px bg-border mb-1" />
          <div className="space-y-0.5">
            {displayTags?.map((tag, index) => (
              <button
                key={tag}
                onClick={(e) => {
                  e.stopPropagation();
                  handleViewArtifact(tag);
                }}
                disabled={loadingArtifact}
                className="w-full flex items-center gap-1.5 py-1 px-1.5 rounded hover:bg-muted/50 transition-colors cursor-pointer group text-left"
              >
                <span className="text-xs text-muted-foreground font-mono w-8 flex-shrink-0">
                  {startIndex + index + 1}.
                </span>
                <code className="text-sm bg-muted px-1.5 py-0.5 rounded flex-1 truncate">
                  {tag}
                </code>
                <Eye className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
              </button>
            ))}
          </div>
          {hasPagination && (
            <div className="flex items-center justify-between gap-2 mt-2 pt-2 border-t">
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  setCurrentPage((p) => Math.max(1, p - 1));
                }}
                disabled={currentPage === 1}
                className="h-7 w-7 p-0"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </Button>
              <span className="text-xs text-muted-foreground">
                Page {currentPage} of {totalPages}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  setCurrentPage((p) => Math.min(totalPages, p + 1));
                }}
                disabled={currentPage === totalPages}
                className="h-7 w-7 p-0"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Artifact Content Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[85vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <DialogTitle className="text-base">Artifact Content</DialogTitle>
                <DialogDescription className="text-xs font-mono mt-1 truncate">
                  {artifactContent?.filename || 'Loading...'}
                </DialogDescription>
              </div>
              {artifactContent && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopy}
                  className="ml-2 h-7 w-7 p-0 flex-shrink-0"
                  title={copied ? 'Copied!' : 'Copy to clipboard'}
                >
                  {copied ? (
                    <Check className="h-3.5 w-3.5 text-green-600" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </Button>
              )}
            </div>
          </DialogHeader>
          <div className="flex-1 overflow-auto border rounded-md bg-slate-950 dark:bg-slate-950">
            {loadingArtifact && !artifactContent ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-slate-400 text-sm">Loading artifact...</div>
              </div>
            ) : artifactError ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-red-400 text-sm">Failed to load artifact</div>
              </div>
            ) : (
              <pre className={`text-xs p-4 overflow-auto text-slate-50 ${getLanguageClass()}`}>
                <code className="text-slate-50">{formatContent()}</code>
              </pre>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ProjectCard({ project, teamId }: { project: any; teamId: string }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <Card className="overflow-hidden hover:shadow-sm transition-shadow">
      <CardHeader
        className="cursor-pointer hover:bg-muted/30 transition-colors p-3"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <div className="flex-shrink-0">
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <CardTitle className="text-sm font-medium truncate">
                {project.name}{' '}
                <span className="text-sm text-muted-foreground font-normal">
                  ({project.id})
                </span>
              </CardTitle>
            </div>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <Layers className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="pt-0 pb-2 px-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {/* Execution Results */}
            <ArtifactSection
              teamId={teamId}
              projectId={project.id}
              repoType="execution"
              icon={<FileText className="h-3.5 w-3.5 text-blue-500" />}
              title="Execution Results"
              color="bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
            />

            {/* Checkpoints */}
            <ArtifactSection
              teamId={teamId}
              projectId={project.id}
              repoType="checkpoint"
              icon={<Database className="h-3.5 w-3.5 text-green-500" />}
              title="Checkpoints"
              color="bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
            />
          </div>
        </CardContent>
      )}
    </Card>
  );
}

export function ArtifactsPage() {
  const { selectedTeamId } = useTeamContext();
  const [searchQuery, setSearchQuery] = useState('');

  const { data: projects, isLoading: projectsLoading } = useProjects(
    selectedTeamId || '',
    {
      pageSize: 100,
    }
  );

  // Filter projects based on search query
  const filteredProjects = projects?.filter((project) =>
    project.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    project.id?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-3 pb-6">
      {/* Page Header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">
            Artifacts
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Browse execution results and checkpoints across all projects
          </p>
        </div>
        <Badge variant="secondary" className="text-xs h-6 px-2">
          {projects?.length || 0} projects
        </Badge>
      </div>

      {/* Search Bar */}
      {projects && projects.length > 0 && (
        <div className="relative max-w-md">
          <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 h-9 text-sm focus:bg-blue-50 focus:border-blue-300 focus-visible:ring-0"
          />
        </div>
      )}

      {/* Projects List */}
      {projectsLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      ) : !projects || projects.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-10">
            <div className="rounded-full bg-muted p-3 mb-3">
              <Layers className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="text-xs font-semibold mb-1">No Projects Found</h3>
            <p className="text-xs text-muted-foreground text-center max-w-sm">
              Create a project to start managing artifacts for your experiments
            </p>
          </CardContent>
        </Card>
      ) : filteredProjects && filteredProjects.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8">
            <Search className="h-8 w-8 text-muted-foreground mb-2" />
            <h3 className="text-xs font-semibold mb-0.5">No matches found</h3>
            <p className="text-xs text-muted-foreground">
              Try adjusting your search query
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {filteredProjects?.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              teamId={selectedTeamId || ''}
            />
          ))}
        </div>
      )}
    </div>
  );
}
