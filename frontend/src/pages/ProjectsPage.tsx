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
} from 'lucide-react';
import {
  getActiveProjectId,
  setActiveProjectId,
  getProjectApiKey,
  setProjectApiKey,
  getAuthHeaders,
  apiUrl,
} from '../config';

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

interface ProjectsPageProps {
  onNavigate?: (page: string) => void;
}

export function ProjectsPage({ onNavigate }: ProjectsPageProps) {
  const [activeTab, setActiveTab] = useState<'projects' | 'endpoints'>('projects');
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

  useEffect(() => {
    fetchProjects();
    fetchEndpoints(activeProjectId);
  }, [activeProjectId, fetchEndpoints]);

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
          ) : (
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
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600, marginBottom: 6 }}>ACTIVE WORKSPACE</div>
          <div style={{ fontSize: 16, fontWeight: 800, color: '#38bdf8', fontFamily: 'monospace' }}>
            {activeProjectId}
          </div>
          <div style={{ fontSize: 11, color: '#10b981', marginTop: 4 }}>
            ● Key active in session
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
    </div>
  );
}
