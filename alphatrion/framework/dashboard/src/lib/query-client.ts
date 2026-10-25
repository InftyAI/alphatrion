import { QueryClient } from '@tanstack/react-query';

/**
 * React Query client configuration with optimized caching and polling
 *
 * Polling Strategy:
 * - Experiments: Poll every 30s when status is RUNNING/PENDING
 * - Runs: Poll every 30s when status is RUNNING/PENDING
 * - Metrics: Poll every 30s when parent experiment is RUNNING
 * - Projects: No polling (static data)
 * - Artifacts: No polling (immutable)
 */

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Cache for 10 minutes by default
      staleTime: 10 * 60 * 1000,

      // Keep unused data in cache for 30 minutes
      gcTime: 30 * 60 * 1000,

      // Retry failed requests up to 2 times
      retry: 2,

      // Don't refetch on window focus by default (use polling instead)
      refetchOnWindowFocus: false,

      // Don't refetch on mount if data exists
      refetchOnMount: false,

      // Refetch on reconnect
      refetchOnReconnect: true,
    },
  },
});

/**
 * Helper function to determine if polling should be active
 * based on entity status
 */
export function shouldPoll(statuses: string[] | undefined): number | false {
  if (!statuses || statuses.length === 0) {
    return false;
  }

  const activeStatuses = ['RUNNING', 'PENDING'];
  const hasActiveStatus = statuses.some(status =>
    activeStatuses.includes(status)
  );

  return hasActiveStatus ? 30000 : false; // Poll every 30 seconds
}

/**
 * Polling interval for runs
 */
export function shouldPollRuns(statuses: string[] | undefined): number | false {
  if (!statuses || statuses.length === 0) {
    return false;
  }

  const activeStatuses = ['RUNNING', 'PENDING'];
  const hasActiveStatus = statuses.some(status =>
    activeStatuses.includes(status)
  );

  return hasActiveStatus ? 30000 : false; // Poll every 30 seconds
}

/**
 * Check if any experiment is in an active state
 */
export function hasActiveExperiment(experiments: { status: string }[] | undefined): boolean {
  if (!experiments) return false;
  return experiments.some(exp =>
    exp.status === 'RUNNING' || exp.status === 'PENDING'
  );
}

/**
 * Get polling interval based on data freshness requirements
 */
export function getPollingInterval(dataType: 'experiments' | 'runs' | 'metrics'): number {
  switch (dataType) {
    case 'experiments':
      return 30000; // 30 seconds
    case 'runs':
      return 30000; // 30 seconds
    case 'metrics':
      return 30000; // 30 seconds
    default:
      return 30000;
  }
}
