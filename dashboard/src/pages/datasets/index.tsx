import { useState, useMemo, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Database, Search, Eye, ExternalLink, FileText, X, Trash2 } from 'lucide-react';
import { useTeamContext } from '../../context/team-context';
import { useDatasets } from '../../hooks/use-datasets';
import { useDeleteDatasets } from '../../hooks/use-dataset-mutations';
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
import { Checkbox } from '../../components/ui/checkbox';
import { Skeleton } from '../../components/ui/skeleton';
import { Pagination } from '../../components/ui/pagination';
import { ArtifactViewer } from '../../components/artifact-viewer';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';
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
  const [selectedDatasets, setSelectedDatasets] = useState<Set<string>>(new Set());
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const deleteDatasetsMutation = useDeleteDatasets();

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

  // Check if all filtered datasets are selected
  const allSelected = filteredDatasets.length > 0 &&
    filteredDatasets.every(dataset => selectedDatasets.has(dataset.id));

  // Toggle select all
  const handleSelectAll = () => {
    if (allSelected) {
      setSelectedDatasets(new Set());
    } else {
      setSelectedDatasets(new Set(filteredDatasets.map(dataset => dataset.id)));
    }
  };

  // Toggle individual dataset selection
  const handleSelectDataset = (datasetId: string) => {
    const newSelected = new Set(selectedDatasets);
    if (newSelected.has(datasetId)) {
      newSelected.delete(datasetId);
    } else {
      newSelected.add(datasetId);
    }
    setSelectedDatasets(newSelected);
  };

  // Handle delete confirmation
  const handleDeleteClick = () => {
    if (selectedDatasets.size === 0) return;
    setShowDeleteDialog(true);
  };

  // Handle delete confirmation
  const handleDeleteConfirm = async (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();

    if (selectedDatasets.size === 0) return;

    try {
      const result = await deleteDatasetsMutation.mutateAsync(Array.from(selectedDatasets));
      console.log(`Successfully deleted ${result} datasets`);
      setSelectedDatasets(new Set());
      setShowDeleteDialog(false);
      // Clear selected dataset view if it was deleted
      if (selectedDataset && selectedDatasets.has(selectedDataset.id)) {
        setSelectedDataset(null);
        setSelectedFile('');
      }
    } catch (error) {
      console.error('Failed to delete datasets:', error);
      alert('Failed to delete datasets. Please try again.');
    }
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
                <div className="flex flex-col items-center justify-center h-full">
                  <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mb-4">
                    <Database className="h-8 w-8 text-muted-foreground/60" />
                  </div>
                  <p className="text-sm font-medium text-foreground">No datasets found</p>
                  <p className="text-xs text-muted-foreground mt-1">Datasets will appear here once created</p>
                </div>
              ) : filteredDatasets.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full">
                  <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mb-4">
                    <Search className="h-8 w-8 text-muted-foreground/60" />
                  </div>
                  <p className="text-sm font-medium text-foreground">No matching datasets</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Try adjusting your search query
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="w-[32%] h-9">
                        <div className="flex items-center gap-2">
                          <Checkbox
                            checked={allSelected}
                            onChange={handleSelectAll}
                            aria-label="Select all datasets"
                          />
                          <button
                            onClick={handleDeleteClick}
                            disabled={deleteDatasetsMutation.isPending || selectedDatasets.size === 0}
                            className={`inline-flex items-center justify-center h-6 w-6 rounded hover:bg-destructive/10 text-destructive transition-colors disabled:opacity-50 ${
                              selectedDatasets.size === 0 ? 'invisible pointer-events-none' : ''
                            }`}
                            title={selectedDatasets.size > 0 ? `Delete ${selectedDatasets.size} ${selectedDatasets.size === 1 ? 'dataset' : 'datasets'}` : ''}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                          <span>Name</span>
                        </div>
                      </TableHead>
                      <TableHead className="w-[22%] h-9">Description</TableHead>
                      <TableHead className="w-[13%] h-9">Experiment</TableHead>
                      <TableHead className="w-[13%] h-9">Run</TableHead>
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
                            <Checkbox
                              checked={selectedDatasets.has(dataset.id)}
                              onChange={() => handleSelectDataset(dataset.id)}
                              aria-label={`Select dataset ${dataset.name}`}
                            />
                            <div className="w-6"></div>
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
                  <div className="flex flex-col items-center justify-center h-full text-center">
                    <div className="w-12 h-12 rounded-full bg-muted/50 flex items-center justify-center mx-auto mb-3">
                      <FileText className="h-6 w-6 text-muted-foreground/60" />
                    </div>
                    <p className="text-sm font-medium text-foreground">No files found</p>
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

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent className="pointer-events-auto sm:max-w-[440px]">
          <DialogHeader className="space-y-3">
            <DialogTitle className="text-lg font-semibold text-foreground">
              Delete {selectedDatasets.size === 1 ? 'Dataset' : 'Datasets'}
            </DialogTitle>
            <DialogDescription className="text-sm text-muted-foreground leading-relaxed">
              You are about to delete <span className="font-medium text-foreground">{selectedDatasets.size}</span> {selectedDatasets.size === 1 ? 'dataset' : 'datasets'}.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setShowDeleteDialog(false);
              }}
              disabled={deleteDatasetsMutation.isPending}
              className="h-9"
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteDatasetsMutation.isPending}
              className="h-9"
            >
              {deleteDatasetsMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
