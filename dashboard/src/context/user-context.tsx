import { createContext, useContext, ReactNode } from 'react';

/**
 * User context for storing current user information
 *
 * The user is loaded on app startup from the backend using the
 * userId provided via the --userid flag to the dashboard command.
 */

export interface User {
  id: string;
  username: string;
  email: string;
  meta?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
  teams?: Array<{
    id: string;
    name: string;
    description?: string;
  }>;
}

const UserContext = createContext<User | null>(null);

export function UserProvider({ user, children }: { user: User; children: ReactNode }) {
  return (
    <UserContext.Provider value={user}>
      {children}
    </UserContext.Provider>
  );
}

export function useCurrentUser(): User {
  const user = useContext(UserContext);
  if (!user) {
    throw new Error('useCurrentUser must be used within UserProvider');
  }
  return user;
}

export { UserContext };
