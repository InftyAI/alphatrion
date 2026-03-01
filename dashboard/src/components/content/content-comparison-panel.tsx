import { useMemo, useState, useCallback, useEffect, useRef, memo } from "react";
import { Badge } from "../ui/badge";
import { Code, Columns2, Rows2, GitBranch, Sprout, ChevronDown, ChevronRight, FileCode, ChevronsUpDown } from "lucide-react";
import type { ContentSnapshot } from "../../types";
import { Highlight, themes } from "prism-react-renderer";
import { formatFitness } from "../../utils/fitness";
import { computeAllFileDiffs, type FileDiff, type DiffLine, type SplitLine } from "../../utils/file-diff";
import { cn } from "../../lib/utils";

type ViewMode = 'unified' | 'split';

// Number of context lines to show around changes
const CONTEXT_LINES = 3;

// Memoized file diff section to prevent re-renders when siblings change
const FileDiffSection = memo(function FileDiffSection({
    fd, viewMode, language, isMultiFile, collapsed, onToggle, onFileSelect,
}: {
    fd: FileDiff;
    viewMode: ViewMode;
    language: string;
    isMultiFile: boolean;
    collapsed: boolean;
    onToggle: () => void;
    onFileSelect?: (filename: string) => void;
}) {
    const hasChanges = fd.additions > 0 || fd.removals > 0;

    // Compute visible line ranges (context collapsing)
    const visibleUnified = useMemo(() => computeVisibleRanges(fd.unified), [fd.unified]);
    const visibleSplit = useMemo(() => computeVisibleRanges(fd.left), [fd.left]);

    return (
        <div data-file-id={fd.filename || undefined}>
            {isMultiFile && (
                <button onClick={() => { onToggle(); onFileSelect?.(fd.filename); }} className="flex items-center gap-2 w-full px-3 py-1.5 bg-gray-50 border-b border-gray-200 hover:bg-gray-100 transition-colors text-left">
                    {collapsed ? <ChevronRight className="h-3.5 w-3.5 text-gray-500 shrink-0" /> : <ChevronDown className="h-3.5 w-3.5 text-gray-500 shrink-0" />}
                    <FileCode className="h-3.5 w-3.5 text-gray-500 shrink-0" />
                    <span className="text-xs font-mono font-medium text-gray-700 truncate">{fd.filename}</span>
                    {hasChanges ? (
                        <span className="flex items-center gap-1.5 ml-auto shrink-0">
                            {fd.additions > 0 && <span className="text-xs font-mono text-green-600">+{fd.additions}</span>}
                            {fd.removals > 0 && <span className="text-xs font-mono text-red-600">-{fd.removals}</span>}
                        </span>
                    ) : (
                        <span className="text-xs text-gray-400 ml-auto shrink-0">unchanged</span>
                    )}
                </button>
            )}
            {!(isMultiFile && collapsed) && viewMode === 'unified' && (
                <Highlight theme={themes.oneLight} code={fd.unified.map(l => l.content).join('\n')} language={language}>
                    {({ tokens, getTokenProps }) => (
                        <table className="w-full border-collapse">
                            <tbody>
                                {renderUnifiedRows(fd.unified, tokens, getTokenProps, visibleUnified)}
                            </tbody>
                        </table>
                    )}
                </Highlight>
            )}
            {!(isMultiFile && collapsed) && viewMode === 'split' && (
                <div className="flex">
                    <div className="w-1/2 border-r-2 border-gray-300" style={{ overflowX: 'auto', overflowY: 'clip' }}>
                        <Highlight theme={themes.oneLight} code={fd.left.map(l => l.content).join('\n')} language={language}>
                            {({ tokens, getTokenProps }) => (
                                <table className="border-collapse" style={{ minWidth: '100%' }}>
                                    <tbody>
                                        {renderSplitRows(fd.left, tokens, getTokenProps, visibleSplit, 'left')}
                                    </tbody>
                                </table>
                            )}
                        </Highlight>
                    </div>
                    <div className="w-1/2" style={{ overflowX: 'auto', overflowY: 'clip' }}>
                        <Highlight theme={themes.oneLight} code={fd.right.map(l => l.content).join('\n')} language={language}>
                            {({ tokens, getTokenProps }) => (
                                <table className="border-collapse" style={{ minWidth: '100%' }}>
                                    <tbody>
                                        {renderSplitRows(fd.right, tokens, getTokenProps, visibleSplit, 'right')}
                                    </tbody>
                                </table>
                            )}
                        </Highlight>
                    </div>
                </div>
            )}
        </div>
    );
});

// Compute which line indices are visible (near changes) vs collapsed
function computeVisibleRanges(lines: (DiffLine | SplitLine)[]): { visible: boolean[]; gaps: { start: number; end: number }[] } {
    const visible = new Array(lines.length).fill(false);
    // Mark changed lines and their context
    for (let i = 0; i < lines.length; i++) {
        const t = lines[i].type;
        if (t === 'added' || t === 'removed' || t === 'empty') {
            for (let j = Math.max(0, i - CONTEXT_LINES); j <= Math.min(lines.length - 1, i + CONTEXT_LINES); j++) {
                visible[j] = true;
            }
        }
    }
    // If all lines are visible (small file or many changes), show everything
    const hiddenCount = visible.filter(v => !v).length;
    if (hiddenCount < 4) {
        visible.fill(true);
    }
    // Compute gap ranges
    const gaps: { start: number; end: number }[] = [];
    let gapStart = -1;
    for (let i = 0; i < visible.length; i++) {
        if (!visible[i] && gapStart === -1) gapStart = i;
        if ((visible[i] || i === visible.length - 1) && gapStart !== -1) {
            const end = visible[i] ? i - 1 : i;
            if (!visible[end]) gaps.push({ start: gapStart, end });
            gapStart = -1;
        }
    }
    return { visible, gaps };
}

// Render a "N lines hidden" separator row
function GapRow({ count, colSpan }: { count: number; colSpan: number }) {
    return (
        <tr className="bg-blue-50/50">
            <td colSpan={colSpan} className="px-3 py-0.5 text-center">
                <span className="inline-flex items-center gap-1 text-[10px] text-blue-500">
                    <ChevronsUpDown className="h-2.5 w-2.5" />
                    {count} unchanged lines
                </span>
            </td>
        </tr>
    );
}

type GetTokenProps = (input: { token: any; key?: number }) => any;

function renderTokenLine(tokens: any[][], lineIdx: number, getTokenProps: GetTokenProps) {
    const lineTokens = tokens[lineIdx];
    if (!lineTokens) return <span> </span>;
    return (
        <span>
            {lineTokens.map((token, key) => (
                <span key={key} {...getTokenProps({ token, key })} />
            ))}
        </span>
    );
}

function renderUnifiedRows(
    lines: DiffLine[], tokens: any[][], getTokenProps: GetTokenProps,
    ranges: { visible: boolean[]; gaps: { start: number; end: number }[] }
) {
    const rows: React.ReactNode[] = [];
    let gapIdx = 0;
    for (let i = 0; i < lines.length; i++) {
        // Insert gap row if we're at the start of a gap
        if (gapIdx < ranges.gaps.length && ranges.gaps[gapIdx].start === i) {
            const gap = ranges.gaps[gapIdx];
            rows.push(<GapRow key={`gap-${i}`} count={gap.end - gap.start + 1} colSpan={4} />);
            i = gap.end; // skip to end of gap
            gapIdx++;
            continue;
        }
        if (!ranges.visible[i]) continue;
        const line = lines[i];
        const bgClass = line.type === 'removed' ? 'bg-red-50' : line.type === 'added' ? 'bg-green-50' : '';
        const lnClass = line.type === 'removed' ? 'bg-red-100 text-red-400' : line.type === 'added' ? 'bg-green-100 text-green-400' : 'bg-gray-50 text-gray-400';
        const indClass = line.type === 'removed' ? 'bg-red-100 text-red-600' : line.type === 'added' ? 'bg-green-100 text-green-600' : 'bg-gray-50 text-gray-400';
        const ind = line.type === 'removed' ? '−' : line.type === 'added' ? '+' : ' ';
        rows.push(
            <tr key={i} className={bgClass}>
                <td className={`${lnClass} px-2 py-0 text-right select-none w-12 border-r border-gray-200`}>{line.oldLineNum ?? ''}</td>
                <td className={`${lnClass} px-2 py-0 text-right select-none w-12 border-r border-gray-200`}>{line.newLineNum ?? ''}</td>
                <td className={`${indClass} px-2 py-0 text-center select-none w-6 border-r border-gray-200 font-bold`}>{ind}</td>
                <td className="px-3 py-0 whitespace-pre">{renderTokenLine(tokens, i, getTokenProps)}</td>
            </tr>
        );
    }
    return rows;
}

function renderSplitRows(
    lines: SplitLine[], tokens: any[][], getTokenProps: GetTokenProps,
    ranges: { visible: boolean[]; gaps: { start: number; end: number }[] },
    side: 'left' | 'right'
) {
    const rows: React.ReactNode[] = [];
    let gapIdx = 0;
    for (let i = 0; i < lines.length; i++) {
        if (gapIdx < ranges.gaps.length && ranges.gaps[gapIdx].start === i) {
            const gap = ranges.gaps[gapIdx];
            rows.push(<GapRow key={`gap-${i}`} count={gap.end - gap.start + 1} colSpan={2} />);
            i = gap.end;
            gapIdx++;
            continue;
        }
        if (!ranges.visible[i]) continue;
        const line = lines[i];
        const isLeft = side === 'left';
        const bgClass = line.type === (isLeft ? 'removed' : 'added') ? (isLeft ? 'bg-red-50' : 'bg-green-50') : line.type === 'empty' ? 'bg-gray-50' : '';
        const lnClass = line.type === (isLeft ? 'removed' : 'added') ? (isLeft ? 'bg-red-100 text-red-400' : 'bg-green-100 text-green-400') : 'bg-gray-50 text-gray-400';
        rows.push(
            <tr key={i} className={bgClass} style={{ height: '20px' }}>
                <td className={`${lnClass} px-2 py-0 text-right select-none w-12 border-r border-gray-200 leading-5`}>{line.lineNum ?? ''}</td>
                <td className="px-3 py-0 whitespace-pre leading-5">{line.type !== 'empty' ? renderTokenLine(tokens, i, getTokenProps) : <span>&nbsp;</span>}</td>
            </tr>
        );
    }
    return rows;
}

interface ContentComparisonPanelProps {
    snapshot1: ContentSnapshot | null;
    snapshot2: ContentSnapshot | null;
    onCompareWithParent?: (() => void);
    onCompareWithSeed?: (() => void);
    externalFileDiffs?: FileDiff[];
    scrollToFile?: string | null;
    onFileSelect?: (filename: string) => void;
}

export default function ContentComparisonPanel({
    snapshot1,
    snapshot2,
    onCompareWithParent,
    onCompareWithSeed,
    externalFileDiffs,
    scrollToFile,
    onFileSelect,
}: ContentComparisonPanelProps) {
    const [viewMode, setViewMode] = useState<ViewMode>('split');
    const [collapsedFiles, setCollapsedFiles] = useState<Set<string>>(new Set());
    const scrollContainerRef = useRef<HTMLDivElement>(null);

    // Use externally provided diffs if available, otherwise compute internally
    const internalFileDiffs = useMemo(() => {
        if (externalFileDiffs) return externalFileDiffs;
        if (!snapshot1 || !snapshot2) return [];
        return computeAllFileDiffs(snapshot1.contentText ?? "", snapshot2.contentText ?? "");
    }, [snapshot1, snapshot2, externalFileDiffs]);
    const fileDiffs = internalFileDiffs;

    // Initialize collapsed state: unchanged files collapsed, changed files expanded
    const initialCollapsed = useMemo(() => {
        const collapsed = new Set<string>();
        for (const fd of fileDiffs) {
            if (fd.filename && fd.additions === 0 && fd.removals === 0) {
                collapsed.add(fd.filename);
            }
        }
        return collapsed;
    }, [fileDiffs]);

    // Reset collapsed state when fileDiffs change
    useEffect(() => {
        setCollapsedFiles(initialCollapsed);
    }, [initialCollapsed]);

    const toggleFile = useCallback((filename: string) => {
        setCollapsedFiles(prev => {
            const next = new Set(prev);
            if (next.has(filename)) next.delete(filename);
            else next.add(filename);
            return next;
        });
    }, []);

    // Scroll to file when scrollToFile prop changes
    useEffect(() => {
        if (!scrollToFile || !scrollContainerRef.current) return;
        // Expand the file if collapsed
        setCollapsedFiles(prev => {
            if (prev.has(scrollToFile)) {
                const next = new Set(prev);
                next.delete(scrollToFile);
                return next;
            }
            return prev;
        });
        // Wait a tick for DOM to update after expanding
        requestAnimationFrame(() => {
            const el = scrollContainerRef.current?.querySelector(`[data-file-id="${CSS.escape(scrollToFile)}"]`);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }, [scrollToFile]);

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

    const lang = snapshot1.language || "python";
    const isMultiFile = fileDiffs.length > 1 || (fileDiffs.length === 1 && fileDiffs[0].filename !== '');

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

            {/* Diff content */}
            <div ref={scrollContainerRef} className="flex-1 overflow-auto font-mono text-xs bg-white">
                {fileDiffs.map((fd, fi) => (
                    <FileDiffSection
                        key={fd.filename || fi}
                        fd={fd}
                        viewMode={viewMode}
                        language={lang}
                        isMultiFile={isMultiFile}
                        collapsed={collapsedFiles.has(fd.filename)}
                        onToggle={() => toggleFile(fd.filename)}
                        onFileSelect={onFileSelect}
                    />
                ))}
            </div>
        </div>
    );
}
