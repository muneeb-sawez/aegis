import React, { useState } from 'react';
import {
  Activity,
  Layers,
  ArrowRight,
  Zap,
} from 'lucide-react';

interface ObservabilityPageProps {
  onNavigate?: (page: string) => void;
}

export const ObservabilityPage: React.FC<ObservabilityPageProps> = ({ onNavigate }) => {
  const [selectedTraceId, setSelectedTraceId] = useState('trace-4f9b8c2d1e');
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>('span-db-pool');

  const traceList = [
    {
      id: 'trace-4f9b8c2d1e',
      rootEndpoint: 'POST /api/checkout',
      duration: '3,450ms',
      status: 'critical',
      service: 'frontend',
      timestamp: '2 mins ago',
      spansCount: 6,
    },
    {
      id: 'trace-8a2f3e4b7c',
      rootEndpoint: 'GET /api/products',
      duration: '42ms',
      status: 'healthy',
      service: 'frontend',
      timestamp: '4 mins ago',
      spansCount: 4,
    },
    {
      id: 'trace-1c5d9e0f2a',
      rootEndpoint: 'POST /api/cart/add',
      duration: '38ms',
      status: 'healthy',
      service: 'cartservice',
      timestamp: '6 mins ago',
      spansCount: 3,
    },
  ];

  const spans = [
    {
      id: 'span-front',
      service: 'frontend',
      name: 'HTTP POST /api/checkout',
      type: 'http',
      startOffset: 0,
      durationMs: 3450,
      status: 'ok',
      tags: { 'http.status_code': 200, 'component': 'ingress-nginx', 'client.ip': '192.168.1.104' },
    },
    {
      id: 'span-chk',
      service: 'checkoutservice',
      name: 'gRPC PlaceOrder',
      type: 'rpc',
      startOffset: 40,
      durationMs: 3410,
      status: 'ok',
      tags: { 'rpc.system': 'grpc', 'rpc.service': 'hipstershop.CheckoutService' },
    },
    {
      id: 'span-pay',
      service: 'paymentservice',
      name: 'gRPC ChargeCreditCard',
      type: 'rpc',
      startOffset: 70,
      durationMs: 3380,
      status: 'degraded',
      tags: { 'rpc.system': 'grpc', 'rpc.method': 'ChargePayment', 'error.rate': '0.42' },
    },
    {
      id: 'span-db-pool',
      service: 'postgres-payment',
      name: 'SQL pool.acquire_connection()',
      type: 'db',
      startOffset: 100,
      durationMs: 3350,
      status: 'critical',
      tags: {
        'db.system': 'postgresql',
        'db.name': 'payment_ledger',
        'pool.status': 'exhausted (100/100)',
        'active_alert': 'DatabaseConnectionPoolExhausted',
      },
    },
    {
      id: 'span-email',
      service: 'emailservice',
      name: 'gRPC SendOrderConfirmation',
      type: 'rpc',
      startOffset: 3420,
      durationMs: 14,
      status: 'ok',
      tags: { 'rpc.system': 'grpc', 'email.recipient': 'user@example.com' },
    },
    {
      id: 'span-curr',
      service: 'currencyservice',
      name: 'gRPC ConvertCurrency(USD -> EUR)',
      type: 'rpc',
      startOffset: 3425,
      durationMs: 18,
      status: 'ok',
      tags: { 'rpc.system': 'grpc', 'cache.hit': 'true' },
    },
  ];

  const activeSpan = spans.find((s) => s.id === selectedSpanId) || spans[3];

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
              backgroundColor: 'rgba(6, 182, 212, 0.15)',
              border: '1px solid rgba(6, 182, 212, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#06b6d4',
            }}
          >
            <Activity size={22} />
          </div>
          <div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
              Phase 2 OpenTelemetry Distributed Traces & Span Waterfall
            </div>
            <div style={{ fontSize: 12, color: '#64748b' }}>
              Microservice transaction traces, p99 critical path latency analysis, and bottleneck localization
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
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
            <span>Remediate in Autonomous Actuator</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* Notice Banner */}
      <div
        style={{
          padding: '12px 18px',
          borderRadius: 8,
          backgroundColor: 'rgba(234, 179, 8, 0.1)',
          border: '1px solid rgba(234, 179, 8, 0.3)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          color: '#facc15',
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        <span style={{ fontSize: 14 }}>ℹ</span>
        <span>Sample data: live OpenTelemetry ingest is planned</span>
      </div>

      {/* Main Grid: Trace Selector & Gantt Waterfall */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 24 }}>

        {/* Left: Trace List */}
        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Layers size={14} color="#38bdf8" />
            <span>Sample Transaction Traces</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {traceList.map((t) => {
              const isSelected = selectedTraceId === t.id;
              const isCritical = t.status === 'critical';

              return (
                <div
                  key={t.id}
                  onClick={() => setSelectedTraceId(t.id)}
                  style={{
                    padding: 12,
                    borderRadius: 8,
                    backgroundColor: isSelected ? 'rgba(6, 182, 212, 0.1)' : '#070b14',
                    border: isSelected ? '1.5px solid #06b6d4' : '1px solid #1e293b',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 6,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>{t.rootEndpoint}</span>
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 800,
                        padding: '2px 6px',
                        borderRadius: 4,
                        backgroundColor: isCritical ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                        color: isCritical ? '#f87171' : '#34d399',
                      }}
                    >
                      {t.duration}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11, color: '#64748b' }}>
                    <span>{t.id}</span>
                    <span>{t.spansCount} spans</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Gantt Waterfall Chart & Span Inspector */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Waterfall Chart */}
          <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>
                  Trace: {selectedTraceId} (Total: 3,450ms)
                </div>
                <div style={{ fontSize: 11, color: '#64748b' }}>
                  Critical path bottleneck identified in PostgreSQL connection queue
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 11, color: '#ef4444', fontWeight: 700 }}>
                  ● 97.1% Duration in paymentservice & DB
                </span>
              </div>
            </div>

            {/* Waterfall Rows */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {spans.map((s) => {
                const isSelected = selectedSpanId === s.id;
                const isCritical = s.status === 'critical';
                const isDegraded = s.status === 'degraded';
                const widthPct = Math.max(2, (s.durationMs / 3450) * 100);
                const leftPct = (s.startOffset / 3450) * 100;

                return (
                  <div
                    key={s.id}
                    onClick={() => setSelectedSpanId(s.id)}
                    style={{
                      padding: '8px 12px',
                      borderRadius: 8,
                      backgroundColor: isSelected ? '#1e293b' : '#070b14',
                      border: isSelected ? '1px solid #38bdf8' : '1px solid #1e293b',
                      cursor: 'pointer',
                      display: 'grid',
                      gridTemplateColumns: '220px 1fr 90px',
                      alignItems: 'center',
                      gap: 16,
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>{s.service}</div>
                      <div style={{ fontSize: 10, color: '#64748b' }}>{s.name}</div>
                    </div>

                    {/* Gantt Bar */}
                    <div style={{ position: 'relative', width: '100%', height: 18, backgroundColor: '#0f172a', borderRadius: 4, overflow: 'hidden' }}>
                      <div
                        style={{
                          position: 'absolute',
                          left: `${leftPct}%`,
                          width: `${widthPct}%`,
                          height: '100%',
                          backgroundColor: isCritical ? '#ef4444' : isDegraded ? '#f97316' : '#10b981',
                          borderRadius: 4,
                          boxShadow: isCritical ? '0 0 10px rgba(239, 68, 68, 0.6)' : undefined,
                        }}
                      />
                    </div>

                    <div style={{ textAlign: 'right', fontSize: 12, fontWeight: 700, color: isCritical ? '#f87171' : isDegraded ? '#fb923c' : '#34d399' }}>
                      {s.durationMs}ms
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Span Details Drawer */}
          {activeSpan && (
            <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginBottom: 12 }}>
                Span Attributes: {activeSpan.service} ({activeSpan.name})
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                {Object.entries(activeSpan.tags).map(([k, v]) => (
                  <div key={k} style={{ backgroundColor: '#070b14', padding: 10, borderRadius: 6, border: '1px solid #1e293b', fontSize: 11 }}>
                    <div style={{ color: '#64748b', fontWeight: 600 }}>{k}</div>
                    <div style={{ color: '#f8fafc', fontWeight: 700, marginTop: 2 }}>{String(v)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
