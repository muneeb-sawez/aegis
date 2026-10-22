import React, { useState, useEffect, useCallback } from 'react';
import {
  FolderPlus,
  KeyRound,
  ShieldCheck,
  CheckCircle,
  Copy,
  Lock,
  AlertTriangle,
  RefreshCw,
  Search,
  Server,
  Sparkles,
  Network,
  Trash2,
  PlusCircle,
  ShieldAlert,
  GitBranch,
  ExternalLink,
  Link2,
  Unlink,
  LogOut,
  Eye,
  EyeOff,
} from 'lucide-react';
import {
  getActiveProjectId,
  setActiveProjectId,
  getProjectApiKey,
  setProjectApiKey,
  getAuthHeaders,
  apiUrl,
  getUserLoginToken,
  setUserLoginToken,
  clearUserLoginToken,
  getAuthenticatedUser,
} from '../config';
import type { GitHubUser } from '../config';

export function GitHubIcon({ size = 16, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color} style={{ flexShrink: 0 }}>
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
      />
    </svg>
  );
}

interface ProjectPublic {
  project_id: string;
  name: string;
  description: string;
  created_at: string;
  key_status: string;
  node_count: number;
  edge_count: number;
}

interface NewProjectResponse {
  project_id: string;
  name: string;
  description: string;
  api_key: string;
  created_at: string;
  message: string;
}

interface ServiceEndpointPublic {
  project_id: string;
  name: string;
  health_url: string;
  admin_url?: string;
  has_secret: boolean;
  secret_source: string;
  created_at: string;
  updated_at: string;
}

interface GitHubStatusResponse {
  authenticated: boolean;
  connected_to_project: boolean;
  project_id: string;
  user: GitHubUser | null;
  connected_projects: string[];
}

interface GitHubAuthResponse {
  success: boolean;
  login_token: string;
  token_type: string;
  user: GitHubUser;
  project_id: string;
  connected_projects: string[];
  message: string;
}

interface ProjectsPageProps {
  onNavigate?: (page: string) => void;
}

export function ProjectsPage({ onNavigate }: ProjectsPageProps) {
  const [activeTab, setActiveTab] = useState<'projects' | 'endpoints' | 'github'>('projects');
  const [projects, setProjects] = useState<ProjectPublic[]>([]);
  const [endpoints, setEndpoints] = useState<ServiceEndpointPublic[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isEndpointsLoading, setIsEndpointsLoading] = useState<boolean>(false);
  const [activeProjectId, setActiveId] = useState<string>(getActiveProjectId());
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [showKeyModal, setShowKeyModal] = useState<boolean>(false);
  const [newKeyData, setNewKeyData] = useState<NewProjectResponse | null>(null);
  const [copiedKey, setCopiedKey] = useState<boolean>(false);
  const [copiedCurl, setCopiedCurl] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Project form states
  const [formName, setFormName] = useState<string>('');
  const [formId, setFormId] = useState<string>('');
  const [formDesc, setFormDesc] = useState<string>('');
  const [formSeedBaseline, setFormSeedBaseline] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Manual key update modal
  const [showKeyUpdateModal, setShowKeyUpdateModal] = useState<boolean>(false);
  const [keyUpdateProjectId, setKeyUpdateProjectId] = useState<string>('');
  const [manualKeyValue, setManualKeyValue] = useState<string>('');

  // Service Endpoint registration modal states
  const [showEndpointModal, setShowEndpointModal] = useState<boolean>(false);
  const [epName, setEpName] = useState<string>('');
  const [epHealthUrl, setEpHealthUrl] = useState<string>('');
  const [epAdminUrl, setEpAdminUrl] = useState<string>('');
  const [epSecret, setEpSecret] = useState<string>('');
  const [epIsSubmitting, setEpIsSubmitting] = useState<boolean>(false);
  const [epError, setEpError] = useState<string | null>(null);
  const [epSuccessNotice, setEpSuccessNotice] = useState<string | null>(null);

  // GitHub authentication & connection states
  const [gitHubUser, setGitHubUser] = useState<GitHubUser | null>(getAuthenticatedUser());
  const [userLoginToken, setUserLoginTokenState] = useState<string>(getUserLoginToken());
  const [isGitHubConnected, setIsGitHubConnected] = useState<boolean>(false);
  const [gitHubConnectedProjects, setGitHubConnectedProjects] = useState<string[]>([]);
  const [isGitHubLoading, setIsGitHubLoading] = useState<boolean>(false);
  const [gitHubError, setGitHubError] = useState<string | null>(null);
  const [gitHubSuccessNotice, setGitHubSuccessNotice] = useState<string | null>(null);
  const [showToken, setShowToken] = useState<boolean>(false);
  const [copiedToken, setCopiedToken] = useState<boolean>(false);
  const [copiedBearerCurl, setCopiedBearerCurl] = useState<boolean>(false);

  // Connect modal and new login token modal states
  const [showConnectModal, setShowConnectModal] = useState<boolean>(false);
  const [showNewTokenModal, setShowNewTokenModal] = useState<boolean>(false);
  const [newTokenResponse, setNewTokenResponse] = useState<GitHubAuthResponse | null>(null);
  const [connectMethod, setConnectMethod] = useState<'demo' | 'pat' | 'oauth'>('demo');
  const [demoUsername, setDemoUsername] = useState<string>('muneeb-sawez');
  const [demoName, setDemoName] = useState<string>('Muneeb Sawez');
  const [patToken, setPatToken] = useState<string>('');
  const [oauthCode, setOauthCode] = useState<string>('');
  const [oauthUrlData, setOauthUrlData] = useState<{ configured: boolean; client_id: string; authorize_url: string } | null>(null);

  const fetchProjects = async () => {
    setIsLoading(true);
    try {
      const resp = await fetch(apiUrl('/api/projects'));
      if (resp.ok) {
        const data: ProjectPublic[] = await resp.json();
        setProjects(data);
      }
    } catch (e) {
      console.error('Failed to load projects list:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchEndpoints = useCallback(async (pid: string) => {
    setIsEndpointsLoading(true);
    try {
      const resp = await fetch(apiUrl(`/api/endpoints?project_id=${pid}`));
      if (resp.ok) {
        const data: ServiceEndpointPublic[] = await resp.json();
        setEndpoints(data);
      }
    } catch (e) {
      console.error('Failed to load endpoints list:', e);
    } finally {
      setIsEndpointsLoading(false);
    }
  }, []);

  const fetchGitHubStatus = useCallback(async (pid: string) => {
    setIsGitHubLoading(true);
    try {
      const headers = getAuthHeaders(pid);
      const resp = await fetch(apiUrl(`/api/auth/github/status?project_id=${pid}`), { headers });
      if (resp.ok) {
        const data: GitHubStatusResponse = await resp.json();
        setIsGitHubConnected(data.connected_to_project);
        setGitHubConnectedProjects(data.connected_projects || []);
        if (data.user) {
          setGitHubUser(data.user);
        }
      }
    } catch (e) {
      console.error('Failed to load GitHub connection status:', e);
    } finally {
      setIsGitHubLoading(false);
    }
  }, []);

  const fetchOAuthUrl = useCallback(async () => {
    try {
      const resp = await fetch(apiUrl('/api/auth/github/url'));
      if (resp.ok) {
        const data = await resp.json();
        setOauthUrlData(data);
      }
    } catch (e) {
      console.error('Failed to query OAuth URL:', e);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
    fetchEndpoints(activeProjectId);
    fetchGitHubStatus(activeProjectId);
    fetchOAuthUrl();
  }, [activeProjectId, fetchEndpoints, fetchGitHubStatus, fetchOAuthUrl]);

  useEffect(() => {
    const handleAuthChange = () => {
      setGitHubUser(getAuthenticatedUser());
      setUserLoginTokenState(getUserLoginToken());
    };
    window.addEventListener('aegis_auth_changed', handleAuthChange);
    return () => window.removeEventListener('aegis_auth_changed', handleAuthChange);
  }, []);

  // Check for GitHub OAuth redirect callback in URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    if (code) {
      handleAuthenticate({ code });
      window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
    }
  }, [activeProjectId]);

  const handleAuthenticate = async (payload: {
    code?: string;
    token?: string;
    demo_login?: boolean;
    demo_username?: string;
    demo_name?: string;
  }) => {
    setGitHubError(null);
    setIsGitHubLoading(true);
    try {
      const resp = await fetch(apiUrl('/api/auth/github/authenticate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...payload,
          project_id: activeProjectId,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Authentication failed (HTTP ${resp.status})`);
      }

      const data: GitHubAuthResponse = await resp.json();
      setUserLoginToken(data.login_token, data.user);
      setUserLoginTokenState(data.login_token);
      setGitHubUser(data.user);
      setIsGitHubConnected(true);
      setGitHubConnectedProjects(data.connected_projects || [activeProjectId]);
      setNewTokenResponse(data);
      setShowNewTokenModal(true);
      setShowConnectModal(false);
      setPatToken('');
      setOauthCode('');
      setGitHubSuccessNotice(
        `Successfully authenticated as @${data.user.username}! User login token generated and linked to project '${activeProjectId}'.`
      );
      setTimeout(() => setGitHubSuccessNotice(null), 6000);
      fetchGitHubStatus(activeProjectId);
    } catch (e: any) {
      setGitHubError(e.message || 'Authentication failed');
    } finally {
      setIsGitHubLoading(false);
    }
  };

  const handleConnectCurrentProject = async () => {
    setGitHubError(null);
    setIsGitHubLoading(true);
    try {
      const resp = await fetch(apiUrl('/api/auth/github/connect'), {
        method: 'POST',
        headers: getAuthHeaders(activeProjectId, { 'Content-Type': 'application/json' }),
        body: JSON.stringify({ project_id: activeProjectId }),
      });
      if (resp.ok) {
        setIsGitHubConnected(true);
        setGitHubSuccessNotice(`Project '${activeProjectId}' linked to GitHub account @${gitHubUser?.username}.`);
        setTimeout(() => setGitHubSuccessNotice(null), 4000);
        fetchGitHubStatus(activeProjectId);
      } else {
        const err = await resp.json().catch(() => ({}));
        setGitHubError(err.detail || 'Failed to connect project');
      }
    } catch (e: any) {
      setGitHubError(e.message || 'Failed to connect project');
    } finally {
      setIsGitHubLoading(false);
    }
  };

  const handleDisconnectCurrentProject = async () => {
    if (!confirm(`Are you sure you want to disconnect project '${activeProjectId}' from GitHub?`)) {
      return;
    }
    setGitHubError(null);
    setIsGitHubLoading(true);
    try {
      const resp = await fetch(apiUrl('/api/auth/github/disconnect'), {
        method: 'POST',
        headers: getAuthHeaders(activeProjectId, { 'Content-Type': 'application/json' }),
        body: JSON.stringify({ project_id: activeProjectId }),
      });
      if (resp.ok) {
        setIsGitHubConnected(false);
        setGitHubSuccessNotice(`Project '${activeProjectId}' disconnected from GitHub.`);
        setTimeout(() => setGitHubSuccessNotice(null), 4000);
        fetchGitHubStatus(activeProjectId);
      } else {
        const err = await resp.json().catch(() => ({}));
        setGitHubError(err.detail || 'Failed to disconnect project');
      }
    } catch (e: any) {
      setGitHubError(e.message || 'Failed to disconnect project');
    } finally {
      setIsGitHubLoading(false);
    }
  };

  const handleLogoutGitHub = () => {
    clearUserLoginToken();
    setGitHubUser(null);
    setUserLoginTokenState('');
    setIsGitHubConnected(false);
    setGitHubSuccessNotice('Logged out from GitHub session. User login token cleared.');
    setTimeout(() => setGitHubSuccessNotice(null), 4000);
  };

  const handleNameChange = (val: string) => {
    setFormName(val);
    const slug = val
      .toLowerCase()
      .replace(/[^a-z0-9-_ ]/g, '')
      .trim()
      .replace(/\s+/g, '-');
    setFormId(slug);
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const cleanId = formId.trim().toLowerCase();
    if (!cleanId) {
      setFormError('Project ID / Slug cannot be empty.');
      return;
    }

    setIsSubmitting(true);
    try {
      const resp = await fetch(apiUrl('/api/projects'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: cleanId,
          name: formName.trim() || cleanId,
          description: formDesc.trim(),
          seed_baseline: formSeedBaseline,
        }),
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to create project (HTTP ${resp.status})`);
      }

      const data: NewProjectResponse = await resp.json();
      setNewKeyData(data);
      setProjectApiKey(data.project_id, data.api_key);
      setShowCreateModal(false);
      setShowKeyModal(true);

      setFormName('');
      setFormId('');
      setFormDesc('');
      fetchProjects();
    } catch (err: any) {
      setFormError(err.message || 'Error creating project');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSwitchProject = (pid: string) => {
    setActiveProjectId(pid);
    setActiveId(pid);
    window.dispatchEvent(new CustomEvent('aegis_project_changed', { detail: { projectId: pid } }));
    fetchEndpoints(pid);
    if (onNavigate) {
      onNavigate('topology');
    }
  };

  const handleCopyKey = () => {
    if (newKeyData?.api_key) {
      navigator.clipboard.writeText(newKeyData.api_key);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2500);
    }
  };

  const getCurlSnippet = (pid: string, key: string) => {
    return `curl -X POST http://localhost:8000/api/chaos/inject \\
  -H "X-API-Key: ${key}" \\
  -H "X-Project-ID: ${pid}" \\
  -H "Content-Type: application/json" \\
  -d '{"fault_id": "pool_exhaustion", "target_service": "paymentservice"}'`;
  };

  const handleCopyCurl = () => {
    if (newKeyData) {
      navigator.clipboard.writeText(getCurlSnippet(newKeyData.project_id, newKeyData.api_key));
      setCopiedCurl(true);
      setTimeout(() => setCopiedCurl(false), 2500);
    }
  };

  const handleSaveManualKey = (e: React.FormEvent) => {
    e.preventDefault();
    if (keyUpdateProjectId && manualKeyValue.trim()) {
      setProjectApiKey(keyUpdateProjectId, manualKeyValue.trim());
      setShowKeyUpdateModal(false);
      setManualKeyValue('');
    }
  };

  const handleRegisterEndpointSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setEpError(null);
    setEpIsSubmitting(true);

    try {
      const headers = getAuthHeaders(activeProjectId, { 'Content-Type': 'application/json' });
      const resp = await fetch(apiUrl('/api/endpoints'), {
        method: 'POST',
        headers,
        body: JSON.stringify({
          name: epName.trim(),
          health_url: epHealthUrl.trim(),
          admin_url: epAdminUrl.trim() || undefined,
          secret: epSecret.trim() || undefined,
          project_id: activeProjectId,
        }),
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || `SSRF or Registration error (HTTP ${resp.status})`);
      }

      setEpSuccessNotice(`Service '${epName.trim()}' registered successfully with SSRF verification.`);
      setTimeout(() => setEpSuccessNotice(null), 4000);
      setShowEndpointModal(false);
      setEpName('');
      setEpHealthUrl('');
      setEpAdminUrl('');
      setEpSecret('');
      fetchEndpoints(activeProjectId);
    } catch (err: any) {
      setEpError(err.message || 'Failed to register endpoint');
    } finally {
      setEpIsSubmitting(false);
    }
  };

  const handleDeleteEndpoint = async (serviceName: string) => {
    if (!confirm(`Are you sure you want to unregister service '${serviceName}' from project '${activeProjectId}'?`)) {
      return;
    }
    try {
      const headers = getAuthHeaders(activeProjectId);
      const resp = await fetch(apiUrl(`/api/endpoints/${serviceName}?project_id=${activeProjectId}`), {
        method: 'DELETE',
        headers,
      });
      if (resp.ok) {
        fetchEndpoints(activeProjectId);
      } else {
        const err = await resp.json().catch(() => ({}));
        alert(err.detail || 'Failed to delete endpoint');
      }
    } catch (e) {
      console.error('Delete endpoint error:', e);
    }
  };

  const filteredProjects = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.project_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ padding: '24px 32px', height: '100%', overflowY: 'auto', backgroundColor: '#060a12', color: '#f8fafc' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 8,
                backgroundColor: 'rgba(56, 189, 248, 0.15)',
                border: '1.5px solid rgba(56, 189, 248, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#38bdf8',
              }}
            >
              <KeyRound size={20} />
            </div>
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0, letterSpacing: '-0.02em', color: '#f8fafc' }}>
                Multi-Tenant Projects & Service Endpoints Registry
              </h1>
              <p style={{ fontSize: 12, color: '#94a3b8', margin: '3px 0 0 0' }}>
                Per-project API keys (hashed in storage), SSRF-protected endpoint registration, and encrypted secret vaulting.
              </p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={() => {
              fetchProjects();
              fetchEndpoints(activeProjectId);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 14px',
              borderRadius: 6,
              backgroundColor: '#0f172a',
              border: '1px solid #1e293b',
              color: '#94a3b8',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={13} />
            <span>Refresh</span>
          </button>

          {activeTab === 'projects' ? (
            <button
              onClick={() => setShowCreateModal(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 16px',
                borderRadius: 6,
                backgroundColor: '#0284c7',
                border: '1px solid #38bdf8',
                color: '#ffffff',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 0 16px rgba(56, 189, 248, 0.3)',
              }}
            >
              <FolderPlus size={15} />
              <span>Create Project</span>
            </button>
          ) : activeTab === 'endpoints' ? (
            <button
              onClick={() => {
                setEpError(null);
                setEpName('');
                setEpHealthUrl('http://127.0.0.1:8000/api/monitor/probe/');
                setEpAdminUrl('');
                setEpSecret('');
                setShowEndpointModal(true);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 16px',
                borderRadius: 6,
                backgroundColor: '#10b981',
                border: '1px solid #34d399',
                color: '#ffffff',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 0 16px rgba(16, 185, 129, 0.3)',
              }}
            >
              <PlusCircle size={15} />
              <span>Register Service Endpoint</span>
            </button>
          ) : (
            <button
              onClick={() => {
                if (gitHubUser) {
                  setShowConnectModal(true);
                } else {
                  setShowConnectModal(true);
                }
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 16px',
                borderRadius: 6,
                backgroundColor: gitHubUser ? 'rgba(56, 189, 248, 0.15)' : '#0284c7',
                border: '1px solid #38bdf8',
                color: '#ffffff',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 0 16px rgba(56, 189, 248, 0.3)',
              }}
            >
              <GitHubIcon size={15} />
              <span>{gitHubUser ? 'Manage / Switch Account' : 'Connect GitHub Account'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Success Notification */}
      {epSuccessNotice && (
        <div
          style={{
            padding: '10px 14px',
            borderRadius: 6,
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            color: '#34d399',
            fontSize: 12,
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <CheckCircle size={16} />
          <span>{epSuccessNotice}</span>
        </div>
      )}

      {/* GitHub Notification */}
      {gitHubSuccessNotice && (
        <div
          style={{
            padding: '10px 14px',
            borderRadius: 6,
            backgroundColor: 'rgba(56, 189, 248, 0.1)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            color: '#38bdf8',
            fontSize: 12,
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <CheckCircle size={16} />
          <span>{gitHubSuccessNotice}</span>
        </div>
      )}

      {/* GitHub Error Notification */}
      {gitHubError && (
        <div
          style={{
            padding: '10px 14px',
            borderRadius: 6,
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#f87171',
            fontSize: 12,
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <AlertTriangle size={16} />
          <span>{gitHubError}</span>
        </div>
      )}

      {/* Navigation Tabs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20, borderBottom: '1px solid #1e293b', paddingBottom: 12 }}>
        <button
          onClick={() => setActiveTab('projects')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 16px',
            borderRadius: 6,
            backgroundColor: activeTab === 'projects' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
            border: activeTab === 'projects' ? '1px solid #38bdf8' : '1px solid transparent',
            color: activeTab === 'projects' ? '#38bdf8' : '#94a3b8',
            fontSize: 12,
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          <Server size={14} />
          <span>Tenant Projects ({projects.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('endpoints')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 16px',
            borderRadius: 6,
            backgroundColor: activeTab === 'endpoints' ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
            border: activeTab === 'endpoints' ? '1px solid #10b981' : '1px solid transparent',
            color: activeTab === 'endpoints' ? '#34d399' : '#94a3b8',
            fontSize: 12,
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          <Network size={14} />
          <span>Service Endpoints & SSRF Registry ({endpoints.length})</span>
          <span
            style={{
              fontSize: 10,
              padding: '1px 6px',
              borderRadius: 4,
              backgroundColor: '#0f172a',
              color: '#38bdf8',
              fontFamily: 'monospace',
            }}
          >
            {activeProjectId}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('github')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 16px',
            borderRadius: 6,
            backgroundColor: activeTab === 'github' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
            border: activeTab === 'github' ? '1px solid #38bdf8' : '1px solid transparent',
            color: activeTab === 'github' ? '#38bdf8' : '#94a3b8',
            fontSize: 12,
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          <GitHubIcon size={14} color={activeTab === 'github' ? '#38bdf8' : '#94a3b8'} />
          <span>GitHub & User Token</span>
          {gitHubUser ? (
            <span
              style={{
                fontSize: 10,
                padding: '1px 6px',
                borderRadius: 4,
                backgroundColor: isGitHubConnected ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                border: isGitHubConnected ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(245, 158, 11, 0.4)',
                color: isGitHubConnected ? '#34d399' : '#fbbf24',
                fontFamily: 'monospace',
              }}
            >
              @{gitHubUser.username}
            </span>
          ) : (
            <span
              style={{
                fontSize: 10,
                padding: '1px 6px',
                borderRadius: 4,
                backgroundColor: '#0f172a',
                color: '#64748b',
              }}
            >
              Connect
            </span>
          )}
        </button>
      </div>

      {/* Metrics & Architecture Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        <div style={{ padding: 16, borderRadius: 8, backgroundColor: '#0a101d', border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600, marginBottom: 6 }}>REGISTERED PROJECTS</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#f8fafc' }}>{projects.length}</div>
          <div style={{ fontSize: 11, color: '#38bdf8', marginTop: 4 }}>Isolated graph namespaces</div>
        </div>

        <div style={{ padding: 16, borderRadius: 8, backgroundColor: '#0a101d', border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600, marginBottom: 6 }}>SSRF DEFENSE ENGINE</div>
          <div style={{ fontSize: 16, fontWeight: 800, color: '#10b981', display: 'flex', alignItems: 'center', gap: 6 }}>
            <ShieldCheck size={18} />
            <span>Active & Guarded</span>
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>Blocks 169.254.169.254 & bad schemes</div>
        </div>

        <div style={{ padding: 16, borderRadius: 8, backgroundColor: '#0a101d', border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600, marginBottom: 6 }}>SECRETS ENCRYPTION</div>
          <div style={{ fontSize: 16, fontWeight: 800, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Lock size={18} />
            <span>PBKDF2-HMAC-SHA256</span>
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>Encrypted at rest, never returned by API</div>
        </div>

        <div style={{ padding: 16, borderRadius: 8, backgroundColor: '#0a101d', border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600, marginBottom: 6 }}>WORKSPACE & GITHUB AUTH</div>
          <div style={{ fontSize: 15, fontWeight: 800, color: '#38bdf8', fontFamily: 'monospace', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span>{activeProjectId}</span>
          </div>
          <div style={{ fontSize: 11, color: gitHubUser ? '#10b981' : '#94a3b8', marginTop: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: gitHubUser ? '#10b981' : '#64748b' }} />
            <span>{gitHubUser ? `@${gitHubUser.username} (Token Active)` : 'No GitHub Linked'}</span>
          </div>
        </div>
      </div>

      {/* TAB 1: PROJECTS TABLE */}
      {activeTab === 'projects' && (
        <div style={{ borderRadius: 8, backgroundColor: '#0a101d', border: '1px solid #1e293b', overflow: 'hidden' }}>
          <div
            style={{
              padding: '14px 20px',
              borderBottom: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Server size={16} color="#38bdf8" />
              <span style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>All Tenant Workspaces</span>
              <span style={{ fontSize: 11, color: '#64748b' }}>({projects.length})</span>
            </div>

            <div style={{ position: 'relative', width: 280 }}>
              <Search size={14} style={{ position: 'absolute', left: 10, top: 10, color: '#64748b' }} />
              <input
                type="text"
                placeholder="Search by name, ID or description..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  padding: '6px 10px 6px 32px',
                  borderRadius: 6,
                  backgroundColor: '#070b14',
                  border: '1px solid #1e293b',
                  color: '#f8fafc',
                  fontSize: 12,
                  outline: 'none',
                }}
              />
            </div>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 12 }}>
            <thead>
              <tr style={{ backgroundColor: '#070b14', borderBottom: '1px solid #1e293b', color: '#64748b' }}>
                <th style={{ padding: '10px 16px', fontWeight: 600 }}>PROJECT NAME / SLUG</th>
                <th style={{ padding: '10px 16px', fontWeight: 600 }}>TOPOLOGY GRAPH</th>
                <th style={{ padding: '10px 16px', fontWeight: 600 }}>KEY STATUS IN STORAGE</th>
                <th style={{ padding: '10px 16px', fontWeight: 600 }}>CREATED</th>
                <th style={{ padding: '10px 16px', fontWeight: 600, textAlign: 'right' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5} style={{ padding: 32, textAlign: 'center', color: '#64748b' }}>
                    Loading project tenants...
                  </td>
                </tr>
              ) : filteredProjects.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: 32, textAlign: 'center', color: '#64748b' }}>
                    No projects match your search criteria. Click "Create Project" to provision a new workspace.
                  </td>
                </tr>
              ) : (
                filteredProjects.map((proj) => {
                  const isActive = proj.project_id === activeProjectId;
                  return (
                    <tr
                      key={proj.project_id}
                      style={{
                        borderBottom: '1px solid #1e293b',
                        backgroundColor: isActive ? 'rgba(56, 189, 248, 0.05)' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div
                            style={{
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              backgroundColor: isActive ? '#38bdf8' : '#475569',
                              boxShadow: isActive ? '0 0 8px #38bdf8' : 'none',
                            }}
                          />
                          <div>
                            <div style={{ fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span>{proj.name}</span>
                              {isActive && (
                                <span
                                  style={{
                                    fontSize: 10,
                                    fontWeight: 800,
                                    padding: '1px 6px',
                                    borderRadius: 4,
                                    backgroundColor: 'rgba(56, 189, 248, 0.15)',
                                    color: '#38bdf8',
                                    border: '1px solid rgba(56, 189, 248, 0.3)',
                                  }}
                                >
                                  ACTIVE CONTEXT
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: 11, color: '#64748b', fontFamily: 'monospace' }}>
                              id: {proj.project_id}
                            </div>
                            {proj.description && (
                              <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{proj.description}</div>
                            )}
                          </div>
                        </div>
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontWeight: 700, color: '#f8fafc' }}>{proj.node_count} nodes</span>
                          <span style={{ color: '#475569' }}>•</span>
                          <span style={{ color: '#94a3b8' }}>{proj.edge_count} edges</span>
                        </div>
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 5,
                            padding: '3px 8px',
                            borderRadius: 4,
                            fontSize: 10,
                            fontWeight: 700,
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            border: '1px solid rgba(16, 185, 129, 0.25)',
                            color: '#34d399',
                          }}
                        >
                          <ShieldCheck size={12} />
                          <span>{proj.key_status}</span>
                        </span>
                      </td>

                      <td style={{ padding: '12px 16px', color: '#64748b', fontSize: 11 }}>
                        {proj.created_at ? proj.created_at.substring(0, 10) : 'Pre-seeded'}
                      </td>

                      <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8 }}>
                          <button
                            onClick={() => {
                              setKeyUpdateProjectId(proj.project_id);
                              setManualKeyValue(getProjectApiKey(proj.project_id));
                              setShowKeyUpdateModal(true);
                            }}
                            title="Set or update active API key for this project in local storage"
                            style={{
                              padding: '5px 10px',
                              borderRadius: 6,
                              backgroundColor: '#0f172a',
                              border: '1px solid #1e293b',
                              color: '#94a3b8',
                              fontSize: 11,
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            Set API Key
                          </button>

                          <button
                            onClick={() => handleSwitchProject(proj.project_id)}
                            disabled={isActive}
                            style={{
                              padding: '5px 12px',
                              borderRadius: 6,
                              backgroundColor: isActive ? 'rgba(56, 189, 248, 0.1)' : '#0284c7',
                              border: isActive ? '1px solid #38bdf8' : '1px solid #0284c7',
                              color: isActive ? '#38bdf8' : '#ffffff',
                              fontSize: 11,
                              fontWeight: 700,
                              cursor: isActive ? 'default' : 'pointer',
                            }}
                          >
                            {isActive ? 'Current Active' : 'Switch Context'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB 2: SERVICE ENDPOINTS REGISTRY */}
      {activeTab === 'endpoints' && (
        <div style={{ borderRadius: 8, backgroundColor: '#0a101d', border: '1px solid #1e293b', overflow: 'hidden' }}>
          <div
            style={{
              padding: '14px 20px',
              borderBottom: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Network size={16} color="#34d399" />
              <span style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
                Service Endpoints for Workspace '{activeProjectId}'
              </span>
              <span style={{ fontSize: 11, color: '#64748b' }}>({endpoints.length} Registered)</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#10b981' }}>
              <ShieldCheck size={14} />
              <span>All URLs Enforced with Strict SSRF Defense</span>
            </div>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 12 }}>
            <thead>
              <tr style={{ backgroundColor: '#070b14', borderBottom: '1px solid #1e293b', color: '#64748b' }}>
                <th style={{ padding: '10px 16px', fontWeight: 600 }}>SERVICE NAME</th>
                <th style={{ padding: '10px 16px', fontWeight: 600 }}>HEALTH PROBE URL</th>
                <th style={{ padding: '10px 16px', fontWeight: 600 }}>ADMIN ACTUATOR URL</th>
                <th style={{ padding: '10px 16px', fontWeight: 600 }}>SECRET SECURITY</th>
                <th style={{ padding: '10px 16px', fontWeight: 600 }}>SSRF STATUS</th>
                <th style={{ padding: '10px 16px', fontWeight: 600, textAlign: 'right' }}>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {isEndpointsLoading ? (
                <tr>
                  <td colSpan={6} style={{ padding: 32, textAlign: 'center', color: '#64748b' }}>
                    Loading service endpoints for {activeProjectId}...
                  </td>
                </tr>
              ) : endpoints.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: 32, textAlign: 'center', color: '#64748b' }}>
                    No service endpoints registered for this project yet. Click "Register Service Endpoint" above.
                  </td>
                </tr>
              ) : (
                endpoints.map((ep) => (
                  <tr key={ep.name} style={{ borderBottom: '1px solid #1e293b' }}>
                    <td style={{ padding: '12px 16px', fontWeight: 700, color: '#f8fafc', fontFamily: 'monospace' }}>
                      {ep.name}
                    </td>

                    <td style={{ padding: '12px 16px', color: '#94a3b8', fontFamily: 'monospace', fontSize: 11 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ wordBreak: 'break-all' }}>{ep.health_url}</span>
                      </div>
                    </td>

                    <td style={{ padding: '12px 16px', color: '#94a3b8', fontFamily: 'monospace', fontSize: 11 }}>
                      {ep.admin_url ? (
                        <span style={{ wordBreak: 'break-all' }}>{ep.admin_url}</span>
                      ) : (
                        <span style={{ color: '#475569', fontStyle: 'italic' }}>None (Emulated)</span>
                      )}
                    </td>

                    <td style={{ padding: '12px 16px' }}>
                      {ep.secret_source === 'env' ? (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4,
                            padding: '2px 8px',
                            borderRadius: 4,
                            backgroundColor: 'rgba(56, 189, 248, 0.1)',
                            border: '1px solid rgba(56, 189, 248, 0.3)',
                            color: '#38bdf8',
                            fontSize: 10,
                            fontWeight: 700,
                          }}
                        >
                          <Lock size={11} />
                          <span>Env Var Override</span>
                        </span>
                      ) : ep.secret_source === 'encrypted_store' ? (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4,
                            padding: '2px 8px',
                            borderRadius: 4,
                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                            border: '1px solid rgba(245, 158, 11, 0.3)',
                            color: '#fbbf24',
                            fontSize: 10,
                            fontWeight: 700,
                          }}
                        >
                          <Lock size={11} />
                          <span>Encrypted at Rest</span>
                        </span>
                      ) : (
                        <span style={{ color: '#475569', fontSize: 11 }}>No secret</span>
                      )}
                    </td>

                    <td style={{ padding: '12px 16px' }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          padding: '2px 8px',
                          borderRadius: 4,
                          backgroundColor: 'rgba(16, 185, 129, 0.1)',
                          border: '1px solid rgba(16, 185, 129, 0.3)',
                          color: '#34d399',
                          fontSize: 10,
                          fontWeight: 700,
                        }}
                      >
                        <ShieldCheck size={11} />
                        <span>SSRF Verified</span>
                      </span>
                    </td>

                    <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                      <button
                        onClick={() => handleDeleteEndpoint(ep.name)}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          padding: '4px 8px',
                          borderRadius: 4,
                          backgroundColor: 'rgba(239, 68, 68, 0.1)',
                          border: '1px solid rgba(239, 68, 68, 0.3)',
                          color: '#f87171',
                          fontSize: 11,
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        <Trash2 size={12} />
                        <span>Unregister</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB 3: GITHUB AUTHENTICATION & LOGIN TOKEN */}
      {activeTab === 'github' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Active User Hero & Token Status */}
          {gitHubUser ? (
            <div style={{ borderRadius: 8, backgroundColor: '#0a101d', border: '1px solid #1e293b', overflow: 'hidden' }}>
              <div
                style={{
                  padding: '16px 20px',
                  borderBottom: '1px solid #1e293b',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  backgroundColor: 'rgba(56, 189, 248, 0.03)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  {gitHubUser.avatar_url ? (
                    <img
                      src={gitHubUser.avatar_url}
                      alt={gitHubUser.username}
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: '50%',
                        border: '2px solid #38bdf8',
                        boxShadow: '0 0 12px rgba(56, 189, 248, 0.3)',
                      }}
                    />
                  ) : (
                    <div
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: '50%',
                        backgroundColor: '#0f172a',
                        border: '2px solid #38bdf8',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#38bdf8',
                      }}
                    >
                      <GitHubIcon size={24} />
                    </div>
                  )}

                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <h2 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#f8fafc' }}>
                        {gitHubUser.name || gitHubUser.username}
                      </h2>
                      <span
                        style={{
                          fontSize: 12,
                          color: '#38bdf8',
                          fontFamily: 'monospace',
                          fontWeight: 700,
                        }}
                      >
                        @{gitHubUser.username}
                      </span>
                      {gitHubUser.html_url && (
                        <a
                          href={gitHubUser.html_url}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: '#64748b', display: 'flex', alignItems: 'center' }}
                          title="View GitHub Profile"
                        >
                          <ExternalLink size={13} />
                        </a>
                      )}
                    </div>
                    <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2, display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span>GitHub ID: {gitHubUser.github_id}</span>
                      {gitHubUser.public_repos !== undefined && (
                        <span>Public Repos: {gitHubUser.public_repos}</span>
                      )}
                      <span>Session Status: Active</span>
                    </div>
                  </div>
                </div>

                {/* Project Connection Controls */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  {isGitHubConnected ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '6px 12px',
                          borderRadius: 6,
                          backgroundColor: 'rgba(16, 185, 129, 0.12)',
                          border: '1px solid rgba(16, 185, 129, 0.35)',
                          color: '#34d399',
                          fontSize: 11,
                          fontWeight: 700,
                        }}
                      >
                        <CheckCircle size={14} />
                        <span>Connected to Project: {activeProjectId}</span>
                      </span>

                      <button
                        onClick={handleDisconnectCurrentProject}
                        disabled={isGitHubLoading}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '6px 12px',
                          borderRadius: 6,
                          backgroundColor: 'rgba(239, 68, 68, 0.1)',
                          border: '1px solid rgba(239, 68, 68, 0.3)',
                          color: '#f87171',
                          fontSize: 11,
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        <Unlink size={13} />
                        <span>Disconnect Project</span>
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '6px 12px',
                          borderRadius: 6,
                          backgroundColor: 'rgba(245, 158, 11, 0.12)',
                          border: '1px solid rgba(245, 158, 11, 0.35)',
                          color: '#fbbf24',
                          fontSize: 11,
                          fontWeight: 700,
                        }}
                      >
                        <AlertTriangle size={14} />
                        <span>Not Linked to: {activeProjectId}</span>
                      </span>

                      <button
                        onClick={handleConnectCurrentProject}
                        disabled={isGitHubLoading}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '6px 14px',
                          borderRadius: 6,
                          backgroundColor: '#0284c7',
                          border: '1px solid #38bdf8',
                          color: '#ffffff',
                          fontSize: 11,
                          fontWeight: 700,
                          cursor: 'pointer',
                        }}
                      >
                        <Link2 size={13} />
                        <span>Link to {activeProjectId}</span>
                      </button>
                    </div>
                  )}

                  <button
                    onClick={handleLogoutGitHub}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '6px 12px',
                      borderRadius: 6,
                      backgroundColor: '#0f172a',
                      border: '1px solid #1e293b',
                      color: '#94a3b8',
                      fontSize: 11,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    <LogOut size={13} />
                    <span>Log Out</span>
                  </button>
                </div>
              </div>

              {/* Generated User Login Token Panel */}
              <div style={{ padding: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <KeyRound size={16} color="#38bdf8" />
                    <span style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
                      Generated User Login Token
                    </span>
                    <span
                      style={{
                        fontSize: 10,
                        padding: '2px 8px',
                        borderRadius: 4,
                        backgroundColor: 'rgba(56, 189, 248, 0.15)',
                        border: '1px solid rgba(56, 189, 248, 0.3)',
                        color: '#38bdf8',
                        fontWeight: 700,
                      }}
                    >
                      BEARER TOKEN
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button
                      onClick={() => setShowToken(!showToken)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '4px 10px',
                        borderRadius: 4,
                        backgroundColor: '#0f172a',
                        border: '1px solid #1e293b',
                        color: '#94a3b8',
                        fontSize: 11,
                        cursor: 'pointer',
                      }}
                    >
                      {showToken ? <EyeOff size={13} /> : <Eye size={13} />}
                      <span>{showToken ? 'Mask Token' : 'Reveal Token'}</span>
                    </button>

                    <button
                      onClick={() => {
                        if (userLoginToken) {
                          navigator.clipboard.writeText(userLoginToken);
                          setCopiedToken(true);
                          setTimeout(() => setCopiedToken(false), 2500);
                        }
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '4px 12px',
                        borderRadius: 4,
                        backgroundColor: copiedToken ? 'rgba(16, 185, 129, 0.2)' : '#0284c7',
                        border: copiedToken ? '1px solid #10b981' : '1px solid #38bdf8',
                        color: '#ffffff',
                        fontSize: 11,
                        fontWeight: 700,
                        cursor: 'pointer',
                      }}
                    >
                      {copiedToken ? <CheckCircle size={13} /> : <Copy size={13} />}
                      <span>{copiedToken ? 'Copied Token!' : 'Copy Login Token'}</span>
                    </button>
                  </div>
                </div>

                <p style={{ fontSize: 12, color: '#94a3b8', margin: '0 0 12px 0' }}>
                  This cryptographically secure login token was generated upon GitHub authentication. It authorizes API mutations, chaos injections, and endpoint registrations across linked projects via <code>Authorization: Bearer &lt;token&gt;</code>.
                </p>

                <div
                  style={{
                    padding: '12px 16px',
                    borderRadius: 6,
                    backgroundColor: '#070b14',
                    border: '1px solid #1e293b',
                    fontFamily: 'monospace',
                    fontSize: 13,
                    color: '#38bdf8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    wordBreak: 'break-all',
                  }}
                >
                  <span>
                    {showToken
                      ? userLoginToken || '(No active token in local session)'
                      : userLoginToken
                      ? `${userLoginToken.substring(0, 14)}${'•'.repeat(26)}`
                      : '(No active token in local session)'}
                  </span>
                </div>

                {/* API Usage & cURL Demonstration */}
                <div style={{ marginTop: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b' }}>
                      CLI & API AUTHENTICATION EXAMPLE
                    </span>
                    <button
                      onClick={() => {
                        const snippet = `curl -X GET http://localhost:8000/api/auth/github/me \\\n  -H "Authorization: Bearer ${userLoginToken}" \\\n  -H "X-Project-ID: ${activeProjectId}"`;
                        navigator.clipboard.writeText(snippet);
                        setCopiedBearerCurl(true);
                        setTimeout(() => setCopiedBearerCurl(false), 2500);
                      }}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: copiedBearerCurl ? '#34d399' : '#38bdf8',
                        fontSize: 11,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                        cursor: 'pointer',
                      }}
                    >
                      {copiedBearerCurl ? <CheckCircle size={12} /> : <Copy size={12} />}
                      <span>{copiedBearerCurl ? 'Copied!' : 'Copy cURL'}</span>
                    </button>
                  </div>

                  <pre
                    style={{
                      margin: 0,
                      padding: '10px 14px',
                      borderRadius: 6,
                      backgroundColor: '#070b14',
                      border: '1px solid #1e293b',
                      fontSize: 11,
                      color: '#a5f3fc',
                      overflowX: 'auto',
                    }}
                  >
{`curl -X GET http://localhost:8000/api/auth/github/me \\
  -H "Authorization: Bearer ${userLoginToken || 'aegis_usr_YOUR_LOGIN_TOKEN'}" \\
  -H "X-Project-ID: ${activeProjectId}"`}
                  </pre>
                </div>
              </div>
            </div>
          ) : (
            /* Unconnected State: Welcome and Connect Options */
            <div
              style={{
                borderRadius: 8,
                backgroundColor: '#0a101d',
                border: '1px solid #1e293b',
                padding: '32px 28px',
                textAlign: 'center',
              }}
            >
              <div
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: 12,
                  backgroundColor: 'rgba(56, 189, 248, 0.1)',
                  border: '1.5px solid rgba(56, 189, 248, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#38bdf8',
                  margin: '0 auto 16px auto',
                }}
              >
                <GitHubIcon size={32} />
              </div>

              <h2 style={{ fontSize: 18, fontWeight: 800, color: '#f8fafc', margin: '0 0 8px 0' }}>
                Connect GitHub to Project '{activeProjectId}'
              </h2>
              <p style={{ fontSize: 13, color: '#94a3b8', maxWidth: 540, margin: '0 auto 24px auto' }}>
                Authenticate your developer account to generate a secure user login token (<code>aegis_usr_*</code>). Once authenticated, your user session links directly to this project workspace.
              </p>

              <div style={{ display: 'flex', justifyContent: 'center', gap: 12 }}>
                <button
                  onClick={() => {
                    setConnectMethod('demo');
                    setShowConnectModal(true);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '10px 20px',
                    borderRadius: 6,
                    backgroundColor: '#0284c7',
                    border: '1px solid #38bdf8',
                    color: '#ffffff',
                    fontSize: 13,
                    fontWeight: 700,
                    cursor: 'pointer',
                    boxShadow: '0 0 20px rgba(56, 189, 248, 0.3)',
                  }}
                >
                  <Sparkles size={16} />
                  <span>One-Click Demo Auth</span>
                </button>

                <button
                  onClick={() => {
                    setConnectMethod('pat');
                    setShowConnectModal(true);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '10px 18px',
                    borderRadius: 6,
                    backgroundColor: '#0f172a',
                    border: '1px solid #1e293b',
                    color: '#f8fafc',
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <KeyRound size={15} />
                  <span>Personal Access Token</span>
                </button>

                <button
                  onClick={() => {
                    setConnectMethod('oauth');
                    setShowConnectModal(true);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '10px 18px',
                    borderRadius: 6,
                    backgroundColor: '#0f172a',
                    border: '1px solid #1e293b',
                    color: '#f8fafc',
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <GitHubIcon size={15} />
                  <span>GitHub OAuth App</span>
                </button>
              </div>
            </div>
          )}

          {/* Linked Projects Multi-Tenant Matrix */}
          <div style={{ borderRadius: 8, backgroundColor: '#0a101d', border: '1px solid #1e293b', overflow: 'hidden' }}>
            <div
              style={{
                padding: '14px 20px',
                borderBottom: '1px solid #1e293b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <GitBranch size={16} color="#38bdf8" />
                <span style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
                  Project Workspace Linkages
                </span>
                <span style={{ fontSize: 11, color: '#64748b' }}>
                  ({gitHubConnectedProjects.length} linked)
                </span>
              </div>
            </div>

            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 12 }}>
              <thead>
                <tr style={{ backgroundColor: '#070b14', borderBottom: '1px solid #1e293b', color: '#64748b' }}>
                  <th style={{ padding: '10px 16px', fontWeight: 600 }}>PROJECT ID</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600 }}>PROJECT NAME</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600 }}>WORKSPACE STATUS</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, textAlign: 'right' }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((proj) => {
                  const isLinked = gitHubConnectedProjects.includes(proj.project_id);
                  const isCurrent = proj.project_id === activeProjectId;
                  return (
                    <tr
                      key={proj.project_id}
                      style={{
                        borderBottom: '1px solid #1e293b',
                        backgroundColor: isCurrent ? 'rgba(56, 189, 248, 0.05)' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontFamily: 'monospace', fontWeight: 700, color: isCurrent ? '#38bdf8' : '#e2e8f0' }}>
                          {proj.project_id}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', color: '#94a3b8' }}>
                        {proj.name}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        {isLinked ? (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 4,
                              padding: '2px 8px',
                              borderRadius: 4,
                              backgroundColor: 'rgba(16, 185, 129, 0.1)',
                              border: '1px solid rgba(16, 185, 129, 0.3)',
                              color: '#34d399',
                              fontSize: 10,
                              fontWeight: 700,
                            }}
                          >
                            <CheckCircle size={11} />
                            <span>Linked to @{gitHubUser?.username || 'User'}</span>
                          </span>
                        ) : (
                          <span style={{ color: '#475569', fontSize: 11 }}>Unlinked</span>
                        )}
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                        {!isCurrent ? (
                          <button
                            onClick={() => {
                              setActiveProjectId(proj.project_id);
                              setActiveId(proj.project_id);
                            }}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 4,
                              padding: '4px 10px',
                              borderRadius: 4,
                              backgroundColor: '#0f172a',
                              border: '1px solid #1e293b',
                              color: '#38bdf8',
                              fontSize: 11,
                              cursor: 'pointer',
                            }}
                          >
                            <span>Switch Workspace</span>
                          </button>
                        ) : (
                          <span style={{ fontSize: 11, color: '#38bdf8', fontWeight: 700 }}>
                            ● Active Workspace
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CREATE PROJECT MODAL */}
      {showCreateModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(4px)',
          }}
        >
          <div
            style={{
              width: 500,
              backgroundColor: '#0a101d',
              border: '1px solid #1e293b',
              borderRadius: 12,
              padding: 24,
              boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <FolderPlus size={18} color="#38bdf8" />
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f8fafc' }}>
                  Create New Fleet Project
                </h3>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#64748b',
                  fontSize: 18,
                  cursor: 'pointer',
                }}
              >
                ✕
              </button>
            </div>

            <p style={{ fontSize: 12, color: '#94a3b8', margin: '0 0 16px 0' }}>
              Creates an isolated namespace in the graph and provisions a cryptographic API key.
            </p>

            {formError && (
              <div
                style={{
                  padding: '8px 12px',
                  borderRadius: 6,
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#f87171',
                  fontSize: 12,
                  marginBottom: 16,
                }}
              >
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateProject}>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>
                  PROJECT NAME
                </label>
                <input
                  type="text"
                  placeholder="e.g. Checkout Microservices"
                  value={formName}
                  onChange={(e) => handleNameChange(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    backgroundColor: '#070b14',
                    border: '1px solid #1e293b',
                    color: '#f8fafc',
                    fontSize: 13,
                    boxSizing: 'border-box',
                    outline: 'none',
                  }}
                />
              </div>

              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>
                  PROJECT ID (SLUG)
                </label>
                <input
                  type="text"
                  placeholder="e.g. checkout-microservices"
                  value={formId}
                  onChange={(e) => setFormId(e.target.value.toLowerCase().replace(/[^a-z0-9-_]/g, ''))}
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    backgroundColor: '#070b14',
                    border: '1px solid #1e293b',
                    color: '#38bdf8',
                    fontFamily: 'monospace',
                    fontSize: 13,
                    boxSizing: 'border-box',
                    outline: 'none',
                  }}
                />
                <span style={{ fontSize: 10, color: '#64748b', marginTop: 2, display: 'block' }}>
                  Used in URL params, headers, and isolation queries.
                </span>
              </div>

              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>
                  DESCRIPTION (OPTIONAL)
                </label>
                <textarea
                  placeholder="High-throughput payment gateway and downstream datastores"
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  rows={2}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    backgroundColor: '#070b14',
                    border: '1px solid #1e293b',
                    color: '#f8fafc',
                    fontSize: 12,
                    boxSizing: 'border-box',
                    outline: 'none',
                    resize: 'none',
                  }}
                />
              </div>

              <div style={{ marginBottom: 20 }}>
                <label
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    cursor: 'pointer',
                    fontSize: 12,
                    color: '#e2e8f0',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={formSeedBaseline}
                    onChange={(e) => setFormSeedBaseline(e.target.checked)}
                    style={{ accentColor: '#38bdf8' }}
                  />
                  <span>Pre-seed standard 54-node & 142-edge baseline topology</span>
                </label>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10 }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  style={{
                    padding: '8px 16px',
                    borderRadius: 6,
                    backgroundColor: '#0f172a',
                    border: '1px solid #1e293b',
                    color: '#94a3b8',
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  style={{
                    padding: '8px 18px',
                    borderRadius: 6,
                    backgroundColor: '#0284c7',
                    border: '1px solid #38bdf8',
                    color: '#ffffff',
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {isSubmitting ? 'Creating Project...' : 'Create & Generate Key'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* REGISTER SERVICE ENDPOINT MODAL (SSRF GUARDED) */}
      {showEndpointModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(4px)',
          }}
        >
          <div
            style={{
              width: 540,
              backgroundColor: '#0a101d',
              border: '1px solid #10b981',
              borderRadius: 12,
              padding: 24,
              boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <PlusCircle size={18} color="#34d399" />
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f8fafc' }}>
                  Register Service Endpoint
                </h3>
              </div>
              <button
                onClick={() => setShowEndpointModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#64748b',
                  fontSize: 18,
                  cursor: 'pointer',
                }}
              >
                ✕
              </button>
            </div>

            {/* SSRF & Security Callout */}
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 8,
                padding: '10px 12px',
                borderRadius: 6,
                backgroundColor: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                color: '#34d399',
                fontSize: 11,
                marginBottom: 16,
              }}
            >
              <ShieldAlert size={16} style={{ flexShrink: 0, marginTop: 1 }} />
              <div>
                <strong>SSRF Protection Enforced:</strong> All URLs are screened against cloud metadata endpoints (169.254.169.254, metadata.google.internal) and unsafe schemes. Secrets are encrypted with PBKDF2-HMAC-SHA256 at rest and never returned by any API.
              </div>
            </div>

            {epError && (
              <div
                style={{
                  padding: '8px 12px',
                  borderRadius: 6,
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#f87171',
                  fontSize: 12,
                  marginBottom: 16,
                }}
              >
                {epError}
              </div>
            )}

            <form onSubmit={handleRegisterEndpointSubmit}>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>
                  SERVICE NAME (NODE ID)
                </label>
                <input
                  type="text"
                  placeholder="e.g. paymentservice"
                  value={epName}
                  onChange={(e) => setEpName(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    backgroundColor: '#070b14',
                    border: '1px solid #1e293b',
                    color: '#f8fafc',
                    fontSize: 13,
                    boxSizing: 'border-box',
                    outline: 'none',
                    fontFamily: 'monospace',
                  }}
                />
              </div>

              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>
                  HEALTH PROBE URL (HTTP / HTTPS)
                </label>
                <input
                  type="url"
                  placeholder="http://127.0.0.1:8000/api/monitor/probe/paymentservice"
                  value={epHealthUrl}
                  onChange={(e) => setEpHealthUrl(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    backgroundColor: '#070b14',
                    border: '1px solid #1e293b',
                    color: '#34d399',
                    fontFamily: 'monospace',
                    fontSize: 12,
                    boxSizing: 'border-box',
                    outline: 'none',
                  }}
                />
                <span style={{ fontSize: 10, color: '#64748b', marginTop: 2, display: 'block' }}>
                  Probed continuously by the health checker background worker.
                </span>
              </div>

              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>
                  ADMIN ACTUATOR URL (OPTIONAL)
                </label>
                <input
                  type="text"
                  placeholder="http://127.0.0.1:8000/api/actuator/fix/paymentservice"
                  value={epAdminUrl}
                  onChange={(e) => setEpAdminUrl(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    backgroundColor: '#070b14',
                    border: '1px solid #1e293b',
                    color: '#38bdf8',
                    fontFamily: 'monospace',
                    fontSize: 12,
                    boxSizing: 'border-box',
                    outline: 'none',
                  }}
                />
                <span style={{ fontSize: 10, color: '#64748b', marginTop: 2, display: 'block' }}>
                  Target for automated remediation fix requests.
                </span>
              </div>

              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>
                  SECRET / HMAC TOKEN (OPTIONAL — ENCRYPTED IN STORAGE)
                </label>
                <input
                  type="password"
                  placeholder="Shared HMAC secret (never returned by API)"
                  value={epSecret}
                  onChange={(e) => setEpSecret(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    backgroundColor: '#070b14',
                    border: '1px solid #1e293b',
                    color: '#f8fafc',
                    fontFamily: 'monospace',
                    fontSize: 12,
                    boxSizing: 'border-box',
                    outline: 'none',
                  }}
                />
                <span style={{ fontSize: 10, color: '#64748b', marginTop: 2, display: 'block' }}>
                  Can also be provided via env var <code style={{ color: '#38bdf8' }}>SERVICE_SECRET_{'{SERVICE}'}</code>.
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10 }}>
                <button
                  type="button"
                  onClick={() => setShowEndpointModal(false)}
                  style={{
                    padding: '8px 16px',
                    borderRadius: 6,
                    backgroundColor: '#0f172a',
                    border: '1px solid #1e293b',
                    color: '#94a3b8',
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={epIsSubmitting}
                  style={{
                    padding: '8px 18px',
                    borderRadius: 6,
                    backgroundColor: '#10b981',
                    border: '1px solid #34d399',
                    color: '#ffffff',
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {epIsSubmitting ? 'Verifying & Registering...' : 'Verify SSRF & Register'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ONE-TIME API KEY REVEAL MODAL */}
      {showKeyModal && newKeyData && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1100,
            backdropFilter: 'blur(5px)',
          }}
        >
          <div
            style={{
              width: 580,
              backgroundColor: '#0a101d',
              border: '1px solid #38bdf8',
              borderRadius: 12,
              padding: 24,
              boxShadow: '0 0 30px rgba(56, 189, 248, 0.3)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: '50%',
                  backgroundColor: 'rgba(16, 185, 129, 0.2)',
                  border: '1.5px solid #10b981',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#10b981',
                }}
              >
                <CheckCircle size={20} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#f8fafc' }}>
                  Project Registered: {newKeyData.name}
                </h3>
                <span style={{ fontSize: 11, color: '#64748b', fontFamily: 'monospace' }}>
                  tenant id: {newKeyData.project_id}
                </span>
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 10,
                padding: '12px 14px',
                borderRadius: 8,
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                color: '#fbbf24',
                fontSize: 12,
                marginBottom: 16,
              }}
            >
              <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: 1 }} />
              <div>
                <strong>Save this API key immediately!</strong>
                <p style={{ margin: '2px 0 0 0', color: '#fef3c7', fontSize: 11 }}>
                  This plaintext API key is only shown once. AEGIS stores keys strictly as SHA-256 hashes in{' '}
                  <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>data/projects.json</code> and cannot recover it once closed.
                </p>
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 700, color: '#94a3b8', marginBottom: 4 }}>
                PER-PROJECT API KEY (PLAIN-TEXT REVEAL)
              </label>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 12px',
                  borderRadius: 6,
                  backgroundColor: '#070b14',
                  border: '1px solid #1e293b',
                }}
              >
                <code style={{ flex: 1, fontFamily: 'monospace', fontSize: 13, color: '#38bdf8', wordBreak: 'break-all' }}>
                  {newKeyData.api_key}
                </code>
                <button
                  onClick={handleCopyKey}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5,
                    padding: '6px 12px',
                    borderRadius: 4,
                    backgroundColor: copiedKey ? '#10b981' : '#0284c7',
                    border: 'none',
                    color: '#ffffff',
                    fontSize: 11,
                    fontWeight: 700,
                    cursor: 'pointer',
                    flexShrink: 0,
                  }}
                >
                  {copiedKey ? <CheckCircle size={13} /> : <Copy size={13} />}
                  <span>{copiedKey ? 'Copied!' : 'Copy Key'}</span>
                </button>
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <label style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8' }}>
                  CURL USAGE SNIPPET (MUTATING ROUTE)
                </label>
                <button
                  onClick={handleCopyCurl}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: copiedCurl ? '#10b981' : '#38bdf8',
                    fontSize: 11,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <Copy size={11} />
                  <span>{copiedCurl ? 'Copied Curl!' : 'Copy Curl'}</span>
                </button>
              </div>

              <pre
                style={{
                  margin: 0,
                  padding: '10px 12px',
                  borderRadius: 6,
                  backgroundColor: '#070b14',
                  border: '1px solid #1e293b',
                  color: '#94a3b8',
                  fontFamily: 'monospace',
                  fontSize: 11,
                  overflowX: 'auto',
                }}
              >
                {getCurlSnippet(newKeyData.project_id, newKeyData.api_key)}
              </pre>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10 }}>
              <button
                onClick={() => {
                  handleSwitchProject(newKeyData.project_id);
                  setShowKeyModal(false);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '8px 18px',
                  borderRadius: 6,
                  backgroundColor: '#0284c7',
                  border: '1px solid #38bdf8',
                  color: '#ffffff',
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                <Sparkles size={14} />
                <span>Switch to this Project & Close</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MANUAL KEY UPDATE MODAL */}
      {showKeyUpdateModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            style={{
              width: 440,
              backgroundColor: '#0a101d',
              border: '1px solid #1e293b',
              borderRadius: 12,
              padding: 24,
            }}
          >
            <h3 style={{ margin: '0 0 8px 0', fontSize: 15, fontWeight: 700, color: '#f8fafc' }}>
              Set Active API Key for '{keyUpdateProjectId}'
            </h3>
            <p style={{ fontSize: 12, color: '#94a3b8', margin: '0 0 16px 0' }}>
              Paste your saved API key to authenticate mutating requests for this project in your browser session.
            </p>

            <form onSubmit={handleSaveManualKey}>
              <div style={{ marginBottom: 16 }}>
                <input
                  type="text"
                  placeholder="aegis_key_..."
                  value={manualKeyValue}
                  onChange={(e) => setManualKeyValue(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    backgroundColor: '#070b14',
                    border: '1px solid #1e293b',
                    color: '#38bdf8',
                    fontFamily: 'monospace',
                    fontSize: 12,
                    boxSizing: 'border-box',
                    outline: 'none',
                  }}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10 }}>
                <button
                  type="button"
                  onClick={() => setShowKeyUpdateModal(false)}
                  style={{
                    padding: '6px 14px',
                    borderRadius: 6,
                    backgroundColor: '#0f172a',
                    border: '1px solid #1e293b',
                    color: '#94a3b8',
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{
                    padding: '6px 14px',
                    borderRadius: 6,
                    backgroundColor: '#0284c7',
                    border: '1px solid #38bdf8',
                    color: '#ffffff',
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Save Key
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* GITHUB CONNECT MODAL (DEMO / PAT / OAUTH) */}
      {showConnectModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(4px)',
          }}
        >
          <div
            style={{
              width: 520,
              backgroundColor: '#0a101d',
              border: '1px solid #1e293b',
              borderRadius: 12,
              padding: 24,
              boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    backgroundColor: 'rgba(56, 189, 248, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#38bdf8',
                  }}
                >
                  <GitHubIcon size={18} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f8fafc' }}>
                    Connect GitHub to Project
                  </h3>
                  <span style={{ fontSize: 11, color: '#94a3b8' }}>
                    Active Workspace: <strong style={{ color: '#38bdf8' }}>{activeProjectId}</strong>
                  </span>
                </div>
              </div>
              <button
                onClick={() => setShowConnectModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#64748b',
                  fontSize: 18,
                  cursor: 'pointer',
                }}
              >
                ✕
              </button>
            </div>

            {gitHubError && (
              <div
                style={{
                  padding: '8px 12px',
                  borderRadius: 6,
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#f87171',
                  fontSize: 12,
                  marginBottom: 16,
                }}
              >
                {gitHubError}
              </div>
            )}

            {/* Method Switcher Tabs */}
            <div style={{ display: 'flex', gap: 6, marginBottom: 18, backgroundColor: '#070b14', padding: 4, borderRadius: 8 }}>
              <button
                type="button"
                onClick={() => setConnectMethod('demo')}
                style={{
                  flex: 1,
                  padding: '8px 10px',
                  borderRadius: 6,
                  backgroundColor: connectMethod === 'demo' ? '#0f172a' : 'transparent',
                  border: connectMethod === 'demo' ? '1px solid #38bdf8' : '1px solid transparent',
                  color: connectMethod === 'demo' ? '#38bdf8' : '#94a3b8',
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                1-Click Demo
              </button>

              <button
                type="button"
                onClick={() => setConnectMethod('pat')}
                style={{
                  flex: 1,
                  padding: '8px 10px',
                  borderRadius: 6,
                  backgroundColor: connectMethod === 'pat' ? '#0f172a' : 'transparent',
                  border: connectMethod === 'pat' ? '1px solid #38bdf8' : '1px solid transparent',
                  color: connectMethod === 'pat' ? '#38bdf8' : '#94a3b8',
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                Personal Token (PAT)
              </button>

              <button
                type="button"
                onClick={() => setConnectMethod('oauth')}
                style={{
                  flex: 1,
                  padding: '8px 10px',
                  borderRadius: 6,
                  backgroundColor: connectMethod === 'oauth' ? '#0f172a' : 'transparent',
                  border: connectMethod === 'oauth' ? '1px solid #38bdf8' : '1px solid transparent',
                  color: connectMethod === 'oauth' ? '#38bdf8' : '#94a3b8',
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                GitHub OAuth
              </button>
            </div>

            {/* METHOD 1: ONE-CLICK DEMO AUTH */}
            {connectMethod === 'demo' && (
              <div>
                <p style={{ fontSize: 12, color: '#94a3b8', margin: '0 0 16px 0' }}>
                  Instantly authenticates a verified developer profile and generates a secure user login token (<code>aegis_usr_*</code>). Ideal for demonstrations and review.
                </p>

                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>
                    GITHUB USERNAME
                  </label>
                  <input
                    type="text"
                    value={demoUsername}
                    onChange={(e) => setDemoUsername(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      backgroundColor: '#070b14',
                      border: '1px solid #1e293b',
                      color: '#f8fafc',
                      fontSize: 13,
                      boxSizing: 'border-box',
                      outline: 'none',
                    }}
                  />
                </div>

                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>
                    DISPLAY NAME
                  </label>
                  <input
                    type="text"
                    value={demoName}
                    onChange={(e) => setDemoName(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      backgroundColor: '#070b14',
                      border: '1px solid #1e293b',
                      color: '#f8fafc',
                      fontSize: 13,
                      boxSizing: 'border-box',
                      outline: 'none',
                    }}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10 }}>
                  <button
                    type="button"
                    onClick={() => setShowConnectModal(false)}
                    style={{
                      padding: '8px 16px',
                      borderRadius: 6,
                      backgroundColor: '#0f172a',
                      border: '1px solid #1e293b',
                      color: '#94a3b8',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Cancel
                  </button>

                  <button
                    type="button"
                    disabled={isGitHubLoading}
                    onClick={() =>
                      handleAuthenticate({
                        demo_login: true,
                        demo_username: demoUsername.trim(),
                        demo_name: demoName.trim(),
                      })
                    }
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '8px 18px',
                      borderRadius: 6,
                      backgroundColor: '#0284c7',
                      border: '1px solid #38bdf8',
                      color: '#ffffff',
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    <Sparkles size={14} />
                    <span>{isGitHubLoading ? 'Authenticating...' : 'Authenticate & Generate Token'}</span>
                  </button>
                </div>
              </div>
            )}

            {/* METHOD 2: PERSONAL ACCESS TOKEN (PAT) */}
            {connectMethod === 'pat' && (
              <div>
                <p style={{ fontSize: 12, color: '#94a3b8', margin: '0 0 16px 0' }}>
                  Authenticates directly against <code>api.github.com/user</code> using your GitHub Personal Access Token (classic or fine-grained with <code>read:user</code> scope).
                </p>

                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>
                    GITHUB PERSONAL ACCESS TOKEN
                  </label>
                  <input
                    type="password"
                    placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                    value={patToken}
                    onChange={(e) => setPatToken(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      backgroundColor: '#070b14',
                      border: '1px solid #1e293b',
                      color: '#38bdf8',
                      fontFamily: 'monospace',
                      fontSize: 13,
                      boxSizing: 'border-box',
                      outline: 'none',
                    }}
                  />
                  <span style={{ fontSize: 10, color: '#64748b', marginTop: 4, display: 'block' }}>
                    Token is validated with GitHub REST API and never stored in plaintext.
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10 }}>
                  <button
                    type="button"
                    onClick={() => setShowConnectModal(false)}
                    style={{
                      padding: '8px 16px',
                      borderRadius: 6,
                      backgroundColor: '#0f172a',
                      border: '1px solid #1e293b',
                      color: '#94a3b8',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Cancel
                  </button>

                  <button
                    type="button"
                    disabled={isGitHubLoading || !patToken.trim()}
                    onClick={() => handleAuthenticate({ token: patToken.trim() })}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '8px 18px',
                      borderRadius: 6,
                      backgroundColor: '#0284c7',
                      border: '1px solid #38bdf8',
                      color: '#ffffff',
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: isGitHubLoading || !patToken.trim() ? 'not-allowed' : 'pointer',
                      opacity: isGitHubLoading || !patToken.trim() ? 0.6 : 1,
                    }}
                  >
                    <KeyRound size={14} />
                    <span>{isGitHubLoading ? 'Validating Token...' : 'Verify & Connect'}</span>
                  </button>
                </div>
              </div>
            )}

            {/* METHOD 3: GITHUB OAUTH APP */}
            {connectMethod === 'oauth' && (
              <div>
                <p style={{ fontSize: 12, color: '#94a3b8', margin: '0 0 16px 0' }}>
                  Standard GitHub OAuth 2.0 Web Application Flow. Authorize with your GitHub account to return a temporary authorization code.
                </p>

                <div
                  style={{
                    padding: '12px 14px',
                    borderRadius: 6,
                    backgroundColor: '#070b14',
                    border: '1px solid #1e293b',
                    marginBottom: 16,
                  }}
                >
                  <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600, marginBottom: 4 }}>
                    OAUTH APP STATUS
                  </div>
                  <div style={{ fontSize: 12, color: oauthUrlData?.configured ? '#34d399' : '#fbbf24', fontWeight: 600 }}>
                    {oauthUrlData?.configured
                      ? `● Configured (Client ID: ${oauthUrlData.client_id})`
                      : '● No GITHUB_CLIENT_ID configured in .env (Use 1-Click Demo or PAT above)'}
                  </div>
                </div>

                {oauthUrlData?.configured && (
                  <div style={{ marginBottom: 16 }}>
                    <a
                      href={oauthUrlData.authorize_url}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 8,
                        width: '100%',
                        padding: '10px 16px',
                        borderRadius: 6,
                        backgroundColor: '#24292f',
                        border: '1px solid #444c56',
                        color: '#ffffff',
                        fontSize: 13,
                        fontWeight: 700,
                        textDecoration: 'none',
                        boxSizing: 'border-box',
                      }}
                    >
                      <GitHubIcon size={16} />
                      <span>Authorize with GitHub</span>
                      <ExternalLink size={14} />
                    </a>
                  </div>
                )}

                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>
                    MANUAL OAUTH CALLBACK CODE (IF APPLICABLE)
                  </label>
                  <input
                    type="text"
                    placeholder="Enter ?code= from GitHub OAuth redirect"
                    value={oauthCode}
                    onChange={(e) => setOauthCode(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: 6,
                      backgroundColor: '#070b14',
                      border: '1px solid #1e293b',
                      color: '#f8fafc',
                      fontSize: 12,
                      fontFamily: 'monospace',
                      boxSizing: 'border-box',
                      outline: 'none',
                    }}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10 }}>
                  <button
                    type="button"
                    onClick={() => setShowConnectModal(false)}
                    style={{
                      padding: '8px 16px',
                      borderRadius: 6,
                      backgroundColor: '#0f172a',
                      border: '1px solid #1e293b',
                      color: '#94a3b8',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Cancel
                  </button>

                  <button
                    type="button"
                    disabled={isGitHubLoading || !oauthCode.trim()}
                    onClick={() => handleAuthenticate({ code: oauthCode.trim() })}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '8px 18px',
                      borderRadius: 6,
                      backgroundColor: '#0284c7',
                      border: '1px solid #38bdf8',
                      color: '#ffffff',
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: isGitHubLoading || !oauthCode.trim() ? 'not-allowed' : 'pointer',
                      opacity: isGitHubLoading || !oauthCode.trim() ? 0.6 : 1,
                    }}
                  >
                    <span>{isGitHubLoading ? 'Exchanging Code...' : 'Exchange Code for Token'}</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* NEW LOGIN TOKEN GENERATED SUCCESS MODAL */}
      {showNewTokenModal && newTokenResponse && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1100,
            backdropFilter: 'blur(5px)',
          }}
        >
          <div
            style={{
              width: 540,
              backgroundColor: '#0a101d',
              border: '1.5px solid rgba(56, 189, 248, 0.5)',
              borderRadius: 12,
              padding: 24,
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 30px rgba(56, 189, 248, 0.2)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 10,
                  backgroundColor: 'rgba(16, 185, 129, 0.15)',
                  border: '1px solid rgba(16, 185, 129, 0.4)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#34d399',
                }}
              >
                <CheckCircle size={22} />
              </div>

              <div>
                <h3 style={{ margin: 0, fontSize: 17, fontWeight: 800, color: '#f8fafc' }}>
                  GitHub Authentication Successful!
                </h3>
                <span style={{ fontSize: 12, color: '#38bdf8' }}>
                  User Login Token Generated & Connected to '{newTokenResponse.project_id}'
                </span>
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '10px 14px',
                borderRadius: 8,
                backgroundColor: '#070b14',
                border: '1px solid #1e293b',
                marginBottom: 16,
              }}
            >
              <GitHubIcon size={18} color="#38bdf8" />
              <div style={{ fontSize: 12, color: '#e2e8f0' }}>
                Authenticated as <strong style={{ color: '#38bdf8' }}>@{newTokenResponse.user.username}</strong>
                {newTokenResponse.user.name ? ` (${newTokenResponse.user.name})` : ''}
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b' }}>
                  YOUR USER LOGIN TOKEN (BEARER CREDENTIAL)
                </span>
                <span style={{ fontSize: 10, color: '#10b981', fontWeight: 600 }}>
                  Active & Saved in Session
                </span>
              </div>

              <div
                style={{
                  padding: '12px 14px',
                  borderRadius: 6,
                  backgroundColor: '#070b14',
                  border: '1.5px solid #0284c7',
                  fontFamily: 'monospace',
                  fontSize: 13,
                  color: '#38bdf8',
                  wordBreak: 'break-all',
                  boxShadow: 'inset 0 0 12px rgba(56, 189, 248, 0.1)',
                }}
              >
                {newTokenResponse.login_token}
              </div>
            </div>

            <p style={{ fontSize: 11, color: '#94a3b8', margin: '0 0 20px 0', lineHeight: 1.5 }}>
              This token has been injected into your current session. All API mutations, chaos tests, and topology updates in project <code>{newTokenResponse.project_id}</code> will automatically authenticate using this bearer credential.
            </p>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10 }}>
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard.writeText(newTokenResponse.login_token);
                  setCopiedToken(true);
                  setTimeout(() => setCopiedToken(false), 2500);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '8px 16px',
                  borderRadius: 6,
                  backgroundColor: copiedToken ? 'rgba(16, 185, 129, 0.2)' : '#0f172a',
                  border: copiedToken ? '1px solid #10b981' : '1px solid #1e293b',
                  color: copiedToken ? '#34d399' : '#f8fafc',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {copiedToken ? <CheckCircle size={14} /> : <Copy size={14} />}
                <span>{copiedToken ? 'Token Copied!' : 'Copy Token'}</span>
              </button>

              <button
                type="button"
                onClick={() => setShowNewTokenModal(false)}
                style={{
                  padding: '8px 20px',
                  borderRadius: 6,
                  backgroundColor: '#0284c7',
                  border: '1px solid #38bdf8',
                  color: '#ffffff',
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 0 16px rgba(56, 189, 248, 0.3)',
                }}
              >
                Done / Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
