import { createContext, useContext, useState, ReactNode } from 'react';

interface TeamContextValue {
  selectedTeamId: string | null;
  setSelectedTeamId: (teamId: string, userId?: string) => void;
}

const TeamContext = createContext<TeamContextValue | undefined>(undefined);

export function TeamProvider({ children }: { children: ReactNode }) {
  const [selectedTeamId, setSelectedTeamIdState] = useState<string | null>(null);

  const setSelectedTeamId = (teamId: string, userId?: string) => {
    setSelectedTeamIdState(teamId);
    if (typeof window !== 'undefined' && userId) {
      const teamKey = `alphatrion_selected_team_${userId}`;
      localStorage.setItem(teamKey, teamId);
    }
  };

  return (
    <TeamContext.Provider value={{ selectedTeamId, setSelectedTeamId }}>
      {children}
    </TeamContext.Provider>
  );
}

export function useTeamContext() {
  const context = useContext(TeamContext);
  if (!context) {
    throw new Error('useTeamContext must be used within TeamProvider');
  }
  return context;
}
