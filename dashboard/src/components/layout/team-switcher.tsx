import { useState, useEffect } from 'react';
import { useTeams } from '../../hooks/use-teams';
import { useTeamContext } from '../../context/team-context';
import { Building2, Check, ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';

export function TeamSwitcher() {
  const { data: teams, isLoading } = useTeams();
  const { selectedTeamId, setSelectedTeamId } = useTeamContext();
  const [isOpen, setIsOpen] = useState(false);

  // Auto-select first team if none selected
  useEffect(() => {
    if (teams && teams.length > 0 && !selectedTeamId) {
      setSelectedTeamId(teams[0].id);
    }
  }, [teams, selectedTeamId, setSelectedTeamId]);

  if (isLoading) {
    return <Skeleton className="h-10 w-48" />;
  }

  if (!teams || teams.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm text-muted-foreground">
        <Building2 className="h-4 w-4" />
        No teams available
      </div>
    );
  }

  const selectedTeam = teams.find((team) => team.id === selectedTeamId);

  return (
    <div className="relative">
      <Button
        variant="outline"
        onClick={() => setIsOpen(!isOpen)}
        className="h-9 px-3 gap-2 border-border/40 hover:border-border hover:bg-accent/50"
      >
        <Building2 className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-medium">
          {selectedTeam?.name || 'Select team'}
        </span>
        <ChevronDown className={cn(
          "h-3.5 w-3.5 text-muted-foreground transition-transform",
          isOpen && "rotate-180"
        )} />
      </Button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="absolute top-full right-0 mt-2 w-64 z-50 rounded-xl border bg-card shadow-xl overflow-hidden">
            <div className="p-2">
              {teams.map((team, index) => {
                const isSelected = team.id === selectedTeamId;
                return (
                  <button
                    key={team.id}
                    onClick={() => {
                      setSelectedTeamId(team.id);
                      setIsOpen(false);
                    }}
                    className={cn(
                      "flex w-full items-center justify-between gap-3 px-3 py-3 rounded-lg text-sm transition-all",
                      isSelected
                        ? "bg-primary/10 text-primary"
                        : "hover:bg-accent text-foreground"
                    )}
                  >
                    <div className="flex-1 text-left">
                      <div className={cn(
                        "font-medium",
                        isSelected && "font-semibold"
                      )}>
                        {team.name || 'Unnamed Team'}
                      </div>
                      {team.description && (
                        <div className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                          {team.description}
                        </div>
                      )}
                    </div>
                    {isSelected && (
                      <Check className="h-4 w-4 flex-shrink-0" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
