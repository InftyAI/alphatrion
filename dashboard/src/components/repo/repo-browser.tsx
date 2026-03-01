import { useState } from "react";
import { FolderX, RefreshCw, AlertCircle } from "lucide-react";
import { useRepoFileTree, useRepoFileContent } from "../../hooks/use-repo-browser";
import FileTree from "./file-tree";
import FileViewer from "./file-viewer";
import { Card } from "../ui/card";
import { Button } from "../ui/button";

interface RepoBrowserProps {
    experimentId: string;
}

export default function RepoBrowser({ experimentId }: RepoBrowserProps) {
    const { tree, isLoading: treeLoading, error: treeError, refresh } = useRepoFileTree(experimentId);
    const { content, isLoading: contentLoading, error: contentError, loadFile, clearContent } = useRepoFileContent(experimentId);
    const [selectedPath, setSelectedPath] = useState<string | null>(null);

    const handleSelectFile = (path: string) => {
        setSelectedPath(path);
        loadFile(path);
    };

    // Loading state
    if (treeLoading) {
        return (
            <Card className="flex items-center justify-center h-[600px]">
                <div className="flex flex-col items-center gap-3">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                    <p className="text-sm text-muted-foreground">Loading repository...</p>
                </div>
            </Card>
        );
    }

    // Error state
    if (treeError || tree?.error) {
        return (
            <Card className="flex items-center justify-center h-[600px]">
                <div className="flex flex-col items-center gap-3 text-center px-4">
                    <AlertCircle className="h-12 w-12 text-destructive" />
                    <p className="text-sm text-muted-foreground">
                        {treeError?.message || tree?.error || "Failed to load repository"}
                    </p>
                    <Button variant="outline" size="sm" onClick={refresh}>
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Try Again
                    </Button>
                </div>
            </Card>
        );
    }

    // No repository found
    if (!tree?.exists || !tree?.root) {
        return (
            <Card className="flex items-center justify-center h-[600px]">
                <div className="flex flex-col items-center gap-3 text-center px-4">
                    <FolderX className="h-12 w-12 text-muted-foreground" />
                    <div>
                        <p className="font-medium">No Repository Available</p>
                        <p className="text-sm text-muted-foreground mt-1">
                            This trial does not have an associated repository snapshot.
                        </p>
                    </div>
                </div>
            </Card>
        );
    }

    return (
        <Card className="flex h-[600px] overflow-hidden">
            {/* File Tree Panel */}
            <div className="w-64 border-r flex flex-col bg-muted/20">
                <div className="flex items-center justify-between px-3 py-2 border-b">
                    <span className="text-sm font-medium">Files</span>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={refresh}
                        title="Refresh"
                    >
                        <RefreshCw className="h-3 w-3" />
                    </Button>
                </div>
                <div className="flex-1 overflow-auto py-1">
                    <FileTree
                        root={tree.root}
                        selectedPath={selectedPath}
                        onSelectFile={handleSelectFile}
                    />
                </div>
            </div>

            {/* File Viewer Panel */}
            <div className="flex-1 bg-[#1e1e1e]">
                <FileViewer
                    content={content}
                    isLoading={contentLoading}
                    error={contentError?.message}
                />
            </div>
        </Card>
    );
}
