import { useState } from "react";
import { ChevronRight, ChevronDown, Folder, FolderOpen, File } from "lucide-react";
import { cn } from "../../../lib/utils";

interface FileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileNode[];
}

interface FileTreeProps {
  node: FileNode;
  onFileSelect: (path: string) => void;
  selectedPath: string | null;
}

interface FileTreeNodeProps {
  entry: FileNode;
  depth: number;
  selectedPath: string | null;
  onFileSelect: (path: string) => void;
}

function FileTreeNode({ entry, depth, selectedPath, onFileSelect }: FileTreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(depth === 0);
  const isSelected = selectedPath === entry.path;
  const isDirectory = entry.type === "directory";

  const handleClick = () => {
    if (isDirectory) {
      setIsExpanded(!isExpanded);
    } else {
      onFileSelect(entry.path);
    }
  };

  return (
    <div>
      <div
        className={cn(
          "flex items-center gap-1 px-2 py-1 text-sm hover:bg-accent cursor-pointer rounded",
          isSelected && "bg-accent"
        )}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onClick={handleClick}
      >
        {isDirectory && (
          <span className="flex-shrink-0">
            {isExpanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
          </span>
        )}
        {!isDirectory && <span className="w-3" />}
        {isDirectory ? (
          isExpanded ? (
            <FolderOpen className="h-4 w-4 text-blue-500" />
          ) : (
            <Folder className="h-4 w-4 text-blue-500" />
          )
        ) : (
          <File className="h-4 w-4 text-muted-foreground" />
        )}
        <span className="truncate">{entry.name}</span>
      </div>

      {isDirectory && isExpanded && entry.children && (
        <div>
          {entry.children.map((child) => (
            <FileTreeNode
              key={child.path}
              entry={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onFileSelect={onFileSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FileTree({ node, onFileSelect, selectedPath }: FileTreeProps) {
  return (
    <div className="text-sm">
      <FileTreeNode
        entry={node}
        depth={0}
        selectedPath={selectedPath}
        onFileSelect={onFileSelect}
      />
    </div>
  );
}
