import { useEffect, useState, createContext, useContext } from 'react';
import { Route, Routes } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { getUserId } from './lib/config';
import { graphqlQuery, queries } from './lib/graphql-client';
import { User, UserProvider } from './context/user-context';
import { useTeamContext } from './context/team-context';
import { Layout } from './components/layout/layout';
import { DashboardPage } from './pages/dashboard';
import { ExperimentsPage } from './pages/experiments';
import { ExperimentDetailPage } from './pages/experiments/[id]';
import { ExperimentComparePage } from './pages/experiments/compare';
import { RunsPage } from './pages/runs';
import { RunDetailPage } from './pages/runs/[id]';
import { ExperimentIDEPage } from './pages/experiments/ide/[id]';
import { ArtifactsPage } from './pages/artifacts';
import type { Team } from './types';

// Selection Context for IDE component
interface SelectionContextType {
  experimentId: string | null;
  setExperimentId: (id: string | null) => void;
  experimentName: string | null;
  setExperimentName: (name: string | null) => void;
  selectedPointName: string | null;
  setSelectedPointName: (name: string | null) => void;
  chartPanelMode: "results" | "metrics";
  setChartPanelMode: (mode: "results" | "metrics") => void;
}

const SelectionContext = createContext<SelectionContextType | null>(null);

export function useSelection() {
  const ctx = useContext(SelectionContext);
  if (!ctx) throw new Error("useSelection must be used within App");
  return ctx;
}

function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const { selectedTeamId, setSelectedTeamId } = useTeamContext();
  const queryClient = useQueryClient();

  // Selection state for IDE component
  const [experimentId, setExperimentId] = useState<string | null>(null);
  const [experimentName, setExperimentName] = useState<string | null>(null);
  const [selectedPointName, setSelectedPointName] = useState<string | null>(null);
  const [chartPanelMode, setChartPanelMode] = useState<"results" | "metrics">("results");

  useEffect(() => {
    async function initialize() {
      try {
        // Step 1: Get userId from config
        const userId = await getUserId();

        // Check if user ID has changed from previous session
        const previousUserId = localStorage.getItem('alphatrion_user_id');
        if (previousUserId && previousUserId !== userId) {
          // User ID changed - clear all cached data
          console.log('User ID changed, clearing cache');
          queryClient.clear();
        }
        // Store current user ID for next session
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
        console.error('Failed to initialize app:', err);
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    }

    initialize();
  }, [setSelectedTeamId, queryClient]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading user information...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center max-w-md">
          <h1 className="text-2xl font-bold text-red-600 mb-4">
            Error Loading User
          </h1>
          <p className="text-gray-700 mb-2">{error.message}</p>
          <p className="text-gray-500 text-sm">
            Please verify:
          </p>
          <ul className="text-gray-500 text-sm text-left mt-2 space-y-1">
            <li>• The user ID exists in the database</li>
            <li>• The backend server is running</li>
            <li>• The dashboard was started with correct --userid flag</li>
          </ul>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    return null;
  }

  const selectionValue = {
    experimentId,
    setExperimentId,
    experimentName,
    setExperimentName,
    selectedPointName,
    setSelectedPointName,
    chartPanelMode,
    setChartPanelMode,
  };

  return (
    <div className="h-full">
      <UserProvider user={currentUser}>
        <SelectionContext.Provider value={selectionValue}>
          <Routes>
            {/* IDE view - full page without layout */}
            <Route path="experiments/:id/ide" element={<ExperimentIDEPage />} />

            {/* Main app with layout */}
            <Route path="/" element={<Layout />}>
              <Route index element={<DashboardPage />} />
              <Route path="experiments">
                <Route index element={<ExperimentsPage />} />
                <Route path=":id" element={<ExperimentDetailPage />} />
                <Route path="compare" element={<ExperimentComparePage />} />
              </Route>
              <Route path="runs">
                <Route index element={<RunsPage />} />
                <Route path=":id" element={<RunDetailPage />} />
              </Route>
              <Route path="artifacts" element={<ArtifactsPage />} />
            </Route>
          </Routes>
        </SelectionContext.Provider>
      </UserProvider>
    </div>
  );
}

export default App;
