import { useState, useMemo } from 'react';
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
  hideLineCount?: boolean;
  hideCloseButton?: boolean;
}

export function ArtifactViewer({
  open,
  onOpenChange,
  artifactContent,
  isLoading,
  error,
  title = 'Artifact Content',
  hideLineCount = false,
  hideCloseButton = false,
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

  const stats = useMemo(() => {
    if (!artifactContent?.content) return null;

    const content = artifactContent.content;
    const lines = content.split('\n').length;
    const bytes = new TextEncoder().encode(content).length;

    let size: string;
    if (bytes < 1024) {
      size = `${bytes} B`;
    } else if (bytes < 1024 * 1024) {
      size = `${(bytes / 1024).toFixed(2)} KB`;
    } else {
      size = `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }

    return { lines, size, bytes };
  }, [artifactContent?.content]);

  const renderMetadata = () => {
    if (!artifactContent || !stats) return null;

    return (
      <div className="p-3 space-y-3">
        <div className="space-y-1.5">
          <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100 uppercase tracking-wide">
            File Information
          </h3>
          <div className="border border-slate-200 dark:border-slate-700 rounded bg-white dark:bg-slate-800">
            <div className="flex justify-between items-center py-1.5 px-2 border-b border-slate-200 dark:border-slate-700">
              <span className="text-slate-600 dark:text-slate-400 font-medium text-xs">Filename</span>
              <code className="font-mono text-slate-900 dark:text-slate-100 text-xs">{artifactContent.filename}</code>
            </div>
            <div className="flex justify-between items-center py-1.5 px-2">
              <span className="text-slate-600 dark:text-slate-400 font-medium text-xs">Content Type</span>
              <code className="font-mono text-slate-900 dark:text-slate-100 text-xs">{artifactContent.contentType}</code>
            </div>
          </div>
        </div>

        <div className="space-y-1.5">
          <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100 uppercase tracking-wide">
            Statistics
          </h3>
          <div className="grid grid-cols-2 gap-1.5">
            <div className="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <div className="text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wide">Lines</div>
              <div className="text-xs font-semibold tabular-nums text-slate-900 dark:text-slate-100">{stats.lines.toLocaleString()}</div>
            </div>
            <div className="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <div className="text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wide">Size</div>
              <div className="text-xs font-semibold tabular-nums text-slate-900 dark:text-slate-100">{stats.size}</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-5xl max-h-[85vh] overflow-hidden flex flex-col gap-0 p-0"
        hideCloseButton={hideCloseButton}
      >
        {/* Header */}
        <DialogHeader className="px-4 py-2.5 border-b bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              {getFileIcon()}
              <div className="flex-1 min-w-0">
                <DialogTitle className="text-sm font-semibold truncate text-slate-900 dark:text-slate-100">
                  {title}
                </DialogTitle>
                <p className="text-xs text-slate-600 dark:text-slate-400 font-mono truncate mt-0.5">
                  {artifactContent?.filename || 'Loading...'}
                </p>
              </div>
              {stats && !hideLineCount && (
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <Badge variant="secondary" className="text-xs font-medium px-2 py-0.5">
                    {stats.lines} lines
                  </Badge>
                </div>
              )}
            </div>
            {artifactContent && (
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopy}
                  className="h-7 px-2.5 text-xs font-medium"
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
                  variant="outline"
                  size="sm"
                  onClick={handleDownload}
                  className="h-7 px-2.5 text-xs font-medium"
                >
                  <Download className="h-3 w-3 mr-1" />
                  Download
                </Button>
              </div>
            )}
          </div>
        </DialogHeader>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex flex-col min-h-0">
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
            <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 min-h-0 flex flex-col">
              <div className="px-4 py-2 border-b bg-muted/30 flex-shrink-0">
                <TabsList className="h-8 bg-background/60">
                  <TabsTrigger value="content" className="text-xs font-medium h-6 px-3 data-[state=active]:bg-background">
                    <Eye className="h-3 w-3 mr-1.5" />
                    Content
                  </TabsTrigger>
                  <TabsTrigger value="metadata" className="text-xs font-medium h-6 px-3 data-[state=active]:bg-background">
                    <Info className="h-3 w-3 mr-1.5" />
                    Metadata
                  </TabsTrigger>
                </TabsList>
              </div>

              <TabsContent value="content" className="flex-1 min-h-0 overflow-y-auto m-0 bg-slate-950 data-[state=active]:block data-[state=inactive]:hidden">
                <pre className="text-xs p-4 text-slate-50 leading-relaxed font-mono">
                  <code>{formatContent()}</code>
                </pre>
              </TabsContent>

              <TabsContent value="metadata" className="flex-1 min-h-0 overflow-y-auto m-0 bg-slate-50 dark:bg-slate-900 data-[state=active]:block data-[state=inactive]:hidden">
                {renderMetadata()}
              </TabsContent>
            </Tabs>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
