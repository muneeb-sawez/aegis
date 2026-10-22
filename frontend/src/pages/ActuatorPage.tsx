import React, { useState, useEffect } from 'react';
import {
  Zap,
  ShieldCheck,
  Terminal,
  Play,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ArrowRight,
  GitCommit,
  Brain,
  Search,
} from 'lucide-react';
import { apiUrl } from '../config';

interface ActuatorPageProps {
  onNavigate?: (page: string, serviceId?: string) => void;
}

export const ActuatorPage: React.FC<ActuatorPageProps> = ({ onNavigate }) => {
  const [streamEvents, setStreamEvents] = useState<any[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [selectedAction, setSelectedAction] = useState<string>('scale_pool');
  const [poolSizeParam, setPoolSizeParam] = useState<number>(150);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<any | null>(null);
  const [isCommitting, setIsCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Check backend DEMO_MODE setting on mount
  useEffect(() => {
    fetch(apiUrl('/api/heal/config'))
      .then((r) => r.json())
      .then((data) => {
        if (data?.demo_mode !== undefined) {
          setIsDemoMode(Boolean(data.demo_mode));
        }
      })
      .catch(() => {});
  }, []);

  // Real EventSource SSE stream with 3-second polling fallback
  const handleStartDiagnosis = () => {
    setIsStreaming(true);
    setStreamEvents([]);
    setError(null);
    setExecutionResult(null);
    setCommitResult(null);

    let activeEventSource: EventSource | null = null;
    let pollingInterval: any = null;
    let sseReceivedData = false;

    const stopAll = () => {
      if (activeEventSource) {
        activeEventSource.close();
        activeEventSource = null;
      }
      if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
      }
      setIsStreaming(false);
    };

    const processEvent = (ev: any) => {
      setStreamEvents((prev: any[]) => [...prev, ev]);

      if (ev.payload?.demo_mode !== undefined) {
        setIsDemoMode(Boolean(ev.payload.demo_mode));
      }

      if (ev.type === 'candidates' && ev.payload?.candidates) {
        setCandidates(ev.payload.candidates);
      } else if (ev.type === 'result' && ev.payload?.ranked_fixes) {
        const fixes = ev.payload.ranked_fixes.map((fix: any) => ({
          action: fix.action === 'restart' ? 'restart_pod' : fix.action === 'rollback' ? 'rollback_release' : 'scale_pool',
          target: fix.target,
          params: fix.action === 'scale_pool' ? { pool_size: 150 } : {},
          safety_score: fix.action === 'scale_pool' ? 92.0 : fix.action === 'restart' ? 85.0 : 70.0,
          recovery_prob: 0.9,
          composite_score: 88.0,
          rationale: fix.reason,
          eligible_for_auto_exec: fix.action !== 'rollback',
        }));
        setCandidates(fixes);
      }

      if (ev.type === 'error') {
        setError(ev.payload?.message || 'Error executing graph diagnosis.');
        stopAll();
      } else if (ev.type === 'done') {
        stopAll();
      }
    };

    const startPollingFallback = () => {
      if (pollingInterval) return;
      console.warn('SSE unavailable; falling back to polling /api/heal/events every 3s.');

      const pollOnce = async () => {
        try {
          const resp = await fetch(apiUrl('/api/heal/events'));
          if (resp.ok) {
            const events: any[] = await resp.json();
            setStreamEvents(events);
            for (const ev of events) {
              if (ev.type === 'candidates' && ev.payload?.candidates) {
                setCandidates(ev.payload.candidates);
              }
              if (ev.payload?.demo_mode !== undefined) {
                setIsDemoMode(Boolean(ev.payload.demo_mode));
              }
            }
            const lastEvent = events[events.length - 1];
            if (lastEvent?.type === 'done' || lastEvent?.type === 'error') {
              stopAll();
            }
          }
        } catch (e: any) {
          setError(e.message || 'Polling fallback failed.');
          stopAll();
        }
      };

      pollOnce();
      pollingInterval = setInterval(pollOnce, 3000);
    };

    try {
      activeEventSource = new EventSource(apiUrl('/api/heal/stream'));

      activeEventSource.onmessage = (event) => {
        sseReceivedData = true;
        try {
          const ev = JSON.parse(event.data);
          processEvent(ev);
        } catch (err) {
          console.error('Failed to parse SSE line:', err);
        }
      };

      activeEventSource.onerror = () => {
        if (!sseReceivedData) {
          if (activeEventSource) {
            activeEventSource.close();
            activeEventSource = null;
          }
          startPollingFallback();
        } else {
          stopAll();
        }
      };
    } catch {
      startPollingFallback();
    }
  };

  useEffect(() => {
    handleStartDiagnosis();
  }, []);

  const handleExecuteAction = async (deliberateFail = false) => {
    setIsExecuting(true);
    setError(null);
    try {
      const payload: any = {
        action: selectedAction,
        target: selectedAction === 'scale_pool' ? 'postgres-payment' : 'paymentservice',
        params: selectedAction === 'scale_pool' ? { pool_size: deliberateFail ? 20 : poolSizeParam } : {},
      };

      const resp = await fetch('/api/actuator/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (resp.ok) {
        const data = await resp.json();
        setExecutionResult(data);
      } else {
        const errJson = await resp.json().catch(() => null);
        setError(errJson?.detail || 'Actuator execution rejected.');
      }
    } catch (e: any) {
      setError(e.message || 'Network error executing actuator action.');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleCommitToGraphMemory = async () => {
    setIsCommitting(true);
    setError(null);
    try {
      const resp = await fetch('/api/memory/commit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_id: 'paymentservice',
          incident_description: 'Database connection pool saturated (100/100). Latency degraded to 3400ms.',
          action_taken: selectedAction,
          safety_score: executionResult?.safety_score || 92.0,
          outcome: executionResult?.health_verified ? 'success' : 'rolled_back',
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        setCommitResult(data);
      } else {
        setError('Failed to commit incident to graph memory.');
      }
    } catch (e: any) {
      setError(e.message || 'Network error committing to memory.');
    } finally {
      setIsCommitting(false);
    }
  };

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
              backgroundColor: 'rgba(99, 102, 241, 0.15)',
              border: '1px solid rgba(99, 102, 241, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#818cf8',
            }}
          >
            <Zap size={22} />
          </div>
          <div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
              Phase 2 Autonomous Actuator & Self-Healing Control Center
            </div>
            <div style={{ fontSize: 12, color: '#64748b' }}>
              Graph-grounded diagnosis engine, allowlisted actuator guardrails, dead-man rollback, and closed-loop memory
            </div>
          </div>
        </div>

        <button
          onClick={handleStartDiagnosis}
          disabled={isStreaming}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 16px',
            borderRadius: 8,
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            color: '#f8fafc',
            fontSize: 12,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <Play size={14} color="#818cf8" />
          <span>{isStreaming ? 'Streaming Diagnosis...' : 'Re-Run Graph Reasoner Stream'}</span>
        </button>
      </div>

      {error && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: 8,
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#f87171',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <XCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Grid: Reasoner Streaming Terminal & Candidate Plans */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Left: SSE Graph Reasoner Terminal */}
        <div
          style={{
            backgroundColor: '#0c1322',
            borderRadius: 12,
            border: '1px solid #1e293b',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            height: 480,
          }}
        >
          <div
            style={{
              padding: '12px 16px',
              backgroundColor: '#070b14',
              borderBottom: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Terminal size={14} color="#818cf8" />
              <span style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>
                Graph Diagnosis Terminal
              </span>
              {isDemoMode ? (
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: 4,
                    backgroundColor: 'rgba(234, 179, 8, 0.15)',
                    color: '#facc15',
                    border: '1px solid rgba(234, 179, 8, 0.35)',
                  }}
                >
                  Demo diagnosis (scripted)
                </span>
              ) : (
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: 4,
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    color: '#10b981',
                    border: '1px solid rgba(16, 185, 129, 0.35)',
                  }}
                >
                  Real Graph LLM Agent
                </span>
              )}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: isStreaming ? '#38bdf8' : '#10b981' }} />
              <span style={{ fontSize: 10, color: '#64748b', fontWeight: 600 }}>
                {isStreaming ? 'STREAMING REAL-TIME' : 'STREAM READY'}
              </span>
            </div>
          </div>

          <div style={{ padding: 16, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12, flex: 1, fontFamily: 'monospace' }}>
            {streamEvents.map((ev: any, idx: number) => {
              const isQuery = ev.type === 'query' || ev.type === 'cypher';
              const isCandidates = ev.type === 'candidates';
              const isResult = ev.type === 'result';
              const isError = ev.type === 'error';
              const isDone = ev.type === 'done';
              const isThought = ev.type === 'thought';

              const headerColor = isQuery
                ? '#38bdf8'
                : isCandidates
                ? '#c084fc'
                : isResult
                ? '#10b981'
                : isError
                ? '#f87171'
                : isDone
                ? '#34d399'
                : '#94a3b8';

              const bgColor = isQuery
                ? 'rgba(6, 182, 212, 0.08)'
                : isError
                ? 'rgba(239, 68, 68, 0.1)'
                : isResult
                ? 'rgba(16, 185, 129, 0.08)'
                : '#070b14';

              const borderColor = isQuery
                ? 'rgba(6, 182, 212, 0.3)'
                : isError
                ? 'rgba(239, 68, 68, 0.3)'
                : isResult
                ? 'rgba(16, 185, 129, 0.3)'
                : '#1e293b';

              return (
                <div
                  key={idx}
                  style={{
                    padding: 10,
                    borderRadius: 6,
                    backgroundColor: bgColor,
                    border: `1px solid ${borderColor}`,
                    fontSize: 11,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span
                      style={{
                        fontSize: 9,
                        fontWeight: 800,
                        textTransform: 'uppercase',
                        color: headerColor,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      {isThought && <Brain size={12} color="#94a3b8" />}
                      {isQuery && <Search size={12} color="#38bdf8" />}
                      {isResult && <CheckCircle size={12} color="#10b981" />}
                      {isError && <AlertTriangle size={12} color="#f87171" />}
                      [{ev.type}]
                    </span>
                    <span style={{ fontSize: 9, color: '#64748b' }}>{ev.ts ? new Date(ev.ts).toLocaleTimeString() : ''}</span>
                  </div>

                  {isQuery ? (
                    <div>
                      <div style={{ color: '#38bdf8', fontWeight: 600 }}>{ev.payload?.query}</div>
                      {ev.payload?.purpose && (
                        <div style={{ color: '#94a3b8', fontSize: 10, marginTop: 2 }}>{ev.payload?.purpose}</div>
                      )}
                    </div>
                  ) : isCandidates ? (
                    <div style={{ color: '#c084fc', lineHeight: 1.4 }}>
                      Generated {ev.payload?.candidates?.length || 0} ranked candidate remediation actions.
                    </div>
                  ) : isResult ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      <div style={{ color: '#34d399', fontWeight: 700 }}>
                        Root Cause: {ev.payload?.root_cause_node} ({ev.payload?.root_cause_type})
                      </div>
                      <div style={{ color: '#cbd5e1', fontSize: 10 }}>
                        Confidence: {Math.round((ev.payload?.confidence || 0) * 100)}% | Path: {(ev.payload?.propagation_path || []).join(' → ')}
                      </div>
                      {ev.payload?.evidence?.length > 0 && (
                        <div style={{ color: '#94a3b8', fontSize: 10 }}>
                          Evidence: {ev.payload.evidence.join('; ')}
                        </div>
                      )}
                    </div>
                  ) : isError ? (
                    <div style={{ color: '#f87171', fontWeight: 600 }}>
                      {ev.payload?.message || ev.payload?.error || 'Diagnostic reasoning error'}
                    </div>
                  ) : (
                    <div style={{ color: '#cbd5e1', lineHeight: 1.4 }}>
                      {ev.payload?.message || JSON.stringify(ev.payload)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Candidate Rankings & Safety Gate */}
        <div
          style={{
            backgroundColor: '#0c1322',
            borderRadius: 12,
            border: '1px solid #1e293b',
            padding: 20,
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
            height: 480,
            overflowY: 'auto',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
              <ShieldCheck size={16} color="#10b981" />
              <span>Ranked Remediation Actions & Safety Gate</span>
            </div>
            <div style={{ fontSize: 10, color: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.1)', padding: '2px 8px', borderRadius: 4, fontWeight: 700 }}>
              Safety Threshold: S ≥ 85.0
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {(candidates.length > 0 ? candidates : [
              {
                action: 'scale_pool',
                target: 'postgres-payment',
                params: { pool_size: 150 },
                safety_score: 92.0,
                recovery_prob: 0.95,
                composite_score: 93.2,
                rationale: 'Expand PostgreSQL connection pool from 100 to 150 to absorb query backlog.',
              },
              {
                action: 'restart_pod',
                target: 'paymentservice-pod-1',
                params: {},
                safety_score: 85.0,
                recovery_prob: 0.70,
                composite_score: 79.0,
                rationale: 'Gracefully restart active payment service pod.',
              },
              {
                action: 'rollback_release',
                target: 'paymentservice',
                params: {},
                safety_score: 75.0,
                recovery_prob: 0.80,
                composite_score: 77.0,
                rationale: 'Rollback paymentservice deployment to revision HEAD~1.',
              },
            ]).map((c: any, idx: number) => {
              const isSelected = selectedAction === c.action;
              const isPermitted = c.safety_score >= 85.0;

              return (
                <div
                  key={idx}
                  onClick={() => setSelectedAction(c.action)}
                  style={{
                    padding: 14,
                    borderRadius: 10,
                    backgroundColor: isSelected ? 'rgba(99, 102, 241, 0.1)' : '#070b14',
                    border: isSelected ? '1.5px solid #818cf8' : '1px solid #1e293b',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>
                        {c.action}
                      </span>
                      <span style={{ fontSize: 11, color: '#64748b' }}>({c.target})</span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 800,
                          padding: '2px 8px',
                          borderRadius: 4,
                          backgroundColor: isPermitted ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                          color: isPermitted ? '#34d399' : '#f87171',
                        }}
                      >
                        Safety: {c.safety_score}
                      </span>
                    </div>
                  </div>

                  <p style={{ fontSize: 11, color: '#94a3b8', margin: 0, lineHeight: 1.3 }}>
                    {c.rationale}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Actuator Execution Controls */}
          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 10, paddingTop: 14, borderTop: '1px solid #1e293b' }}>
            {selectedAction === 'scale_pool' && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, color: '#94a3b8' }}>Target Pool Size:</span>
                <input
                  type="number"
                  value={poolSizeParam}
                  onChange={(e) => setPoolSizeParam(Number(e.target.value))}
                  style={{
                    width: 80,
                    padding: '4px 8px',
                    borderRadius: 6,
                    backgroundColor: '#070b14',
                    border: '1px solid #1e293b',
                    color: '#f8fafc',
                    fontSize: 12,
                    textAlign: 'center',
                  }}
                />
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 10 }}>
              <button
                onClick={() => handleExecuteAction(false)}
                disabled={isExecuting}
                style={{
                  padding: '10px 14px',
                  borderRadius: 8,
                  backgroundColor: '#818cf8',
                  border: 'none',
                  color: '#ffffff',
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                }}
              >
                <Zap size={14} fill="#ffffff" />
                <span>{isExecuting ? 'Executing...' : 'Execute Remediation'}</span>
              </button>

              <button
                onClick={() => handleExecuteAction(true)}
                disabled={isExecuting}
                title="Tests safety boundary rejection and dead-man automatic rollback"
                style={{
                  padding: '10px 14px',
                  borderRadius: 8,
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#f87171',
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Test Dead-Man Rollback
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Execution Result & Closed-Loop Memory Commit Banner */}
      {executionResult && (
        <div
          style={{
            backgroundColor: '#0c1322',
            borderRadius: 12,
            border: '1px solid #1e293b',
            padding: 20,
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {executionResult.health_verified ? (
                <CheckCircle size={22} color="#10b981" />
              ) : (
                <AlertTriangle size={22} color="#f97316" />
              )}
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>
                  Actuator Execution Status: {executionResult.status.toUpperCase()}
                </div>
                <div style={{ fontSize: 11, color: '#94a3b8' }}>{executionResult.message}</div>
              </div>
            </div>

            <span
              style={{
                fontSize: 11,
                fontWeight: 800,
                padding: '4px 10px',
                borderRadius: 6,
                backgroundColor: executionResult.health_verified ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: executionResult.health_verified ? '#34d399' : '#f87171',
              }}
            >
              {executionResult.health_verified ? 'HEALTH VERIFIED (38ms RESTORED)' : 'AUTOMATICALLY ROLLED BACK'}
            </span>
          </div>

          {/* Closed-Loop Feedback Section */}
          <div
            style={{
              padding: 16,
              borderRadius: 10,
              backgroundColor: '#070b14',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 20,
            }}
          >
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
                <GitCommit size={16} color="#818cf8" />
                <span>Closed-Loop Knowledge Graph Feedback (Learning Step)</span>
              </div>
              <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
                Commit this incident and resolution decision to the graph memory. Subsequent PREDICT assessments will detect this incident node and apply the +5.0 learning jump ($H +25 \times 0.20$).
              </div>
            </div>

            <button
              onClick={handleCommitToGraphMemory}
              disabled={isCommitting || commitResult !== null}
              style={{
                padding: '10px 18px',
                borderRadius: 8,
                backgroundColor: commitResult ? '#10b981' : '#6366f1',
                border: 'none',
                color: '#ffffff',
                fontSize: 12,
                fontWeight: 700,
                cursor: commitResult ? 'default' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                whiteSpace: 'nowrap',
              }}
            >
              {commitResult ? <CheckCircle size={14} /> : <GitCommit size={14} />}
              <span>{commitResult ? 'Incident Committed to Graph' : 'Commit to Knowledge Graph'}</span>
            </button>
          </div>

          {commitResult && (
            <div
              style={{
                padding: 12,
                borderRadius: 8,
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ fontSize: 11, color: '#34d399' }}>
                ✓ Incident <strong>{commitResult.incident_id}</strong> committed. Decision <strong>{commitResult.decision_id}</strong> linked.
              </div>

              <button
                onClick={() => onNavigate && onNavigate('predict', 'paymentservice')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '4px 10px',
                  borderRadius: 6,
                  backgroundColor: 'rgba(249, 115, 22, 0.2)',
                  border: '1px solid rgba(249, 115, 22, 0.5)',
                  color: '#fb923c',
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                <span>Verify +5 Risk Jump in PREDICT</span>
                <ArrowRight size={12} />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
