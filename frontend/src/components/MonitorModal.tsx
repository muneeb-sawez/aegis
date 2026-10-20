import React, { useState, useEffect } from 'react';
import {
  X,
  Activity,
  RefreshCw,
  Flame,
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  AlertOctagon,
  HelpCircle,
  Radio,
  Plus,
  Trash2,
} from 'lucide-react';

interface HealthRecord {
  service_id: string;
  endpoint_url: string | null;
  status: 'healthy' | 'degraded' | 'unavailable' | 'unhealthy' | 'unconfigured' | 'pending' | 'unknown';
  http_status: number | null;
  response_time_ms: number | null;
  last_check_time: string;
  error_message: string | null;
  consecutive_failures: number;
  failure_threshold: number;
  data_source: 'observed' | 'simulated' | 'unconfigured';
  is_simulated_fault: boolean;
  fault_type: string | null;
  alert_active: boolean;
  active_incident_id: string | null;
  recovery_time: string | null;
}

interface MonitorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAlertStatusChange?: (alertCount: number) => void;
}

export const MonitorModal: React.FC<MonitorModalProps> = ({ isOpen, onClose, onAlertStatusChange }) => {
  const [healthRecords, setHealthRecords] = useState<HealthRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedService, setSelectedService] = useState('paymentservice');
  const [faultType, setFaultType] = useState('timeout');
  const [configService, setConfigService] = useState('frontend');
  const [configUrl, setConfigUrl] = useState('http://127.0.0.1:8000/health');
  const [configError, setConfigError] = useState<string | null>(null);
  const [configSuccess, setConfigSuccess] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchStatus = async () => {
    try {
      const resp = await fetch('/api/monitor/status');
      if (resp.ok) {
        const data: HealthRecord[] = await resp.json();
        setHealthRecords(data);
        const alertCount = data.filter((r) => r.alert_active || r.status === 'unavailable').length;
        if (onAlertStatusChange) {
          onAlertStatusChange(alertCount);
        }
      }
    } catch (e) {
      console.error('Fetch status error:', e);
    }
  };

  const handleCheckNow = async () => {
    setIsLoading(true);
    try {
      const resp = await fetch('/api/monitor/check-now', { method: 'POST' });
      if (resp.ok) {
        const data: HealthRecord[] = await resp.json();
        setHealthRecords(data);
        const alertCount = data.filter((r) => r.alert_active || r.status === 'unavailable').length;
        if (onAlertStatusChange) {
          onAlertStatusChange(alertCount);
        }
      }
    } catch (e) {
      console.error('Check now error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApplyFault = async () => {
    try {
      await fetch('/api/monitor/fault', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_id: selectedService,
          fault_type: faultType,
          consecutive_failures: faultType === 'elevated_latency' ? 1 : 2,
          latency_ms: 3500.0,
        }),
      });
      await fetchStatus();
    } catch (e) {
      console.error('Apply fault error:', e);
    }
  };

  const handleClearFault = async () => {
    try {
      await fetch('/api/monitor/fault', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_id: selectedService,
          fault_type: 'clear',
        }),
      });
      await fetchStatus();
    } catch (e) {
      console.error('Clear fault error:', e);
    }
  };

  const handleConfigureEndpoint = async () => {
    setConfigError(null);
    setConfigSuccess(null);
    try {
      const resp = await fetch('/api/monitor/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_id: configService,
          endpoint_url: configUrl,
        }),
      });
      if (resp.ok) {
        setConfigSuccess(`Configured probe endpoint for '${configService}'.`);
        await handleCheckNow();
      } else {
        const err = await resp.json();
        setConfigError(err.detail || 'Failed to configure endpoint.');
      }
    } catch (e: any) {
      setConfigError(e.message || 'Network error.');
    }
  };

  const handleUnconfigureEndpoint = async (serviceId: string) => {
    try {
      await fetch(`/api/monitor/unconfigure?service_id=${serviceId}`, { method: 'POST' });
      await fetchStatus();
    } catch (e) {
      console.error('Unconfigure error:', e);
    }
  };

  // Safe periodic polling while modal is open (Directive §3.C: 4-second refresh cycle)
  useEffect(() => {
    if (!isOpen) return;

    fetchStatus();

    if (!autoRefresh) return;
    const intervalId = setInterval(() => {
      fetchStatus();
    }, 4000);

    return () => clearInterval(intervalId);
  }, [isOpen, autoRefresh]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
      }}
    >
      <div
        style={{
          width: 980,
          height: '88vh',
          maxHeight: '88vh',
          backgroundColor: '#0a101d',
          border: '1px solid #1e293b',
          borderRadius: 14,
          boxShadow: '0 25px 60px rgba(0, 0, 0, 0.9)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #1e293b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Activity size={20} color="#10b981" />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 15, fontWeight: 700, color: '#f8fafc' }}>
                  MONITOR — Periodic Health Verification & Fault Simulation
                </span>
                <span
                  style={{
                    fontSize: 9,
                    fontWeight: 700,
                    padding: '2px 6px',
                    borderRadius: 4,
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    color: '#34d399',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <Radio size={9} className="animate-pulse" />
                  {autoRefresh ? 'POLLING (4s)' : 'PAUSED'}
                </span>
              </div>
              <div style={{ fontSize: 11, color: '#64748b' }}>
                Continuous asynchronous HTTP health checks with SSRF protection, consecutive failure thresholds, and automatic incident writeback
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              style={{
                padding: '5px 10px',
                borderRadius: 6,
                backgroundColor: autoRefresh ? '#0f172a' : '#1e293b',
                border: '1px solid #334155',
                color: autoRefresh ? '#38bdf8' : '#94a3b8',
                fontSize: 11,
                cursor: 'pointer',
              }}
            >
              {autoRefresh ? 'Pause Polling' : 'Resume Polling'}
            </button>
            <button
              onClick={handleCheckNow}
              disabled={isLoading}
              style={{
                padding: '6px 12px',
                borderRadius: 6,
                backgroundColor: '#0284c7',
                border: 'none',
                color: '#fff',
                fontSize: 11,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                cursor: 'pointer',
              }}
            >
              <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
              <span>{isLoading ? 'Checking...' : 'Check Health Now'}</span>
            </button>
            <button
              onClick={onClose}
              style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '16px 20px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Fault Simulation Controls */}
          <div
            style={{
              flexShrink: 0,
              padding: '14px 16px',
              borderRadius: 10,
              backgroundColor: '#070c16',
              border: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Flame size={16} color="#ef4444" />
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>Deterministic Fault Simulator</div>
                <div style={{ fontSize: 10, color: '#64748b' }}>Simulate timeout, latency, or threshold failures (simulated / emulator time)</div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <select
                value={selectedService}
                onChange={(e) => setSelectedService(e.target.value)}
                style={{
                  padding: '6px 10px',
                  borderRadius: 6,
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  color: '#f8fafc',
                  fontSize: 11,
                  outline: 'none',
                }}
              >
                {healthRecords.map((r) => (
                  <option key={r.service_id} value={r.service_id}>
                    {r.service_id}
                  </option>
                ))}
              </select>

              <select
                value={faultType}
                onChange={(e) => setFaultType(e.target.value)}
                style={{
                  padding: '6px 10px',
                  borderRadius: 6,
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  color: '#f8fafc',
                  fontSize: 11,
                  outline: 'none',
                }}
              >
                <option value="timeout">Simulated Timeout (504 Gateway Timeout)</option>
                <option value="elevated_latency">Elevated Latency Spike (3500ms)</option>
                <option value="consecutive_failure">Consecutive 500 Failures (Threshold Breach)</option>
              </select>

              <button
                onClick={handleApplyFault}
                style={{
                  padding: '6px 12px',
                  borderRadius: 6,
                  backgroundColor: 'rgba(239, 68, 68, 0.2)',
                  border: '1px solid #ef4444',
                  color: '#fca5a5',
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                Inject Fault
              </button>

              <button
                onClick={handleClearFault}
                style={{
                  padding: '6px 12px',
                  borderRadius: 6,
                  backgroundColor: 'rgba(16, 185, 129, 0.15)',
                  border: '1px solid #10b981',
                  color: '#34d399',
                  fontSize: 11,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
                title="Clear fault condition and verify health recovery"
              >
                <RotateCcw size={11} />
                <span>Clear / Recover</span>
              </button>
            </div>
          </div>

          {/* Endpoint Configuration Bar */}
          <div
            style={{
              flexShrink: 0,
              padding: '10px 14px',
              borderRadius: 8,
              backgroundColor: '#0a101d',
              border: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Plus size={14} color="#38bdf8" />
              <span style={{ fontSize: 11, fontWeight: 600, color: '#f8fafc' }}>Configure HTTP Probe:</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, maxWidth: 620 }}>
              <select
                value={configService}
                onChange={(e) => setConfigService(e.target.value)}
                style={{
                  padding: '5px 8px',
                  borderRadius: 5,
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  color: '#f8fafc',
                  fontSize: 11,
                  outline: 'none',
                }}
              >
                {healthRecords.map((r) => (
                  <option key={r.service_id} value={r.service_id}>
                    {r.service_id}
                  </option>
                ))}
              </select>

              <input
                type="text"
                value={configUrl}
                onChange={(e) => setConfigUrl(e.target.value)}
                placeholder="http://127.0.0.1:8000/health"
                style={{
                  flex: 1,
                  padding: '5px 10px',
                  borderRadius: 5,
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  color: '#f8fafc',
                  fontSize: 11,
                  fontFamily: 'JetBrains Mono, monospace',
                  outline: 'none',
                }}
              />

              <button
                onClick={handleConfigureEndpoint}
                style={{
                  padding: '5px 12px',
                  borderRadius: 5,
                  backgroundColor: '#0284c7',
                  border: 'none',
                  color: '#fff',
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                Set Endpoint
              </button>
            </div>
          </div>

          {configError && (
            <div style={{ flexShrink: 0, padding: '8px 12px', borderRadius: 6, backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5', fontSize: 11 }}>
              {configError}
            </div>
          )}

          {configSuccess && (
            <div style={{ flexShrink: 0, padding: '8px 12px', borderRadius: 6, backgroundColor: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#34d399', fontSize: 11 }}>
              {configSuccess}
            </div>
          )}

          {/* Health Records Table */}
          <div
            style={{
              flex: 1,
              minHeight: 260,
              overflowY: 'auto',
              borderRadius: 10,
              backgroundColor: '#070c16',
              border: '1px solid #1e293b',
            }}
          >
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 11 }}>
              <thead style={{ position: 'sticky', top: 0, zIndex: 10 }}>
                <tr style={{ backgroundColor: '#0f172a', borderBottom: '1px solid #1e293b', color: '#94a3b8' }}>
                  <th style={{ padding: '10px 14px' }}>Service</th>
                  <th style={{ padding: '10px 14px' }}>Endpoint</th>
                  <th style={{ padding: '10px 14px' }}>Status</th>
                  <th style={{ padding: '10px 14px' }}>Telemetry Source</th>
                  <th style={{ padding: '10px 14px' }}>HTTP Code</th>
                  <th style={{ padding: '10px 14px' }}>Latency</th>
                  <th style={{ padding: '10px 14px' }}>Failures</th>
                  <th style={{ padding: '10px 14px' }}>Incident / Recovery</th>
                  <th style={{ padding: '10px 14px', textAlign: 'center' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {healthRecords.length > 0 ? (
                  healthRecords.map((r) => {
                    const isAlert = r.alert_active || r.status === 'unavailable' || r.status === 'unhealthy';
                    const isHealthy = r.status === 'healthy';
                    const isDegraded = r.status === 'degraded';
                    const isUnconfigured = r.status === 'unconfigured';

                    const statusBg = isHealthy
                      ? 'rgba(16, 185, 129, 0.15)'
                      : isDegraded
                      ? 'rgba(245, 158, 11, 0.15)'
                      : isAlert
                      ? 'rgba(239, 68, 68, 0.15)'
                      : 'rgba(100, 116, 139, 0.15)';

                    const statusColor = isHealthy
                      ? '#34d399'
                      : isDegraded
                      ? '#fbbf24'
                      : isAlert
                      ? '#f87171'
                      : '#94a3b8';

                    return (
                      <tr
                        key={r.service_id}
                        style={{
                          borderBottom: '1px solid rgba(30, 41, 59, 0.5)',
                          backgroundColor: isAlert ? 'rgba(239, 68, 68, 0.04)' : 'transparent',
                        }}
                      >
                        <td style={{ padding: '10px 14px', fontWeight: 600, color: '#f8fafc' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            {isHealthy && <CheckCircle size={13} color="#10b981" />}
                            {isDegraded && <AlertTriangle size={13} color="#f59e0b" />}
                            {isAlert && <AlertOctagon size={13} color="#ef4444" />}
                            {isUnconfigured && <HelpCircle size={13} color="#64748b" />}
                            <span>{r.service_id}</span>
                          </div>
                        </td>

                        <td style={{ padding: '10px 14px', fontFamily: 'JetBrains Mono, monospace', color: '#94a3b8', fontSize: 10 }}>
                          {r.endpoint_url || <span style={{ color: '#475569' }}>None (Unconfigured)</span>}
                        </td>

                        <td style={{ padding: '10px 14px' }}>
                          <span
                            style={{
                              padding: '2px 7px',
                              borderRadius: 4,
                              fontSize: 10,
                              fontWeight: 700,
                              textTransform: 'uppercase',
                              backgroundColor: statusBg,
                              color: statusColor,
                            }}
                          >
                            {r.status}
                          </span>
                        </td>

                        <td style={{ padding: '10px 14px' }}>
                          {r.data_source === 'simulated' ? (
                            <span style={{ fontSize: 9, color: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.15)', padding: '2px 6px', borderRadius: 4, border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                              Simulated ({r.fault_type || 'fault'})
                            </span>
                          ) : r.data_source === 'observed' ? (
                            <span style={{ fontSize: 9, color: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.15)', padding: '2px 6px', borderRadius: 4, border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                              Observed (HTTP)
                            </span>
                          ) : (
                            <span style={{ fontSize: 9, color: '#64748b', backgroundColor: 'rgba(100, 116, 139, 0.15)', padding: '2px 6px', borderRadius: 4 }}>
                              Unconfigured
                            </span>
                          )}
                        </td>

                        <td style={{ padding: '10px 14px', color: '#f8fafc', fontFamily: 'JetBrains Mono, monospace' }}>
                          {r.http_status ? r.http_status : '—'}
                        </td>

                        <td style={{ padding: '10px 14px', color: '#f8fafc' }}>
                          {r.response_time_ms ? `${r.response_time_ms} ms` : '—'}
                        </td>

                        <td style={{ padding: '10px 14px', color: r.consecutive_failures >= (r.failure_threshold || 2) ? '#ef4444' : '#94a3b8' }}>
                          {r.consecutive_failures} / {r.failure_threshold || 2}
                        </td>

                        <td style={{ padding: '10px 14px' }}>
                          {r.active_incident_id ? (
                            <span style={{ fontSize: 9, color: '#ef4444', backgroundColor: 'rgba(239, 68, 68, 0.15)', padding: '2px 6px', borderRadius: 4, fontWeight: 700 }}>
                              {r.active_incident_id} (Alert Active)
                            </span>
                          ) : r.recovery_time ? (
                            <span style={{ fontSize: 9, color: '#34d399', backgroundColor: 'rgba(16, 185, 129, 0.15)', padding: '2px 6px', borderRadius: 4 }}>
                              Recovered
                            </span>
                          ) : (
                            <span style={{ color: '#475569', fontSize: 10 }}>—</span>
                          )}
                        </td>

                        <td style={{ padding: '10px 14px', textAlign: 'center' }}>
                          {r.endpoint_url && (
                            <button
                              onClick={() => handleUnconfigureEndpoint(r.service_id)}
                              style={{
                                background: 'none',
                                border: 'none',
                                color: '#64748b',
                                cursor: 'pointer',
                                padding: 2,
                              }}
                              title="Unconfigure endpoint"
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={9} style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>
                      No health records available. Click "Check Health Now" to initiate check cycle.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
