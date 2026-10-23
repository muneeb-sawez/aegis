import { useState, useEffect } from 'react';
import {
  Network,
  ShieldAlert,
  Activity,
  Flame,
  Zap,
  FolderGit2,
  GitCommit,
  Sparkles,
  KeyRound,
  LayoutDashboard,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';

// Multi-Page Views
import { OverviewPage } from './pages/OverviewPage';
import { TopologyPage } from './pages/TopologyPage';
import { PredictPage } from './pages/PredictPage';
import { MonitorPage } from './pages/MonitorPage';
import { ChaosPage } from './pages/ChaosPage';
import { ActuatorPage } from './pages/ActuatorPage';
import { ObservabilityPage } from './pages/ObservabilityPage';
import { IngestPage } from './pages/IngestPage';
import { IncidentLedgerPage } from './pages/IncidentLedgerPage';
import { ProjectsPage } from './pages/ProjectsPage';

// Modals
import { GitHubAuthModal } from './components/GitHubAuthModal';
import { GitHubRepoSelectorModal } from './components/GitHubRepoSelectorModal';

import {
  getActiveProjectId,
  apiUrl,
  getAuthenticatedUser,
  getUserLoginToken,
  setUserLoginToken,
} from './config';
import type { GitHubUser } from './config';

type PageId =
  | 'overview'
  | 'topology'
  | 'predict'
  | 'monitor'
  | 'chaos'
  | 'actuator'
  | 'observability'
  | 'ingest'
  | 'incidents'
  | 'projects';

interface NavItem {
  id: PageId;
  label: string;
  icon: any;
  highlight?: string;
}

interface NavGroup {
  group: string;
  items: NavItem[];
}

export function App() {
  const getInitialPage = (): PageId => {
    const hash = window.location.hash.replace('#', '') as PageId;
    const validPages: PageId[] = [
      'overview',
      'topology',
      'predict',
      'monitor',
      'chaos',
      'actuator',
      'observability',
      'ingest',
      'incidents',
      'projects',
    ];
    return validPages.includes(hash) ? hash : 'overview';
  };

  const [activePage, setActivePage] = useState<PageId>(getInitialPage);
  const [activeProjectId, setActiveProjectIdState] = useState<string>(getActiveProjectId);
  const [selectedServiceContext, setSelectedServiceContext] = useState<string>('paymentservice');
  const [gitHubUser, setGitHubUser] = useState<GitHubUser | null>(getAuthenticatedUser);
  const [, setUserLoginTokenState] = useState<string>(getUserLoginToken);
  const [resetNotification, setResetNotification] = useState<string | null>(null);

  // Sidebar collapsible state (persisted)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem('aegis_sidebar_collapsed') === 'true';
  });

  // Modal open states
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  const [showRepoModal, setShowRepoModal] = useState<boolean>(false);

  const toggleSidebar = () => {
    setIsSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('aegis_sidebar_collapsed', String(next));
      return next;
    });
  };

  useEffect(() => {
    const onAuthChanged = () => {
      setGitHubUser(getAuthenticatedUser());
      setUserLoginTokenState(getUserLoginToken());
    };
    window.addEventListener('aegis_auth_changed', onAuthChanged);
    return () => window.removeEventListener('aegis_auth_changed', onAuthChanged);
  }, []);

  useEffect(() => {
    const onProjectChange = (e: any) => {
      const newPid = e.detail?.projectId || getActiveProjectId();
      setActiveProjectIdState(newPid);
    };
    window.addEventListener('aegis_project_changed', onProjectChange);
    return () => window.removeEventListener('aegis_project_changed', onProjectChange);
  }, []);

  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash.replace('#', '') as PageId;
      if (hash && hash !== activePage) {
        setActivePage(hash);
      }
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, [activePage]);

  // Handle GitHub OAuth redirect callback (?code=...)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    if (code) {
      fetch(apiUrl('/api/auth/github/authenticate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code,
          project_id: activeProjectId,
        }),
      })
        .then((r) => r.ok && r.json())
        .then((data) => {
          if (data && data.user) {
            setUserLoginToken(data.login_token, data.user);
            setGitHubUser(data.user);
            setResetNotification(`Signed in as @${data.user.username}!`);
            setTimeout(() => setResetNotification(null), 5000);
          }
        })
        .catch((e) => console.error('OAuth callback failed:', e))
        .finally(() => {
          window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
        });
    }
  }, [activeProjectId]);

  const handleNavigate = (page: string, serviceId?: string) => {
    if (serviceId) {
      setSelectedServiceContext(serviceId);
    }
    setActivePage(page as PageId);
    window.location.hash = page;
  };

  // Decluttered, clean navigation groups (no paragraph noise)
  const navGroups: NavGroup[] = [
    {
      group: 'WORKSPACE',
      items: [
        {
          id: 'overview',
          label: 'Platform Home',
          icon: LayoutDashboard,
          highlight: '#38bdf8',
        },
        {
          id: 'topology',
          label: 'Architecture Graph',
          icon: Network,
          highlight: '#0284c7',
        },
        {
          id: 'predict',
          label: 'Pre-Flight Risk Engine',
          icon: ShieldAlert,
          highlight: '#f97316',
        },
      ],
    },
    {
      group: 'OPERATIONS & INCIDENTS',
      items: [
        {
          id: 'monitor',
          label: 'Fleet Telemetry',
          icon: Activity,
          highlight: '#10b981',
        },
        {
          id: 'incidents',
          label: 'Incident Memory Ledger',
          icon: GitCommit,
          highlight: '#38bdf8',
        },
        {
          id: 'observability',
          label: 'OpenTelemetry Traces',
          icon: Activity,
          highlight: '#06b6d4',
        },
      ],
    },
    {
      group: 'RESILIENCE PLAYGROUND',
      items: [
        {
          id: 'chaos',
          label: 'Chaos Fault Injection',
          icon: Flame,
          highlight: '#ef4444',
        },
        {
          id: 'actuator',
          label: 'Self-Healing Actuator',
          icon: Zap,
          highlight: '#818cf8',
        },
      ],
    },
    {
      group: 'SETTINGS & CODE',
      items: [
        {
          id: 'ingest',
          label: 'Repository Ingestion',
          icon: FolderGit2,
        },
        {
          id: 'projects',
          label: 'Projects & API Keys',
          icon: KeyRound,
          highlight: '#38bdf8',
        },
      ],
    },
  ];

  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        backgroundColor: '#060a12',
        color: '#f8fafc',
        display: 'flex',
        flexDirection: 'column',
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        overflow: 'hidden',
      }}
    >
      {/* Sleek Top Navigation Bar */}
      <header
        style={{
          height: 52,
          backgroundColor: '#090e1a',
          borderBottom: '1px solid #1e293b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          zIndex: 50,
          flexShrink: 0,
        }}
      >
        {/* Left: Sidebar Toggle + Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={toggleSidebar}
            title={isSidebarCollapsed ? 'Expand sidebar (Ctrl+B)' : 'Collapse sidebar (Ctrl+B)'}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: 6,
              borderRadius: 6,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background-color 0.15s ease',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            {isSidebarCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>

          <div
            onClick={() => handleNavigate('overview')}
            style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 7,
                backgroundColor: 'rgba(6, 182, 212, 0.15)',
                border: '1px solid rgba(6, 182, 212, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#06b6d4',
              }}
            >
              <Sparkles size={16} />
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
              <span style={{ fontSize: 15, fontWeight: 900, letterSpacing: '0.06em', color: '#f8fafc' }}>
                AEGIS
              </span>
              <span style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>
                Control Plane
              </span>
            </div>
          </div>
        </div>

        {/* Center: Clean Repository Quick Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={() => setShowRepoModal(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 7,
              padding: '6px 14px',
              borderRadius: 8,
              backgroundColor: 'rgba(2, 132, 199, 0.15)',
              border: '1px solid rgba(2, 132, 199, 0.35)',
              color: '#38bdf8',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <FolderGit2 size={14} />
            <span>Select GitHub Repo</span>
          </button>
        </div>

        {/* Right: GitHub User Profile & Tenant Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {resetNotification && (
            <span style={{ fontSize: 11, color: '#4ade80', fontWeight: 600, marginRight: 8 }}>
              {resetNotification}
            </span>
          )}

          <button
            onClick={() => handleNavigate('projects')}
            title="Active project tenant"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 10px',
              borderRadius: 16,
              backgroundColor: '#0f172a',
              border: '1px solid #1e293b',
              fontSize: 11,
              color: '#94a3b8',
              cursor: 'pointer',
            }}
          >
            <KeyRound size={11} color="#38bdf8" />
            <span>{activeProjectId}</span>
          </button>

          {gitHubUser ? (
            <button
              onClick={() => setShowAuthModal(true)}
              title={`Logged in as @${gitHubUser.username}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 7,
                padding: '4px 12px',
                borderRadius: 20,
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                border: '1px solid rgba(34, 197, 94, 0.3)',
                fontSize: 11,
                color: '#4ade80',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {gitHubUser.avatar_url ? (
                <img
                  src={gitHubUser.avatar_url}
                  alt={gitHubUser.username}
                  style={{ width: 18, height: 18, borderRadius: '50%', border: '1px solid #4ade80' }}
                />
              ) : (
                <div style={{ width: 14, height: 14, borderRadius: '50%', backgroundColor: '#4ade80' }} />
              )}
              <span>@{gitHubUser.username}</span>
            </button>
          ) : (
            <button
              onClick={() => setShowAuthModal(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '5px 12px',
                borderRadius: 20,
                backgroundColor: '#2563eb',
                border: 'none',
                fontSize: 11,
                color: '#ffffff',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                />
              </svg>
              <span>GitHub Sign In</span>
            </button>
          )}
        </div>
      </header>

      {/* Main Layout Body */}
      <div style={{ display: 'flex', flex: 1, height: 'calc(100vh - 52px)', overflow: 'hidden' }}>
        {/* Collapsible Sidebar */}
        <aside
          style={{
            width: isSidebarCollapsed ? 56 : 230,
            backgroundColor: '#070c17',
            borderRight: '1px solid #1e293b',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: isSidebarCollapsed ? '12px 6px' : '16px 10px',
            flexShrink: 0,
            overflowY: 'auto',
            transition: 'width 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        >
          {/* Navigation Items */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {navGroups.map((group, gIdx) => (
              <div key={gIdx} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {!isSidebarCollapsed && (
                  <div
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      color: '#475569',
                      letterSpacing: '0.06em',
                      padding: '4px 8px 2px 8px',
                    }}
                  >
                    {group.group}
                  </div>
                )}

                {group.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = activePage === item.id;
                  const color = item.highlight || '#38bdf8';

                  return (
                    <button
                      key={item.id}
                      onClick={() => handleNavigate(item.id)}
                      title={isSidebarCollapsed ? item.label : undefined}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: isSidebarCollapsed ? 'center' : 'flex-start',
                        gap: isSidebarCollapsed ? 0 : 10,
                        padding: isSidebarCollapsed ? '10px 0' : '8px 10px',
                        borderRadius: 7,
                        border: isActive ? `1px solid ${color}40` : '1px solid transparent',
                        backgroundColor: isActive ? 'rgba(30, 41, 59, 0.65)' : 'transparent',
                        color: isActive ? '#f8fafc' : '#94a3b8',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all 0.15s ease',
                        boxShadow: isActive ? `0 0 10px ${color}18` : 'none',
                        width: '100%',
                      }}
                      onMouseEnter={(e) => {
                        if (!isActive) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive) e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                    >
                      <Icon size={16} color={isActive ? color : '#64748b'} style={{ flexShrink: 0 }} />
                      {!isSidebarCollapsed && (
                        <span style={{ fontSize: 12, fontWeight: isActive ? 700 : 500, color: isActive ? '#f8fafc' : '#cbd5e1', whiteSpace: 'nowrap' }}>
                          {item.label}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          {/* Sidebar Footer */}
          {!isSidebarCollapsed && (
            <div
              style={{
                padding: '10px 12px',
                borderRadius: 8,
                backgroundColor: '#0a101d',
                border: '1px solid #1e293b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: 10,
                color: '#64748b',
              }}
            >
              <span>Platform Mode</span>
              <span style={{ color: '#10b981', fontWeight: 700 }}>● Online</span>
            </div>
          )}
        </aside>

        {/* Dynamic Main Workspace View */}
        <main style={{ flex: 1, height: '100%', position: 'relative', overflow: 'hidden', backgroundColor: '#060a12' }}>
          {activePage === 'overview' && (
            <OverviewPage
              onNavigate={handleNavigate}
              onOpenRepoSelector={() => setShowRepoModal(true)}
              onOpenAuthModal={() => setShowAuthModal(true)}
            />
          )}
          {activePage === 'topology' && <TopologyPage onNavigate={handleNavigate} />}
          {activePage === 'predict' && <PredictPage />}
          {activePage === 'monitor' && <MonitorPage />}
          {activePage === 'chaos' && <ChaosPage onNavigate={handleNavigate} initialService={selectedServiceContext} />}
          {activePage === 'actuator' && <ActuatorPage onNavigate={handleNavigate} />}
          {activePage === 'observability' && <ObservabilityPage onNavigate={handleNavigate} />}
          {activePage === 'ingest' && <IngestPage onNavigate={handleNavigate} />}
          {activePage === 'incidents' && <IncidentLedgerPage onNavigate={handleNavigate} />}
          {activePage === 'projects' && <ProjectsPage onNavigate={handleNavigate} />}
        </main>
      </div>

      {/* Global Modals for Auth and Repo Selection */}
      <GitHubAuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        currentUser={gitHubUser}
        onAuthSuccess={(user) => {
          setGitHubUser(user);
        }}
      />

      <GitHubRepoSelectorModal
        isOpen={showRepoModal}
        onClose={() => setShowRepoModal(false)}
        onOpenAuthModal={() => {
          setShowRepoModal(false);
          setShowAuthModal(true);
        }}
        onRepoSelected={() => {
          setActivePage('topology');
          window.location.hash = 'topology';
        }}
      />
    </div>
  );
}

export default App;
