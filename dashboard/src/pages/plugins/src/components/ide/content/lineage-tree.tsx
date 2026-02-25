import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Code, ArrowDown, Eye } from "lucide-react";
import type { ContentSnapshot, ContentSnapshotSummary } from "../../types";
import { formatFitness } from "../../utils/fitness";

interface LineageTreeProps {
    lineage: (ContentSnapshot | ContentSnapshotSummary)[] | null;
    open?: boolean;
    onClose: () => void;
    onViewCode: (snapshot: ContentSnapshot | ContentSnapshotSummary) => void;
}

export default function LineageTree({ lineage, open, onClose, onViewCode }: LineageTreeProps) {
    // If open prop is provided, use it; otherwise fall back to checking if lineage exists
    const isOpen = open !== undefined ? open : lineage !== null;
    return (
        <Dialog open={isOpen} onOpenChange={() => onClose()}>
            <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Content Lineage</DialogTitle>
                    <p className="text-sm text-muted-foreground">
                        Evolution path from seed to current content
                    </p>
                </DialogHeader>

                {lineage && lineage.length > 0 && (
                    <div className="space-y-2">
                        {lineage.map((snapshot, index) => (
                            <div key={snapshot.id}>
                                {/* Snapshot Card */}
                                <div
                                    className={`p-4 rounded-lg border-2 ${
                                        index === 0
                                            ? "border-blue-500 bg-blue-50 dark:bg-blue-950"
                                            : index === lineage.length - 1
                                            ? "border-green-500 bg-green-50 dark:bg-green-950"
                                            : "border-gray-300 bg-white dark:bg-slate-900"
                                    }`}
                                >
                                    <div className="flex items-start justify-between gap-4">
                                        {/* Left: Info */}
                                        <div className="flex-1 space-y-2">
                                            <div className="flex items-center gap-2">
                                                <Code className="w-4 h-4" />
                                                <span className="font-mono text-sm">
                                                    {snapshot.contentUid}
                                                </span>
                                                {index === 0 && (
                                                    <Badge variant="outline" className="text-xs">
                                                        Seed
                                                    </Badge>
                                                )}
                                                {index === lineage.length - 1 && (
                                                    <Badge variant="default" className="text-xs">
                                                        Current
                                                    </Badge>
                                                )}
                                            </div>

                                            <div className="grid grid-cols-2 gap-2 text-sm">
                                                <div>
                                                    <span className="text-muted-foreground">
                                                        Generation:
                                                    </span>
                                                    <span className="ml-2 font-semibold">{index}</span>
                                                </div>
                                                <div>
                                                    <span className="text-muted-foreground">
                                                        Fitness:
                                                    </span>
                                                    <span className="ml-2 font-semibold text-green-600">
                                                        {formatFitness(snapshot.fitness)}
                                                    </span>
                                                </div>
                                            </div>

                                            {snapshot.coParentUids && snapshot.coParentUids.length > 0 && (
                                                <div className="text-xs text-muted-foreground">
                                                    Crossover with {snapshot.coParentUids.length} co-parent(s)
                                                </div>
                                            )}

                                            <div className="text-xs text-muted-foreground">
                                                {new Date(snapshot.createdAt).toLocaleString()}
                                            </div>
                                        </div>

                                        {/* Right: Actions */}
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => onViewCode(snapshot)}
                                        >
                                            <Eye className="w-4 h-4 mr-2" />
                                            View
                                        </Button>
                                    </div>
                                </div>

                                {/* Arrow */}
                                {index < lineage.length - 1 && (
                                    <div className="flex justify-center py-2">
                                        <ArrowDown className="w-6 h-6 text-muted-foreground" />
                                    </div>
                                )}
                            </div>
                        ))}

                        {/* Summary */}
                        <div className="mt-6 p-4 bg-muted rounded-lg">
                            <h4 className="text-sm font-semibold mb-2">Lineage Summary</h4>
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span className="text-muted-foreground">Total Generations:</span>
                                    <span className="ml-2 font-semibold">{lineage.length}</span>
                                </div>
                                <div>
                                    <span className="text-muted-foreground">Fitness Improvement:</span>
                                    <span className="ml-2 font-semibold text-green-600">
                                        {formatFitness(lineage[0].fitness)} →{" "}
                                        {formatFitness(lineage[lineage.length - 1].fitness)}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {(!lineage || lineage.length === 0) && (
                    <div className="flex flex-col items-center justify-center py-12">
                        <Code className="w-12 h-12 text-muted-foreground mb-4" />
                        <p className="text-muted-foreground">No lineage data available</p>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
