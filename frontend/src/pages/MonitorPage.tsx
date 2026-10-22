import React, { useState, useEffect } from 'react';
import {
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
  Search,
} from 'lucide-react';

import { DEFAULT_PROBE_URL } from '../config';

export const MonitorPage: React.FC = () => {
  const [healthRecords, setHealthRecords] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedService, setSelectedService] = useState('paymentservice');
  const [faultType, setFaultType] = useState('timeout');
  const [configService, setConfigService] = useState('frontend');
  const [configUrl, setConfigUrl] = useState(DEFAULT_PROBE_URL);
  const [configError, setConfigError] = useState<string | null>(null);
  const [configSuccess, setConfigSuccess] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');

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

  useEffect(() => {
    fetchStatus();
    if (!autoRefresh) return;
    const intervalId = setInterval(fetchStatus, 4000);
    return () => clearInterval(intervalId);
  }, [autoRefresh]);

  const healthyCount = healthRecords.filter((r) => r.status === 'healthy').length;
  const degradedCount = healthRecords.filter((r) => r.status === 'degraded').length;
  const unavailableCount = healthRecords.filter((r) => r.status === 'unavailable' || r.status === 'unhealthy').length;
  const unconfiguredCount = healthRecords.filter((r) => r.status === 'unconfigured').length;

  const filteredRecords = healthRecords.filter((r) => {
    const matchesSearch = r.service_id.toLowerCase().includes(searchTerm.toLowerCase());
    if (filterStatus === 'all') return matchesSearch;
    if (filterStatus === 'healthy') return matchesSearch && r.status === 'healthy';
    if (filterStatus === 'degraded') return matchesSearch && r.status === 'degraded';
    if (filterStatus === 'unavailable') return matchesSearch && (r.status === 'unavailable' || r.status === 'unhealthy');
    if (filterStatus === 'unconfigured') return matchesSearch && r.status === 'unconfigured';
    return matchesSearch;
  });

  return (
    <div style={{ padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: 20, height: '100%', overflowY: 'auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, backgroundColor: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10b981' }}>
            <Activity size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 20, fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
                MONITOR — Live Fleet Health & Telemetry Center
              </span>
              <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 4, backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.3)', display: 'flex', alignItems: 'center', gap: 5 }}>
                <Radio size={10} className="animate-pulse" />
                {autoRefresh ? 'LIVE POLLING (4s)' : 'PAUSED'}
              </span>
            </div>
            <div style={{ fontSize: 12, color: '#64748b' }}>
              Real-time HTTP health inspection, SSRF protection, consecutive failure thresholds, and automatic incident writeback
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            style={{
              padding: '8px 14px',
              borderRadius: 8,
              backgroundColor: autoRefresh ? '#0f172a' : '#1e293b',
              border: '1px solid #334155',
              color: autoRefresh ? '#38bdf8' : '#94a3b8',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {autoRefresh ? 'Pause Polling' : 'Resume Polling'}
          </button>

          <button
            onClick={handleCheckNow}
            disabled={isLoading}
            style={{
              padding: '8px 16px',
              borderRadius: 8,
              backgroundColor: '#0284c7',
              border: 'none',
              color: '#fff',
              fontSize: 12,
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              cursor: 'pointer',
              boxShadow: '0 4px 14px rgba(2, 132, 199, 0.35)',
            }}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>{isLoading ? 'Checking Fleet...' : 'Check Fleet Now'}</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 14 }}>
        <div style={{ padding: '16px', borderRadius: 10, backgroundColor: '#0a101d', border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>Total Microservices</div>
          <div style={{ fontSize: 26, fontWeight: 800, color: '#f8fafc', marginTop: 4, fontFamily: 'JetBrains Mono, monospace' }}>
            {healthRecords.length}
          </div>
          <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>Registered in Topology</div>
        </div>

        <div style={{ padding: '16px', borderRadius: 10, backgroundColor: '#0a101d', border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>Healthy Endpoints</div>
          <div style={{ fontSize: 26, fontWeight: 800, color: '#10b981', marginTop: 4, fontFamily: 'JetBrains Mono, monospace' }}>
            {healthyCount}
          </div>
          <div style={{ fontSize: 10, color: '#34d399', marginTop: 4 }}>HTTP 200 Verified</div>
        </div>

        <div style={{ padding: '16px', borderRadius: 10, backgroundColor: '#0a101d', border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>Degraded Latency</div>
          <div style={{ fontSize: 26, fontWeight: 800, color: '#f59e0b', marginTop: 4, fontFamily: 'JetBrains Mono, monospace' }}>
            {degradedCount}
          </div>
          <div style={{ fontSize: 10, color: '#fbbf24', marginTop: 4 }}>Elevated Latency / 4xx</div>
        </div>

        <div style={{ padding: '16px', borderRadius: 10, backgroundColor: '#0a101d', border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>Unavailable / Alerting</div>
          <div style={{ fontSize: 26, fontWeight: 800, color: '#ef4444', marginTop: 4, fontFamily: 'JetBrains Mono, monospace' }}>
            {unavailableCount}
          </div>
          <div style={{ fontSize: 10, color: '#f87171', marginTop: 4 }}>Threshold Breached (≥ 2)</div>
        </div>

        <div style={{ padding: '16px', borderRadius: 10, backgroundColor: '#0a101d', border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>Unconfigured Probes</div>
          <div style={{ fontSize: 26, fontWeight: 800, color: '#94a3b8', marginTop: 4, fontFamily: 'JetBrains Mono, monospace' }}>
            {unconfiguredCount}
          </div>
          <div style={{ fontSize: 10, color: '#64748b', marginTop: 4 }}>No Fake Default Health</div>
        </div>
      </div>

      {/* Fault Simulator & Probe Config Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Fault Simulator Card */}
        <div style={{ padding: '16px', borderRadius: 10, backgroundColor: '#0a101d', border: '1px solid #1e293b', display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Flame size={16} color="#ef4444" />
            <span style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>Deterministic Fault Simulator</span>
            <span style={{ fontSize: 10, color: '#64748b' }}>(simulated / emulator time)</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '130px 1fr auto auto', gap: 8, alignItems: 'center' }}>
            <select
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
              style={{
                padding: '7px 10px',
                borderRadius: 6,
                backgroundColor: '#070c16',
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
                padding: '7px 10px',
                borderRadius: 6,
                backgroundColor: '#070c16',
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
                padding: '7px 14px',
                borderRadius: 6,
                backgroundColor: 'rgba(239, 68, 68, 0.2)',
                border: '1px solid #ef4444',
                color: '#fca5a5',
                fontSize: 11,
                fontWeight: 700,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              Inject Fault
            </button>

            <button
              onClick={handleClearFault}
              style={{
                padding: '7px 14px',
                borderRadius: 6,
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid #10b981',
                color: '#34d399',
                fontSize: 11,
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              <RotateCcw size={12} />
              <span>Clear / Recover</span>
            </button>
          </div>
        </div>

        {/* Configure Probe Card */}
        <div style={{ padding: '16px', borderRadius: 10, backgroundColor: '#0a101d', border: '1px solid #1e293b', display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Plus size={16} color="#38bdf8" />
            <span style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>Configure Real HTTP Health Probe</span>
            <span style={{ fontSize: 10, color: '#64748b' }}>(SSRF Protected)</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '130px 1fr auto', gap: 8, alignItems: 'center' }}>
            <select
              value={configService}
              onChange={(e) => setConfigService(e.target.value)}
              style={{
                padding: '7px 10px',
                borderRadius: 6,
                backgroundColor: '#070c16',
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
              placeholder={DEFAULT_PROBE_URL}
              style={{
                padding: '7px 12px',
                borderRadius: 6,
                backgroundColor: '#070c16',
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
                padding: '7px 14px',
                borderRadius: 6,
                backgroundColor: '#0284c7',
                border: 'none',
                color: '#fff',
                fontSize: 11,
                fontWeight: 700,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              Set Endpoint
            </button>
          </div>

          {configError && <div style={{ fontSize: 11, color: '#f87171' }}>{configError}</div>}
          {configSuccess && <div style={{ fontSize: 11, color: '#34d399' }}>{configSuccess}</div>}
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, maxWidth: 360, backgroundColor: '#0a101d', padding: '6px 12px', borderRadius: 8, border: '1px solid #1e293b' }}>
          <Search size={14} color="#64748b" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search service name..."
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              color: '#f8fafc',
              fontSize: 12,
              outline: 'none',
              width: '100%',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {['all', 'healthy', 'degraded', 'unavailable', 'unconfigured'].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              style={{
                padding: '6px 12px',
                borderRadius: 6,
                backgroundColor: filterStatus === st ? 'rgba(56, 189, 248, 0.15)' : '#0a101d',
                border: filterStatus === st ? '1px solid #38bdf8' : '1px solid #1e293b',
                color: filterStatus === st ? '#38bdf8' : '#94a3b8',
                fontSize: 11,
                fontWeight: 600,
                textTransform: 'capitalize',
                cursor: 'pointer',
              }}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Live Health Records Table */}
      <div style={{ borderRadius: 12, backgroundColor: '#0a101d', border: '1px solid #1e293b', overflow: 'hidden', flex: 1, minHeight: 320 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 11 }}>
          <thead style={{ position: 'sticky', top: 0, zIndex: 10 }}>
            <tr style={{ backgroundColor: '#0f172a', borderBottom: '1px solid #1e293b', color: '#94a3b8' }}>
              <th style={{ padding: '12px 16px' }}>Service</th>
              <th style={{ padding: '12px 16px' }}>Monitored Probe URL</th>
              <th style={{ padding: '12px 16px' }}>Health Status</th>
              <th style={{ padding: '12px 16px' }}>Telemetry Source</th>
              <th style={{ padding: '12px 16px' }}>HTTP Code</th>
              <th style={{ padding: '12px 16px' }}>Latency (ms)</th>
              <th style={{ padding: '12px 16px' }}>Failures</th>
              <th style={{ padding: '12px 16px' }}>Active Incident / Recovery</th>
              <th style={{ padding: '12px 16px', textAlign: 'center' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredRecords.length > 0 ? (
              filteredRecords.map((r) => {
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
                    <td style={{ padding: '12px 16px', fontWeight: 600, color: '#f8fafc' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        {isHealthy && <CheckCircle size={14} color="#10b981" />}
                        {isDegraded && <AlertTriangle size={14} color="#f59e0b" />}
                        {isAlert && <AlertOctagon size={14} color="#ef4444" />}
                        {isUnconfigured && <HelpCircle size={14} color="#64748b" />}
                        <span>{r.service_id}</span>
                      </div>
                    </td>

                    <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', color: '#94a3b8', fontSize: 10 }}>
                      {r.endpoint_url || <span style={{ color: '#475569' }}>None (Unconfigured)</span>}
                    </td>

                    <td style={{ padding: '12px 16px' }}>
                      <span
                        style={{
                          padding: '3px 8px',
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

                    <td style={{ padding: '12px 16px' }}>
                      {r.data_source === 'simulated' ? (
                        <span style={{ fontSize: 9, color: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.15)', padding: '2px 7px', borderRadius: 4, border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                          Simulated ({r.fault_type || 'fault'})
                        </span>
                      ) : r.data_source === 'observed' ? (
                        <span style={{ fontSize: 9, color: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.15)', padding: '2px 7px', borderRadius: 4, border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                          Observed (HTTP)
                        </span>
                      ) : (
                        <span style={{ fontSize: 9, color: '#64748b', backgroundColor: 'rgba(100, 116, 139, 0.15)', padding: '2px 7px', borderRadius: 4 }}>
                          Unconfigured
                        </span>
                      )}
                    </td>

                    <td style={{ padding: '12px 16px', color: '#f8fafc', fontFamily: 'JetBrains Mono, monospace' }}>
                      {r.http_status ? r.http_status : '—'}
                    </td>

                    <td style={{ padding: '12px 16px', color: '#f8fafc' }}>
                      {r.response_time_ms ? `${r.response_time_ms} ms` : '—'}
                    </td>

                    <td style={{ padding: '12px 16px', color: r.consecutive_failures >= (r.failure_threshold || 2) ? '#ef4444' : '#94a3b8' }}>
                      {r.consecutive_failures} / {r.failure_threshold || 2}
                    </td>

                    <td style={{ padding: '12px 16px' }}>
                      {r.active_incident_id ? (
                        <span style={{ fontSize: 9, color: '#ef4444', backgroundColor: 'rgba(239, 68, 68, 0.15)', padding: '3px 8px', borderRadius: 4, fontWeight: 700 }}>
                          {r.active_incident_id} (Alert Active)
                        </span>
                      ) : r.recovery_time ? (
                        <span style={{ fontSize: 9, color: '#34d399', backgroundColor: 'rgba(16, 185, 129, 0.15)', padding: '3px 8px', borderRadius: 4 }}>
                          Recovered
                        </span>
                      ) : (
                        <span style={{ color: '#475569', fontSize: 10 }}>—</span>
                      )}
                    </td>

                    <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                      {r.endpoint_url && (
                        <button
                          onClick={() => handleUnconfigureEndpoint(r.service_id)}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: '#64748b',
                            cursor: 'pointer',
                            padding: 4,
                          }}
                          title="Unconfigure endpoint"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={9} style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>
                  No services matching filter criteria.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
