import React, { useState, useEffect } from 'react';
import {
  GitCommit,
  TrendingUp,
  ArrowRight,
  RefreshCw,
  Inbox,
  CheckCircle2,
  RotateCcw,
  XCircle,
  Clock,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  History,
} from 'lucide-react';
import { apiUrl } from '../config';


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

interface DecisionRecord {
  decision_id: string;
  incident_id: string;
  service_id: string;
  action: string;
  params: Record<string, any>;
  fault_type: string;
  safety_score: number;
  recovery_score: number;
  composite_score: number;
  status: string;
  outcome?: string;
  reason: string;
  created_at: string;
  updated_at: string;
  emulated: boolean;
}

interface PRComparisonData {
  pr_id: string;
  target_service: string;
  baseline_score: number;
  current_score: number;
  delta_score: number;
  baseline_history_score: number;
  current_history_score: number;
  delta_history_score: number;
  incident_count: number;
  verdict_before: string;
  verdict_after: string;
  explanation: string;
}

export const IncidentLedgerPage: React.FC<IncidentLedgerPageProps> = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState<'decisions' | 'incidents'>('decisions');
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);
  const [decisions, setDecisions] = useState<DecisionRecord[]>([]);
  const [comparison, setComparison] = useState<PRComparisonData | null>(null);
  const [selectedPrId, setSelectedPrId] = useState<string>('PR-142');
  const [isLoading, setIsLoading] = useState(true);
  const [isComparing, setIsComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [incResp, decResp] = await Promise.all([
        fetch(apiUrl('/api/incidents')),
        fetch(apiUrl('/api/decisions')),
      ]);

      if (incResp.ok) {
        const incData = await incResp.json();
        setIncidents(Array.isArray(incData) ? incData : []);
      }

      if (decResp.ok) {
        const decData = await decResp.json();
        setDecisions(Array.isArray(decData) ? decData : []);
      }
    } catch (e: any) {
      setError(e.message || 'Error loading Knowledge Graph ledger data.');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchComparison = async (prId: string) => {
    setIsComparing(true);
    try {
      const resp = await fetch(apiUrl(`/api/predict/pr-comparison?pr_id=${encodeURIComponent(prId)}`));
      if (resp.ok) {
        const data = await resp.json();
        setComparison(data);
      }
    } catch (e: any) {
      console.error('Failed to load PR comparison:', e);
    } finally {
      setIsComparing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    fetchComparison(selectedPrId);
  }, [selectedPrId]);

  const totalIncidents = incidents.length;
  const totalDecisions = decisions.length;
  const successfulDecisions = decisions.filter((d) => d.status === 'succeeded' || d.outcome === 'succeeded').length;
  const healingRateDisplay =
    totalDecisions > 0 ? `${Math.round((successfulDecisions / totalDecisions) * 100)}%` : totalIncidents > 0 ? '100%' : 'n/a';
  const hTermDisplay = totalIncidents > 0 ? `+${Math.min(100, totalIncidents * 25.0).toFixed(1)}` : '0.0';

  const renderOutcomeBadge = (status: string) => {
    const s = status.toLowerCase();
    if (s === 'succeeded') {
      return (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            padding: '4px 8px',
            borderRadius: 6,
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            color: '#34d399',
            fontSize: 11,
            fontWeight: 700,
          }}
        >
          <CheckCircle2 size={13} />
          SUCCEEDED
        </span>
      );
    }
    if (s === 'rolled_back') {
      return (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            padding: '4px 8px',
            borderRadius: 6,
            backgroundColor: 'rgba(245, 158, 11, 0.15)',
            border: '1px solid rgba(245, 158, 11, 0.4)',
            color: '#fbbf24',
            fontSize: 11,
            fontWeight: 700,
          }}
        >
          <RotateCcw size={13} />
          ROLLED BACK
        </span>
      );
    }
    if (s === 'refused') {
      return (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            padding: '4px 8px',
            borderRadius: 6,
            backgroundColor: 'rgba(168, 85, 247, 0.15)',
            border: '1px solid rgba(168, 85, 247, 0.4)',
            color: '#c084fc',
            fontSize: 11,
            fontWeight: 700,
          }}
        >
          <ShieldAlert size={13} />
          REFUSED (SAFETY)
        </span>
      );
    }
    if (s === 'failed') {
      return (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            padding: '4px 8px',
            borderRadius: 6,
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: '#f87171',
            fontSize: 11,
            fontWeight: 700,
          }}
        >
          <XCircle size={13} />
          FAILED
        </span>
      );
    }
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          padding: '4px 8px',
          borderRadius: 6,
          backgroundColor: 'rgba(56, 189, 248, 0.15)',
          border: '1px solid rgba(56, 189, 248, 0.4)',
          color: '#38bdf8',
          fontSize: 11,
          fontWeight: 700,
        }}
      >
        <Clock size={13} />
        {status.toUpperCase()}
      </span>
    );
  };

  return (
    <div style={{ padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: 24, height: '100%', overflowY: 'auto' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
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
            <GitCommit size={22} />
          </div>
          <div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
              Closed-Loop Feedback & Incident Memory Ledger
            </div>
            <div style={{ fontSize: 12, color: '#64748b' }}>
              M8 Feedback Loop: Terminal outcomes persist to Knowledge Graph and measurably change future PR risk scores
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={() => {
              fetchData();
              fetchComparison(selectedPrId);
            }}
            disabled={isLoading || isComparing}
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
            <RefreshCw size={14} className={isLoading || isComparing ? 'animate-spin' : ''} />
            <span>Refresh Ledger</span>
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
            <span>Open PREDICT Studio</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 18 }}>
          <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Decisions Recorded</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#f8fafc', marginTop: 4 }}>
            {isLoading ? '...' : totalDecisions}
          </div>
          <div style={{ fontSize: 11, color: '#38bdf8', marginTop: 2 }}>Immutable audit trail</div>
        </div>

        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 18 }}>
          <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Graph Incident Nodes</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#34d399', marginTop: 4 }}>
            {isLoading ? '...' : totalIncidents}
          </div>
          <div style={{ fontSize: 11, color: '#10b981', marginTop: 2 }}>Committed via GraphRepository</div>
        </div>

        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 18 }}>
          <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Remediation Success Rate</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#10b981', marginTop: 4 }}>
            {healingRateDisplay}
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>Derived from graph (:Outcome) nodes</div>
        </div>

        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 18 }}>
          <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Active History Term (H)</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#f97316', marginTop: 4 }}>
            {hTermDisplay}
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>min(100, incidents × 25)</div>
        </div>
      </div>

      {/* BEFORE VS AFTER RISK CARD FOR PR #142 (Acceptance Criterion §5) */}
      <div
        style={{
          backgroundColor: '#0c1322',
          borderRadius: 14,
          border: '1px solid rgba(249, 115, 22, 0.4)',
          boxShadow: '0 8px 32px rgba(249, 115, 22, 0.08)',
          padding: 24,
          display: 'flex',
          flexDirection: 'column',
          gap: 18,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                backgroundColor: 'rgba(249, 115, 22, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#f97316',
              }}
            >
              <TrendingUp size={18} />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 800, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>Closed-Loop "Before vs After" Risk Card</span>
                <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, backgroundColor: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', fontWeight: 700 }}>
                  Review 2 Golden Loop
                </span>
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>
                Demonstrates how recorded incident outcomes shift future pre-deployment risk scores in real-time
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600 }}>Select PR:</span>
            <select
              value={selectedPrId}
              onChange={(e) => setSelectedPrId(e.target.value)}
              style={{
                backgroundColor: '#070b14',
                color: '#f8fafc',
                border: '1px solid #1e293b',
                borderRadius: 6,
                padding: '6px 12px',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              <option value="PR-142">PR #142 (paymentservice — Breaking Change)</option>
              <option value="PR-010">PR #010 (productcatalogservice — Safe Change)</option>
              <option value="PR-077">PR #077 (frontend — Cyclic Dependency)</option>
              <option value="PR-055">PR #055 (checkoutservice — Moderate Risk)</option>
            </select>

            <button
              onClick={() => fetchComparison(selectedPrId)}
              disabled={isComparing}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 12px',
                borderRadius: 6,
                backgroundColor: '#1e293b',
                border: 'none',
                color: '#f8fafc',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <RefreshCw size={13} className={isComparing ? 'animate-spin' : ''} />
              <span>Re-calculate</span>
            </button>
          </div>
        </div>

        {/* 3-Column Comparison Grid: Before -> Delta -> After */}
        {comparison && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 20, alignItems: 'stretch' }}>
            {/* BEFORE INCIDENT CARD */}
            <div
              style={{
                backgroundColor: '#070b14',
                borderRadius: 10,
                border: '1px solid #1e293b',
                padding: 18,
                display: 'flex',
                flexDirection: 'column',
                gap: 12,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: '#64748b' }}>
                  Before Incident (Baseline)
                </span>
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: 4,
                    backgroundColor: 'rgba(100, 116, 139, 0.2)',
                    color: '#94a3b8',
                    fontSize: 11,
                    fontWeight: 700,
                  }}
                >
                  H = {comparison.baseline_history_score.toFixed(1)}
                </span>
              </div>

              <div>
                <div style={{ fontSize: 32, fontWeight: 900, color: '#f8fafc' }}>
                  {comparison.baseline_score.toFixed(1)}
                  <span style={{ fontSize: 14, color: '#64748b', fontWeight: 600 }}> / 100</span>
                </div>
                <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                  Verdict:{' '}
                  <strong style={{ color: comparison.verdict_before === 'Blocked' ? '#f87171' : '#fbbf24' }}>
                    {comparison.verdict_before}
                  </strong>
                </div>
              </div>

              <div style={{ fontSize: 11, color: '#64748b', display: 'flex', flexDirection: 'column', gap: 4, borderTop: '1px solid #1e293b', paddingTop: 8 }}>
                <div>Target Service: <strong style={{ color: '#cbd5e1' }}>{comparison.target_service}</strong></div>
                <div>Incident Penalty: <strong style={{ color: '#cbd5e1' }}>0.0 pts (0 incidents)</strong></div>
              </div>
            </div>

            {/* DELTA ARROW & LEARNING BADGE */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '0 8px' }}>
              <div
                style={{
                  padding: '8px 16px',
                  borderRadius: 20,
                  backgroundColor: comparison.delta_score > 0 ? 'rgba(249, 115, 22, 0.2)' : 'rgba(16, 185, 129, 0.15)',
                  border: comparison.delta_score > 0 ? '1px solid rgba(249, 115, 22, 0.6)' : '1px solid rgba(16, 185, 129, 0.4)',
                  color: comparison.delta_score > 0 ? '#fb923c' : '#34d399',
                  fontSize: 15,
                  fontWeight: 900,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <span>{comparison.delta_score > 0 ? `+${comparison.delta_score.toFixed(1)}` : '0.0'}</span>
                <span style={{ fontSize: 11, fontWeight: 700 }}>Learning Delta</span>
              </div>
              <div style={{ fontSize: 11, color: '#64748b', textAlign: 'center', maxWidth: 120 }}>
                Formula: 0.20 × ΔH ({comparison.delta_history_score > 0 ? `+${comparison.delta_history_score.toFixed(0)}` : '0'})
              </div>
            </div>

            {/* AFTER INCIDENT CARD */}
            <div
              style={{
                backgroundColor: '#070b14',
                borderRadius: 10,
                border: comparison.delta_score > 0 ? '1px solid rgba(249, 115, 22, 0.5)' : '1px solid #1e293b',
                padding: 18,
                display: 'flex',
                flexDirection: 'column',
                gap: 12,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: comparison.delta_score > 0 ? '#fb923c' : '#64748b' }}>
                  After Incident (Live Graph)
                </span>
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: 4,
                    backgroundColor: comparison.delta_score > 0 ? 'rgba(249, 115, 22, 0.2)' : 'rgba(100, 116, 139, 0.2)',
                    color: comparison.delta_score > 0 ? '#fb923c' : '#94a3b8',
                    fontSize: 11,
                    fontWeight: 700,
                  }}
                >
                  H = {comparison.current_history_score.toFixed(1)} (+{comparison.delta_history_score.toFixed(1)})
                </span>
              </div>

              <div>
                <div style={{ fontSize: 32, fontWeight: 900, color: comparison.delta_score > 0 ? '#fb923c' : '#f8fafc' }}>
                  {comparison.current_score.toFixed(1)}
                  <span style={{ fontSize: 14, color: '#64748b', fontWeight: 600 }}> / 100</span>
                </div>
                <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                  Verdict:{' '}
                  <strong style={{ color: comparison.verdict_after === 'Blocked' ? '#f87171' : '#fbbf24' }}>
                    {comparison.verdict_after}
                  </strong>
                </div>
              </div>

              <div style={{ fontSize: 11, color: '#64748b', display: 'flex', flexDirection: 'column', gap: 4, borderTop: '1px solid #1e293b', paddingTop: 8 }}>
                <div>Active Incidents in 30d: <strong style={{ color: comparison.delta_score > 0 ? '#fb923c' : '#cbd5e1' }}>{comparison.incident_count}</strong></div>
                <div>History Contribution: <strong style={{ color: comparison.delta_score > 0 ? '#fb923c' : '#cbd5e1' }}>+{(0.20 * comparison.current_history_score).toFixed(1)} pts</strong></div>
              </div>
            </div>
          </div>
        )}

        {/* Human-Readable Explanation Box */}
        {comparison && (
          <div
            style={{
              padding: '12px 16px',
              borderRadius: 8,
              backgroundColor: '#070b14',
              border: '1px solid #1e293b',
              fontSize: 12,
              color: '#cbd5e1',
              lineHeight: 1.6,
              display: 'flex',
              alignItems: 'flex-start',
              gap: 10,
            }}
          >
            <Sparkles size={16} color="#f97316" style={{ flexShrink: 0, marginTop: 2 }} />
            <div>
              <strong style={{ color: '#f8fafc' }}>Autonomous Learning Explanation: </strong>
              {comparison.explanation}
            </div>
          </div>
        )}
      </div>

      {/* Tabs: Decision Audit Log vs Historical Incidents */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={() => setActiveTab('decisions')}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              backgroundColor: activeTab === 'decisions' ? '#1e293b' : 'transparent',
              border: 'none',
              color: activeTab === 'decisions' ? '#f8fafc' : '#64748b',
              fontSize: 13,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <ShieldCheck size={16} color={activeTab === 'decisions' ? '#38bdf8' : '#64748b'} />
            <span>Remediation Decisions & Graph Outcomes ({totalDecisions})</span>
          </button>

          <button
            onClick={() => setActiveTab('incidents')}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              backgroundColor: activeTab === 'incidents' ? '#1e293b' : 'transparent',
              border: 'none',
              color: activeTab === 'incidents' ? '#f8fafc' : '#64748b',
              fontSize: 13,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <History size={16} color={activeTab === 'incidents' ? '#34d399' : '#64748b'} />
            <span>Graph Incident Records ({totalIncidents})</span>
          </button>
        </div>

        <div style={{ fontSize: 11, color: '#64748b' }}>
          {activeTab === 'decisions' ? 'Queried via GET /api/decisions' : 'Queried via GraphRepository.incidents()'}
        </div>
      </div>

      {/* TAB 1: REMEDIATION DECISIONS AUDIT LOG */}
      {activeTab === 'decisions' && (
        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 20 }}>
          {error && (
            <div style={{ padding: '12px 16px', borderRadius: 8, backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#f87171', fontSize: 12, marginBottom: 16 }}>
              {error}
            </div>
          )}

          {totalDecisions === 0 && !isLoading && (
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
                <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>No Decisions Logged Yet</div>
                <div style={{ fontSize: 12, color: '#64748b', maxWidth: 460, marginTop: 4, lineHeight: 1.5 }}>
                  The actuator audit registry records all remediation decisions and their graph outcomes.
                  Inject a fault and run auto-remediation in Actuator or Monitor to see decision audit records appear here.
                </div>
              </div>
            </div>
          )}

          {totalDecisions > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div
                style={{
                  padding: '8px 14px',
                  display: 'grid',
                  gridTemplateColumns: '130px 140px 1fr 180px 150px',
                  gap: 16,
                  fontSize: 11,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  color: '#64748b',
                }}
              >
                <div>Decision ID</div>
                <div>Target Service</div>
                <div>Action & Rationale</div>
                <div>Safety & Scores</div>
                <div style={{ textAlign: 'right' }}>Outcome Status</div>
              </div>

              {decisions.map((dec) => {
                const formattedDate = dec.created_at ? new Date(dec.created_at).toLocaleTimeString() : 'Recent';
                const effectiveOutcome = dec.outcome || dec.status;

                return (
                  <div
                    key={dec.decision_id}
                    style={{
                      padding: 14,
                      borderRadius: 8,
                      backgroundColor: '#070b14',
                      border: '1px solid #1e293b',
                      display: 'grid',
                      gridTemplateColumns: '130px 140px 1fr 180px 150px',
                      alignItems: 'center',
                      gap: 16,
                      fontSize: 12,
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700, color: '#f8fafc', fontFamily: 'monospace' }}>{dec.decision_id}</div>
                      <div style={{ fontSize: 10, color: '#64748b' }}>{formattedDate}</div>
                      <div style={{ fontSize: 9, color: '#475569', marginTop: 2 }}>{dec.fault_type}</div>
                    </div>

                    <div>
                      <span style={{ padding: '3px 8px', borderRadius: 4, backgroundColor: '#1e293b', color: '#38bdf8', fontWeight: 600, fontSize: 11 }}>
                        {dec.service_id}
                      </span>
                      <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4, fontFamily: 'monospace' }}>
                        action: {dec.action}
                      </div>
                    </div>

                    <div>
                      <div style={{ color: '#cbd5e1', fontWeight: 500, fontSize: 12 }}>{dec.reason || 'Autonomous remediation'}</div>
                      {dec.params && Object.keys(dec.params).length > 0 && (
                        <div style={{ fontSize: 11, color: '#64748b', marginTop: 2, fontFamily: 'monospace' }}>
                          params: {JSON.stringify(dec.params)}
                        </div>
                      )}
                    </div>

                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontSize: 11, color: '#64748b' }}>Safety:</span>
                        <strong style={{ color: dec.safety_score >= 75 ? '#34d399' : '#f87171', fontSize: 12 }}>
                          {dec.safety_score.toFixed(1)}
                        </strong>
                        <span style={{ fontSize: 10, color: '#64748b' }}>
                          (Score: {dec.composite_score.toFixed(1)})
                        </span>
                      </div>
                      <div style={{ fontSize: 10, color: '#64748b', marginTop: 2 }}>
                        (:Decision)-[:RESULTED_IN]-&gt;(:Outcome)
                      </div>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      {renderOutcomeBadge(effectiveOutcome)}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: HISTORICAL INCIDENTS TABLE */}
      {activeTab === 'incidents' && (
        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 20 }}>
          {totalIncidents === 0 && !isLoading && (
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
                <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>No Incidents Recorded in Graph</div>
                <div style={{ fontSize: 12, color: '#64748b', maxWidth: 460, marginTop: 4, lineHeight: 1.5 }}>
                  The Knowledge Graph contains no recorded incidents.
                  Inject a fault in Chaos or Monitor, then heal and commit the incident to see it appear in this ledger.
                </div>
              </div>
            </div>
          )}

          {totalIncidents > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div
                style={{
                  padding: '8px 14px',
                  display: 'grid',
                  gridTemplateColumns: '130px 140px 1fr 180px 140px',
                  gap: 16,
                  fontSize: 11,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  color: '#64748b',
                }}
              >
                <div>Incident ID</div>
                <div>Target Service</div>
                <div>Description</div>
                <div>Historical Impact</div>
                <div style={{ textAlign: 'right' }}>Resolution</div>
              </div>

              {incidents.map((inc) => {
                const action = inc.properties?.action || 'remediation';
                const formattedDate = inc.timestamp ? new Date(inc.timestamp).toLocaleTimeString() : 'Recent';

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
                      <div style={{ fontWeight: 700, color: '#f8fafc', fontFamily: 'monospace' }}>{inc.id}</div>
                      <div style={{ fontSize: 10, color: '#64748b' }}>{formattedDate}</div>
                    </div>

                    <div>
                      <span style={{ padding: '3px 8px', borderRadius: 4, backgroundColor: '#1e293b', color: '#38bdf8', fontWeight: 600, fontSize: 11 }}>
                        {inc.service_id}
                      </span>
                    </div>

                    <div>
                      <div style={{ color: '#cbd5e1', fontWeight: 500 }}>{inc.description}</div>
                      <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>action: {action}</div>
                    </div>

                    <div>
                      <div style={{ color: '#f97316', fontWeight: 700, fontSize: 11 }}>+25 H-factor (+5.0 Risk)</div>
                      <div style={{ fontSize: 10, color: '#64748b' }}>weight: 0.20 × 25.0</div>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <span style={{ padding: '4px 8px', borderRadius: 4, backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontSize: 11, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                        <CheckCircle2 size={12} />
                        <span>RESOLVED</span>
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default IncidentLedgerPage;
