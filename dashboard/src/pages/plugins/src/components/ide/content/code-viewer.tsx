import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Copy, Check, Download } from "lucide-react";
import type { ContentSnapshot } from "../../types";
import { formatFitness } from "../../utils/fitness";

interface CodeViewerProps {
    snapshot: ContentSnapshot | null;
    code: string | null;
    onClose: () => void;
}

export default function CodeViewer({ snapshot, code, onClose }: CodeViewerProps) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        if (code) {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const handleDownload = () => {
        if (code && snapshot) {
            const blob = new Blob([code], { type: "text/plain" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${snapshot.contentUid}.${snapshot.language || "py"}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    };

    return (
        <Dialog open={snapshot !== null} onOpenChange={() => onClose()}>
            <DialogContent className="max-w-4xl max-h-[80vh]">
                <DialogHeader>
                    <div className="flex items-center justify-between">
                        <DialogTitle>Content Snapshot</DialogTitle>
                        <div className="flex items-center gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleCopy}
                            >
                                {copied ? (
                                    <>
                                        <Check className="w-4 h-4 mr-2" />
                                        Copied
                                    </>
                                ) : (
                                    <>
                                        <Copy className="w-4 h-4 mr-2" />
                                        Copy
                                    </>
                                )}
                            </Button>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleDownload}
                            >
                                <Download className="w-4 h-4 mr-2" />
                                Download
                            </Button>
                        </div>
                    </div>
                </DialogHeader>

                {snapshot && (
                    <div className="space-y-4">
                        {/* Metadata */}
                        <div className="flex flex-wrap items-center gap-4 text-sm">
                            <div>
                                <span className="text-muted-foreground">UID:</span>
                                <span className="ml-2 font-mono">{snapshot.contentUid}</span>
                            </div>
                            <div>
                                <span className="text-muted-foreground">Fitness:</span>
                                <span className="ml-2 font-semibold text-green-600">
                                    {formatFitness(snapshot.fitness)}
                                </span>
                            </div>
                            <div>
                                <span className="text-muted-foreground">Language:</span>
                                <Badge variant="secondary" className="ml-2">
                                    {snapshot.language || "python"}
                                </Badge>
                            </div>
                            {!snapshot.parentUid && (
                                <Badge variant="outline">Seed Content</Badge>
                            )}
                        </div>

                        {/* Parent Info */}
                        {snapshot.parentUid && (
                            <div className="text-sm text-muted-foreground">
                                <span>Parent: {snapshot.parentUid}</span>
                                {snapshot.coParentUids && snapshot.coParentUids.length > 0 && (
                                    <span className="ml-2">
                                        + {snapshot.coParentUids.length} co-parent(s): {" "}
                                        {snapshot.coParentUids.join(", ")}
                                    </span>
                                )}
                            </div>
                        )}

                        {/* Code */}
                        <div className="relative">
                            <pre className="bg-slate-950 text-slate-50 p-4 rounded-lg overflow-auto max-h-[50vh] text-sm">
                                <code>{code || "Loading code..."}</code>
                            </pre>
                        </div>

                        {/* Evaluation Results */}
                        {snapshot.evaluation && Object.keys(snapshot.evaluation).length > 0 && (
                            <div>
                                <h4 className="text-sm font-semibold mb-2">Evaluation Results</h4>
                                <div className="bg-muted p-3 rounded-lg">
                                    <pre className="text-xs overflow-auto">
                                        {JSON.stringify(snapshot.evaluation, null, 2)}
                                    </pre>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
