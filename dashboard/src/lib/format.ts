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
