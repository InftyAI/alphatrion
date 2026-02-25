import { useRef, useEffect } from 'react';
import { Terminal as TerminalIcon } from 'lucide-react';
import { Input } from '../../ui/input';

interface TerminalPanelProps {
  output: string;
  command: string;
  onCommandChange: (command: string) => void;
  onExecute: () => void;
  podName?: string;
}

export function TerminalPanel({
  output,
  command,
  onCommandChange,
  onExecute,
  podName,
}: TerminalPanelProps) {
  const outputRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when output changes
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      onExecute();
    }
  };

  return (
    <div className="flex flex-col h-full bg-black text-green-400 font-mono text-sm">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-800 bg-gray-900">
        <TerminalIcon className="h-4 w-4" />
        <span className="text-xs">Terminal {podName && `(${podName})`}</span>
      </div>

      <div
        ref={outputRef}
        className="flex-1 overflow-y-auto p-3 whitespace-pre-wrap"
      >
        {output || 'Ready to execute commands...'}
      </div>

      <div className="px-3 py-2 border-t border-gray-800 bg-gray-900">
        <div className="flex items-center gap-2">
          <span className="text-green-400">$</span>
          <Input
            value={command}
            onChange={(e) => onCommandChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter command..."
            className="flex-1 bg-transparent border-none text-green-400 focus-visible:ring-0"
          />
        </div>
      </div>
    </div>
  );
}
