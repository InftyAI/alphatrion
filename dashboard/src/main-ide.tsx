import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TeamProvider, useTeamContext } from './context/team-context';
import { UserProvider } from './context/user-context';
import { getUserId } from './lib/config';
import { graphqlQuery, queries } from './lib/graphql-client';
import CloudIDEFull from './pages/plugins/cloud-ide-full';
import type { User, Team } from './types';
import './styles/index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Wrapper component to initialize user and team context
function IDEApp() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const { setSelectedTeamId } = useTeamContext();

  useEffect(() => {
    async function initialize() {
      try {
        // Step 1: Get userId from config
        const userId = await getUserId();

        // Store current user ID
        localStorage.setItem('alphatrion_user_id', userId);

        // Step 2: Query user information
        const data = await graphqlQuery<{ user: User }>(
          queries.getUser,
          { id: userId }
        );

        if (!data.user) {
          throw new Error(`User with ID ${userId} not found`);
        }

        setCurrentUser(data.user);

        // Step 3: Query user's teams and auto-select team
        const teamsData = await graphqlQuery<{ teams: Team[] }>(
          queries.listTeams,
          { userId }
        );

        if (teamsData.teams && teamsData.teams.length > 0) {
          // Check if this user has a saved team preference in localStorage
          const teamKey = `alphatrion_selected_team_${userId}`;
          const savedTeamId = localStorage.getItem(teamKey);

          let teamToSelect: string;

          if (savedTeamId) {
            // Verify saved team still exists in user's teams
            const savedTeam = teamsData.teams.find(t => t.id === savedTeamId);
            if (savedTeam) {
              teamToSelect = savedTeamId;
            } else {
              // Saved team not found, use first team
              teamToSelect = teamsData.teams[0].id;
            }
          } else {
            // No saved team, use first team
            teamToSelect = teamsData.teams[0].id;
          }

          setSelectedTeamId(teamToSelect, userId);
        }
      } catch (err) {
        console.error('Failed to initialize IDE:', err);
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    }

    initialize();
  }, [setSelectedTeamId]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading Cloud IDE...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center max-w-md">
          <h1 className="text-2xl font-bold text-red-600 mb-4">
            Error Loading IDE
          </h1>
          <p className="text-gray-700 mb-2">{error.message}</p>
          <p className="text-gray-500 text-sm">
            Please verify the backend server is running and try again.
          </p>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    return null;
  }

  return (
    <UserProvider user={currentUser}>
      <BrowserRouter>
        <CloudIDEFull />
      </BrowserRouter>
    </UserProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <TeamProvider>
        <IDEApp />
      </TeamProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
