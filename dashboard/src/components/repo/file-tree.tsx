import { useState } from "react";
import { ChevronRight, ChevronDown, Folder, FolderOpen, File, FileCode, FileJson, FileText } from "lucide-react";
import type { RepoFileEntry } from "../../types";
import { cn } from "../../lib/utils";

export type ChangeStats = Map<string, { additions: number; removals: number }>;

interface FileTreeProps {
    root: RepoFileEntry;
    selectedPath: string | null;
    onSelectFile: (path: string) => void;
    modifiedPaths?: Set<string>;  // Files modified by current evolution snapshot
    changeStats?: ChangeStats;    // Per-file diff stats (comparison mode)
    showOnlyChanged?: boolean;    // Filter to only changed files
}

interface FileTreeNodeProps {
    entry: RepoFileEntry;
    depth: number;
    selectedPath: string | null;
    onSelectFile: (path: string) => void;
    modifiedPaths?: Set<string>;
    changeStats?: ChangeStats;
    showOnlyChanged?: boolean;
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

function hasChangedDescendant(entry: RepoFileEntry, changeStats: ChangeStats): boolean {
    if (!entry.isDir) {
        const stats = changeStats.get(entry.path);
        return !!stats && (stats.additions > 0 || stats.removals > 0);
    }
    return !!entry.children?.some(child => hasChangedDescendant(child, changeStats));
}

function FileTreeNode({ entry, depth, selectedPath, onSelectFile, modifiedPaths, changeStats, showOnlyChanged, defaultExpanded = false }: FileTreeNodeProps) {
    const autoExpand = showOnlyChanged && changeStats && entry.isDir && hasChangedDescendant(entry, changeStats);
    const [isExpanded, setIsExpanded] = useState(defaultExpanded || !!autoExpand);
    const isSelected = selectedPath === entry.path;
    const fileChangeStats = !entry.isDir && changeStats ? changeStats.get(entry.path) : undefined;
    const isModified = !entry.isDir && !changeStats && modifiedPaths?.has(entry.path);
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
                    fileChangeStats && (fileChangeStats.additions > 0 || fileChangeStats.removals > 0) && "text-foreground font-medium",
                    isSelected && "text-foreground font-medium"
                )}>
                    {entry.name || "(root)"}
                    {isModified && <span className="ml-1 text-[10px] text-amber-500">●</span>}
                </span>
                {/* Diff stats badges (comparison mode) */}
                {fileChangeStats && (fileChangeStats.additions > 0 || fileChangeStats.removals > 0) ? (
                    <span className="flex items-center gap-1 ml-auto shrink-0">
                        {fileChangeStats.additions > 0 && <span className="text-[10px] font-mono text-green-600">+{fileChangeStats.additions}</span>}
                        {fileChangeStats.removals > 0 && <span className="text-[10px] font-mono text-red-600">-{fileChangeStats.removals}</span>}
                    </span>
                ) : fileChangeStats ? (
                    <span className="text-[10px] text-gray-400 ml-auto shrink-0">unchanged</span>
                ) : null}
            </div>

            {/* Children */}
            {entry.isDir && isExpanded && entry.children && (
                <div>
                    {(showOnlyChanged && changeStats
                        ? entry.children.filter(child => hasChangedDescendant(child, changeStats))
                        : entry.children
                    ).map((child) => (
                        <FileTreeNode
                            key={child.path}
                            entry={child}
                            depth={depth + 1}
                            selectedPath={selectedPath}
                            onSelectFile={onSelectFile}
                            modifiedPaths={modifiedPaths}
                            changeStats={changeStats}
                            showOnlyChanged={showOnlyChanged}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

export default function FileTree({ root, selectedPath, onSelectFile, modifiedPaths, changeStats, showOnlyChanged }: FileTreeProps) {
    // If root has no name (it's the actual root), render children directly
    if (!root.name && root.children) {
        const children = showOnlyChanged && changeStats
            ? root.children.filter(child => hasChangedDescendant(child, changeStats))
            : root.children;
        return (
            <div className="overflow-auto">
                {children.map((child) => (
                    <FileTreeNode
                        key={child.path}
                        entry={child}
                        depth={0}
                        selectedPath={selectedPath}
                        onSelectFile={onSelectFile}
                        modifiedPaths={modifiedPaths}
                        changeStats={changeStats}
                        showOnlyChanged={showOnlyChanged}
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
                changeStats={changeStats}
                showOnlyChanged={showOnlyChanged}
                defaultExpanded={false}
            />
        </div>
    );
}
