import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTeams } from '../../hooks/use-teams';
import { useTeamContext } from '../../context/team-context';
import { Building2, Check, ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';

export function TeamSwitcher() {
  const navigate = useNavigate();
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
    return <Skeleton className="h-9 w-40 rounded-lg" />;
  }

  if (!teams || teams.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-border/40 px-3 py-1.5 text-xs text-muted-foreground">
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
        <span className="text-xs font-medium">
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
          <div className="absolute top-full right-0 mt-1.5 w-52 z-50 rounded-lg border bg-card shadow-lg overflow-hidden">
            <div className="p-1.5">
              {teams.map((team, index) => {
                const isSelected = team.id === selectedTeamId;
                return (
                  <button
                    key={team.id}
                    onClick={() => {
                      setSelectedTeamId(team.id);
                      setIsOpen(false);
                      navigate('/');
                    }}
                    className={cn(
                      "flex w-full items-center justify-between gap-2 px-2.5 py-2 rounded-md transition-colors",
                      isSelected
                        ? "bg-accent/50 text-foreground"
                        : "hover:bg-accent/30 text-foreground"
                    )}
                  >
                    <div className="flex-1 text-left truncate">
                      <div className="text-xs font-medium">
                        {team.name || 'Unnamed Team'}
                      </div>
                    </div>
                    {isSelected && (
                      <Check className="h-3 w-3 flex-shrink-0 text-primary" />
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
