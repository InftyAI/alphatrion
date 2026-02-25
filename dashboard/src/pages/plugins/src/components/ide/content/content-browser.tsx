import { useState, useEffect } from "react";
import { Card, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Code, GitBranch, Eye, TrendingUp } from "lucide-react";
import type { ContentSnapshotSummary } from "../../types";
import { formatFitness, getFitnessValue } from "../../utils/fitness";

interface ContentBrowserProps {
    snapshots: ContentSnapshotSummary[];
    onViewCode: (snapshot: ContentSnapshotSummary) => void;
    onViewLineage: (snapshot: ContentSnapshotSummary) => void;
}

export default function ContentBrowser({
    snapshots,
    onViewCode,
    onViewLineage,
}: ContentBrowserProps) {
    const [sortedSnapshots, setSortedSnapshots] = useState<ContentSnapshotSummary[]>([]);
    const [sortBy, setSortBy] = useState<"fitness" | "created">("fitness");

    useEffect(() => {
        const sorted = [...snapshots].sort((a, b) => {
            if (sortBy === "fitness") {
                const fitnessA = getFitnessValue(a.fitness);
                const fitnessB = getFitnessValue(b.fitness);
                return fitnessB - fitnessA; // Descending
            } else {
                return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
            }
        });
        setSortedSnapshots(sorted);
    }, [snapshots, sortBy]);

    if (snapshots.length === 0) {
        return (
            <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                    <Code className="w-12 h-12 text-muted-foreground mb-4" />
                    <p className="text-muted-foreground">No content snapshots available</p>
                    <p className="text-sm text-muted-foreground mt-2">
                        Content will appear here as the experiment runs
                    </p>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-4">
            {/* Controls */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Sort by:</span>
                    <Button
                        variant={sortBy === "fitness" ? "default" : "outline"}
                        size="sm"
                        onClick={() => setSortBy("fitness")}
                    >
                        <TrendingUp className="w-4 h-4 mr-2" />
                        Fitness
                    </Button>
                    <Button
                        variant={sortBy === "created" ? "default" : "outline"}
                        size="sm"
                        onClick={() => setSortBy("created")}
                    >
                        Recent
                    </Button>
                </div>
                <Badge variant="secondary">{snapshots.length} snapshots</Badge>
            </div>

            {/* Content List */}
            <div className="grid gap-4">
                {sortedSnapshots.map((snapshot) => (
                    <Card key={snapshot.id} className="hover:shadow-md transition-shadow">
                        <CardContent className="pt-6">
                            <div className="flex items-start justify-between gap-4">
                                {/* Left: Info */}
                                <div className="flex-1 space-y-2">
                                    <div className="flex items-center gap-2">
                                        <Code className="w-4 h-4 text-blue-600" />
                                        <span className="font-mono text-sm text-muted-foreground">
                                            {snapshot.contentUid}
                                        </span>
                                        {!snapshot.parentUid && (
                                            <Badge variant="outline" className="text-xs">
                                                Seed
                                            </Badge>
                                        )}
                                    </div>

                                    <div className="text-sm">
                                        <span className="text-muted-foreground">Fitness:</span>
                                        <span className="ml-2 font-semibold text-green-600">
                                            {formatFitness(snapshot.fitness)}
                                        </span>
                                    </div>

                                    {snapshot.parentUid && (
                                        <div className="text-xs text-muted-foreground">
                                            Parent: {snapshot.parentUid.slice(0, 8)}
                                            {snapshot.coParentUids && snapshot.coParentUids.length > 0 && (
                                                <span className="ml-2">
                                                    + {snapshot.coParentUids.length} co-parent(s)
                                                </span>
                                            )}
                                        </div>
                                    )}

                                    <div className="text-xs text-muted-foreground">
                                        Created: {new Date(snapshot.createdAt).toLocaleString()}
                                    </div>
                                </div>

                                {/* Right: Actions */}
                                <div className="flex flex-col gap-2">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => onViewCode(snapshot)}
                                    >
                                        <Eye className="w-4 h-4 mr-2" />
                                        View Code
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => onViewLineage(snapshot)}
                                        disabled={!snapshot.parentUid}
                                    >
                                        <GitBranch className="w-4 h-4 mr-2" />
                                        Lineage
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
}
