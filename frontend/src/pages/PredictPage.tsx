import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Play,
  CheckCircle,
  GitPullRequest,
  Layers,
} from 'lucide-react';
import { getActiveProjectId, apiUrl } from '../config';

export const PredictPage: React.FC = () => {
  const [services, setServices] = useState<any[]>([]);
  const [selectedService, setSelectedService] = useState('paymentservice');
  const [changeType, setChangeType] = useState('api_breaking');
  const [changeTitle, setChangeTitle] = useState('Refactor payment authorization payload');
  const [changeDesc, setChangeDesc] = useState('Deprecate legacy card_token and introduce strict idempotency keys.');
  const [dependencyTarget, setDependencyTarget] = useState('frontend');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Load available services from active graph
  useEffect(() => {
    const fetchServices = async () => {
      try {
        const pid = getActiveProjectId();
        const resp = await fetch(apiUrl(`/api/predict/services?project_id=${encodeURIComponent(pid)}`));
        if (resp.ok) {
          const data = await resp.json();
          setServices(data);
          if (data.length > 0 && !data.some((s: any) => s.id === selectedService)) {
            setSelectedService(data[0].id);
          }
        }
      } catch (e) {
        console.error('Failed to load services:', e);
      }
    };
    fetchServices();

    const onProjectChange = () => fetchServices();
    window.addEventListener('aegis_project_changed', onProjectChange);
    return () => window.removeEventListener('aegis_project_changed', onProjectChange);
  }, []);

  const handleRunAnalysis = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const pid = getActiveProjectId();
      const payload: any = {
        service_id: selectedService,
        change_type: changeType,
        change_title: changeTitle,
        description: changeDesc,
        project_id: pid,
      };

      if (changeType === 'dependency_add' || changeType === 'dependency_cycle') {
        payload.new_dependency_target = dependencyTarget;
      }

      if (changeType === 'api_breaking') {
        payload.removed_fields = ['card_token', 'cvv_inline'];
        payload.added_fields = ['idempotency_key', 'payment_intent_id'];
      } else if (changeType === 'additive_safe') {
        payload.added_fields = ['loyalty_rewards_id', 'metadata_tags'];
      }

      const resp = await fetch(apiUrl('/api/predict/analyze'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (resp.ok) {
        const data = await resp.json();
        setResult(data);
      } else {
        const errJson = await resp.json().catch(() => null);
        setError(errJson?.detail || `PREDICT failed with HTTP ${resp.status}`);
      }
    } catch (e: any) {
      setError(e.message || 'Network error communicating with PREDICT API.');
    } finally {
      setIsLoading(false);
    }
  };

  // Run initial analysis on mount
  useEffect(() => {
    handleRunAnalysis();
  }, []);

  const riskScore = result?.risk_score !== undefined ? Number(result.risk_score) : null;
  const verdict = result?.verdict || 'Ready';

  return (
    <div style={{ padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: 24, height: '100%', overflowY: 'auto' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, backgroundColor: 'rgba(249, 115, 22, 0.15)', border: '1px solid rgba(249, 115, 22, 0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f97316' }}>
              <ShieldAlert size={20} />
            </div>
            <div>
              <div style={{ fontSize: 20, fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
                PREDICT — Pre-Deployment Risk Intelligence Studio
              </div>
              <div style={{ fontSize: 12, color: '#64748b' }}>
                Graph-grounded architectural blast radius, schema breaking contract diffs, and Tarjan cycle detection
              </div>
            </div>
          </div>
        </div>

        <button
          onClick={handleRunAnalysis}
          disabled={isLoading}
          style={{
            padding: '10px 20px',
            borderRadius: 8,
            backgroundColor: '#ea580c',
            border: 'none',
            color: '#fff',
            fontSize: 13,
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            cursor: 'pointer',
            boxShadow: '0 4px 16px rgba(234, 88, 12, 0.35)',
          }}
        >
          <Play size={15} fill="#fff" />
          <span>{isLoading ? 'Computing Graph Blast...' : 'Run Risk Analysis'}</span>
        </button>
      </div>

      {/* Main 2-Column Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', gap: 24 }}>
        {/* Left Column: Change Configuration Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div style={{ padding: '20px', borderRadius: 12, backgroundColor: '#0a101d', border: '1px solid #1e293b', display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
              <GitPullRequest size={16} color="#38bdf8" />
              <span>Propose Pull Request / Software Change</span>
            </div>

            {/* Target Service */}
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 6, display: 'block' }}>
                Target Microservice
              </label>
              <select
                value={selectedService}
                onChange={(e) => setSelectedService(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: 7,
                  backgroundColor: '#070c16',
                  border: '1px solid #334155',
                  color: '#f8fafc',
                  fontSize: 12,
                  outline: 'none',
                }}
              >
                {services.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name || s.id} ({s.id})
                  </option>
                ))}
              </select>
            </div>

            {/* Change Type Cards */}
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 6, display: 'block' }}>
                Change Category & Semantic Nature
              </label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[
                  { id: 'api_breaking', title: 'Breaking API Contract', desc: 'Deletes required fields or alters types (C=100.0)', color: '#ef4444' },
                  { id: 'additive_safe', title: 'Additive (Non-Breaking)', desc: 'Adds optional fields with defaults (C=0.0)', color: '#10b981' },
                  { id: 'dependency_add', title: 'Add New Outbound Call', desc: 'Adds new dependency edge; checks cycle safety', color: '#38bdf8' },
                  { id: 'dependency_cycle', title: 'Introduce Circular Call', desc: 'Creates circular feedback deadlock (D=100.0)', color: '#a855f7' },
                ].map((item) => (
                  <div
                    key={item.id}
                    onClick={() => setChangeType(item.id)}
                    style={{
                      padding: '10px 14px',
                      borderRadius: 8,
                      backgroundColor: changeType === item.id ? 'rgba(56, 189, 248, 0.08)' : '#070c16',
                      border: changeType === item.id ? `1.5px solid ${item.color}` : '1px solid #1e293b',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700, color: item.color, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span>{item.title}</span>
                      {changeType === item.id && <CheckCircle size={14} color={item.color} />}
                    </div>
                    <div style={{ fontSize: 10, color: '#64748b', marginTop: 3 }}>{item.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Dependency Target if relevant */}
            {(changeType === 'dependency_add' || changeType === 'dependency_cycle') && (
              <div>
                <label style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 6, display: 'block' }}>
                  Target Destination Service (CALLED By {selectedService})
                </label>
                <select
                  value={dependencyTarget}
                  onChange={(e) => setDependencyTarget(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: 7,
                    backgroundColor: '#070c16',
                    border: '1px solid #334155',
                    color: '#f8fafc',
                    fontSize: 12,
                    outline: 'none',
                  }}
                >
                  {services.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name || s.id} ({s.id})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Change Title */}
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 6, display: 'block' }}>
                Pull Request / Change Title
              </label>
              <input
                type="text"
                value={changeTitle}
                onChange={(e) => setChangeTitle(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: 7,
                  backgroundColor: '#070c16',
                  border: '1px solid #334155',
                  color: '#f8fafc',
                  fontSize: 12,
                  outline: 'none',
                }}
              />
            </div>

            {/* Description */}
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 6, display: 'block' }}>
                Change Rationale & Notes
              </label>
              <textarea
                value={changeDesc}
                onChange={(e) => setChangeDesc(e.target.value)}
                rows={3}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: 7,
                  backgroundColor: '#070c16',
                  border: '1px solid #334155',
                  color: '#f8fafc',
                  fontSize: 11,
                  fontFamily: 'Inter, sans-serif',
                  outline: 'none',
                  resize: 'none',
                }}
              />
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div style={{ padding: '12px 16px', borderRadius: 8, backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.4)', color: '#fca5a5', fontSize: 12 }}>
              {error}
            </div>
          )}
        </div>

        {/* Right Column: Computed Risk Results & Blast Visualization */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {/* Top Score Banner */}
          <div
            style={{
              padding: '24px',
              borderRadius: 14,
              backgroundColor: '#0a101d',
              border: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              boxShadow: '0 8px 30px rgba(0, 0, 0, 0.5)',
            }}
          >
            <div>
              <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
                AEGIS Multi-Factor Risk Score (Computed from Graph)
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginTop: 6 }}>
                <span style={{ fontSize: 48, fontWeight: 900, color: riskScore !== null && riskScore >= 70 ? '#ef4444' : riskScore !== null && riskScore >= 40 ? '#f97316' : '#10b981', fontFamily: 'JetBrains Mono, monospace' }}>
                  {riskScore !== null ? riskScore.toFixed(1) : '--'}
                </span>
                <span style={{ fontSize: 18, color: '#64748b', fontWeight: 600 }}>/ 100</span>
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>
                Formula: <code style={{ color: '#38bdf8' }}>0.35B + 0.30C + 0.15D + 0.20H</code>
              </div>
            </div>

            {/* Verdict Card */}
            <div
              style={{
                padding: '16px 24px',
                borderRadius: 10,
                backgroundColor: verdict === 'Blocked' ? 'rgba(239, 68, 68, 0.15)' : verdict === 'Warn' || verdict === 'Warning' ? 'rgba(249, 115, 22, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                border: verdict === 'Blocked' ? '1.5px solid #ef4444' : verdict === 'Warn' || verdict === 'Warning' ? '1.5px solid #f97316' : '1.5px solid #10b981',
                textAlign: 'center',
                minWidth: 170,
              }}
            >
              <div style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>Merge Recommendation</div>
              <div style={{ fontSize: 20, fontWeight: 800, marginTop: 4, color: verdict === 'Blocked' ? '#f87171' : verdict === 'Warn' || verdict === 'Warning' ? '#fb923c' : '#34d399' }}>
                {verdict.toUpperCase()}
              </div>
            </div>
          </div>

          {/* 4 Factor Breakdown Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
            {/* Term B: Blast Radius */}
            <div style={{ padding: '16px', borderRadius: 10, backgroundColor: '#070c16', border: '1px solid #1e293b' }}>
              <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>Blast Radius (B)</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: '#f8fafc', marginTop: 4, fontFamily: 'JetBrains Mono, monospace' }}>
                {result?.breakdown?.blast_score !== undefined ? Number(result.breakdown.blast_score).toFixed(1) : '--'}
              </div>
              <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>Weight: 0.35</div>
              <div style={{ fontSize: 10, color: '#38bdf8', marginTop: 2 }}>
                {result?.blast_details?.length || 0} Upstream Callers
              </div>
            </div>

            {/* Term C: Contract Diff */}
            <div style={{ padding: '16px', borderRadius: 10, backgroundColor: '#070c16', border: '1px solid #1e293b' }}>
              <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>Contract Diff (C)</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: (result?.breakdown?.contract_score ?? 0) > 0 ? '#ef4444' : '#10b981', marginTop: 4, fontFamily: 'JetBrains Mono, monospace' }}>
                {result?.breakdown?.contract_score !== undefined ? Number(result.breakdown.contract_score).toFixed(1) : '--'}
              </div>
              <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>Weight: 0.30</div>
              <div style={{ fontSize: 10, color: (result?.breakdown?.contract_score ?? 0) > 0 ? '#fca5a5' : '#34d399', marginTop: 2 }}>
                {result?.contract_diff?.is_breaking ? 'Breaking AST Diff' : 'Safe Additive'}
              </div>
            </div>

            {/* Term D: Cycle Penalty */}
            <div style={{ padding: '16px', borderRadius: 10, backgroundColor: '#070c16', border: '1px solid #1e293b' }}>
              <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>Cycle Penalty (D)</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: (result?.breakdown?.cycle_score ?? 0) > 0 ? '#a855f7' : '#10b981', marginTop: 4, fontFamily: 'JetBrains Mono, monospace' }}>
                {result?.breakdown?.cycle_score !== undefined ? Number(result.breakdown.cycle_score).toFixed(1) : '--'}
              </div>
              <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>Weight: 0.15</div>
              <div style={{ fontSize: 10, color: (result?.breakdown?.cycle_score ?? 0) > 0 ? '#c084fc' : '#34d399', marginTop: 2 }}>
                {result?.cycle_check?.has_cycle ? 'Tarjan Cycle Detected' : 'Clean DAG Topology'}
              </div>
            </div>

            {/* Term H: Incident History */}
            <div style={{ padding: '16px', borderRadius: 10, backgroundColor: '#070c16', border: '1px solid #1e293b' }}>
              <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>Incident History (H)</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: (result?.breakdown?.history_score ?? 0) > 0 ? '#f59e0b' : '#94a3b8', marginTop: 4, fontFamily: 'JetBrains Mono, monospace' }}>
                {result?.breakdown?.history_score !== undefined ? Number(result.breakdown.history_score).toFixed(1) : '--'}
              </div>
              <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>Weight: 0.20</div>
              <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>
                {result?.incident_count_30d !== undefined ? `${result.incident_count_30d} incidents in 30d` : 'Clean Memory'}
              </div>
            </div>
          </div>

          {/* Upstream Impact Hierarchy & Deductions */}
          <div style={{ padding: '20px', borderRadius: 12, backgroundColor: '#0a101d', border: '1px solid #1e293b', display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Layers size={16} color="#38bdf8" />
              <span>Upstream Dependency Hierarchy (Discovered Callers)</span>
            </div>

            {result?.blast_details && result.blast_details.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
                {result.blast_details.map((caller: any, idx: number) => (
                  <div
                    key={idx}
                    style={{
                      padding: '10px 14px',
                      borderRadius: 8,
                      backgroundColor: '#070c16',
                      border: '1px solid #1e293b',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 4,
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#f97316' }} />
                      <span>{caller.node}</span>
                    </div>
                    <div style={{ fontSize: 10, color: '#64748b' }}>
                      Distance: <span style={{ color: '#38bdf8' }}>{caller.hops} hop(s)</span> • Attenuation: <span style={{ color: '#94a3b8' }}>{(caller.impact_weight * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '16px', color: '#64748b', fontSize: 12, textAlign: 'center', backgroundColor: '#070c16', borderRadius: 8 }}>
                No upstream callers discovered for {selectedService}. Service is an ingress leaf or isolated component.
              </div>
            )}

            {/* Explanation Deductions */}
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6 }}>
                Evidence & Explanations:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {(result?.explanation || ['Run risk analysis to compute evidence deductions.']).map((exp: string, idx: number) => (
                  <div key={idx} style={{ padding: '8px 12px', borderRadius: 6, backgroundColor: '#070c16', border: '1px solid #1e293b', fontSize: 11, color: '#94a3b8' }}>
                    • {exp}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
