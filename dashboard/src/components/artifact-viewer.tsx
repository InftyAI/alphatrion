import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import {
  Copy,
  Check,
  Download,
  FileText,
  Database,
  Package,
  Eye,
  Info,
} from 'lucide-react';

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
  const [activeTab, setActiveTab] = useState('content');

  const handleCopy = () => {
    if (artifactContent?.content) {
      navigator.clipboard.writeText(artifactContent.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (artifactContent) {
      const blob = new Blob([artifactContent.content], { type: artifactContent.contentType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = artifactContent.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const formatContent = () => {
    if (!artifactContent) return '';

    const { content, filename, contentType } = artifactContent;

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

  const getFileIcon = () => {
    if (!artifactContent) return <Package className="h-3.5 w-3.5 text-purple-600" />;

    // Extract repo name from title (format: "repoName - tag")
    const repoName = title.split(' - ')[0]?.toLowerCase() || '';

    if (repoName.includes('execution') || repoName.includes('run')) {
      return <FileText className="h-3.5 w-3.5 text-blue-600" />;
    }
    if (repoName.includes('checkpoint') || repoName.includes('model')) {
      return <Database className="h-3.5 w-3.5 text-green-600" />;
    }
    return <Package className="h-3.5 w-3.5 text-purple-600" />;
  };

  const getContentStats = () => {
    if (!artifactContent?.content) return null;

    const content = artifactContent.content;
    const lines = content.split('\n').length;
    const bytes = new Blob([content]).size;
    const chars = content.length;
    const words = content.split(/\s+/).filter(Boolean).length;

    let size: string;
    if (bytes < 1024) {
      size = `${bytes} B`;
    } else if (bytes < 1024 * 1024) {
      size = `${(bytes / 1024).toFixed(2)} KB`;
    } else {
      size = `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }

    return { lines, size, bytes, chars, words };
  };

  const stats = getContentStats();

  const renderMetadata = () => {
    if (!artifactContent || !stats) return null;

    return (
      <div className="p-3 space-y-3">
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">FILE INFORMATION</p>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between py-1 border-b">
              <span className="text-muted-foreground">Filename</span>
              <code className="font-mono">{artifactContent.filename}</code>
            </div>
            <div className="flex justify-between py-1 border-b">
              <span className="text-muted-foreground">Content Type</span>
              <code className="font-mono">{artifactContent.contentType}</code>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">STATISTICS</p>
          <div className="grid grid-cols-2 gap-2">
            <div className="p-2 rounded bg-muted">
              <div className="text-xs text-muted-foreground">Lines</div>
              <div className="text-base font-semibold tabular-nums">{stats.lines.toLocaleString()}</div>
            </div>
            <div className="p-2 rounded bg-muted">
              <div className="text-xs text-muted-foreground">Size</div>
              <div className="text-base font-semibold tabular-nums">{stats.size}</div>
            </div>
            <div className="p-2 rounded bg-muted">
              <div className="text-xs text-muted-foreground">Words</div>
              <div className="text-base font-semibold tabular-nums">{stats.words.toLocaleString()}</div>
            </div>
            <div className="p-2 rounded bg-muted">
              <div className="text-xs text-muted-foreground">Characters</div>
              <div className="text-base font-semibold tabular-nums">{stats.chars.toLocaleString()}</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[85vh] overflow-hidden flex flex-col gap-0 p-0">
        {/* Header */}
        <DialogHeader className="px-4 py-3 border-b">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              {getFileIcon()}
              <div className="flex-1 min-w-0">
                <DialogTitle className="text-sm font-semibold truncate">
                  {title}
                </DialogTitle>
                <p className="text-xs text-muted-foreground font-mono truncate mt-0.5">
                  {artifactContent?.filename || 'Loading...'}
                </p>
              </div>
              {stats && (
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Badge variant="secondary" className="text-xs">
                    {stats.lines} lines
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    {stats.size}
                  </Badge>
                </div>
              )}
            </div>
            {artifactContent && (
              <div className="flex items-center gap-1 flex-shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopy}
                  className="h-7 px-2 text-xs"
                >
                  {copied ? (
                    <>
                      <Check className="h-3 w-3 mr-1" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-3 w-3 mr-1" />
                      Copy
                    </>
                  )}
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleDownload}
                  className="h-7 px-2 text-xs"
                >
                  <Download className="h-3 w-3 mr-1" />
                  Download
                </Button>
              </div>
            )}
          </div>
        </DialogHeader>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {isLoading && !artifactContent ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-sm text-muted-foreground">Loading artifact...</div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <p className="text-sm font-medium text-destructive">Failed to load artifact</p>
                <p className="text-xs text-muted-foreground mt-1">{error.message}</p>
              </div>
            </div>
          ) : (
            <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
              <div className="px-4 py-2 border-b bg-muted/20">
                <TabsList className="h-8">
                  <TabsTrigger value="content" className="text-xs h-6 px-3">
                    <Eye className="h-3 w-3 mr-1.5" />
                    Content
                  </TabsTrigger>
                  <TabsTrigger value="metadata" className="text-xs h-6 px-3">
                    <Info className="h-3 w-3 mr-1.5" />
                    Metadata
                  </TabsTrigger>
                </TabsList>
              </div>

              <TabsContent value="content" className="flex-1 overflow-auto m-0 bg-slate-950">
                <pre className="text-xs p-4 text-slate-50 leading-relaxed min-h-full">
                  <code className="font-mono">{formatContent()}</code>
                </pre>
              </TabsContent>

              <TabsContent value="metadata" className="flex-1 overflow-auto m-0">
                {renderMetadata()}
              </TabsContent>
            </Tabs>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
