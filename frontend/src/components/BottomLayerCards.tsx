import React from 'react';
import { Network, ShieldCheck, Activity, CheckCircle2 } from 'lucide-react';

interface BottomLayerCardsProps {
  nodeCount?: number;
  edgeCount?: number;
  riskScore?: number | null;
  riskCategory?: string;
  targetService?: string;
  activeAlertsCount?: number;
  onOpenPredict?: () => void;
  onOpenMonitor?: () => void;
  onOpenIngest?: () => void;
}

export const BottomLayerCards: React.FC<BottomLayerCardsProps> = ({
  nodeCount = 54,
  edgeCount = 142,
  riskScore = null,
  riskCategory = 'Ready',
  targetService = 'None',
  activeAlertsCount = 0,
  onOpenPredict,
  onOpenMonitor,
  onOpenIngest,
}) => {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 16,
        padding: '14px 20px 16px 20px',
        backgroundColor: '#060a12',
        borderTop: '1px solid #1e293b',
        zIndex: 15,
      }}
    >
      {/* 1. Topology & Graph State */}
      <div
        onClick={onOpenIngest}
        style={{
          padding: '14px 18px',
          borderRadius: 10,
          backgroundColor: '#0a101d',
          border: '1px solid #1e293b',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          cursor: onOpenIngest ? 'pointer' : 'default',
          transition: 'border-color 0.2s',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 30,
                height: 30,
                borderRadius: 7,
                backgroundColor: 'rgba(56, 189, 248, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#38bdf8',
              }}
            >
              <Network size={16} />
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>Graph Topology</div>
              <div style={{ fontSize: 10, color: '#64748b' }}>NetworkX In-Memory Repository</div>
            </div>
          </div>
          <div
            style={{
              padding: '2px 8px',
              borderRadius: 4,
              backgroundColor: 'rgba(56, 189, 248, 0.12)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              color: '#38bdf8',
              fontSize: 10,
              fontWeight: 700,
            }}
          >
            ACTIVE GRAPH
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 4 }}>
          <div>
            <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Services & Nodes</div>
            <div style={{ fontSize: 17, fontWeight: 800, color: '#f8fafc', marginTop: 2 }}>{nodeCount}</div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>CALLS Edges</div>
            <div style={{ fontSize: 17, fontWeight: 800, color: '#f8fafc', marginTop: 2 }}>{edgeCount}</div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Direction</div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#10b981', marginTop: 4 }}>Caller &rarr; Callee</div>
          </div>
        </div>
      </div>

      {/* 2. PREDICT Risk Engine */}
      <div
        onClick={onOpenPredict}
        style={{
          padding: '14px 18px',
          borderRadius: 10,
          backgroundColor: '#0a101d',
          border: '1px solid #1e293b',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          cursor: onOpenPredict ? 'pointer' : 'default',
          transition: 'border-color 0.2s',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 30,
                height: 30,
                borderRadius: 7,
                backgroundColor: 'rgba(249, 115, 22, 0.12)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#f97316',
              }}
            >
              <ShieldCheck size={16} />
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>PREDICT Engine</div>
              <div style={{ fontSize: 10, color: '#64748b' }}>0.35B + 0.30C + 0.15D + 0.20H</div>
            </div>
          </div>
          <div
            style={{
              padding: '2px 8px',
              borderRadius: 4,
              backgroundColor: riskCategory === 'Approved' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(249, 115, 22, 0.15)',
              border: `1px solid ${riskCategory === 'Approved' ? '#10b981' : '#f97316'}`,
              color: riskCategory === 'Approved' ? '#10b981' : '#f97316',
              fontSize: 10,
              fontWeight: 700,
            }}
          >
            {riskCategory.toUpperCase()}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 4 }}>
          <div>
            <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Computed Risk</div>
            <div style={{ fontSize: 17, fontWeight: 800, color: '#f8fafc', marginTop: 2 }}>
              {riskScore !== null && riskScore !== undefined ? `${Number(riskScore).toFixed(1)} / 100` : '-- / 100'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Target Service</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#38bdf8', marginTop: 4 }}>
              {targetService || 'paymentservice'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Verdict</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 4, color: riskCategory === 'Approved' ? '#10b981' : '#f97316', fontSize: 11, fontWeight: 600 }}>
              <CheckCircle2 size={14} />
              {riskCategory}
            </div>
          </div>
        </div>
      </div>

      {/* 3. MONITOR Health & Faults */}
      <div
        onClick={onOpenMonitor}
        style={{
          padding: '14px 18px',
          borderRadius: 10,
          backgroundColor: '#0a101d',
          border: '1px solid #1e293b',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          cursor: onOpenMonitor ? 'pointer' : 'default',
          transition: 'border-color 0.2s',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 30,
                height: 30,
                borderRadius: 7,
                backgroundColor: activeAlertsCount > 0 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.12)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: activeAlertsCount > 0 ? '#ef4444' : '#10b981',
              }}
            >
              <Activity size={16} />
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>MONITOR Service</div>
              <div style={{ fontSize: 10, color: '#64748b' }}>Deterministic Chaos & Probing</div>
            </div>
          </div>
          <div
            style={{
              padding: '2px 8px',
              borderRadius: 4,
              backgroundColor: activeAlertsCount > 0 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.12)',
              border: `1px solid ${activeAlertsCount > 0 ? '#ef4444' : '#10b981'}`,
              color: activeAlertsCount > 0 ? '#ef4444' : '#10b981',
              fontSize: 10,
              fontWeight: 700,
            }}
          >
            {activeAlertsCount > 0 ? `${activeAlertsCount} ALERT ACTIVE` : 'ALL HEALTHY'}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 4 }}>
          <div>
            <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Active Incidents</div>
            <div style={{ fontSize: 17, fontWeight: 800, color: activeAlertsCount > 0 ? '#ef4444' : '#10b981', marginTop: 2 }}>
              {activeAlertsCount}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Consecutive Threshold</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#94a3b8', marginTop: 4 }}>&ge; 3 Failures</div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>SSRF Defense</div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#10b981', marginTop: 4 }}>Metadata Blocked</div>
          </div>
        </div>
      </div>
    </div>
  );
};
