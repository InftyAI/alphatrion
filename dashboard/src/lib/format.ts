/**
 * Truncate a UUID to show first 4 and last 4 characters
 * Example: "1934e567-89ab-cdef-0123-456789ab440a" -> "1934....440a"
 */
export function truncateId(id: string, prefixLen: number = 4, suffixLen: number = 4): string {
  if (!id || id.length <= prefixLen + suffixLen) {
    return id;
  }
  return `${id.slice(0, prefixLen)}....${id.slice(-suffixLen)}`;
}

/**
 * Format duration in seconds to human-readable format
 * Example: 3665 seconds -> "1h 1m 5s"
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

  return parts.join(' ');
}
