import { useState } from "react";
import { ChevronRight, ChevronDown, Folder, FolderOpen, File, FileCode, FileJson, FileText } from "lucide-react";
import type { RepoFileEntry } from "../../types";
import { cn } from "../../lib/utils";

interface FileTreeProps {
    root: RepoFileEntry;
    selectedPath: string | null;
    onSelectFile: (path: string) => void;
    modifiedPaths?: Set<string>;  // Files modified by current evolution snapshot
}

interface FileTreeNodeProps {
    entry: RepoFileEntry;
    depth: number;
    selectedPath: string | null;
    onSelectFile: (path: string) => void;
    modifiedPaths?: Set<string>;
    defaultExpanded?: boolean;
}

// Get icon based on file extension
function getFileIcon(name: string) {
    const ext = name.split(".").pop()?.toLowerCase();

    // Code files
    if (["js", "jsx", "ts", "tsx", "py", "java", "go", "rs", "rb", "php", "c", "cpp", "h", "hpp", "cs", "swift", "kt", "scala"].includes(ext || "")) {
        return <FileCode className="h-4 w-4 text-gray-500" />;
    }

    // JSON/Config files
    if (["json", "yaml", "yml", "toml", "xml", "ini", "env"].includes(ext || "")) {
        return <FileJson className="h-4 w-4 text-gray-500" />;
    }

    // Documentation files
    if (["md", "txt", "rst", "doc", "docx", "pdf"].includes(ext || "")) {
        return <FileText className="h-4 w-4 text-gray-500" />;
    }

    return <File className="h-4 w-4 text-gray-500" />;
}

function FileTreeNode({ entry, depth, selectedPath, onSelectFile, modifiedPaths, defaultExpanded = false }: FileTreeNodeProps) {
    const [isExpanded, setIsExpanded] = useState(defaultExpanded);
    const isSelected = selectedPath === entry.path;
    const isModified = !entry.isDir && modifiedPaths?.has(entry.path);
    const hasChildren = entry.isDir && entry.children && entry.children.length > 0;

    const handleClick = () => {
        if (entry.isDir) {
            setIsExpanded(!isExpanded);
        } else {
            onSelectFile(entry.path);
        }
    };

    return (
        <div>
            <div
                className={cn(
                    "flex items-center gap-1 py-1 px-2 cursor-pointer rounded text-sm hover:bg-muted/50 transition-colors whitespace-nowrap",
                    isSelected && "bg-muted"
                )}
                style={{ paddingLeft: `${depth * 12 + 4}px` }}
                onClick={handleClick}
            >
                {/* Expand/collapse icon for directories */}
                {entry.isDir ? (
                    <span className="w-4 h-4 flex-shrink-0 flex items-center justify-center">
                        {hasChildren ? (
                            isExpanded ? (
                                <ChevronDown className="h-3 w-3 text-muted-foreground" />
                            ) : (
                                <ChevronRight className="h-3 w-3 text-muted-foreground" />
                            )
                        ) : null}
                    </span>
                ) : (
                    <span className="w-4 h-4 flex-shrink-0" />
                )}

                {/* File/folder icon */}
                <span className="w-4 h-4 flex-shrink-0 flex items-center justify-center">
                    {entry.isDir ? (
                        isExpanded ? (
                            <FolderOpen className="h-4 w-4 text-gray-500" />
                        ) : (
                            <Folder className="h-4 w-4 text-gray-500" />
                        )
                    ) : (
                        getFileIcon(entry.name)
                    )}
                </span>

                {/* File name */}
                <span className={cn(
                    "truncate min-w-0",
                    entry.isDir ? "text-foreground" : "text-muted-foreground",
                    isModified && "text-amber-600 dark:text-amber-400 font-medium",
                    isSelected && "text-foreground font-medium"
                )}>
                    {entry.name || "(root)"}
                    {isModified && <span className="ml-1 text-[10px] text-amber-500">●</span>}
                </span>
            </div>

            {/* Children */}
            {entry.isDir && isExpanded && entry.children && (
                <div>
                    {entry.children.map((child) => (
                        <FileTreeNode
                            key={child.path}
                            entry={child}
                            depth={depth + 1}
                            selectedPath={selectedPath}
                            onSelectFile={onSelectFile}
                            modifiedPaths={modifiedPaths}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

export default function FileTree({ root, selectedPath, onSelectFile, modifiedPaths }: FileTreeProps) {
    // If root has no name (it's the actual root), render children directly
    if (!root.name && root.children) {
        return (
            <div className="overflow-auto">
                {root.children.map((child) => (
                    <FileTreeNode
                        key={child.path}
                        entry={child}
                        depth={0}
                        selectedPath={selectedPath}
                        onSelectFile={onSelectFile}
                        modifiedPaths={modifiedPaths}
                        defaultExpanded={false}
                    />
                ))}
            </div>
        );
    }

    return (
        <div className="overflow-auto">
            <FileTreeNode
                entry={root}
                depth={0}
                selectedPath={selectedPath}
                onSelectFile={onSelectFile}
                modifiedPaths={modifiedPaths}
                defaultExpanded={false}
            />
        </div>
    );
}
