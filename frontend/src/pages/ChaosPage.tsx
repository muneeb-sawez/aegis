import React, { useState, useEffect } from 'react';
import {
  Flame,
  AlertTriangle,
  Play,
  RotateCcw,
  CheckCircle,
  Database,
  Server,
  Zap,
  Activity,
  ArrowRight,
  Clock,
  Sliders,
  TrendingUp,
} from 'lucide-react';
import { getActiveProjectId, apiUrl, getAuthHeaders } from '../config';

interface ChaosPageProps {
  onNavigate?: (page: string) => void;
  initialService?: string;
}

export const ChaosPage: React.FC<ChaosPageProps> = ({ onNavigate, initialService }) => {
  const [services, setServices] = useState<any[]>([]);
  const [targetService, setTargetService] = useState(initialService || 'paymentservice');
  const [faultType, setFaultType] = useState('pool_exhaustion');
  const [isLoading, setIsLoading] = useState(false);
  const [activeFault, setActiveFault] = useState<any | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchServices = async () => {
      try {
        const pid = getActiveProjectId();
        const resp = await fetch(apiUrl(`/api/predict/services?project_id=${encodeURIComponent(pid)}`));
        if (resp.ok) {
          const data = await resp.json();
          setServices(data);
          if (data.length > 0 && !data.some((s: any) => s.id === targetService)) {
            setTargetService(data[0].id);
          }
        }
      } catch (e) {
        console.error('Fetch services error:', e);
      }
    };
    fetchServices();

    const onProjectChange = () => fetchServices();
    window.addEventListener('aegis_project_changed', onProjectChange);
    return () => window.removeEventListener('aegis_project_changed', onProjectChange);
  }, []);

  const handleInjectFault = async () => {
    setIsLoading(true);
    setToastMessage(null);
    try {
      const pid = getActiveProjectId();
      const resp = await fetch(apiUrl('/api/chaos/inject'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders(pid) },
        body: JSON.stringify({
          fault_id: faultType,
          target_service: targetService,
          duration_seconds: 300,
          project_id: pid,
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        setActiveFault(data);
        const record = {
          id: `chaos-${Date.now()}`,
          ts: new Date().toLocaleTimeString(),
          fault: faultType,
          target: targetService,
          altered: data.altered_nodes || [targetService],
          status: 'Active',
          p99: faultType === 'pool_exhaustion' ? '3,400ms' : faultType === 'pod_crash' ? '1,800ms' : '2,200ms',
          errorRate: faultType === 'pool_exhaustion' ? '42%' : faultType === 'pod_crash' ? '25%' : '15%',
        };
        setHistory((prev) => [record, ...prev]);
        setToastMessage(`Fault '${faultType}' successfully injected on ${targetService}.`);
      }
    } catch (e) {
      console.error('Inject fault error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearFaults = async () => {
    setIsLoading(true);
    try {
      await fetch('/api/reset', { method: 'POST' });
      setActiveFault(null);
      setToastMessage('All chaos faults cleared. Graph topology and telemetry restored to healthy baseline.');
    } catch (e) {
      console.error('Clear fault error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const faultCatalog = [
    {
      id: 'pool_exhaustion',
      title: 'PostgreSQL Pool Saturation',
      desc: 'Simulates DB connection exhaustion (100/100 conn). Spikes p99 latency to 3,400ms and generates error bursts.',
      badge: 'DATABASE FAULT',
      icon: Database,
      color: '#f97316',
    },
    {
      id: 'pod_crash',
      title: 'CrashLoopBackOff Pod Failure',
      desc: 'Kills target pod container. Triggers K8s CrashLoopBackOff with restart increments and 25% request drops.',
      badge: 'CONTAINER FAULT',
      icon: Server,
      color: '#ef4444',
    },
    {
      id: 'latency_spike',
      title: 'Cross-AZ Latency Degradation',
      desc: 'Injects synthetic 2,200ms gRPC round-trip transit delay into upstream callers without outright failing requests.',
      badge: 'NETWORK FAULT',
      icon: TrendingUp,
      color: '#eab308',
    },
    {
      id: 'timeout',
      title: 'Ingress 504 Gateway Timeout',
      desc: 'Forces gateway edge timeout on incoming HTTP sessions, breaking client checkouts.',
      badge: 'GATEWAY FAULT',
      icon: AlertTriangle,
      color: '#a855f7',
    },
  ];

  return (
    <div style={{ padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: 24, height: '100%', overflowY: 'auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 38,
              height: 38,
              borderRadius: 10,
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ef4444',
            }}
          >
            <Flame size={22} />
          </div>
          <div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
              Phase 2 Chaos Engineering Studio
            </div>
            <div style={{ fontSize: 12, color: '#64748b' }}>
              Deterministic fault injection, blast radius emulation, and resiliency boundary testing
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={handleClearFaults}
            disabled={isLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 14px',
              borderRadius: 8,
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              color: '#94a3b8',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={14} />
            <span>Clear Faults & Restore Baseline</span>
          </button>

          {activeFault && (
            <button
              onClick={() => onNavigate && onNavigate('actuator')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 16px',
                borderRadius: 8,
                backgroundColor: 'rgba(99, 102, 241, 0.2)',
                border: '1px solid rgba(99, 102, 241, 0.5)',
                color: '#818cf8',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              <Zap size={14} />
              <span>Diagnose in Self-Healing Actuator</span>
              <ArrowRight size={14} />
            </button>
          )}
        </div>
      </div>

      {toastMessage && (
        <div
          style={{
            padding: '10px 16px',
            borderRadius: 8,
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            color: '#34d399',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <CheckCircle size={16} />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Main Grid: Fault Config & Live Telemetry Delta */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 24 }}>
        {/* Left: Fault Configuration Panel */}
        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 20, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sliders size={16} color="#38bdf8" />
            <span>Select Target & Failure Scenario</span>
          </div>

          {/* Service Selector */}
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: 6 }}>
              Target Microservice
            </label>
            <select
              value={targetService}
              onChange={(e) => setTargetService(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: 8,
                backgroundColor: '#070b14',
                border: '1px solid #1e293b',
                color: '#f8fafc',
                fontSize: 13,
                outline: 'none',
              }}
            >
              {services.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.id} ({s.layer || 'Service'})
                </option>
              ))}
            </select>
          </div>

          {/* Fault Cards Grid */}
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: 8 }}>
              Chaos Experiment Type
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {faultCatalog.map((fc) => {
                const Icon = fc.icon;
                const isSelected = faultType === fc.id;
                return (
                  <div
                    key={fc.id}
                    onClick={() => setFaultType(fc.id)}
                    style={{
                      padding: 14,
                      borderRadius: 10,
                      backgroundColor: isSelected ? 'rgba(239, 68, 68, 0.1)' : '#070b14',
                      border: isSelected ? '1.5px solid #ef4444' : '1px solid #1e293b',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 6,
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Icon size={16} color={fc.color} />
                        <span style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>{fc.title}</span>
                      </div>
                      <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, backgroundColor: '#1e293b', color: fc.color }}>
                        {fc.badge}
                      </span>
                    </div>
                    <p style={{ fontSize: 11, color: '#64748b', margin: 0, lineHeight: 1.3 }}>
                      {fc.desc}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Launch Button */}
          <button
            onClick={handleInjectFault}
            disabled={isLoading}
            style={{
              padding: '12px 20px',
              borderRadius: 8,
              backgroundColor: '#ef4444',
              border: 'none',
              color: '#ffffff',
              fontSize: 13,
              fontWeight: 800,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 10,
              boxShadow: '0 0 20px rgba(239, 68, 68, 0.4)',
              marginTop: 4,
            }}
          >
            <Play size={16} fill="#ffffff" />
            <span>{isLoading ? 'Injecting Chaos...' : 'Inject Chaos Experiment Into Active Graph'}</span>
          </button>
        </div>

        {/* Right: Active Anomaly & Blast Radius Status */}
        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Activity size={16} color="#ef4444" />
            <span>Active Anomaly & Blast Radius Impact</span>
          </div>

          {activeFault ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div
                style={{
                  padding: 14,
                  borderRadius: 10,
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.4)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 12, fontWeight: 800, color: '#f87171' }}>
                    ACTIVE ANOMALY: {activeFault.fault_id.toUpperCase()}
                  </span>
                  <span style={{ fontSize: 10, fontWeight: 700, color: '#ef4444', backgroundColor: 'rgba(239, 68, 68, 0.2)', padding: '2px 8px', borderRadius: 4 }}>
                    DEGRADED
                  </span>
                </div>
                <div style={{ fontSize: 11, color: '#cbd5e1', lineHeight: 1.4 }}>
                  {activeFault.message}
                </div>
              </div>

              {/* Telemetry Metric Deltas */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div style={{ backgroundColor: '#070b14', padding: 12, borderRadius: 8, border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>p99 Latency</div>
                  <div style={{ fontSize: 18, fontWeight: 800, color: '#ef4444', marginTop: 4 }}>
                    {faultType === 'pool_exhaustion' ? '3,400ms' : '2,200ms'}
                  </div>
                  <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>Baseline: 38ms (90x spike)</div>
                </div>

                <div style={{ backgroundColor: '#070b14', padding: 12, borderRadius: 8, border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Error Rate</div>
                  <div style={{ fontSize: 18, fontWeight: 800, color: '#f97316', marginTop: 4 }}>
                    {faultType === 'pool_exhaustion' ? '42.0%' : '25.0%'}
                  </div>
                  <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>Baseline: 0.01% (4200x increase)</div>
                </div>
              </div>

              {/* Altered Nodes List */}
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', marginBottom: 6 }}>
                  Directly Altered Graph Nodes:
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(activeFault.altered_nodes || [targetService]).map((nodeId: string) => (
                    <span
                      key={nodeId}
                      style={{
                        padding: '4px 10px',
                        borderRadius: 6,
                        backgroundColor: '#1e293b',
                        border: '1px solid #ef4444',
                        color: '#f8fafc',
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    >
                      {nodeId}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 30,
                textAlign: 'center',
                color: '#64748b',
                gap: 8,
              }}
            >
              <CheckCircle size={32} color="#10b981" />
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>Fleet Baseline Operating Normally</div>
              <div style={{ fontSize: 11 }}>No active chaos fault injected. Select a target service to begin resiliency testing.</div>
            </div>
          )}
        </div>
      </div>

      {/* History Log */}
      <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Clock size={16} color="#64748b" />
          <span>Chaos Experiment Run Log</span>
        </div>

        {history.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {history.map((h) => (
              <div
                key={h.id}
                style={{
                  padding: '10px 14px',
                  borderRadius: 8,
                  backgroundColor: '#070b14',
                  border: '1px solid #1e293b',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: 12,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ color: '#64748b', fontSize: 11 }}>{h.ts}</span>
                  <span style={{ fontWeight: 700, color: '#f8fafc' }}>{h.target}</span>
                  <span style={{ color: '#ef4444', fontWeight: 600 }}>{h.fault}</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <span style={{ color: '#cbd5e1' }}>p99: <strong style={{ color: '#ef4444' }}>{h.p99}</strong></span>
                  <span style={{ color: '#cbd5e1' }}>Errors: <strong style={{ color: '#f97316' }}>{h.errorRate}</strong></span>
                  <span style={{ padding: '2px 8px', borderRadius: 4, backgroundColor: 'rgba(239, 68, 68, 0.2)', color: '#f87171', fontSize: 10, fontWeight: 700 }}>
                    {h.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ fontSize: 12, color: '#64748b', textAlign: 'center', padding: '16px 0' }}>
            No chaos experiments logged in this session yet.
          </div>
        )}
      </div>
    </div>
  );
};
