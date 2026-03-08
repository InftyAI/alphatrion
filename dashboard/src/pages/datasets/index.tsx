import { useState, useMemo, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Database, Search, Eye, ExternalLink, FileText, X } from 'lucide-react';
import { useTeamContext } from '../../context/team-context';
import { useDatasets } from '../../hooks/use-datasets';
import { useArtifactFiles, useArtifactContent } from '../../hooks/use-artifacts';
import {
  Card,
  CardContent,
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
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { Pagination } from '../../components/ui/pagination';
import { ArtifactViewer } from '../../components/artifact-viewer';
import { formatDistanceToNow } from 'date-fns';
import type { Dataset } from '../../types';

const PAGE_SIZE = 10;

export function DatasetsPage() {
  const { selectedTeamId } = useTeamContext();
  const [searchParams] = useSearchParams();
  const [currentPage, setCurrentPage] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [contentDialogOpen, setContentDialogOpen] = useState(false);

  // Handle URL search parameters
  useEffect(() => {
    const experimentId = searchParams.get('experimentId');
    const runId = searchParams.get('runId');

    if (experimentId) {
      setSearchQuery(experimentId);
    } else if (runId) {
      setSearchQuery(runId);
    }
  }, [searchParams]);

  const { data: datasets, isLoading } = useDatasets(
    selectedTeamId || '',
    { page: currentPage, pageSize: PAGE_SIZE, enabled: !!selectedTeamId }
  );

  // Parse dataset path to extract repo name and tag
  const parseDatasetPath = (path: string) => {
    const match = path.match(/^[^/]+\/([^:]+):(.+)$/);
    if (match) {
      return { repoName: match[1], tag: match[2] };
    }
    return { repoName: '', tag: '' };
  };

  const { repoName, tag } = selectedDataset
    ? parseDatasetPath(selectedDataset.path)
    : { repoName: '', tag: '' };

  const { data: files, isLoading: filesLoading } = useArtifactFiles(
    selectedTeamId || '',
    tag,
    repoName,
    Boolean(selectedDataset)
  );

  const {
    data: fileContent,
    isLoading: contentLoading,
    error: contentError
  } = useArtifactContent(
    selectedTeamId || '',
    tag,
    repoName,
    selectedFile,
    contentDialogOpen && Boolean(selectedFile)
  );

  const handleViewFiles = (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setSelectedFile('');
  };

  const handleSelectFile = (filename: string) => {
    setSelectedFile(filename);
    setContentDialogOpen(true);
  };

  // Filter datasets based on search query
  const filteredDatasets = useMemo(() => {
    if (!datasets) return [];
    if (!searchQuery.trim()) return datasets;

    const query = searchQuery.toLowerCase();
    return datasets.filter((dataset) => {
      return (
        dataset.name.toLowerCase().includes(query) ||
        dataset.description?.toLowerCase().includes(query) ||
        dataset.experimentId?.toLowerCase().includes(query) ||
        dataset.runId?.toLowerCase().includes(query) ||
        dataset.id.toLowerCase().includes(query)
      );
    });
  }, [datasets, searchQuery]);

  // Calculate total pages and items
  const totalPages = datasets && datasets.length === PAGE_SIZE ? currentPage + 2 : currentPage + 1;
  const totalItems = datasets
    ? (datasets.length < PAGE_SIZE
        ? currentPage * PAGE_SIZE + datasets.length
        : (currentPage + 1) * PAGE_SIZE)
    : 0;

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (!selectedTeamId) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <Database className="h-12 w-12 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm font-medium mb-1">No team selected</p>
          <p className="text-xs text-muted-foreground">
            Please select a team to view datasets
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">Datasets</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Browse and manage datasets
          </p>
        </div>

        {/* Search Bar */}
        <div className="relative w-80">
          <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search datasets..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(0);
            }}
            className="pl-8 h-9 text-sm focus:bg-blue-50 focus:border-blue-300 focus-visible:ring-0"
          />
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="flex-1 grid grid-cols-12 gap-2 min-h-0">
        {/* Left: Datasets Table */}
        <div className={selectedDataset ? "col-span-8" : "col-span-12"}>
          <Card className="h-full flex flex-col">
            <CardContent className="p-0 flex-1 overflow-auto">
              {isLoading ? (
                <div className="p-3 space-y-1.5">
                  {[...Array(10)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : !datasets || datasets.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <Database className="h-10 w-10 text-muted-foreground/30 mb-3" />
                  <p className="text-sm font-medium">No datasets found</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Create your first dataset to get started
                  </p>
                </div>
              ) : filteredDatasets.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <Search className="h-10 w-10 text-muted-foreground/30 mb-3" />
                  <p className="text-sm font-medium">No matching datasets</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Try adjusting your search query
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="w-[35%] h-9">Name</TableHead>
                      <TableHead className="w-[25%] h-9">Description</TableHead>
                      <TableHead className="w-[15%] h-9">Experiment</TableHead>
                      <TableHead className="w-[15%] h-9">Run</TableHead>
                      <TableHead className="w-[10%] h-9 text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredDatasets.map((dataset) => (
                      <TableRow
                        key={dataset.id}
                        className={selectedDataset?.id === dataset.id ? 'bg-accent/50' : ''}
                      >
                        <TableCell className="py-2">
                          <div className="flex items-center gap-2">
                            <Database className="h-4 w-4 text-blue-500 flex-shrink-0" />
                            <div className="min-w-0">
                              <p className="text-sm font-medium truncate">{dataset.name}</p>
                              <p className="text-xs text-muted-foreground">
                                {formatDistanceToNow(new Date(dataset.createdAt), {
                                  addSuffix: true,
                                })}
                              </p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="py-2">
                          <p className="text-sm text-muted-foreground line-clamp-1">
                            {dataset.description || '-'}
                          </p>
                        </TableCell>
                        <TableCell className="py-2">
                          {dataset.experimentId ? (
                            <Link
                              to={`/experiments/${dataset.experimentId}`}
                              className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 hover:underline"
                            >
                              <span className="font-mono truncate max-w-[100px]">
                                {dataset.experimentId.slice(0, 8)}
                              </span>
                              <ExternalLink className="h-3.5 w-3.5 flex-shrink-0" />
                            </Link>
                          ) : (
                            <span className="text-sm text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="py-2">
                          {dataset.runId ? (
                            <Link
                              to={`/runs/${dataset.runId}`}
                              className="inline-flex items-center gap-1 text-sm text-green-600 hover:text-green-700 hover:underline"
                            >
                              <span className="font-mono truncate max-w-[100px]">
                                {dataset.runId.slice(0, 8)}
                              </span>
                              <ExternalLink className="h-3.5 w-3.5 flex-shrink-0" />
                            </Link>
                          ) : (
                            <span className="text-sm text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="py-2 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewFiles(dataset)}
                            className="h-7 px-2"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>

            {/* Pagination */}
            {datasets && datasets.length > 0 && totalPages > 1 && (
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                pageSize={PAGE_SIZE}
                totalItems={totalItems}
                onPageChange={setCurrentPage}
                itemName="datasets"
              />
            )}
          </Card>
        </div>

        {/* Right: Files Viewer */}
        {selectedDataset && (
          <div className="col-span-4">
            <Card className="h-full flex flex-col">
              {/* Dataset Header */}
              <div className="p-3 border-b bg-muted/30">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <Database className="h-4 w-4 text-blue-500 flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold truncate">{selectedDataset.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {files?.length || 0} {files?.length === 1 ? 'file' : 'files'}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSelectedDataset(null);
                      setSelectedFile('');
                    }}
                    className="h-7 w-7 p-0"
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              {/* Files List */}
              <div className="flex-1 overflow-y-auto">
                {filesLoading ? (
                  <div className="p-2 space-y-1">
                    {[...Array(10)].map((_, i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : !files || files.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <FileText className="h-10 w-10 text-muted-foreground/30 mb-3" />
                    <p className="text-sm font-medium">No files found</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      This dataset is empty
                    </p>
                  </div>
                ) : (
                  <div className="divide-y">
                    {files.map((file) => (
                      <button
                        key={file.filename}
                        onClick={() => handleSelectFile(file.filename)}
                        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-accent transition-colors group text-left"
                      >
                        <FileText className="h-4 w-4 text-blue-500 flex-shrink-0 group-hover:text-blue-600" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{file.filename}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatFileSize(file.size)} • {file.contentType}
                          </p>
                        </div>
                        <Eye className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* File Content Viewer Dialog */}
      <ArtifactViewer
        open={contentDialogOpen}
        onOpenChange={setContentDialogOpen}
        artifactContent={fileContent}
        isLoading={contentLoading}
        error={contentError}
        title={selectedFile ? `${selectedDataset?.name} / ${selectedFile}` : 'File Content'}
        hideLineCount={true}
        hideCloseButton={true}
      />
    </div>
  );
}
