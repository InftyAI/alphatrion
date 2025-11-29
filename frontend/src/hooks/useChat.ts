import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import api from "../services/api";
import type { ChatMessage, ChatRequest } from "../types";

export function useChat() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isOpen, setIsOpen] = useState(false);

    const mutation = useMutation({
        mutationFn: (request: ChatRequest) => api.sendChatMessage(request),
        onSuccess: (data, variables) => {
            // Add user message
            const userMessage: ChatMessage = {
                id: `user-${Date.now()}`,
                role: "user",
                content: variables.message,
                timestamp: new Date(),
            };

            // Add assistant response
            const assistantMessage: ChatMessage = {
                id: `assistant-${Date.now()}`,
                role: "assistant",
                content: data.response,
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, userMessage, assistantMessage]);
        },
        onError: (error: Error) => {
            // Add error message
            const errorMessage: ChatMessage = {
                id: `error-${Date.now()}`,
                role: "assistant",
                content: `Error: ${error.message}`,
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, errorMessage]);
        },
    });

    const sendMessage = (message: string, context: any = {}) => {
        mutation.mutate({ message, context });
    };

    const clearMessages = () => {
        setMessages([]);
    };

    const toggleChat = () => {
        setIsOpen((prev) => !prev);
    };

    return {
        messages,
        isOpen,
        isLoading: mutation.isPending,
        sendMessage,
        clearMessages,
        toggleChat,
        setIsOpen,
    };
}