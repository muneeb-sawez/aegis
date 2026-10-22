/**
 * AEGIS Frontend Configuration
 * Centralized API base URL and probe endpoints.
 */

// If VITE_API_BASE is set, e.g. "http://localhost:8000", use it; otherwise fallback to empty string (relative paths)
export const API_BASE_URL: string = (import.meta.env.VITE_API_BASE as string) || '';

// Default probe URL for service health endpoint monitoring
export const DEFAULT_PROBE_URL: string =
  (import.meta.env.VITE_DEFAULT_PROBE_URL as string) ||
  (API_BASE_URL ? `${API_BASE_URL}/health` : 'http://127.0.0.1:8000/health');

/**
 * Helper to construct full API endpoint URL
 */
export function apiUrl(path: string): string {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
}
