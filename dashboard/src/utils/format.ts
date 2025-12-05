/**
 * Format ID for display: prefix 6 + ... + suffix 4
 * Example: "df0b18c9-1234-5678-9abc-def012345678" → "df0b18...5678"
 */
export function formatId(id: string): string {
    if (id.length <= 12) return id;
    return `${id.slice(0, 6)}...${id.slice(-4)}`;
}