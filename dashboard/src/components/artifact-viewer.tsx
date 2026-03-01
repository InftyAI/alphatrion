import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Copy, Check } from 'lucide-react';

interface ArtifactContent {
  filename: string;
  content: string;
  contentType: string;
}

interface ArtifactViewerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  artifactContent: ArtifactContent | null | undefined;
  isLoading: boolean;
  error: Error | null;
  title?: string;
}

export function ArtifactViewer({
  open,
  onOpenChange,
  artifactContent,
  isLoading,
  error,
  title = 'Artifact Content',
}: ArtifactViewerProps) {
  const [copied, setCopied] = useState(false);

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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <DialogTitle className="text-base">{title}</DialogTitle>
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
          {isLoading && !artifactContent ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-slate-400 text-sm">Loading artifact...</div>
            </div>
          ) : error ? (
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
  );
}
