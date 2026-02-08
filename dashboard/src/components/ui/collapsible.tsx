import * as React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';

interface CollapsibleProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
}

export function Collapsible({
  title,
  children,
  defaultOpen = false,
  className,
}: CollapsibleProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen);

  return (
    <div className={cn('border rounded-lg', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between p-4 text-left hover:bg-accent transition-colors"
      >
        <span className="font-semibold text-sm">{title}</span>
        <ChevronDown
          className={cn(
            'h-4 w-4 transition-transform text-muted-foreground',
            isOpen && 'rotate-180'
          )}
        />
      </button>
      {isOpen && (
        <div className="border-t p-4">
          {children}
        </div>
      )}
    </div>
  );
}
