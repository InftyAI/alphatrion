import { AlertCircle, Loader2, MessageSquare, X } from "lucide-react";
import { useCallback, useEffect, useRef } from "react";
import { useChat } from "../../hooks/use-chat";
import { Button } from "../ui/button";
import { ChatInput } from "./ChatInput";
import { ChatMessage } from "./ChatMessage";

interface ChatPanelProps {
    experimentId: string;
    onClose: () => void;
}

export function ChatPanel({ experimentId, onClose }: ChatPanelProps) {
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

    // Start session when panel opens
    useEffect(() => {
        if (!initializedRef.current) {
            initializedRef.current = true;
            startSession(experimentId).catch((err) => {
                console.error("Failed to start chat session:", err);
            });
        }
    }, [experimentId, startSession]);

    // Scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            clearChat();
        };
    }, [clearChat]);

    const handleClose = useCallback(() => {
        clearChat();
        onClose();
    }, [clearChat, onClose]);

    const suggestedQuestions = [
        "What are the top 3 snapshots by fitness?",
        "How has the fitness improved over time?",
        "What's the lineage of the best snapshot?",
        "Show me the code for the best performing version",
    ];

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 z-40"
                onClick={handleClose}
            />

            {/* Panel */}
            <div className="fixed right-4 top-20 bottom-4 w-[500px] bg-background rounded-lg shadow-xl z-50 flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b">
                    <div className="flex items-center gap-2">
                        <MessageSquare className="h-5 w-5" />
                        <h2 className="text-lg font-semibold">Trial Analysis</h2>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={handleClose}
                    >
                        <X className="h-4 w-4" />
                    </Button>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-auto p-4 space-y-4">
                    {/* Loading state */}
                    {!sessionId && !error && (
                        <div className="flex flex-col items-center justify-center h-full gap-4">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                            <p className="text-sm text-muted-foreground">
                                Starting chat session...
                            </p>
                        </div>
                    )}

                    {/* Error state */}
                    {error && (
                        <div className="flex items-start gap-3 p-4 bg-destructive/10 text-destructive rounded-lg">
                            <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                            <div>
                                <p className="font-medium">Error</p>
                                <p className="text-sm mt-1">{error.message}</p>
                            </div>
                        </div>
                    )}

                    {/* Empty state with suggestions */}
                    {sessionId && messages.length === 0 && !error && (
                        <div className="space-y-4">
                            <p className="text-sm text-muted-foreground">
                                Ask questions about your experiment data.
                            </p>
                            <div className="space-y-2">
                                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                    Suggested questions
                                </p>
                                {suggestedQuestions.map((question, index) => (
                                    <button
                                        key={index}
                                        onClick={() => sendMessage(question)}
                                        className="block w-full text-left text-sm p-2 rounded-lg border hover:bg-muted/50 transition-colors"
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
                            toolUses={msg.toolUses}
                        />
                    ))}

                    {/* Scroll anchor */}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <ChatInput
                    onSend={sendMessage}
                    disabled={!sessionId || isStreaming}
                    placeholder={
                        !sessionId
                            ? "Connecting..."
                            : isStreaming
                            ? "Waiting for response..."
                            : "Ask about your trial data..."
                    }
                />
            </div>
        </>
    );
}
