import { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Activity,
  Network,
  ArrowRight,
  Zap,
  CheckCircle2,
  KeyRound,
} from 'lucide-react';
import {
  getActiveProjectId,
  getAuthenticatedUser,
  apiUrl,
  getAuthHeaders,
} from '../config';
import type { GitHubUser, GitHubRepoSummary } from '../config';

interface OverviewPageProps {
  onNavigate: (page: string) => void;
  onOpenRepoSelector: () => void;
  onOpenAuthModal: () => void;
}

export function OverviewPage({
  onNavigate,
  onOpenRepoSelector,
  onOpenAuthModal,
}: OverviewPageProps) {
  const [gitHubUser, setGitHubUser] = useState<GitHubUser | null>(getAuthenticatedUser());
  const [activeProjectId, setActiveId] = useState<string>(getActiveProjectId());
  const [projects, setProjects] = useState<any[]>([]);
  const [recentRepos, setRecentRepos] = useState<GitHubRepoSummary[]>([]);
  const [isLoadingRepos, setIsLoadingRepos] = useState<boolean>(false);

  useEffect(() => {
    const handleAuth = () => setGitHubUser(getAuthenticatedUser());
    const handleProj = () => setActiveId(getActiveProjectId());
    window.addEventListener('aegis_auth_changed', handleAuth);
    window.addEventListener('aegis_project_changed', handleProj);
    return () => {
      window.removeEventListener('aegis_auth_changed', handleAuth);
      window.removeEventListener('aegis_project_changed', handleProj);
    };
  }, []);

  useEffect(() => {
    fetch(apiUrl('/api/projects'))
      .then((r) => r.ok && r.json())
      .then((data) => {
        if (Array.isArray(data)) setProjects(data);
      })
      .catch(() => {});

    if (gitHubUser) {
      setIsLoadingRepos(true);
      fetch(apiUrl('/api/auth/github/repos'), { headers: getAuthHeaders(activeProjectId) })
        .then((r) => r.ok && r.json())
        .then((data) => {
          if (Array.isArray(data)) setRecentRepos(data.slice(0, 6));
        })
        .catch(() => {})
        .finally(() => setIsLoadingRepos(false));
    }
  }, [gitHubUser, activeProjectId]);

  const currentProject = projects.find((p) => p.project_id === activeProjectId);

  return (
    <div
      style={{
        flex: 1,
        overflowY: 'auto',
        backgroundColor: '#070b14',
        padding: '36px 48px',
        color: '#f8fafc',
      }}
    >
      <div style={{ maxWidth: 1040, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 28 }}>
        
        {/* Header Intro */}
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 800, margin: '0 0 6px 0', letterSpacing: '-0.02em', color: '#f8fafc' }}>
            AEGIS Control Center
          </h1>
          <p style={{ fontSize: 13, color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
            Automated reliability engineering and pre-flight contract verification for microservice architectures.
          </p>
        </div>

        {/* Linear 3-Step Guided Workflow */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: 16,
          }}
        >
          {/* Step 1: GitHub Account */}
          <div
            style={{
              backgroundColor: '#0b1120',
              border: '1px solid #1e293b',
              borderRadius: 12,
              padding: 22,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: 16,
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
                  Step 1 • Authentication
                </span>
                {gitHubUser ? (
                  <span
                    style={{
                      fontSize: 10,
                      backgroundColor: 'rgba(34, 197, 94, 0.15)',
                      color: '#4ade80',
                      padding: '2px 8px',
                      borderRadius: 12,
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                  >
                    <CheckCircle2 size={11} /> READY
                  </span>
                ) : (
                  <span
                    style={{
                      fontSize: 10,
                      backgroundColor: 'rgba(239, 68, 68, 0.15)',
                      color: '#f87171',
                      padding: '2px 8px',
                      borderRadius: 12,
                      fontWeight: 700,
                    }}
                  >
                    REQUIRED
                  </span>
                )}
              </div>

              <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 6px 0', color: '#f8fafc' }}>
                GitHub Profile
              </h2>
              <p style={{ fontSize: 12, color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
                {gitHubUser
                  ? `Authenticated as @${gitHubUser.username}. Repositories and permissions are linked.`
                  : 'Authorize with your GitHub credentials to discover and scan private or public repositories.'}
              </p>
            </div>

            <button
              onClick={onOpenAuthModal}
              style={{
                width: '100%',
                padding: '9px 14px',
                borderRadius: 8,
                backgroundColor: gitHubUser ? 'rgba(255, 255, 255, 0.05)' : '#2563eb',
                border: gitHubUser ? '1px solid #334155' : 'none',
                color: '#f8fafc',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                textAlign: 'center',
                transition: 'background-color 0.15s ease',
              }}
            >
              {gitHubUser ? 'Manage GitHub Account' : 'Sign in with GitHub'}
            </button>
          </div>

          {/* Step 2: Select Repository */}
          <div
            style={{
              backgroundColor: '#0b1120',
              border: '1px solid #1e293b',
              borderRadius: 12,
              padding: 22,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: 16,
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
                  Step 2 • Code Source
                </span>
                {currentProject?.repo_full_name ? (
                  <span
                    style={{
                      fontSize: 10,
                      backgroundColor: 'rgba(56, 189, 248, 0.15)',
                      color: '#38bdf8',
                      padding: '2px 8px',
                      borderRadius: 12,
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                  >
                    <CheckCircle2 size={11} /> CONNECTED
                  </span>
                ) : (
                  <span style={{ fontSize: 10, color: '#64748b' }}>PENDING</span>
                )}
              </div>

              <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 6px 0', color: '#f8fafc' }}>
                Target Repository
              </h2>
              <p
                style={{
                  fontSize: 12,
                  color: '#94a3b8',
                  margin: 0,
                  lineHeight: 1.5,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {currentProject?.repo_full_name ? (
                  <strong style={{ color: '#f8fafc' }}>{currentProject.repo_full_name}</strong>
                ) : (
                  'Choose a repository from your GitHub profile or enter a public Git URL.'
                )}
              </p>
            </div>

            <button
              onClick={onOpenRepoSelector}
              style={{
                width: '100%',
                padding: '9px 14px',
                borderRadius: 8,
                backgroundColor: currentProject?.repo_full_name ? 'rgba(56, 189, 248, 0.12)' : '#0284c7',
                border: currentProject?.repo_full_name ? '1px solid rgba(56, 189, 248, 0.3)' : 'none',
                color: currentProject?.repo_full_name ? '#38bdf8' : '#ffffff',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                textAlign: 'center',
              }}
            >
              {currentProject?.repo_full_name ? 'Change Repository' : 'Select GitHub Repo'}
            </button>
          </div>

          {/* Step 3: Architecture Graph */}
          <div
            style={{
              backgroundColor: '#0b1120',
              border: '1px solid #1e293b',
              borderRadius: 12,
              padding: 22,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: 16,
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
                  Step 3 • Visualization
                </span>
                <span style={{ fontSize: 10, color: '#38bdf8', fontWeight: 600 }}>DEDICATED PAGE</span>
              </div>

              <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 6px 0', color: '#f8fafc' }}>
                Architecture Graph
              </h2>
              <p style={{ fontSize: 12, color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
                View the isolated, full-screen dependency topology and blast radius on its dedicated canvas.
              </p>
            </div>

            <button
              onClick={() => onNavigate('topology')}
              style={{
                width: '100%',
                padding: '9px 14px',
                borderRadius: 8,
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid #334155',
                color: '#f8fafc',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
              }}
            >
              <Network size={14} color="#0284c7" />
              <span>Open Graph Canvas</span>
            </button>
          </div>
        </div>

        {/* Feature Capabilities Directory */}
        <div style={{ marginTop: 8 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 14px 0', color: '#cbd5e1' }}>
            Platform Modules
          </h2>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 14 }}>
            {/* Module 1: Pre-Flight */}
            <div
              onClick={() => onNavigate('predict')}
              style={{
                padding: 18,
                borderRadius: 10,
                backgroundColor: '#090e1a',
                border: '1px solid #1e293b',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
                transition: 'border-color 0.15s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#f97316')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#1e293b')}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <ShieldAlert size={18} color="#f97316" />
                <span style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>Pre-Flight Risk</span>
              </div>
              <p style={{ fontSize: 12, color: '#94a3b8', margin: 0, lineHeight: 1.4 }}>
                Simulate PR diffs against OpenAPI schemas before deployment.
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#f97316', fontSize: 11, fontWeight: 600, marginTop: 4 }}>
                <span>Run contract diff</span>
                <ArrowRight size={12} />
              </div>
            </div>

            {/* Module 2: Fleet Telemetry */}
            <div
              onClick={() => onNavigate('monitor')}
              style={{
                padding: 18,
                borderRadius: 10,
                backgroundColor: '#090e1a',
                border: '1px solid #1e293b',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
                transition: 'border-color 0.15s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#10b981')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#1e293b')}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Activity size={18} color="#10b981" />
                <span style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>Fleet Telemetry</span>
              </div>
              <p style={{ fontSize: 12, color: '#94a3b8', margin: 0, lineHeight: 1.4 }}>
                Real-time health probers and HTTP response time monitors.
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#10b981', fontSize: 11, fontWeight: 600, marginTop: 4 }}>
                <span>Inspect probers</span>
                <ArrowRight size={12} />
              </div>
            </div>

            {/* Module 3: Chaos Playground */}
            <div
              onClick={() => onNavigate('chaos')}
              style={{
                padding: 18,
                borderRadius: 10,
                backgroundColor: '#090e1a',
                border: '1px solid #1e293b',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
                transition: 'border-color 0.15s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#ef4444')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#1e293b')}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Zap size={18} color="#ef4444" />
                <span style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>Chaos Playground</span>
              </div>
              <p style={{ fontSize: 12, color: '#94a3b8', margin: 0, lineHeight: 1.4 }}>
                Inject controlled HTTP latency or 500 faults to test resiliency.
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#ef4444', fontSize: 11, fontWeight: 600, marginTop: 4 }}>
                <span>Open playground</span>
                <ArrowRight size={12} />
              </div>
            </div>

            {/* Module 4: Settings & Tenants */}
            <div
              onClick={() => onNavigate('projects')}
              style={{
                padding: 18,
                borderRadius: 10,
                backgroundColor: '#090e1a',
                border: '1px solid #1e293b',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
                transition: 'border-color 0.15s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#38bdf8')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#1e293b')}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <KeyRound size={18} color="#38bdf8" />
                <span style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>Settings & Tenants</span>
              </div>
              <p style={{ fontSize: 12, color: '#94a3b8', margin: 0, lineHeight: 1.4 }}>
                Manage API keys, service endpoints, and tenants.
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#38bdf8', fontSize: 11, fontWeight: 600, marginTop: 4 }}>
                <span>Configure workspace</span>
                <ArrowRight size={12} />
              </div>
            </div>
          </div>
        </div>

        {/* GitHub Quick Repositories Drawer (if logged in) */}
        {gitHubUser && (
          <div
            style={{
              backgroundColor: '#090e1a',
              border: '1px solid #1e293b',
              borderRadius: 12,
              padding: 20,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
                Your Repositories (@{gitHubUser.username})
              </span>
              <button
                onClick={onOpenRepoSelector}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#38bdf8',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <span>Browse all</span>
                <ArrowRight size={12} />
              </button>
            </div>

            {isLoadingRepos ? (
              <div style={{ padding: '16px 0', textAlign: 'center', color: '#64748b', fontSize: 12 }}>
                Loading repositories...
              </div>
            ) : recentRepos.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
                {recentRepos.map((r) => (
                  <div
                    key={r.id}
                    onClick={onOpenRepoSelector}
                    style={{
                      padding: '10px 14px',
                      borderRadius: 8,
                      backgroundColor: '#0d1322',
                      border: '1px solid #1e293b',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      transition: 'border-color 0.15s ease',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#38bdf8')}
                    onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#1e293b')}
                  >
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc' }}>{r.name}</span>
                    <span
                      style={{
                        fontSize: 10,
                        padding: '1px 5px',
                        borderRadius: 4,
                        backgroundColor: r.private ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                        color: r.private ? '#f87171' : '#34d399',
                      }}
                    >
                      {r.private ? 'Private' : 'Public'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '12px 0', textAlign: 'center', color: '#64748b', fontSize: 12 }}>
                No repositories found for this account.
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
