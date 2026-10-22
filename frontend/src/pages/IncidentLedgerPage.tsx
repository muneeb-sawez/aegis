import React, { useState, useEffect } from 'react';
import {
  GitCommit,
  TrendingUp,
  ArrowRight,
  RefreshCw,
  Inbox,
  CheckCircle2,
} from 'lucide-react';

interface IncidentLedgerPageProps {
  onNavigate?: (page: string, serviceId?: string) => void;
}

interface IncidentRecord {
  id: string;
  service_id: string;
  description: string;
  timestamp: string;
  resolved: boolean;
  decision_id?: string | null;
  properties?: Record<string, any>;
}

export const IncidentLedgerPage: React.FC<IncidentLedgerPageProps> = ({ onNavigate }) => {
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchIncidents = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetch('/api/incidents');
      if (resp.ok) {
        const data = await resp.json();
        setIncidents(Array.isArray(data) ? data : []);
      } else {
        setError(`Failed to fetch incidents (HTTP ${resp.status})`);
      }
    } catch (e: any) {
      setError(e.message || 'Error fetching incidents from graph');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  const totalIncidents = incidents.length;
  const resolvedCount = incidents.filter(
    (i) => i.resolved || i.properties?.outcome === 'success' || i.properties?.status === 'resolved'
  ).length;

  const mttrDisplay = 'n/a';
  const healingRateDisplay = totalIncidents > 0 ? `${Math.round((resolvedCount / totalIncidents) * 100)}%` : 'n/a';
  const hTermDisplay = totalIncidents > 0 ? `+${Math.min(100, totalIncidents * 25.0).toFixed(1)}` : '0.0';

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
              Real Knowledge Graph incident records queried via GraphRepository.incidents()
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={fetchIncidents}
            disabled={isLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 14px',
              borderRadius: 8,
              backgroundColor: '#0f172a',
              border: '1px solid #1e293b',
              color: '#94a3b8',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>

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
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 18 }}>
          <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Incidents Recorded</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#f8fafc', marginTop: 4 }}>
            {isLoading ? '...' : totalIncidents}
          </div>
          <div style={{ fontSize: 11, color: '#10b981', marginTop: 2 }}>Committed to Graph</div>
        </div>

        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 18 }}>
          <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>MTTR (Simulated)</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#38bdf8', marginTop: 4 }}>
            {mttrDisplay}
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>Measured per run</div>
        </div>

        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 18 }}>
          <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Autonomous Healing Rate</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#10b981', marginTop: 4 }}>
            {healingRateDisplay}
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>From live incident outcomes</div>
        </div>

        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 18 }}>
          <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Graph Learning Term (H)</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#f97316', marginTop: 4 }}>
            {hTermDisplay}
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>Calculated from active incidents</div>
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
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
            Historical Knowledge Graph Incident Records
          </div>
          {totalIncidents > 0 && (
            <span style={{ fontSize: 11, color: '#64748b' }}>
              Showing {totalIncidents} recorded incident{totalIncidents !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {error && (
          <div style={{ padding: '12px 16px', borderRadius: 8, backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#f87171', fontSize: 12 }}>
            {error}
          </div>
        )}

        {totalIncidents === 0 && !isLoading && !error && (
          <div
            style={{
              padding: '48px 24px',
              borderRadius: 8,
              backgroundColor: '#070b14',
              border: '1px solid #1e293b',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 12,
              textAlign: 'center',
            }}
          >
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: '50%',
                backgroundColor: 'rgba(100, 116, 139, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#64748b',
              }}
            >
              <Inbox size={22} />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>No incidents yet</div>
              <div style={{ fontSize: 12, color: '#64748b', maxWidth: 460, marginTop: 4, lineHeight: 1.5 }}>
                The Knowledge Graph contains no recorded incidents for the baseline topology.
                Inject a fault in Chaos or Monitor, then heal and commit the incident to see it appear in this ledger.
              </div>
            </div>
          </div>
        )}

        {totalIncidents > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {incidents.map((inc) => {
              const action = inc.properties?.action || 'remediation';
              const safetyScore = inc.properties?.safety_score !== undefined ? inc.properties.safety_score : 'n/a';
              const outcome = inc.properties?.outcome || (inc.resolved ? 'success' : 'open');
              const formattedDate = inc.timestamp ? new Date(inc.timestamp).toLocaleString() : 'Recent';

              return (
                <div
                  key={inc.id}
                  style={{
                    padding: 14,
                    borderRadius: 8,
                    backgroundColor: '#070b14',
                    border: '1px solid #1e293b',
                    display: 'grid',
                    gridTemplateColumns: '130px 140px 1fr 180px 140px',
                    alignItems: 'center',
                    gap: 16,
                    fontSize: 12,
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, color: '#f8fafc' }}>{inc.id}</div>
                    <div style={{ fontSize: 10, color: '#64748b' }}>{formattedDate}</div>
                  </div>

                  <div>
                    <span style={{ padding: '3px 8px', borderRadius: 4, backgroundColor: '#1e293b', color: '#38bdf8', fontWeight: 600, fontSize: 11 }}>
                      {inc.service_id}
                    </span>
                  </div>

                  <div>
                    <div style={{ color: '#cbd5e1', fontWeight: 500 }}>{inc.description}</div>
                    <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>Action: {action}</div>
                  </div>

                  <div>
                    <div style={{ color: '#f97316', fontWeight: 700, fontSize: 11 }}>+25 H-factor (+5.0 Risk)</div>
                    <div style={{ fontSize: 10, color: '#64748b' }}>Safety Score: {safetyScore}</div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <span style={{ padding: '4px 8px', borderRadius: 4, backgroundColor: outcome === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)', color: outcome === 'success' ? '#34d399' : '#f87171', fontSize: 11, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                      <CheckCircle2 size={12} />
                      <span>{outcome}</span>
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default IncidentLedgerPage;
