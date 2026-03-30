import React, { createContext, useContext, useEffect, useState } from 'react';

interface AuthContextType {
  orgId: string | null;
  teamId: string | null;
  userId: string | null;
  setAuthData: (orgId: string, teamId: string, userId: string) => void;
  clearAuth: () => void;
  isReady: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [orgId, setOrgId] = useState<string | null>(null);
  const [teamId, setTeamId] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  // Load from URL params or localStorage on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlOrgId = params.get('orgId');
    const urlTeamId = params.get('teamId');
    const urlUserId = params.get('userId');

    // Try URL params first (for dashboard proxy mode)
    if (urlOrgId && urlTeamId && urlUserId) {
      setAuthData(urlOrgId, urlTeamId, urlUserId);
    } else {
      // Fallback to localStorage
      const storedOrgId = localStorage.getItem('alphatrion_org_id');
      const storedTeamId = localStorage.getItem('alphatrion_team_id');
      const storedUserId = localStorage.getItem('alphatrion_user_id');

      if (storedOrgId && storedTeamId && storedUserId) {
        setOrgId(storedOrgId);
        setTeamId(storedTeamId);
        setUserId(storedUserId);
      }
    }

    setIsReady(true);
  }, []);

  const setAuthData = (newOrgId: string, newTeamId: string, newUserId: string) => {
    setOrgId(newOrgId);
    setTeamId(newTeamId);
    setUserId(newUserId);

    // Persist to localStorage
    localStorage.setItem('alphatrion_org_id', newOrgId);
    localStorage.setItem('alphatrion_team_id', newTeamId);
    localStorage.setItem('alphatrion_user_id', newUserId);
  };

  const clearAuth = () => {
    setOrgId(null);
    setTeamId(null);
    setUserId(null);

    localStorage.removeItem('alphatrion_org_id');
    localStorage.removeItem('alphatrion_team_id');
    localStorage.removeItem('alphatrion_user_id');
  };

  return (
    <AuthContext.Provider value={{ orgId, teamId, userId, setAuthData, clearAuth, isReady }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
