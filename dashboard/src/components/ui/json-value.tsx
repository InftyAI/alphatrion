import { useState } from "react";
import { cn } from "../../lib/utils";

// Collapsible JSON value renderer for evaluation results
export function JsonValue({ value, defaultExpanded = false }: { value: unknown; defaultExpanded?: boolean }) {
    const [expanded, setExpanded] = useState(defaultExpanded);

    if (value === null || value === undefined) {
        return <span className="text-gray-400 italic">null</span>;
    }

    if (typeof value === "boolean") {
        return <span className="text-purple-600">{String(value)}</span>;
    }

    if (typeof value === "number") {
        return <span className="text-blue-600">{value}</span>;
    }

    if (typeof value === "string") {
        // Multiline strings: show with preserved whitespace
        if (value.includes("\n")) {
            return (
                <span className="whitespace-pre-wrap break-words text-green-700">
                    &quot;{value}&quot;
                </span>
            );
        }
        return <span className="text-green-700">&quot;{value}&quot;</span>;
    }

    if (Array.isArray(value)) {
        if (value.length === 0) return <span className="text-gray-500">[]</span>;
        return (
            <span>
                <button
                    type="button"
                    onClick={() => setExpanded(!expanded)}
                    className="text-gray-500 hover:text-gray-700"
                >
                    {expanded ? "▾" : "▸"}{" "}
                    <span className="text-gray-400">[{value.length}]</span>
                </button>
                {expanded && (
                    <div className="ml-4 border-l border-gray-200 pl-2">
                        {value.map((item, i) => (
                            <div key={i} className="py-0.5">
                                <span className="text-gray-400 mr-1">{i}:</span>
                                <JsonValue value={item} />
                            </div>
                        ))}
                    </div>
                )}
            </span>
        );
    }

    if (typeof value === "object") {
        const entries = Object.entries(value as Record<string, unknown>);
        if (entries.length === 0) return <span className="text-gray-500">{"{}"}</span>;
        return (
            <span>
                <button
                    type="button"
                    onClick={() => setExpanded(!expanded)}
                    className="text-gray-500 hover:text-gray-700"
                >
                    {expanded ? "▾" : "▸"}{" "}
                    <span className="text-gray-400">
                        {"{"}
                        {entries.length}
                        {"}"}
                    </span>
                </button>
                {expanded && (
                    <div className="ml-4 border-l border-gray-200 pl-2">
                        {entries.map(([k, v]) => (
                            <div key={k} className="py-0.5">
                                <span className="font-medium text-gray-700">{k}:</span>{" "}
                                <JsonValue value={v} />
                            </div>
                        ))}
                    </div>
                )}
            </span>
        );
    }

    return <span>{String(value)}</span>;
}

// Renders an evaluation result object with special fitness highlighting
export function EvaluationResult({ result }: { result: unknown }) {
    if (result === null || result === undefined) {
        return <p className="text-xs text-muted-foreground">No evaluation data available for this point.</p>;
    }

    const entries = typeof result === "object" && result !== null
        ? Object.entries(result as Record<string, unknown>).sort(([a], [b]) => {
            if (a === "fitness") return -1;
            if (b === "fitness") return 1;
            return 0;
        })
        : [];

    return (
        <div className="p-2 bg-green-50 border border-green-200 rounded text-xs">
            {entries.length > 0 ? (
                <div className="space-y-0.5">
                    {entries.map(([key, value]) => (
                        <div key={key} className="py-0.5">
                            <span className={cn(
                                "font-medium",
                                key === "fitness" ? "text-green-800 text-sm" : "text-gray-700"
                            )}>
                                {key}:
                            </span>{" "}
                            {key === "fitness" ? (
                                <span className="text-green-800 text-sm font-semibold">
                                    <JsonValue value={value} defaultExpanded />
                                </span>
                            ) : (
                                <JsonValue
                                    value={value}
                                    defaultExpanded={typeof value !== "object" || value === null}
                                />
                            )}
                        </div>
                    ))}
                </div>
            ) : (
                <p className="text-sm text-green-800">
                    Result: <JsonValue value={result} defaultExpanded />
                </p>
            )}
        </div>
    );
}
