/**
 * Configuration fetching from dashboard backend
 *
 * The dashboard is started with --userid flag, which stores the user ID
 * in the backend. The frontend fetches this configuration on startup.
 */

interface Config {
  userId: string;
}

let cachedConfig: Config | null = null;

/**
 * Fetch configuration from the dashboard backend
 */
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

/**
 * Get the current user ID from configuration
 */
export async function getUserId(): Promise<string> {
  const config = await getConfig();
  return config.userId;
}
