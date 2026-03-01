import { useState, useCallback, useRef } from "react";

// API base URL for REST endpoints
// In production, use relative URL (empty string); in dev, use localhost
const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ||
    (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

export interface ToolUse {
    name: string;
    timestamp: string;
}

export interface ChatMessage {
    role: "user" | "assistant";
    content: string;
    timestamp: string;
    toolUses?: ToolUse[];
}

interface ChatStartResponse {
    session_id: string;
    trial_name: string | null;
    snapshot_count: number;
}

interface UseChatResult {
    messages: ChatMessage[];
    isStreaming: boolean;
    error: Error | null;
    sessionId: string | null;
    startSession: (experimentId: string) => Promise<void>;
    sendMessage: (message: string) => Promise<void>;
    clearChat: () => void;
}

/**
 * Hook for managing chat sessions with Claude for trial analysis.
 */
export function useChat(): UseChatResult {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    const startSession = useCallback(async (experimentId: string) => {
        setError(null);
        setMessages([]);

        try {
            const response = await fetch(`${API_BASE_URL}/api/chat/start`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ experiment_id: experimentId }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(
                    errorData.detail || `HTTP error! status: ${response.status}`
                );
            }

            const data: ChatStartResponse = await response.json();
            setSessionId(data.session_id);
        } catch (err) {
            const error = err instanceof Error ? err : new Error("Failed to start chat session");
            setError(error);
            throw error;
        }
    }, []);

    const sendMessage = useCallback(async (message: string) => {
        if (!sessionId) {
            setError(new Error("No active session"));
            return;
        }

        setError(null);
        setIsStreaming(true);

        // Add user message immediately
        const userMessage: ChatMessage = {
            role: "user",
            content: message,
            timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, userMessage]);

        // Create placeholder for assistant response
        const assistantMessage: ChatMessage = {
            role: "assistant",
            content: "",
            timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMessage]);

        try {
            // Cancel any existing request
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
            abortControllerRef.current = new AbortController();

            const response = await fetch(
                `${API_BASE_URL}/api/chat/${sessionId}/message`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ message }),
                    signal: abortControllerRef.current.signal,
                }
            );

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(
                    errorData.detail || `HTTP error! status: ${response.status}`
                );
            }

            // Handle SSE stream
            const reader = response.body?.getReader();
            if (!reader) {
                throw new Error("No response body");
            }

            const decoder = new TextDecoder();
            let accumulatedContent = "";
            let accumulatedToolUses: ToolUse[] = [];

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split("\n");

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const data = line.slice(6);
                        if (data === "[DONE]") {
                            continue;
                        }
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.type === "tool_use" && parsed.tool_name) {
                                // Add tool use event
                                accumulatedToolUses = [
                                    ...accumulatedToolUses,
                                    {
                                        name: parsed.tool_name,
                                        timestamp: new Date().toISOString(),
                                    },
                                ];
                                // Update assistant message with tool uses
                                setMessages((prev) => {
                                    const updated = [...prev];
                                    const lastMsg = updated[updated.length - 1];
                                    if (lastMsg && lastMsg.role === "assistant") {
                                        updated[updated.length - 1] = {
                                            ...lastMsg,
                                            toolUses: accumulatedToolUses,
                                        };
                                    }
                                    return updated;
                                });
                            } else if (parsed.content) {
                                accumulatedContent += parsed.content;
                                // Update assistant message in place
                                setMessages((prev) => {
                                    const updated = [...prev];
                                    const lastMsg = updated[updated.length - 1];
                                    if (lastMsg && lastMsg.role === "assistant") {
                                        updated[updated.length - 1] = {
                                            ...lastMsg,
                                            content: accumulatedContent,
                                        };
                                    }
                                    return updated;
                                });
                            }
                            if (parsed.error) {
                                throw new Error(parsed.error);
                            }
                        } catch (parseErr) {
                            // Ignore parse errors for incomplete chunks
                            if (data !== "[DONE]" && !data.startsWith("{")) {
                                console.warn("Failed to parse SSE data:", data);
                            }
                        }
                    }
                }
            }
        } catch (err) {
            if (err instanceof Error && err.name === "AbortError") {
                // Request was cancelled, ignore
                return;
            }
            const error = err instanceof Error ? err : new Error("Failed to send message");
            setError(error);
            // Remove the empty assistant message on error
            setMessages((prev) => {
                const updated = [...prev];
                const lastMsg = updated[updated.length - 1];
                if (lastMsg && lastMsg.role === "assistant" && !lastMsg.content) {
                    updated.pop();
                }
                return updated;
            });
        } finally {
            setIsStreaming(false);
            abortControllerRef.current = null;
        }
    }, [sessionId]);

    const clearChat = useCallback(() => {
        // Cancel any ongoing request
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        setMessages([]);
        setError(null);
        setSessionId(null);
        setIsStreaming(false);
    }, []);

    return {
        messages,
        isStreaming,
        error,
        sessionId,
        startSession,
        sendMessage,
        clearChat,
    };
}
