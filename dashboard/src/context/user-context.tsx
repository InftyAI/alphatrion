import { createContext, useContext, ReactNode, useState } from 'react';

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
  avatarUrl?: string;
  meta?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
  teams?: Array<{
    id: string;
    name: string;
    description?: string;
  }>;
}

interface UserContextType {
  user: User;
  updateUser: (updates: Partial<User>) => void;
}

const UserContext = createContext<UserContextType | null>(null);

export function UserProvider({ user: initialUser, children }: { user: User; children: ReactNode }) {
  const [user, setUser] = useState<User>(initialUser);

  const updateUser = (updates: Partial<User>) => {
    setUser(prev => ({ ...prev, ...updates }));
  };

  return (
    <UserContext.Provider value={{ user, updateUser }}>
      {children}
    </UserContext.Provider>
  );
}

export function useCurrentUser(): User {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useCurrentUser must be used within UserProvider');
  }
  return context.user;
}

export function useUpdateUser() {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUpdateUser must be used within UserProvider');
  }
  return context.updateUser;
}

export { UserContext };
