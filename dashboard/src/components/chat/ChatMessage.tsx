import { memo, type ReactNode } from "react";
import { cn } from "../../lib/utils";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Wrench, Search, FileCode, GitBranch, BarChart3, GitCompare, Database, Loader2 } from "lucide-react";
import type { ToolUse } from "../../hooks/use-chat";

interface ChatMessageProps {
    role: "user" | "assistant";
    content: string;
    timestamp?: string;
    isStreaming?: boolean;
    onSnapshotClick?: (contentUid: string) => void;
    toolUses?: ToolUse[];
}

// Map tool names to icons and display names
const TOOL_CONFIG: Record<string, { icon: typeof Wrench; label: string }> = {
    get_trial_summary: { icon: Database, label: "Fetching trial summary" },
    get_top_snapshots: { icon: BarChart3, label: "Finding top snapshots" },
    get_snapshot_content: { icon: FileCode, label: "Loading code" },
    get_lineage: { icon: GitBranch, label: "Tracing lineage" },
    analyze_fitness_distribution: { icon: BarChart3, label: "Analyzing fitness" },
    compare_snapshots: { icon: GitCompare, label: "Comparing snapshots" },
    search_snapshots: { icon: Search, label: "Searching snapshots" },
};

function ToolUseIndicator({ toolUses, isLoading }: { toolUses: ToolUse[]; isLoading?: boolean }) {
    if (toolUses.length === 0) return null;

    return (
        <div className="flex flex-wrap gap-1.5 mb-2">
            {toolUses.map((tool, index) => {
                const config = TOOL_CONFIG[tool.name] || { icon: Wrench, label: tool.name.replace(/_/g, " ") };
                const Icon = config.icon;
                const isLastTool = index === toolUses.length - 1;
                const showSpinner = isLoading && isLastTool;

                return (
                    <div
                        key={`${tool.name}-${index}`}
                        className={cn(
                            "inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium",
                            showSpinner
                                ? "bg-primary/20 text-primary animate-pulse"
                                : "bg-primary/10 text-primary"
                        )}
                    >
                        {showSpinner ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                            <Icon className="w-3 h-3" />
                        )}
                        <span>{config.label}</span>
                    </div>
                );
            })}
        </div>
    );
}

// Pattern to match 8-character hex strings that look like content UIDs
const CONTENT_UID_PATTERN = /\b([a-f0-9]{8})\b/gi;

// Process React children to add clickable UID links
function processChildren(
    children: ReactNode,
    onSnapshotClick?: (uid: string) => void
): ReactNode {
    if (!onSnapshotClick) return children;

    return processNode(children, onSnapshotClick);
}

function processNode(
    node: ReactNode,
    onSnapshotClick: (uid: string) => void
): ReactNode {
    if (typeof node === "string") {
        return <TextWithUidLinks text={node} onSnapshotClick={onSnapshotClick} />;
    }

    if (Array.isArray(node)) {
        return node.map((child, index) => (
            <span key={index}>{processNode(child, onSnapshotClick)}</span>
        ));
    }

    // For other React elements, return as-is (they may contain their own text)
    return node;
}

// Component to render text with clickable UID links
function TextWithUidLinks({
    text,
    onSnapshotClick,
}: {
    text: string;
    onSnapshotClick?: (uid: string) => void;
}) {
    if (!onSnapshotClick) {
        return <>{text}</>;
    }

    const parts: ReactNode[] = [];
    let lastIndex = 0;
    let match;

    // Reset regex state
    CONTENT_UID_PATTERN.lastIndex = 0;

    while ((match = CONTENT_UID_PATTERN.exec(text)) !== null) {
        // Add text before the match
        if (match.index > lastIndex) {
            parts.push(text.slice(lastIndex, match.index));
        }

        // Add the clickable UID
        const uid = match[1];
        parts.push(
            <button
                key={`${match.index}-${uid}`}
                onClick={() => onSnapshotClick(uid)}
                className="text-primary hover:underline font-mono text-sm bg-primary/10 px-1 rounded cursor-pointer"
                title={`View snapshot ${uid}`}
            >
                {uid}
            </button>
        );

        lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < text.length) {
        parts.push(text.slice(lastIndex));
    }

    return <>{parts}</>;
}

export const ChatMessage = memo(function ChatMessage({
    role,
    content,
    isStreaming = false,
    onSnapshotClick,
    toolUses,
}: ChatMessageProps) {
    const isUser = role === "user";

    return (
        <div
            className={cn(
                "flex",
                isUser ? "justify-end" : "justify-start"
            )}
        >
            <div
                className={cn(
                    "max-w-[85%] px-3 py-2 rounded-2xl",
                    isUser
                        ? "bg-primary text-primary-foreground rounded-br-md"
                        : "bg-muted rounded-bl-md"
                )}
            >
                {isUser ? (
                    <p className="text-sm whitespace-pre-wrap">{content}</p>
                ) : (
                    <div className="prose prose-sm max-w-none dark:prose-invert prose-p:leading-relaxed prose-pre:p-0 prose-pre:my-2">
                        {toolUses && toolUses.length > 0 && (
                            <ToolUseIndicator toolUses={toolUses} isLoading={isStreaming} />
                        )}
                        <ReactMarkdown
                            components={{
                                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                code({ className, children, ...props }: any) {
                                    const match = /language-(\w+)/.exec(className || "");
                                    const isInline = !match && !className;

                                    if (isInline) {
                                        // Check if inline code looks like a UID
                                        const text = String(children);
                                        if (onSnapshotClick && /^[a-f0-9]{8}$/i.test(text)) {
                                            return (
                                                <button
                                                    onClick={() => onSnapshotClick(text)}
                                                    className="text-primary hover:underline font-mono text-sm bg-primary/10 px-1 rounded cursor-pointer"
                                                    title={`View snapshot ${text}`}
                                                >
                                                    {text}
                                                </button>
                                            );
                                        }
                                        return (
                                            <code
                                                className="bg-background/50 px-1 py-0.5 rounded text-sm"
                                                {...props}
                                            >
                                                {children}
                                            </code>
                                        );
                                    }

                                    return (
                                        <SyntaxHighlighter
                                            style={oneLight}
                                            language={match ? match[1] : "text"}
                                            PreTag="div"
                                            customStyle={{
                                                margin: 0,
                                                fontSize: "0.8rem",
                                                borderRadius: "0.375rem",
                                            }}
                                        >
                                            {String(children).replace(/\n$/, "")}
                                        </SyntaxHighlighter>
                                    );
                                },
                                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                p({ children }: any) {
                                    return (
                                        <p className="mb-2 last:mb-0 text-sm">
                                            {processChildren(children, onSnapshotClick)}
                                        </p>
                                    );
                                },
                                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                ul({ children }: any) {
                                    return <ul className="list-disc pl-4 mb-2 text-sm">{children}</ul>;
                                },
                                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                ol({ children }: any) {
                                    return <ol className="list-decimal pl-4 mb-2 text-sm">{children}</ol>;
                                },
                                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                li({ children }: any) {
                                    return (
                                        <li className="mb-1">
                                            {processChildren(children, onSnapshotClick)}
                                        </li>
                                    );
                                },
                                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                strong({ children }: any) {
                                    // Check if bold text is a UID
                                    const text = String(children);
                                    if (onSnapshotClick && /^[a-f0-9]{8}$/i.test(text)) {
                                        return (
                                            <button
                                                onClick={() => onSnapshotClick(text)}
                                                className="font-bold text-primary hover:underline cursor-pointer"
                                                title={`View snapshot ${text}`}
                                            >
                                                {text}
                                            </button>
                                        );
                                    }
                                    return (
                                        <strong>
                                            {processChildren(children, onSnapshotClick)}
                                        </strong>
                                    );
                                },
                                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                em({ children }: any) {
                                    // Check if italic text is a UID
                                    const text = String(children);
                                    if (onSnapshotClick && /^[a-f0-9]{8}$/i.test(text)) {
                                        return (
                                            <button
                                                onClick={() => onSnapshotClick(text)}
                                                className="italic text-primary hover:underline cursor-pointer"
                                                title={`View snapshot ${text}`}
                                            >
                                                {text}
                                            </button>
                                        );
                                    }
                                    return (
                                        <em>
                                            {processChildren(children, onSnapshotClick)}
                                        </em>
                                    );
                                },
                            }}
                        >
                            {content || (isStreaming ? "..." : "")}
                        </ReactMarkdown>
                        {isStreaming && !content && (
                            <span className="inline-block animate-pulse">▋</span>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
});
