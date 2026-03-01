import * as React from "react"
import { ChevronDown, X } from "lucide-react"
import { cn } from "../../lib/utils"
import { Badge } from "./badge"

export interface MultiSelectOption {
  value: string
  label: string
  group?: string
}

export interface MultiSelectDropdownProps {
  values: string[]
  onChange: (values: string[]) => void
  options: MultiSelectOption[]
  className?: string
  placeholder?: string
}

export function MultiSelectDropdown({ values, onChange, options, className, placeholder }: MultiSelectDropdownProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const dropdownRef = React.useRef<HTMLDivElement>(null)

  const selectedOptions = options.filter(opt => values.includes(opt.value))

  // Group options by group field
  const groupedOptions = React.useMemo(() => {
    const groups: Record<string, MultiSelectOption[]> = {}
    options.forEach(option => {
      const groupName = option.group || 'Other'
      if (!groups[groupName]) {
        groups[groupName] = []
      }
      groups[groupName].push(option)
    })
    return groups
  }, [options])

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

  const toggleOption = (value: string) => {
    if (values.includes(value)) {
      onChange(values.filter(v => v !== value))
    } else {
      onChange([...values, value])
    }
  }

  const removeOption = (value: string, e: React.MouseEvent) => {
    e.stopPropagation()
    onChange(values.filter(v => v !== value))
  }

  const clearAll = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange([])
  }

  return (
    <div ref={dropdownRef} className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex min-h-9 w-full items-center justify-between rounded-md border bg-background px-3 py-1.5 text-[13px]",
          "hover:bg-accent hover:text-accent-foreground transition-colors",
          "focus:outline-none focus:border-blue-300 focus:bg-blue-50",
          "disabled:cursor-not-allowed disabled:opacity-50"
        )}
      >
        <div className="flex flex-wrap gap-1 flex-1">
          {selectedOptions.length === 0 ? (
            <span className="text-muted-foreground font-medium">{placeholder || "Select labels..."}</span>
          ) : (
            selectedOptions.map((option) => {
              // For "Any" options, show the full label. For specific values, show key:value
              const displayLabel = option.value.endsWith(':*')
                ? option.label
                : `${option.group}:${option.label}`;

              return (
                <Badge
                  key={option.value}
                  variant="outline"
                  className="text-[11px] px-1.5 py-0 font-normal"
                >
                  {displayLabel}
                  <X
                    className="ml-1 h-3 w-3 cursor-pointer hover:text-destructive"
                    onClick={(e) => removeOption(option.value, e)}
                  />
                </Badge>
              );
            })
          )}
        </div>
        <div className="flex items-center gap-1 ml-2">
          {selectedOptions.length > 0 && (
            <X
              className="h-3.5 w-3.5 opacity-50 hover:opacity-100 cursor-pointer"
              onClick={clearAll}
            />
          )}
          <ChevronDown className={cn("h-3.5 w-3.5 opacity-50 transition-transform", isOpen && "transform rotate-180")} />
        </div>
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-lg">
          <div className="max-h-80 overflow-auto p-1">
            {Object.entries(groupedOptions).map(([groupName, groupOptions]) => (
              <div key={groupName}>
                <div className="px-2 py-1.5 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  {groupName}
                </div>
                {groupOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => toggleOption(option.value)}
                    className={cn(
                      "w-full rounded-sm px-2 py-1.5 pl-6 text-[13px] text-left cursor-pointer transition-colors flex items-center gap-2",
                      "hover:bg-accent hover:text-accent-foreground"
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={values.includes(option.value)}
                      onChange={() => {}}
                      className="h-3.5 w-3.5 rounded border-gray-300"
                    />
                    <span className={cn(values.includes(option.value) && "font-medium")}>
                      {option.label}
                    </span>
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
