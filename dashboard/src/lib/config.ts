/**
 * Configuration fetching from dashboard backend
 *
 * The dashboard is started with --userid flag, which stores the user ID
 * in the backend. The frontend fetches this configuration on startup.
 */

interface Config {
  userId: string;
}

/**
 * Fetch configuration from the dashboard backend
 * Always fetches fresh config to avoid stale user ID when dashboard is restarted with different user
 */
export async function getConfig(): Promise<Config> {
  const response = await fetch('/api/config', {
    cache: 'no-store',
    headers: {
      'Cache-Control': 'no-cache',
    },
  });
  if (!response.ok) {
    throw new Error('Failed to load configuration');
  }

  return await response.json();
}

/**
 * Get the current user ID from configuration
 */
export async function getUserId(): Promise<string> {
  const config = await getConfig();
  return config.userId;
}
