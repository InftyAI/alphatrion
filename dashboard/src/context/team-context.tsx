import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface TeamContextValue {
  selectedTeamId: string | null;
  setSelectedTeamId: (teamId: string) => void;
}

const TeamContext = createContext<TeamContextValue | undefined>(undefined);

const TEAM_STORAGE_KEY = 'alphatrion_selected_team';

export function TeamProvider({ children }: { children: ReactNode }) {
  // Load from localStorage or default to null
  const [selectedTeamId, setSelectedTeamIdState] = useState<string | null>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(TEAM_STORAGE_KEY);
    }
    return null;
  });

  const setSelectedTeamId = (teamId: string) => {
    setSelectedTeamIdState(teamId);
    if (typeof window !== 'undefined') {
      localStorage.setItem(TEAM_STORAGE_KEY, teamId);
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
