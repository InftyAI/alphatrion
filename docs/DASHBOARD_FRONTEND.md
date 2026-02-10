# Dashboard Frontend Guide

## Overview

The dashboard frontend needs to fetch the current user ID on startup and query user information before rendering the main application.

## Starting the Dashboard

```bash
alphatrion dashboard --userid <USER_UUID> --port 5173
```

The `--userid` flag is **required**. The dashboard will:
1. Store the userId in memory
2. Expose it via `/api/config` endpoint
3. Frontend fetches it and uses it in all queries

## Frontend Implementation

### Step 1: Fetch User ID on App Startup

When the app loads, fetch the userId from the config endpoint:

```typescript
// src/lib/config.ts
interface Config {
  userId: string;
}

let cachedConfig: Config | null = null;

export async function getConfig(): Promise<Config> {
  if (cachedConfig) {
    return cachedConfig;
  }

  const response = await fetch('/api/config');
  if (!response.ok) {
    throw new Error('Failed to load configuration');
  }

  cachedConfig = await response.json();
  return cachedConfig;
}

export async function getUserId(): Promise<string> {
  const config = await getConfig();
  return config.userId;
}
```

### Step 2: Query User Information on Startup

Before rendering the main app, query the user information:

```typescript
// src/App.tsx
import { useEffect, useState } from 'react';
import { getUserId } from './lib/config';
import { graphqlRequest } from './lib/graphql-client';

interface User {
  id: string;
  username: string;
  email: string;
  teams: Array<{
    id: string;
    name: string;
  }>;
}

export function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function loadUser() {
      try {
        const userId = await getUserId();

        const data = await graphqlRequest<{ user: User }>(
          `
          query GetCurrentUser($id: ID!) {
            user(id: $id) {
              id
              username
              email
              teams {
                id
                name
              }
            }
          }
          `,
          { id: userId }
        );

        if (!data.user) {
          throw new Error('User not found');
        }

        setCurrentUser(data.user);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, []);

  if (loading) {
    return <div>Loading user information...</div>;
  }

  if (error) {
    return (
      <div>
        <h1>Error Loading User</h1>
        <p>{error.message}</p>
        <p>Please check that the user ID exists in the database.</p>
      </div>
    );
  }

  return (
    <UserContext.Provider value={currentUser}>
      <Router>
        <Routes>
          {/* Your routes here */}
        </Routes>
      </Router>
    </UserContext.Provider>
  );
}
```

### Step 3: Create User Context

Store the user information in React Context for easy access:

```typescript
// src/context/user-context.tsx
import { createContext, useContext } from 'react';

interface User {
  id: string;
  username: string;
  email: string;
  teams: Array<{
    id: string;
    name: string;
  }>;
}

const UserContext = createContext<User | null>(null);

export function useCurrentUser() {
  const user = useContext(UserContext);
  if (!user) {
    throw new Error('useCurrentUser must be used within UserContext.Provider');
  }
  return user;
}

export { UserContext };
```

### Step 4: Use User ID in Queries

Use the userId in all subsequent queries:

```typescript
// src/hooks/use-teams.ts
import { useQuery } from '@tanstack/react-query';
import { useCurrentUser } from '../context/user-context';
import { graphqlRequest } from '../lib/graphql-client';

const TEAMS_QUERY = `
  query GetTeams($userId: ID!) {
    teams(userId: $userId) {
      id
      name
      description
      totalProjects
      totalExperiments
      totalRuns
    }
  }
`;

export function useTeams() {
  const currentUser = useCurrentUser();

  return useQuery({
    queryKey: ['teams', currentUser.id],
    queryFn: async () => {
      const data = await graphqlRequest<{ teams: Team[] }>(
        TEAMS_QUERY,
        { userId: currentUser.id }
      );
      return data.teams;
    },
  });
}
```

## GraphQL Client Helper

```typescript
// src/lib/graphql-client.ts
interface GraphQLResponse<T> {
  data?: T;
  errors?: Array<{ message: string }>;
}

export async function graphqlRequest<T>(
  query: string,
  variables: Record<string, any> = {}
): Promise<T> {
  const response = await fetch('/graphql', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      variables,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const result: GraphQLResponse<T> = await response.json();

  if (result.errors && result.errors.length > 0) {
    throw new Error(result.errors[0].message);
  }

  if (!result.data) {
    throw new Error('No data returned from GraphQL');
  }

  return result.data;
}
```

## Complete Example

```typescript
// src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { App } from './App';
import './index.css';

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
```

```typescript
// src/App.tsx
import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { getUserId } from './lib/config';
import { graphqlRequest } from './lib/graphql-client';
import { UserContext } from './context/user-context';
import { DashboardPage } from './pages/dashboard';
import { ProjectsPage } from './pages/projects';

interface User {
  id: string;
  username: string;
  email: string;
  teams: Array<{ id: string; name: string }>;
}

export function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function initialize() {
      try {
        // Step 1: Get userId from config
        const userId = await getUserId();

        // Step 2: Query user information
        const data = await graphqlRequest<{ user: User }>(
          `
          query GetCurrentUser($id: ID!) {
            user(id: $id) {
              id
              username
              email
              teams {
                id
                name
              }
            }
          }
          `,
          { id: userId }
        );

        if (!data.user) {
          throw new Error(`User with ID ${userId} not found`);
        }

        setCurrentUser(data.user);
      } catch (err) {
        console.error('Failed to initialize app:', err);
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    }

    initialize();
  }, []);

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

  return (
    <UserContext.Provider value={currentUser}>
      <Router>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          {/* Add more routes */}
        </Routes>
      </Router>
    </UserContext.Provider>
  );
}
```

## API Endpoints

### GET /api/config

Returns the current user ID configured for this dashboard instance.

**Request:**
```bash
curl http://localhost:5173/api/config
```

**Response:**
```json
{
  "userId": "123e4567-e89b-12d3-a456-426614174000"
}
```

### POST /graphql (proxied)

All GraphQL requests are proxied to the backend server. The frontend must include the `userId` in query variables.

**Request:**
```bash
curl -X POST http://localhost:5173/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetUser($id: ID!) { user(id: $id) { id username } }",
    "variables": { "id": "123e4567-e89b-12d3-a456-426614174000" }
  }'
```

## Flow Diagram

```
┌─────────────────────────────────────────────┐
│     Dashboard Start Command                 │
│                                             │
│  alphatrion dashboard --userid alice-uuid   │
│                                             │
│  • Stores userId in app.state               │
│  • Exposes /api/config endpoint             │
└─────────────────┬───────────────────────────┘
                  │
                  │ Dashboard loads in browser
                  ▼
┌─────────────────────────────────────────────┐
│          React App Initialization           │
│                                             │
│  useEffect(() => {                          │
│    1. GET /api/config                       │
│       → {"userId": "alice-uuid"}            │
│                                             │
│    2. POST /graphql                         │
│       query GetCurrentUser($id: ID!)        │
│       variables: { id: "alice-uuid" }       │
│       → { user: {...} }                     │
│                                             │
│    3. Store user in context                 │
│    4. Render main app                       │
│  }, [])                                     │
└─────────────────┬───────────────────────────┘
                  │
                  │ App renders
                  ▼
┌─────────────────────────────────────────────┐
│          Main Application                   │
│                                             │
│  • useCurrentUser() provides user data      │
│  • All queries include userId               │
│  • Teams, projects, experiments filtered    │
└─────────────────────────────────────────────┘
```

## Error Handling

### User Not Found

If the user ID doesn't exist:

```typescript
if (!data.user) {
  throw new Error(`User with ID ${userId} not found. Please create the user first.`);
}
```

### Backend Unavailable

If the backend server is not running:

```typescript
catch (err) {
  if (err.message.includes('Failed to fetch')) {
    setError(new Error('Backend server not available. Please start it with: alphatrion server'));
  } else {
    setError(err);
  }
}
```

### No Teams

If the user has no teams:

```typescript
if (currentUser.teams.length === 0) {
  return (
    <div>
      <h2>Welcome, {currentUser.username}!</h2>
      <p>You don't belong to any teams yet.</p>
      <p>Please contact an administrator to be added to a team.</p>
    </div>
  );
}
```

## Testing

### Test Config Endpoint

```bash
# Start dashboard
alphatrion dashboard --userid test-user-uuid

# Query config
curl http://localhost:5173/api/config
# Should return: {"userId": "test-user-uuid"}
```

### Test User Query

```bash
# Query user via GraphQL
curl -X POST http://localhost:5173/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { user(id: \"test-user-uuid\") { id username email } }"
  }'
```

## Summary

1. ✅ Dashboard requires `--userid` flag
2. ✅ Frontend fetches userId from `/api/config`
3. ✅ Frontend queries user information on startup
4. ✅ User data stored in React Context
5. ✅ All subsequent queries use userId from context
6. ✅ Clean error handling for missing users
