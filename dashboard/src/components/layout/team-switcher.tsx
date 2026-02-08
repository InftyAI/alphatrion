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
        className="flex items-center gap-2 min-w-[200px] justify-between"
      >
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4" />
          <span className="font-medium">
            {selectedTeam?.name || 'Select team'}
          </span>
        </div>
        <ChevronDown className={cn(
          "h-4 w-4 transition-transform",
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
          <div className="absolute top-full left-0 mt-2 w-full min-w-[240px] z-50 rounded-md border bg-popover p-1 shadow-lg">
            <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
              Teams
            </div>
            <div className="space-y-1">
              {teams.map((team) => {
                const isSelected = team.id === selectedTeamId;
                return (
                  <button
                    key={team.id}
                    onClick={() => {
                      setSelectedTeamId(team.id);
                      setIsOpen(false);
                    }}
                    className={cn(
                      "flex w-full items-center gap-2 rounded-sm px-2 py-2 text-sm transition-colors hover:bg-accent",
                      isSelected && "bg-accent"
                    )}
                  >
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    <div className="flex-1 text-left">
                      <div className="font-medium">{team.name || 'Unnamed Team'}</div>
                      {team.description && (
                        <div className="text-xs text-muted-foreground line-clamp-1">
                          {team.description}
                        </div>
                      )}
                    </div>
                    {isSelected && (
                      <Check className="h-4 w-4 text-primary" />
                    )}
                  </button>
                );
              })}
            </div>

            {teams.length > 1 && (
              <div className="mt-2 border-t pt-2 px-2 pb-1">
                <p className="text-xs text-muted-foreground">
                  {teams.length} team(s) • Multi-tenant isolation
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
