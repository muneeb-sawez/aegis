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

type PageId =
  | 'topology'
  | 'predict'
  | 'monitor'
  | 'chaos'
  | 'actuator'
  | 'observability'
  | 'ingest'
  | 'incidents';

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
    ];
    return validPages.includes(hash) ? hash : 'topology';
  };

  const [activePage, setActivePage] = useState<PageId>(getInitialPage);
  const [selectedServiceContext, setSelectedServiceContext] = useState<string>('paymentservice');
  const [nodeCount, setNodeCount] = useState<number>(54);
  const [edgeCount, setEdgeCount] = useState<number>(142);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [resetNotification, setResetNotification] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState<string>(new Date().toISOString().substring(11, 19) + ' UTC');

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
        const resp = await fetch('/api/graph/topology');
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
  }, [activePage]);

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
      const resp = await fetch('/api/reset', { method: 'POST' });
      if (resp.ok) {
        const data = await resp.json();
        setNodeCount(data.node_count || 54);
        setEdgeCount(data.edge_count || 142);
        setResetNotification('Demo baseline restored (54 nodes, 142 edges).');
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
          desc: 'LLM graph reasoner & guarded rollback',
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
              <span>Reasoner LLM</span>
              <span style={{ color: '#c084fc', fontWeight: 700 }}>● LiteLLM Free Tier</span>
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
        </main>
      </div>
    </div>
  );
}

export default App;
