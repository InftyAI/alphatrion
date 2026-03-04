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
      <div className="p-6 space-y-6">
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 uppercase tracking-wide">
            File Information
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between items-center py-2.5 px-3 border-b bg-white dark:bg-slate-800 rounded">
              <span className="text-slate-600 dark:text-slate-400 font-medium">Filename</span>
              <code className="font-mono text-slate-900 dark:text-slate-100 text-sm">{artifactContent.filename}</code>
            </div>
            <div className="flex justify-between items-center py-2.5 px-3 border-b bg-white dark:bg-slate-800 rounded">
              <span className="text-slate-600 dark:text-slate-400 font-medium">Content Type</span>
              <code className="font-mono text-slate-900 dark:text-slate-100 text-sm">{artifactContent.contentType}</code>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 uppercase tracking-wide">
            Statistics
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-4 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm">
              <div className="text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1">Lines</div>
              <div className="text-2xl font-bold tabular-nums text-slate-900 dark:text-slate-100">{stats.lines.toLocaleString()}</div>
            </div>
            <div className="p-4 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm">
              <div className="text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1">Size</div>
              <div className="text-2xl font-bold tabular-nums text-slate-900 dark:text-slate-100">{stats.size}</div>
            </div>
            <div className="p-4 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm">
              <div className="text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1">Words</div>
              <div className="text-2xl font-bold tabular-nums text-slate-900 dark:text-slate-100">{stats.words.toLocaleString()}</div>
            </div>
            <div className="p-4 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm">
              <div className="text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1">Characters</div>
              <div className="text-2xl font-bold tabular-nums text-slate-900 dark:text-slate-100">{stats.chars.toLocaleString()}</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden flex flex-col gap-0 p-0">
        {/* Header */}
        <DialogHeader className="px-6 py-4 border-b bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              {getFileIcon()}
              <div className="flex-1 min-w-0">
                <DialogTitle className="text-base font-semibold truncate text-slate-900 dark:text-slate-100">
                  {title}
                </DialogTitle>
                <p className="text-sm text-slate-600 dark:text-slate-400 font-mono truncate mt-1">
                  {artifactContent?.filename || 'Loading...'}
                </p>
              </div>
              {stats && (
                <div className="flex items-center gap-2 flex-shrink-0">
                  <Badge variant="secondary" className="text-xs font-medium px-2.5 py-1">
                    {stats.lines} lines
                  </Badge>
                  <Badge variant="secondary" className="text-xs font-medium px-2.5 py-1">
                    {stats.size}
                  </Badge>
                </div>
              )}
            </div>
            {artifactContent && (
              <div className="flex items-center gap-2 flex-shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopy}
                  className="h-8 px-3 text-xs font-medium"
                >
                  {copied ? (
                    <>
                      <Check className="h-3.5 w-3.5 mr-1.5" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5 mr-1.5" />
                      Copy
                    </>
                  )}
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleDownload}
                  className="h-8 px-3 text-xs font-medium"
                >
                  <Download className="h-3.5 w-3.5 mr-1.5" />
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
              <div className="text-base text-muted-foreground">Loading artifact...</div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <p className="text-base font-medium text-destructive">Failed to load artifact</p>
                <p className="text-sm text-muted-foreground mt-2">{error.message}</p>
              </div>
            </div>
          ) : (
            <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
              <div className="px-6 py-2.5 border-b bg-muted/30">
                <TabsList className="h-9 bg-background/60">
                  <TabsTrigger value="content" className="text-xs font-medium h-7 px-4 data-[state=active]:bg-background">
                    <Eye className="h-3.5 w-3.5 mr-2" />
                    Content
                  </TabsTrigger>
                  <TabsTrigger value="metadata" className="text-xs font-medium h-7 px-4 data-[state=active]:bg-background">
                    <Info className="h-3.5 w-3.5 mr-2" />
                    Metadata
                  </TabsTrigger>
                </TabsList>
              </div>

              <TabsContent value="content" className="flex-1 overflow-auto m-0 bg-slate-950">
                <pre className="text-sm p-6 text-slate-50 leading-relaxed min-h-full font-mono">
                  <code>{formatContent()}</code>
                </pre>
              </TabsContent>

              <TabsContent value="metadata" className="flex-1 overflow-auto m-0 bg-slate-50 dark:bg-slate-900">
                {renderMetadata()}
              </TabsContent>
            </Tabs>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
