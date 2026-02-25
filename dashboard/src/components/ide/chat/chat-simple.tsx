import { useState } from 'react';
import { Send } from 'lucide-react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';

interface ChatPanelProps {
  experimentId?: string;
  context?: any;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export function ChatPanel({ experimentId, context }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages([...messages, userMessage]);
    setInput('');

    // Placeholder for chat API integration
    // In a real implementation, this would call the chat service
    setTimeout(() => {
      const assistantMessage: Message = {
        role: 'assistant',
        content: 'Chat integration coming soon. This will connect to your AI assistant.',
      };
      setMessages((prev) => [...prev, assistantMessage]);
    }, 500);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground text-sm py-8">
            Ask questions about your code or experiment
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`rounded-lg p-3 ${
              msg.role === 'user'
                ? 'bg-blue-50 dark:bg-blue-950 ml-8'
                : 'bg-muted mr-8'
            }`}
          >
            <div className="text-xs font-semibold mb-1">
              {msg.role === 'user' ? 'You' : 'Assistant'}
            </div>
            <div className="text-sm">{msg.content}</div>
          </div>
        ))}
      </div>

      <div className="p-3 border-t">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Ask a question..."
            className="flex-1"
          />
          <Button size="sm" onClick={sendMessage}>
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
