import { useState, useEffect } from 'react';
import {
  Network,
  ShieldAlert,
  Activity,
  Flame,
  Zap,
  Layers,
  FolderGit2,
  GitCommit,
  RotateCcw,
  CheckCircle,
  Clock,
  Sparkles,
  Radio,
  KeyRound,
} from 'lucide-react';

// Multi-Page Views
import { TopologyPage } from './pages/TopologyPage';
import { PredictPage } from './pages/PredictPage';
import { MonitorPage } from './pages/MonitorPage';
import { ChaosPage } from './pages/ChaosPage';
import { ActuatorPage } from './pages/ActuatorPage';
import { ObservabilityPage } from './pages/ObservabilityPage';
import { IngestPage } from './pages/IngestPage';
import { IncidentLedgerPage } from './pages/IncidentLedgerPage';
import { ProjectsPage } from './pages/ProjectsPage';
import {
  getActiveProjectId,
  getAuthHeaders,
  apiUrl,
  getAuthenticatedUser,
  getUserLoginToken,
} from './config';
import type { GitHubUser } from './config';

type PageId =
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
  desc: string;
  badge?: string;
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
    return validPages.includes(hash) ? hash : 'topology';
  };

  const [activePage, setActivePage] = useState<PageId>(getInitialPage);
  const [activeProjectId, setActiveProjectIdState] = useState<string>(getActiveProjectId);
  const [selectedServiceContext, setSelectedServiceContext] = useState<string>('paymentservice');
  const [gitHubUser, setGitHubUser] = useState<GitHubUser | null>(getAuthenticatedUser);
  const [userLoginToken, setUserLoginTokenState] = useState<string>(getUserLoginToken);
  const [nodeCount, setNodeCount] = useState<number>(54);
  const [edgeCount, setEdgeCount] = useState<number>(142);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [resetNotification, setResetNotification] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState<string>(new Date().toISOString().substring(11, 19) + ' UTC');

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
    const timer = setInterval(() => {
      setCurrentTime(new Date().toISOString().substring(11, 19) + ' UTC');
    }, 1000);
    return () => clearInterval(timer);
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

  useEffect(() => {
    const fetchCounts = async () => {
      try {
        const resp = await fetch(apiUrl(`/api/graph/topology?project_id=${activeProjectId}`));
        if (resp.ok) {
          const data = await resp.json();
          if (data.nodes) setNodeCount(data.nodes.length);
          if (data.edges) setEdgeCount(data.edges.length);
        }
      } catch (e) {
        console.error('Failed to query graph topology counts:', e);
      }
    };
    fetchCounts();
  }, [activePage, activeProjectId]);

  const handleNavigate = (page: string, serviceId?: string) => {
    if (serviceId) {
      setSelectedServiceContext(serviceId);
    }
    setActivePage(page as PageId);
    window.location.hash = page;
  };

  const handleGlobalReset = async () => {
    setIsResetting(true);
    setResetNotification(null);
    try {
      const resp = await fetch(apiUrl(`/api/reset?project_id=${activeProjectId}`), {
        method: 'POST',
        headers: getAuthHeaders(activeProjectId),
      });
      if (resp.ok) {
        const data = await resp.json();
        setNodeCount(data.node_count || 54);
        setEdgeCount(data.edge_count || 142);
        setResetNotification(`Baseline restored for '${activeProjectId}'.`);
        setTimeout(() => setResetNotification(null), 4000);
      } else {
        const err = await resp.json().catch(() => ({}));
        setResetNotification(err.detail || 'Reset failed (401 Unauthorized)');
        setTimeout(() => setResetNotification(null), 4000);
      }
    } catch (e) {
      console.error('Reset error:', e);
    } finally {
      setIsResetting(false);
    }
  };

  const navItems: NavGroup[] = [
    {
      group: 'CORE RELIABILITY ENGINE',
      items: [
        {
          id: 'topology',
          label: 'Topology Explorer',
          icon: Network,
          desc: 'Interactive graph canvas & node inspector',
          badge: `${nodeCount} Nodes`,
        },
        {
          id: 'predict',
          label: 'Pre-Flight Risk Engine',
          icon: ShieldAlert,
          desc: 'AST contract diff & 4-term risk score',
          highlight: '#f97316',
        },
        {
          id: 'monitor',
          label: 'Fleet Telemetry',
          icon: Activity,
          desc: 'Real-time HTTP health probers & probes',
          highlight: '#10b981',
        },
      ],
    },
    {
      group: 'PHASE 2 RESILIENCE & AUTONOMY',
      items: [
        {
          id: 'chaos',
          label: 'Chaos Engineering Studio',
          icon: Flame,
          desc: 'Targeted fault & latency injection',
          highlight: '#ef4444',
          badge: 'PHASE 2',
        },
        {
          id: 'actuator',
          label: 'Self-Healing Actuator',
          icon: Zap,
          desc: 'Diagnosis reasoner & guarded rollback',
          highlight: '#818cf8',
          badge: 'PHASE 2',
        },
        {
          id: 'observability',
          label: 'OpenTelemetry Traces',
          icon: Layers,
          desc: 'Distributed span waterfall analyzer',
          highlight: '#06b6d4',
          badge: 'PHASE 2',
        },
      ],
    },
    {
      group: 'DATA & AUDIT LEDGER',
      items: [
        {
          id: 'ingest',
          label: 'Repository Ingestion Hub',
          icon: FolderGit2,
          desc: 'GitHub & Docker Compose parser',
        },
        {
          id: 'incidents',
          label: 'Incident Memory Ledger',
          icon: GitCommit,
          desc: 'Closed-loop feedback (+5.0 learning)',
        },
      ],
    },
    {
      group: 'SECURITY & WORKSPACES',
      items: [
        {
          id: 'projects',
          label: 'Projects & API Keys',
          icon: KeyRound,
          desc: 'Per-project keys (hashed) & tenants',
          highlight: '#38bdf8',
          badge: 'AUTH',
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
      {/* Top Global Command Bar */}
      <header
        style={{
          height: 56,
          backgroundColor: '#0a101d',
          borderBottom: '1px solid #1e293b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          zIndex: 50,
          flexShrink: 0,
        }}
      >
        {/* Left: Brand Identity */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              backgroundColor: 'rgba(6, 182, 212, 0.15)',
              border: '1.5px solid rgba(6, 182, 212, 0.45)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#06b6d4',
              boxShadow: '0 0 14px rgba(6, 182, 212, 0.35)',
            }}
          >
            <Sparkles size={18} />
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ fontSize: 16, fontWeight: 900, letterSpacing: '0.08em', color: '#f8fafc' }}>
              AEGIS
            </span>
            <span style={{ fontSize: 11, color: '#64748b', fontWeight: 600, letterSpacing: '0.04em' }}>
              AUTONOMOUS GRAPH SRE & RELIABILITY CONTROL PLANE
            </span>
          </div>
        </div>

        {/* Center: Live Graph Stats & Fleet Health Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '4px 12px',
              borderRadius: 20,
              backgroundColor: '#0f172a',
              border: '1px solid #1e293b',
              fontSize: 11,
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#10b981', boxShadow: '0 0 8px #10b981' }} />
            <span style={{ color: '#94a3b8' }}>Fleet Topology:</span>
            <strong style={{ color: '#f8fafc' }}>{nodeCount} Nodes</strong>
            <span style={{ color: '#64748b' }}>•</span>
            <strong style={{ color: '#f8fafc' }}>{edgeCount} Edges</strong>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 10px',
              borderRadius: 20,
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              fontSize: 11,
              color: '#34d399',
              fontWeight: 600,
            }}
          >
            <Radio size={12} />
            <span>OPERATIONAL</span>
          </div>

          <button
            onClick={() => handleNavigate('projects')}
            title="Click to view all projects or create a new project tenant"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 10px',
              borderRadius: 20,
              backgroundColor: 'rgba(56, 189, 248, 0.1)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              fontSize: 11,
              color: '#38bdf8',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            <KeyRound size={12} />
            <span>Tenant: {activeProjectId}</span>
          </button>

          {/* GitHub Connection & User Token Status Badge */}
          {gitHubUser ? (
            <button
              onClick={() => handleNavigate('projects')}
              title={`Authenticated as @${gitHubUser.username}. Login Token: ${userLoginToken ? userLoginToken.substring(0, 14) + '...' : 'active'}. Click to manage.`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                borderRadius: 20,
                backgroundColor: 'rgba(34, 197, 94, 0.12)',
                border: '1px solid rgba(34, 197, 94, 0.35)',
                fontSize: 11,
                color: '#4ade80',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              {gitHubUser.avatar_url ? (
                <img
                  src={gitHubUser.avatar_url}
                  alt={gitHubUser.username}
                  style={{ width: 16, height: 16, borderRadius: '50%', border: '1px solid #4ade80' }}
                />
              ) : (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    clipRule="evenodd"
                    d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                  />
                </svg>
              )}
              <span>@{gitHubUser.username}</span>
              <span
                style={{
                  fontSize: 9,
                  padding: '1px 5px',
                  borderRadius: 4,
                  backgroundColor: 'rgba(34, 197, 94, 0.25)',
                  color: '#86efac',
                  fontFamily: 'monospace',
                }}
              >
                TOKEN ACTIVE
              </span>
            </button>
          ) : (
            <button
              onClick={() => handleNavigate('projects')}
              title="Connect GitHub account to project and generate login token"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                borderRadius: 20,
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid #334155',
                fontSize: 11,
                color: '#94a3b8',
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
              <span>Connect GitHub</span>
            </button>
          )}
        </div>

        {/* Right: Live Clock & Reset Baseline Action */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          {resetNotification && (
            <div style={{ fontSize: 11, color: '#34d399', display: 'flex', alignItems: 'center', gap: 6 }}>
              <CheckCircle size={13} />
              <span>{resetNotification}</span>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#64748b', fontFamily: 'monospace' }}>
            <Clock size={13} />
            <span>{currentTime}</span>
          </div>

          <button
            onClick={handleGlobalReset}
            disabled={isResetting}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 12px',
              borderRadius: 6,
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#f87171',
              fontSize: 11,
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <RotateCcw size={12} />
            <span>{isResetting ? 'Resetting...' : 'Reset Baseline'}</span>
          </button>
        </div>
      </header>

      {/* Main Workspace Body */}
      <div style={{ display: 'flex', flex: 1, height: 'calc(100vh - 56px)', overflow: 'hidden' }}>
        {/* Left Enterprise Navigation Sidebar */}
        <aside
          style={{
            width: 260,
            backgroundColor: '#080d18',
            borderRight: '1px solid #1e293b',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: '16px 12px',
            flexShrink: 0,
            overflowY: 'auto',
          }}
        >
          {/* Nav Links by Group */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {navItems.map((group, gIdx) => (
              <div key={gIdx} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    color: '#475569',
                    letterSpacing: '0.08em',
                    padding: '0 8px 6px 8px',
                  }}
                >
                  {group.group}
                </div>

                {group.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = activePage === item.id;
                  const color = item.highlight || '#38bdf8';

                  return (
                    <button
                      key={item.id}
                      onClick={() => handleNavigate(item.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '9px 12px',
                        borderRadius: 8,
                        border: isActive ? `1px solid ${color}` : '1px solid transparent',
                        backgroundColor: isActive ? 'rgba(30, 41, 59, 0.7)' : 'transparent',
                        color: isActive ? '#f8fafc' : '#94a3b8',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all 0.15s ease',
                        boxShadow: isActive ? `0 0 12px ${color}25` : 'none',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <Icon size={16} color={isActive ? color : '#64748b'} />
                        <div>
                          <div style={{ fontSize: 12, fontWeight: isActive ? 700 : 500, color: isActive ? '#f8fafc' : '#cbd5e1' }}>
                            {item.label}
                          </div>
                          <div style={{ fontSize: 10, color: '#475569', lineHeight: 1.2 }}>
                            {item.desc}
                          </div>
                        </div>
                      </div>

                      {item.badge && (
                        <span
                          style={{
                            fontSize: 9,
                            fontWeight: 800,
                            padding: '2px 6px',
                            borderRadius: 4,
                            backgroundColor: '#0f172a',
                            border: '1px solid #1e293b',
                            color: color,
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {item.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          {/* SRE Infrastructure Diagnostics Footer */}
          <div
            style={{
              padding: '12px 14px',
              borderRadius: 8,
              backgroundColor: '#070b14',
              border: '1px solid #1e293b',
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
              fontSize: 10,
              color: '#64748b',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>Backend API</span>
              <span style={{ color: '#10b981', fontWeight: 700 }}>● FastAPI 3.11</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>Graph Engine</span>
              <span style={{ color: '#38bdf8', fontWeight: 700 }}>● Neo4j / NetworkX</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>Diagnosis Engine</span>
              <span style={{ color: '#c084fc', fontWeight: 700 }}>● Scripted Demo</span>
            </div>
          </div>
        </aside>

        {/* Dynamic Multi-Page Main Content View */}
        <main style={{ flex: 1, height: '100%', position: 'relative', overflow: 'hidden', backgroundColor: '#060a12' }}>
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
    </div>
  );
}

export default App;
