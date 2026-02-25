import { useMemo, useState } from "react";
import { Badge } from "../../ui/badge";
import { Code, Columns2, Rows2, GitBranch, Sprout } from "lucide-react";
import type { ContentSnapshot } from "../../../types";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { formatFitness } from "../../../utils/fitness";
import { diffLines } from "diff";
import { cn } from "../../../lib/utils";

interface ContentComparisonPanelProps {
    snapshot1: ContentSnapshot | null;
    snapshot2: ContentSnapshot | null;
    onCompareWithParent?: (() => void);
    onCompareWithSeed?: (() => void);
}

type DiffLine = {
    type: 'same' | 'removed' | 'added';
    content: string;
    oldLineNum: number | null;
    newLineNum: number | null;
};

type ViewMode = 'unified' | 'split';

export default function ContentComparisonPanel({
    snapshot1,
    snapshot2,
    onCompareWithParent,
    onCompareWithSeed,
}: ContentComparisonPanelProps) {
    const [viewMode, setViewMode] = useState<ViewMode>('split');

    const diffResult = useMemo(() => {
        if (!snapshot1 || !snapshot2) return { unified: [], left: [], right: [] };

        const text1 = snapshot1.contentText ?? "";
        const text2 = snapshot2.contentText ?? "";
        const changes = diffLines(text1, text2);

        // Unified view
        const unified: DiffLine[] = [];
        let oldLineNum = 1;
        let newLineNum = 1;

        // Split view
        const left: { type: 'same' | 'removed' | 'empty'; content: string; lineNum: number | null }[] = [];
        const right: { type: 'same' | 'added' | 'empty'; content: string; lineNum: number | null }[] = [];
        let leftLineNum = 1;
        let rightLineNum = 1;

        for (const change of changes) {
            const lines = change.value.replace(/\n$/, '').split('\n');

            for (const line of lines) {
                if (change.removed) {
                    unified.push({ type: 'removed', content: line, oldLineNum: oldLineNum++, newLineNum: null });
                    left.push({ type: 'removed', content: line, lineNum: leftLineNum++ });
                    right.push({ type: 'empty', content: '', lineNum: null });
                } else if (change.added) {
                    unified.push({ type: 'added', content: line, oldLineNum: null, newLineNum: newLineNum++ });
                    left.push({ type: 'empty', content: '', lineNum: null });
                    right.push({ type: 'added', content: line, lineNum: rightLineNum++ });
                } else {
                    unified.push({ type: 'same', content: line, oldLineNum: oldLineNum++, newLineNum: newLineNum++ });
                    left.push({ type: 'same', content: line, lineNum: leftLineNum++ });
                    right.push({ type: 'same', content: line, lineNum: rightLineNum++ });
                }
            }
        }

        return { unified, left, right };
    }, [snapshot1, snapshot2]);

    if (!snapshot1 && !snapshot2) {
        return (
            <div className="flex flex-col items-center justify-center h-full py-12">
                <Code className="w-12 h-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground text-center">
                    Select two points from the chart to compare
                </p>
            </div>
        );
    }

    if (!snapshot1 || !snapshot2) {
        return (
            <div className="flex flex-col items-center justify-center h-full py-12">
                <Code className="w-12 h-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground text-center">
                    Select one more point to compare
                </p>
                {(snapshot1 || snapshot2) && (
                    <>
                        <Badge variant="secondary" className="mt-2">
                            1 of 2 selected
                        </Badge>
                        {(onCompareWithParent || onCompareWithSeed) && (
                            <div className="flex items-center gap-2 mt-4">
                                <span className="text-xs text-muted-foreground">Quick:</span>
                                {onCompareWithParent && (
                                    <button
                                        onClick={onCompareWithParent}
                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-gray-200 bg-white hover:bg-gray-50 text-foreground transition-colors"
                                    >
                                        <GitBranch className="h-3 w-3" />
                                        vs Parent
                                    </button>
                                )}
                                {onCompareWithSeed && (
                                    <button
                                        onClick={onCompareWithSeed}
                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-gray-200 bg-white hover:bg-gray-50 text-foreground transition-colors"
                                    >
                                        <Sprout className="h-3 w-3" />
                                        vs Seed
                                    </button>
                                )}
                            </div>
                        )}
                    </>
                )}
            </div>
        );
    }

    const renderCodeLine = (content: string, language: string) => (
        <SyntaxHighlighter
            language={language}
            style={oneLight}
            PreTag="span"
            customStyle={{ margin: 0, padding: 0, fontSize: '0.75rem', background: 'transparent', display: 'inline' }}
            codeTagProps={{ style: { background: 'transparent', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' } }}
        >
            {content || ' '}
        </SyntaxHighlighter>
    );

    return (
        <div className="h-full overflow-hidden flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-red-500" />
                        <span className="text-xs font-mono text-muted-foreground">{snapshot1.contentUid.substring(0, 8)}</span>
                        <span className="text-xs text-red-600 font-medium">{formatFitness(snapshot1.fitness)}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">→</span>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-green-500" />
                        <span className="text-xs font-mono text-muted-foreground">{snapshot2.contentUid.substring(0, 8)}</span>
                        <span className="text-xs text-green-600 font-medium">{formatFitness(snapshot2.fitness)}</span>
                    </div>
                </div>
                {/* View mode toggle */}
                <div className="flex items-center gap-1 bg-gray-100 rounded-md p-0.5">
                    <button
                        onClick={() => setViewMode('split')}
                        className={cn("p-1.5 rounded", viewMode === 'split' ? 'bg-white shadow-sm' : 'hover:bg-gray-200')}
                        title="Split view"
                    >
                        <Columns2 className="h-3.5 w-3.5" />
                    </button>
                    <button
                        onClick={() => setViewMode('unified')}
                        className={cn("p-1.5 rounded", viewMode === 'unified' ? 'bg-white shadow-sm' : 'hover:bg-gray-200')}
                        title="Unified view"
                    >
                        <Rows2 className="h-3.5 w-3.5" />
                    </button>
                </div>
            </div>

            {/* Unified view */}
            {viewMode === 'unified' && (
                <div className="flex-1 overflow-auto font-mono text-xs bg-white">
                    <table className="w-full border-collapse">
                        <tbody>
                            {diffResult.unified.map((line, i) => {
                                const bgClass = line.type === 'removed' ? 'bg-red-50' : line.type === 'added' ? 'bg-green-50' : '';
                                const lineNumClass = line.type === 'removed' ? 'bg-red-100 text-red-400' : line.type === 'added' ? 'bg-green-100 text-green-400' : 'bg-gray-50 text-gray-400';
                                const indicatorClass = line.type === 'removed' ? 'bg-red-100 text-red-600' : line.type === 'added' ? 'bg-green-100 text-green-600' : 'bg-gray-50 text-gray-400';
                                const indicator = line.type === 'removed' ? '−' : line.type === 'added' ? '+' : ' ';

                                return (
                                    <tr key={i} className={bgClass}>
                                        <td className={`${lineNumClass} px-2 py-0 text-right select-none w-12 border-r border-gray-200`}>{line.oldLineNum ?? ''}</td>
                                        <td className={`${lineNumClass} px-2 py-0 text-right select-none w-12 border-r border-gray-200`}>{line.newLineNum ?? ''}</td>
                                        <td className={`${indicatorClass} px-2 py-0 text-center select-none w-6 border-r border-gray-200 font-bold`}>{indicator}</td>
                                        <td className="px-3 py-0 whitespace-pre">{renderCodeLine(line.content, snapshot1.language || "python")}</td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Split view - single vertical scroll, sticky horizontal scrollbars per panel */}
            {viewMode === 'split' && (
                <div className="flex-1 overflow-y-auto overflow-x-hidden font-mono text-xs bg-white">
                    <div className="flex min-h-full">
                        {/* Left panel */}
                        <div
                            className="w-1/2 border-r-2 border-gray-300"
                            style={{ overflowX: 'auto', overflowY: 'clip' }}
                        >
                            <table className="border-collapse" style={{ minWidth: '100%' }}>
                                <tbody>
                                    {diffResult.left.map((line, i) => {
                                        const bgClass = line.type === 'removed' ? 'bg-red-50' : line.type === 'empty' ? 'bg-gray-50' : '';
                                        const lineNumClass = line.type === 'removed' ? 'bg-red-100 text-red-400' : 'bg-gray-50 text-gray-400';
                                        return (
                                            <tr key={i} className={bgClass} style={{ height: '20px' }}>
                                                <td className={`${lineNumClass} px-2 py-0 text-right select-none w-12 border-r border-gray-200 leading-5`}>{line.lineNum ?? ''}</td>
                                                <td className="px-3 py-0 whitespace-pre leading-5">{line.type !== 'empty' ? renderCodeLine(line.content, snapshot1.language || "python") : <span>&nbsp;</span>}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                        {/* Right panel */}
                        <div
                            className="w-1/2"
                            style={{ overflowX: 'auto', overflowY: 'clip' }}
                        >
                            <table className="border-collapse" style={{ minWidth: '100%' }}>
                                <tbody>
                                    {diffResult.right.map((line, i) => {
                                        const bgClass = line.type === 'added' ? 'bg-green-50' : line.type === 'empty' ? 'bg-gray-50' : '';
                                        const lineNumClass = line.type === 'added' ? 'bg-green-100 text-green-400' : 'bg-gray-50 text-gray-400';
                                        return (
                                            <tr key={i} className={bgClass} style={{ height: '20px' }}>
                                                <td className={`${lineNumClass} px-2 py-0 text-right select-none w-12 border-r border-gray-200 leading-5`}>{line.lineNum ?? ''}</td>
                                                <td className="px-3 py-0 whitespace-pre leading-5">{line.type !== 'empty' ? renderCodeLine(line.content, snapshot2.language || "python") : <span>&nbsp;</span>}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
