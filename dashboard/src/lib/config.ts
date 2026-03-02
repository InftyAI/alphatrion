/**
 * Configuration fetching
 *
 * In CLI mode: The dashboard is started with --userid flag, which stores the user ID
 * in the backend. The frontend fetches this via /api/config endpoint.
 *
 * In Kubernetes mode: The dashboard pod writes userId from environment variables
 * to /config.json file at startup. The frontend fetches this static file.
 */

interface Config {
  userId: string;
  teamId?: string;
}

/**
 * Fetch configuration
 * Always fetches fresh config to avoid stale user ID when dashboard is restarted with different user
 */
export async function getConfig(): Promise<Config> {
  // Try /config.json first (Kubernetes mode)
  let response = await fetch('/config.json', {
    cache: 'no-store',
    headers: {
      'Cache-Control': 'no-cache',
    },
  });

  // Check if response is actually JSON (not HTML from SPA fallback)
  const contentType = response.headers.get('content-type');
  const isJson = contentType?.includes('application/json');

  // Fallback to /api/config (CLI mode) if not JSON or not ok
  if (!response.ok || !isJson) {
    response = await fetch('/api/config', {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
      },
    });
  }

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
