import { useEffect, useState } from 'react';
import { Route, Routes, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { User, UserProvider } from './context/user-context';
import { useTeamContext } from './context/team-context';
import { Layout } from './components/layout/layout';
import { DashboardPage } from './pages/dashboard';
import { ExperimentsPage } from './pages/experiments';
import { ExperimentDetailPage } from './pages/experiments/[id]';
import { ExperimentComparePage } from './pages/experiments/compare';
import { RunsPage } from './pages/runs';
import { RunDetailPage } from './pages/runs/[id]';
import { AgentsPage } from './pages/agents';
import { AgentDetailPage } from './pages/agents/[id]';
import { SessionDetailPage } from './pages/sessions/[id]';
import { DatasetsPage } from './pages/datasets';
import { ArtifactsPage } from './pages/artifacts';
import { LoginPage } from './pages/login';
import type { Team } from './types';

// Helper to decode JWT
function decodeJWT(token: string): any {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const { selectedTeamId, setSelectedTeamId } = useTeamContext();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  useEffect(() => {
    async function initialize() {
      try {
        // Check for JWT token
        const token = localStorage.getItem('alphatrion_token');
        const storedUser = localStorage.getItem('alphatrion_user');

        console.log('Initializing app...', {
          hasToken: !!token,
          hasUser: !!storedUser,
          currentPath: window.location.pathname
        });

        if (!token || !storedUser) {
          // No token, redirect to login (only if not already there)
          console.log('No token or user, redirecting to login');
          if (window.location.pathname !== '/login') {
            navigate('/login');
          }
          setLoading(false);
          return;
        }

        // Decode JWT to check expiration
        const payload = decodeJWT(token);
        const isExpired = !payload || payload.exp * 1000 < Date.now();
        console.log('Token validation:', { isExpired, exp: payload?.exp });

        if (isExpired) {
          // Token expired, clear and redirect to login
          console.log('Token expired, clearing and redirecting');
          localStorage.removeItem('alphatrion_token');
          localStorage.removeItem('alphatrion_user');
          if (window.location.pathname !== '/login') {
            navigate('/login');
          }
          setLoading(false);
          return;
        }

        console.log('User authenticated, loading dashboard');

        // Parse stored user info (already has teams from login response)
        const user = JSON.parse(storedUser);
        const userId = user.id;
        const orgId = payload.org_id;

        // Check if user ID has changed from previous session
        const previousUserId = localStorage.getItem('alphatrion_user_id');
        if (previousUserId && previousUserId !== userId) {
          // User ID changed - clear all cached data
          console.log('User ID changed, clearing cache');
          queryClient.clear();
        }

        // Store current user ID and org ID for GraphQL headers
        localStorage.setItem('alphatrion_user_id', userId);
        localStorage.setItem('alphatrion_org_id', orgId);

        // Use stored user info (already complete from login)
        setCurrentUser(user);

        // Handle team selection
        if (user.teams && user.teams.length > 0) {
          // Check for saved team preference in localStorage
          const teamKey = `alphatrion_selected_team_${userId}`;
          const savedTeamId = localStorage.getItem(teamKey);

          let selectedTeamId: string;

          if (savedTeamId) {
            const savedTeam = user.teams.find((t: any) => t.id === savedTeamId);
            selectedTeamId = savedTeam ? savedTeamId : user.teams[0].id;
          } else {
            // No saved team, use first team
            selectedTeamId = user.teams[0].id;
          }

          localStorage.setItem('alphatrion_team_id', selectedTeamId);
          setSelectedTeamId(selectedTeamId, userId);
        }
      } catch (err) {
        console.error('Failed to initialize app:', err);
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    }

    initialize();
  }, [setSelectedTeamId, queryClient, navigate]);

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
            Error Initializing Dashboard
          </h1>
          <p className="text-gray-700 mb-2">{error.message}</p>
          <p className="text-gray-500 text-sm">
            Please try:
          </p>
          <ul className="text-gray-500 text-sm text-left mt-2 space-y-1">
            <li>• Clear browser cache and localStorage</li>
            <li>• Verify the backend server is running</li>
            <li>• <button onClick={() => { localStorage.clear(); window.location.href = '/login'; }} className="text-blue-600 underline">Logout and login again</button></li>
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full">
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        {currentUser ? (
          <Route path="/" element={<UserProvider user={currentUser}><Layout /></UserProvider>}>
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
            <Route path="agents">
              <Route index element={<AgentsPage />} />
              <Route path=":id" element={<AgentDetailPage />} />
            </Route>
            <Route path="sessions">
              <Route path=":id" element={<SessionDetailPage />} />
            </Route>
            <Route path="datasets" element={<DatasetsPage />} />
            <Route path="artifacts" element={<ArtifactsPage />} />
          </Route>
        ) : null}
      </Routes>
    </div>
  );
}

export default App;
