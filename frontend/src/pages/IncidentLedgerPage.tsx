import React from 'react';
import {
  GitCommit,
  TrendingUp,
  ArrowRight,
} from 'lucide-react';

interface IncidentLedgerPageProps {
  onNavigate?: (page: string, serviceId?: string) => void;
}

export const IncidentLedgerPage: React.FC<IncidentLedgerPageProps> = ({ onNavigate }) => {
  const incidents = [
    {
      id: 'inc-9481a',
      service: 'paymentservice',
      ts: 'Today, 14:22 UTC',
      cause: 'PostgreSQL connection pool saturated (100/100). Latency degraded to 3,400ms.',
      remediation: 'scale_pool (postgres-payment pool_size=150)',
      safetyScore: 92.0,
      outcome: 'Resolved & Verified',
      graphImpact: '+25 H-factor (+5.0 Risk on PR #142)',
    },
    {
      id: 'inc-8120b',
      service: 'checkoutservice',
      ts: 'Yesterday, 09:14 UTC',
      cause: 'Upstream gRPC deadline exceeded cascading from cartservice timeout.',
      remediation: 'circuit_break (trip timeout 500ms)',
      safetyScore: 88.5,
      outcome: 'Resolved',
      graphImpact: '+10 H-factor',
    },
    {
      id: 'inc-7049c',
      service: 'frontend',
      ts: '3 days ago',
      cause: 'Ingress pod CrashLoopBackOff following unhandled null token exception.',
      remediation: 'restart_pod (frontend-pod-3)',
      safetyScore: 85.0,
      outcome: 'Resolved',
      graphImpact: '+10 H-factor',
    },
  ];

  return (
    <div style={{ padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: 24, height: '100%', overflowY: 'auto' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 38,
              height: 38,
              borderRadius: 10,
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#34d399',
            }}
          >
            <GitCommit size={22} />
          </div>
          <div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
              Closed-Loop Incident Memory & Knowledge Ledger
            </div>
            <div style={{ fontSize: 12, color: '#64748b' }}>
              Immutable audit ledger of self-healed incidents and their mathematical feedback into the graph risk engine
            </div>
          </div>
        </div>

        <button
          onClick={() => onNavigate && onNavigate('predict', 'paymentservice')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 16px',
            borderRadius: 8,
            backgroundColor: 'rgba(249, 115, 22, 0.2)',
            border: '1px solid rgba(249, 115, 22, 0.5)',
            color: '#fb923c',
            fontSize: 12,
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          <span>Verify Risk Jump in PREDICT</span>
          <ArrowRight size={14} />
        </button>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 18 }}>
          <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Incidents Recorded</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#f8fafc', marginTop: 4 }}>3</div>
          <div style={{ fontSize: 11, color: '#10b981', marginTop: 2 }}>Committed to Graph</div>
        </div>

        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 18 }}>
          <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>MTTR (Simulated)</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#38bdf8', marginTop: 4 }}>7.4s</div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>From anomaly to recovery</div>
        </div>

        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 18 }}>
          <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Autonomous Healing Rate</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#10b981', marginTop: 4 }}>100%</div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>Zero unhandled rollbacks</div>
        </div>

        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 18 }}>
          <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Graph Learning Term (H)</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#f97316', marginTop: 4 }}>+25.0</div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>Calculated dynamically</div>
        </div>
      </div>

      {/* Closed-Loop Learning Explanation Panel */}
      <div
        style={{
          padding: 20,
          borderRadius: 12,
          backgroundColor: '#0c1322',
          border: '1px solid #1e293b',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
          <TrendingUp size={16} color="#38bdf8" />
          <span>The Closed Loop in Action: Predict → Deploy → Monitor → Diagnose → Heal → Learn</span>
        </div>

        <p style={{ fontSize: 12, color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
          When an incident occurs and is resolved by AEGIS, an <code style={{ color: '#38bdf8' }}>(:Incident)</code> node is committed into the Neo4j/NetworkX graph and linked to the target service.
          When engineers next test a change in PREDICT, the query <code style={{ color: '#38bdf8' }}>incidents(service_id, 30)</code> finds this node and adds <code style={{ color: '#f97316' }}>+25</code> to the historical risk term <strong style={{ color: '#f8fafc' }}>H</strong>.
          Since the formula is:
        </p>

        <div
          style={{
            padding: 12,
            borderRadius: 8,
            backgroundColor: '#070b14',
            border: '1px solid #1e293b',
            fontFamily: 'monospace',
            fontSize: 13,
            color: '#38bdf8',
            textAlign: 'center',
          }}
        >
          Risk = 0.35 * BlastRadius + 0.30 * ContractDiff + 0.15 * Cycles + 0.20 * History
        </div>

        <div style={{ fontSize: 12, color: '#cbd5e1' }}>
          One incident adds <strong style={{ color: '#f97316' }}>+25 to H</strong>, which yields exactly <strong style={{ color: '#f97316' }}>+5.0 points</strong> to the overall risk score (e.g. 86.0 → 91.0).
        </div>
      </div>

      {/* Incident Ledger Table */}
      <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginBottom: 16 }}>
          Historical Knowledge Graph Incident Records
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {incidents.map((inc) => (
            <div
              key={inc.id}
              style={{
                padding: 14,
                borderRadius: 8,
                backgroundColor: '#070b14',
                border: '1px solid #1e293b',
                display: 'grid',
                gridTemplateColumns: '120px 140px 1fr 180px 140px',
                alignItems: 'center',
                gap: 16,
                fontSize: 12,
              }}
            >
              <div>
                <div style={{ fontWeight: 700, color: '#f8fafc' }}>{inc.id}</div>
                <div style={{ fontSize: 10, color: '#64748b' }}>{inc.ts}</div>
              </div>

              <div>
                <span style={{ padding: '3px 8px', borderRadius: 4, backgroundColor: '#1e293b', color: '#38bdf8', fontWeight: 600, fontSize: 11 }}>
                  {inc.service}
                </span>
              </div>

              <div>
                <div style={{ color: '#cbd5e1', fontWeight: 500 }}>{inc.cause}</div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>Action: {inc.remediation}</div>
              </div>

              <div>
                <div style={{ color: '#f97316', fontWeight: 700, fontSize: 11 }}>{inc.graphImpact}</div>
                <div style={{ fontSize: 10, color: '#64748b' }}>Safety Score: {inc.safetyScore}</div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span style={{ padding: '4px 8px', borderRadius: 4, backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontSize: 11, fontWeight: 700 }}>
                  ✓ {inc.outcome}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
