import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "../../lib/utils"

export interface DropdownOption {
  value: string
  label: string
}

export interface DropdownProps {
  value: string
  onChange: (value: string) => void
  options: DropdownOption[]
  className?: string
  placeholder?: string
}

export function Dropdown({ value, onChange, options, className, placeholder }: DropdownProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const dropdownRef = React.useRef<HTMLDivElement>(null)

  const selectedOption = options.find(opt => opt.value === value)

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  return (
    <div ref={dropdownRef} className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex h-9 w-full items-center justify-between rounded-md border bg-background px-3 py-2 text-[13px] font-medium text-foreground",
          "hover:bg-accent hover:text-accent-foreground transition-colors",
          "focus:outline-none focus:border-blue-300 focus:bg-blue-50",
          "disabled:cursor-not-allowed disabled:opacity-50"
        )}
      >
        <span>{selectedOption?.label || placeholder || "Select..."}</span>
        <ChevronDown className={cn("h-3.5 w-3.5 opacity-50 transition-transform", isOpen && "transform rotate-180")} />
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-lg">
          <div className="max-h-60 overflow-auto p-1">
            {options.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => {
                  onChange(option.value)
                  setIsOpen(false)
                }}
                className={cn(
                  "w-full rounded-sm px-2 py-1.5 text-[13px] text-left cursor-pointer transition-colors",
                  "hover:bg-accent hover:text-accent-foreground",
                  value === option.value && "bg-accent text-accent-foreground font-medium"
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
