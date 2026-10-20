import React, { useState, useEffect } from 'react';
import { X, Activity, RefreshCw, Flame, RotateCcw } from 'lucide-react';

interface MonitorModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MonitorModal: React.FC<MonitorModalProps> = ({ isOpen, onClose }) => {
  const [healthRecords, setHealthRecords] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedService, setSelectedService] = useState('paymentservice');
  const [faultType, setFaultType] = useState('timeout');

  const fetchStatus = async () => {
    try {
      const resp = await fetch('/api/monitor/status');
      if (resp.ok) {
        const data = await resp.json();
        setHealthRecords(data);
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
        const data = await resp.json();
        setHealthRecords(data);
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
          consecutive_failures: faultType === 'consecutive_failure' ? 3 : 1,
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

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
      }}
    >
      <div
        style={{
          width: 860,
          maxHeight: '90vh',
          backgroundColor: '#0a101d',
          border: '1px solid #1e293b',
          borderRadius: 14,
          boxShadow: '0 25px 60px rgba(0, 0, 0, 0.85)',
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
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Activity size={20} color="#10b981" />
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#f8fafc' }}>
                MONITOR — Service Health & Simulated Telemetry
              </div>
              <div style={{ fontSize: 11, color: '#64748b' }}>
                Continuous HTTP health verification with SSRF protection & deterministic fault injection
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
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

        <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 18 }}>
          {/* Fault Simulation Controls */}
          <div
            style={{
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
                <div style={{ fontSize: 10, color: '#64748b' }}>Simulate timeout or failures to test alert triggers</div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
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
                <option value="paymentservice">paymentservice</option>
                <option value="checkoutservice">checkoutservice</option>
                <option value="cartservice">cartservice</option>
                <option value="orderservice">orderservice</option>
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
                <option value="timeout">Simulated Timeout (504)</option>
                <option value="elevated_latency">Elevated Latency (3500ms)</option>
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
                }}
              >
                Inject Fault
              </button>

              <button
                onClick={handleClearFault}
                style={{
                  padding: '6px 12px',
                  borderRadius: 6,
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  color: '#94a3b8',
                  fontSize: 11,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  cursor: 'pointer',
                }}
              >
                <RotateCcw size={11} />
                <span>Clear</span>
              </button>
            </div>
          </div>

          {/* Health Table */}
          <div
            style={{
              borderRadius: 10,
              backgroundColor: '#070c16',
              border: '1px solid #1e293b',
              overflow: 'hidden',
            }}
          >
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 11 }}>
              <thead>
                <tr style={{ backgroundColor: '#0f172a', borderBottom: '1px solid #1e293b', color: '#94a3b8' }}>
                  <th style={{ padding: '10px 14px' }}>Service</th>
                  <th style={{ padding: '10px 14px' }}>Monitored Endpoint</th>
                  <th style={{ padding: '10px 14px' }}>Status</th>
                  <th style={{ padding: '10px 14px' }}>Latency</th>
                  <th style={{ padding: '10px 14px' }}>Failures</th>
                  <th style={{ padding: '10px 14px' }}>Telemetry Source</th>
                </tr>
              </thead>
              <tbody>
                {healthRecords.length > 0 ? (
                  healthRecords.map((r, i) => (
                    <tr
                      key={i}
                      style={{
                        borderBottom: '1px solid rgba(30, 41, 59, 0.5)',
                        backgroundColor: r.alert_active ? 'rgba(239, 68, 68, 0.05)' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '10px 14px', fontWeight: 600, color: '#f8fafc' }}>
                        {r.service_id}
                      </td>
                      <td style={{ padding: '10px 14px', fontFamily: 'JetBrains Mono, monospace', color: '#94a3b8', fontSize: 10 }}>
                        {r.endpoint_url || 'N/A'}
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <span
                          style={{
                            padding: '2px 7px',
                            borderRadius: 4,
                            fontSize: 10,
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            backgroundColor:
                              r.status === 'healthy'
                                ? 'rgba(16, 185, 129, 0.15)'
                                : r.status === 'degraded'
                                ? 'rgba(249, 115, 22, 0.15)'
                                : 'rgba(239, 68, 68, 0.15)',
                            color:
                              r.status === 'healthy'
                                ? '#34d399'
                                : r.status === 'degraded'
                                ? '#fb923c'
                                : '#f87171',
                          }}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px', color: '#f8fafc' }}>
                        {r.response_time_ms ? `${r.response_time_ms} ms` : '—'}
                      </td>
                      <td style={{ padding: '10px 14px', color: r.consecutive_failures >= 3 ? '#ef4444' : '#94a3b8' }}>
                        {r.consecutive_failures} / 3
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        {r.is_simulated_fault ? (
                          <span style={{ fontSize: 9, color: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.15)', padding: '2px 6px', borderRadius: 4 }}>
                            Simulated ({r.fault_type})
                          </span>
                        ) : (
                          <span style={{ fontSize: 9, color: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.15)', padding: '2px 6px', borderRadius: 4 }}>
                            Live HTTP Probe
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>
                      Click "Check Health Now" to run HTTP health probes across all services.
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
