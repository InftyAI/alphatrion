import { AlertCircle, ChevronDown, ChevronUp, Loader2, MessageSquare } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useChat } from "../../hooks/use-chat";
import { ChatInput } from "./ChatInput";
import { ChatMessage } from "./ChatMessage";

interface ChatInlineProps {
    experimentId: string;
    isExpanded: boolean;
    onToggle: () => void;
    onSnapshotClick?: (contentUid: string) => void;
}

export function ChatInline({ experimentId, isExpanded, onToggle, onSnapshotClick }: ChatInlineProps) {
    const {
        messages,
        isStreaming,
        error,
        sessionId,
        startSession,
        sendMessage,
        clearChat,
    } = useChat();
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const initializedRef = useRef(false);
    const [height, setHeight] = useState(300);
    const resizeRef = useRef<HTMLDivElement>(null);

    // Start session when expanded
    useEffect(() => {
        if (isExpanded && !initializedRef.current) {
            initializedRef.current = true;
            startSession(experimentId).catch((err) => {
                console.error("Failed to start chat session:", err);
            });
        }
    }, [isExpanded, experimentId, startSession]);

    // Reset when trial changes
    useEffect(() => {
        initializedRef.current = false;
        clearChat();
    }, [experimentId, clearChat]);

    // Scroll to bottom on new messages
    useEffect(() => {
        if (isExpanded) {
            messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages, isExpanded]);

    // Resize handling
    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        const startY = e.clientY;
        const startHeight = height;

        const handleMouseMove = (e: MouseEvent) => {
            const delta = startY - e.clientY;
            setHeight(Math.max(150, Math.min(600, startHeight + delta)));
        };

        const handleMouseUp = () => {
            document.removeEventListener("mousemove", handleMouseMove);
            document.removeEventListener("mouseup", handleMouseUp);
        };

        document.addEventListener("mousemove", handleMouseMove);
        document.addEventListener("mouseup", handleMouseUp);
    }, [height]);

    const suggestedQuestions = [
        "What are the top 3 snapshots?",
        "How has fitness improved?",
        "Show me the best code",
    ];

    if (!isExpanded) {
        return (
            <div
                className="flex items-center justify-between px-3 py-2 border-t bg-muted/30 cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={onToggle}
            >
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <MessageSquare className="h-4 w-4" />
                    <span>Chat with the Hive about this experiment</span>
                </div>
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="border-t flex flex-col" style={{ height }}>
            {/* Resize handle */}
            <div
                ref={resizeRef}
                className="h-1 bg-border hover:bg-primary/50 cursor-ns-resize flex-shrink-0"
                onMouseDown={handleMouseDown}
            />

            {/* Header */}
            <div
                className="flex items-center justify-between px-3 py-1.5 bg-muted/30 cursor-pointer hover:bg-muted/50 transition-colors flex-shrink-0"
                onClick={onToggle}
            >
                <div className="flex items-center gap-2 text-sm font-medium">
                    <MessageSquare className="h-4 w-4" />
                    <span>Chat</span>
                    {isStreaming && <Loader2 className="h-3 w-3 animate-spin" />}
                </div>
                <ChevronDown className="h-4 w-4" />
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-auto px-3 py-2 space-y-3 min-h-0">
                {/* Loading state */}
                {!sessionId && !error && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Connecting...</span>
                    </div>
                )}

                {/* Error state */}
                {error && (
                    <div className="flex items-start gap-2 p-2 bg-destructive/10 text-destructive rounded text-sm">
                        <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                        <span>{error.message}</span>
                    </div>
                )}

                {/* Empty state with suggestions */}
                {sessionId && messages.length === 0 && !error && (
                    <div className="space-y-2">
                        <p className="text-xs text-muted-foreground">
                            Ask about fitness trends, snapshots, code evolution...
                        </p>
                        <div className="flex flex-wrap gap-1">
                            {suggestedQuestions.map((question, index) => (
                                <button
                                    key={index}
                                    onClick={() => sendMessage(question)}
                                    className="text-xs px-2 py-1 rounded border hover:bg-muted/50 transition-colors"
                                >
                                    {question}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Message list */}
                {messages.map((msg, index) => (
                    <ChatMessage
                        key={index}
                        role={msg.role}
                        content={msg.content}
                        timestamp={msg.timestamp}
                        isStreaming={
                            isStreaming &&
                            index === messages.length - 1 &&
                            msg.role === "assistant"
                        }
                        onSnapshotClick={onSnapshotClick}
                        toolUses={msg.toolUses}
                    />
                ))}

                {/* Scroll anchor */}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="flex-shrink-0">
                <ChatInput
                    onSend={sendMessage}
                    disabled={!sessionId || isStreaming}
                    placeholder={
                        !sessionId
                            ? "Connecting..."
                            : isStreaming
                            ? "Waiting..."
                            : "Ask about this trial..."
                    }
                />
            </div>
        </div>
    );
}
