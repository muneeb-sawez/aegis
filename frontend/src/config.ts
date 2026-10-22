/**
 * AEGIS Frontend Configuration & Authentication Helper.
 * Centralized API base URL, multi-project context, and per-project API key management.
 */

export const API_BASE_URL: string = (import.meta.env.VITE_API_BASE as string) || '';

export const DEFAULT_PROBE_URL: string =
  (import.meta.env.VITE_DEFAULT_PROBE_URL as string) ||
  (API_BASE_URL ? `${API_BASE_URL}/health` : 'http://127.0.0.1:8000/health');

export const DEFAULT_DEMO_KEY = 'aegis-demo-api-key';

export function apiUrl(path: string): string {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
}

export function getActiveProjectId(): string {
  if (typeof window === 'undefined') return 'demo';
  return localStorage.getItem('aegis_active_project_id') || 'demo';
}

export function setActiveProjectId(projectId: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('aegis_active_project_id', projectId);
  window.dispatchEvent(new CustomEvent('aegis_project_changed', { detail: { projectId } }));
}

export function getProjectApiKey(projectId?: string): string {
  if (typeof window === 'undefined') return DEFAULT_DEMO_KEY;
  const targetId = projectId || getActiveProjectId();
  const stored = localStorage.getItem(`aegis_key_${targetId}`);
  if (stored) return stored;
  if (targetId === 'demo') return DEFAULT_DEMO_KEY;
  return localStorage.getItem('aegis_active_api_key') || '';
}

export function setProjectApiKey(projectId: string, key: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(`aegis_key_${projectId}`, key);
  localStorage.setItem('aegis_active_api_key', key);
  window.dispatchEvent(new CustomEvent('aegis_key_updated', { detail: { projectId, key } }));
}

export interface GitHubUser {
  username: string;
  github_id: string;
  name: string;
  email?: string | null;
  avatar_url?: string | null;
  html_url?: string | null;
  public_repos?: number;
}

export function getUserLoginToken(): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('aegis_user_login_token') || '';
}

export function setUserLoginToken(token: string, user?: GitHubUser | null): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('aegis_user_login_token', token);
  if (user) {
    localStorage.setItem('aegis_github_user', JSON.stringify(user));
  }
  window.dispatchEvent(new CustomEvent('aegis_auth_changed', { detail: { token, user } }));
}

export function clearUserLoginToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('aegis_user_login_token');
  localStorage.removeItem('aegis_github_user');
  window.dispatchEvent(new CustomEvent('aegis_auth_changed', { detail: { token: '', user: null } }));
}

export function getAuthenticatedUser(): GitHubUser | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem('aegis_github_user');
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function getAuthHeaders(projectId?: string, extraHeaders?: HeadersInit): Record<string, string> {
  const targetId = projectId || getActiveProjectId();
  const key = getProjectApiKey(targetId);
  const userToken = getUserLoginToken();

  const base: Record<string, string> = {
    'X-Project-ID': targetId,
    ...((extraHeaders as Record<string, string>) || {}),
  };
  
  if (userToken) {
    base['Authorization'] = `Bearer ${userToken}`;
    base['X-Login-Token'] = userToken;
  } else if (key) {
    base['X-API-Key'] = key;
  }
  return base;
}

export async function authFetch(url: string, init?: RequestInit): Promise<Response> {
  const customHeaders = (init?.headers as Record<string, string>) || {};
  const mergedHeaders = {
    ...getAuthHeaders(),
    ...customHeaders,
  };
  return fetch(apiUrl(url), {
    ...init,
    headers: mergedHeaders,
  });
}
