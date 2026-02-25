import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { GitBranch, ChevronDown, ChevronRight } from "lucide-react";
import type { ContentSnapshot, ContentSnapshotSummary } from "../../types";
import { formatFitness } from "../../utils/fitness";

interface LineageHistoryProps {
    lineage: (ContentSnapshot | ContentSnapshotSummary)[];
    selectedUid?: string;
}

export default function LineageHistory({ lineage, selectedUid }: LineageHistoryProps) {
    const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

    if (lineage.length === 0) {
        return null;
    }

    const toggleExpand = (contentUid: string) => {
        setExpandedItems(prev => {
            const next = new Set(prev);
            if (next.has(contentUid)) {
                next.delete(contentUid);
            } else {
                next.add(contentUid);
            }
            return next;
        });
    };

    return (
        <Card className="rounded-none border-x-0 border-b-0">
            <CardHeader className="py-2 px-3">
                <CardTitle className="flex items-center gap-2 text-sm">
                    <GitBranch className="w-4 h-4" />
                    Evolution History ({lineage.length} step{lineage.length !== 1 ? "s" : ""})
                </CardTitle>
            </CardHeader>
            <CardContent className="px-3 pb-3 pt-0">
                <div className="relative">
                    {/* Vertical line connecting steps */}
                    <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-border" />

                    <div className="space-y-2">
                        {lineage.map((snapshot, index) => {
                            const metainfo = snapshot.metainfo as Record<string, unknown> | null;
                            const aiSummary = metainfo?.ai_summary as { title?: string; summary?: string } | undefined;
                            const isSelected = snapshot.contentUid === selectedUid;
                            const isSeed = !snapshot.parentUid;
                            const isLast = index === lineage.length - 1;
                            const isExpanded = expandedItems.has(snapshot.contentUid);

                            return (
                                <div
                                    key={snapshot.contentUid}
                                    className="relative pl-8"
                                >
                                    {/* Step indicator */}
                                    <div
                                        className={`absolute left-1 w-4 h-4 rounded-full border-2 flex items-center justify-center text-[10px] font-medium
                                            ${isSelected
                                                ? "bg-blue-600 border-blue-600 text-white"
                                                : isSeed
                                                    ? "bg-green-100 border-green-500 text-green-700 dark:bg-green-950 dark:text-green-400"
                                                    : "bg-background border-muted-foreground/30 text-muted-foreground"
                                            }`}
                                    >
                                        {index + 1}
                                    </div>

                                    {/* Content */}
                                    <div className="space-y-0.5">
                                        {/* Collapsed row: chevron > title > score */}
                                        <div
                                            className="flex items-center gap-1.5 cursor-pointer"
                                            onClick={() => toggleExpand(snapshot.contentUid)}
                                        >
                                            <span className="text-muted-foreground hover:text-foreground p-0.5 -ml-1 flex-shrink-0">
                                                {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                                            </span>
                                            <span className="text-xs font-medium text-foreground truncate">
                                                {aiSummary?.title || (isSeed ? "Initial version" : snapshot.contentUid.substring(0, 8))}
                                            </span>
                                            {isSeed && (
                                                <Badge variant="outline" className="text-[10px] px-1 py-0 bg-green-50 dark:bg-green-950 flex-shrink-0">
                                                    Seed
                                                </Badge>
                                            )}
                                            {isLast && !isSeed && (
                                                <Badge variant="outline" className="text-[10px] px-1 py-0 bg-blue-50 dark:bg-blue-950 flex-shrink-0">
                                                    Current
                                                </Badge>
                                            )}
                                            <span className="text-[10px] text-green-600 font-medium flex-shrink-0">
                                                {formatFitness(snapshot.fitness)}
                                            </span>
                                        </div>

                                        {/* Expanded: commit code + description */}
                                        {isExpanded && (
                                            <div className="space-y-0.5 pl-4">
                                                <span className="font-mono text-[10px] text-muted-foreground">
                                                    {snapshot.contentUid.substring(0, 8)}
                                                </span>
                                                {aiSummary?.summary && (
                                                    <p className="text-xs text-muted-foreground">
                                                        {aiSummary.summary}
                                                    </p>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
