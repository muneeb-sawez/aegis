import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import {
  Database,
  Server,
  Layers,
  Globe,
  Shield,
  Lock,
  UserCheck,
  Cpu,
} from 'lucide-react';

export interface NodeData {
  label: string;
  sublabel?: string;
  iconType?: 'db' | 'k8s' | 'gateway' | 'internet' | 'dns' | 'waf' | 'vpc' | 'iam' | 'service';
  status?: 'critical' | 'healthy' | 'warning' | 'normal';
  healthStatus?: 'healthy' | 'degraded' | 'unavailable' | 'unhealthy' | 'unconfigured' | 'pending';
  badge?: string;
  alertBadge?: boolean;
  subnets?: string[];
  metrics?: { p99?: number; err?: number };
  latency_ms?: number;
  baseline_latency_ms?: number;
  rolling_latencies?: number[];
  error_rate?: number;
  raw?: any;
}

function getStatusTheme(healthStatus?: string, fallbackCritical = false) {
  if (healthStatus === 'healthy') {
    return {
      border: '1.5px solid #10b981',
      boxShadow: '0 0 16px rgba(16, 185, 129, 0.35)',
      badgeBg: 'rgba(16, 185, 129, 0.15)',
      badgeBorder: '1px solid #10b981',
      badgeColor: '#10b981',
      badgeText: 'HEALTHY',
      dotColor: '#10b981',
      alert: false,
    };
  } else if (healthStatus === 'degraded') {
    return {
      border: '1.5px solid #f59e0b',
      boxShadow: '0 0 18px rgba(245, 158, 11, 0.45)',
      badgeBg: 'rgba(245, 158, 11, 0.15)',
      badgeBorder: '1px solid #f59e0b',
      badgeColor: '#f59e0b',
      badgeText: 'DEGRADED',
      dotColor: '#f59e0b',
      alert: true,
    };
  } else if (healthStatus === 'unavailable' || healthStatus === 'unhealthy') {
    return {
      border: '1.5px solid #ef4444',
      boxShadow: '0 0 22px rgba(239, 68, 68, 0.65), inset 0 0 10px rgba(239, 68, 68, 0.25)',
      badgeBg: 'rgba(239, 68, 68, 0.25)',
      badgeBorder: '1px solid #ef4444',
      badgeColor: '#f87171',
      badgeText: 'OUTAGE',
      dotColor: '#ef4444',
      alert: true,
    };
  }

  // Baseline / unconfigured / critical fallback
  if (fallbackCritical) {
    return {
      border: '1.5px solid #f97316',
      boxShadow: '0 0 18px rgba(249, 115, 22, 0.4), inset 0 0 10px rgba(249, 115, 22, 0.08)',
      badgeBg: 'rgba(249, 115, 22, 0.15)',
      badgeBorder: '1px solid rgba(249, 115, 22, 0.4)',
      badgeColor: '#fb923c',
      badgeText: 'CRITICAL',
      dotColor: '#f97316',
      alert: false,
    };
  }

  return {
    border: '1px solid #1e293b',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.35)',
    badgeBg: 'rgba(51, 65, 85, 0.25)',
    badgeBorder: '1px solid #334155',
    badgeColor: '#94a3b8',
    badgeText: healthStatus ? healthStatus.toUpperCase() : undefined,
    dotColor: '#38bdf8',
    alert: false,
  };
}

// 1. Critical Highlighted Service/DB Node (Orange / Status Glow)
export const CriticalNode = memo(({ data }: { data: NodeData }) => {
  const theme = getStatusTheme(data.healthStatus, true);
  const showAlert = data.alertBadge || theme.alert;

  return (
    <div
      style={{
        minWidth: 175,
        padding: '12px 14px',
        borderRadius: 10,
        backgroundColor: '#0c1322',
        border: theme.border,
        boxShadow: theme.boxShadow,
        color: '#f8fafc',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        transition: 'all 0.3s ease',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: theme.dotColor, width: 7, height: 7 }} />
      <Handle type="target" position={Position.Left} style={{ background: theme.dotColor, width: 7, height: 7 }} />

      {showAlert && (
        <div
          style={{
            position: 'absolute',
            top: -9,
            right: -9,
            width: 20,
            height: 20,
            borderRadius: '50%',
            backgroundColor: '#ef4444',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 10px #ef4444',
            color: '#fff',
            fontSize: 12,
            fontWeight: 800,
          }}
        >
          !
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 7,
            backgroundColor: `${theme.badgeBg}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: theme.dotColor,
          }}
        >
          {data.iconType === 'db' ? <Database size={18} /> : <Server size={18} />}
        </div>

        <div>
          <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: -0.2 }}>{data.label}</div>
          <div style={{ fontSize: 11, color: '#94a3b8' }}>
            {data.sublabel || 'Service'}
            {data.latency_ms !== undefined && data.latency_ms !== null && (
              <span style={{ marginLeft: 6, color: theme.dotColor, fontWeight: 600 }}>
                {Number(data.latency_ms).toFixed(0)}ms
              </span>
            )}
          </div>
        </div>
      </div>

      {(theme.badgeText || data.badge) && (
        <div
          style={{
            marginTop: 4,
            padding: '2px 8px',
            borderRadius: 4,
            backgroundColor: theme.badgeBg,
            border: theme.badgeBorder,
            color: theme.badgeColor,
            fontSize: 9,
            fontWeight: 800,
            letterSpacing: 0.8,
            textAlign: 'center',
            textTransform: 'uppercase',
          }}
        >
          {theme.badgeText || data.badge}
        </div>
      )}

      <Handle type="source" position={Position.Right} style={{ background: theme.dotColor, width: 7, height: 7 }} />
      <Handle type="source" position={Position.Bottom} style={{ background: theme.dotColor, width: 7, height: 7 }} />
    </div>
  );
});

// 2. Standard Service / Database Node (Dynamic Status Glow: Green/Amber/Red)
export const ServiceNode = memo(({ data }: { data: NodeData }) => {
  const theme = getStatusTheme(data.healthStatus, false);
  const showAlert = data.alertBadge || theme.alert;

  return (
    <div
      style={{
        minWidth: 165,
        padding: '10px 12px',
        borderRadius: 9,
        backgroundColor: '#0a101d',
        border: theme.border,
        boxShadow: theme.boxShadow,
        color: '#f8fafc',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        position: 'relative',
        transition: 'all 0.3s ease',
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: theme.dotColor, width: 6, height: 6 }} />
      <Handle type="target" position={Position.Top} style={{ background: theme.dotColor, width: 6, height: 6 }} />

      {showAlert && (
        <div
          style={{
            position: 'absolute',
            top: -7,
            right: -7,
            width: 18,
            height: 18,
            borderRadius: '50%',
            backgroundColor: '#ef4444',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 8px #ef4444',
            color: '#fff',
            fontSize: 11,
            fontWeight: 800,
          }}
        >
          !
        </div>
      )}

      <div
        style={{
          width: 30,
          height: 30,
          borderRadius: 6,
          backgroundColor: theme.badgeBg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: theme.dotColor,
        }}
      >
        {data.iconType === 'db' ? (
          <Database size={16} />
        ) : data.iconType === 'internet' ? (
          <Globe size={16} />
        ) : data.iconType === 'dns' || data.iconType === 'waf' ? (
          <Shield size={16} />
        ) : (
          <Cpu size={16} />
        )}
      </div>

      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12, fontWeight: 600 }}>{data.label}</div>
        <div style={{ fontSize: 10, color: '#64748b', display: 'flex', justifyContent: 'space-between' }}>
          <span>{data.sublabel || 'Service'}</span>
          {data.latency_ms !== undefined && data.latency_ms !== null && (
            <span style={{ color: theme.dotColor, fontWeight: 700 }}>
              {Number(data.latency_ms).toFixed(0)}ms
            </span>
          )}
        </div>
      </div>

      <Handle type="source" position={Position.Right} style={{ background: theme.dotColor, width: 6, height: 6 }} />
      <Handle type="source" position={Position.Bottom} style={{ background: theme.dotColor, width: 6, height: 6 }} />
    </div>
  );
});

// 3. VPC / Boundary Group Container Node
export const VpcGroupNode = memo(({ data }: { data: NodeData }) => {
  return (
    <div
      style={{
        minWidth: 260,
        padding: '14px 16px',
        borderRadius: 12,
        backgroundColor: 'rgba(10, 16, 28, 0.65)',
        border: '1px dashed #334155',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.45)',
        color: '#f8fafc',
        position: 'relative',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#64748b', width: 6, height: 6 }} />
      
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <Layers size={16} color="#38bdf8" />
        <div>
          <div style={{ fontSize: 12, fontWeight: 700 }}>{data.label}</div>
          <div style={{ fontSize: 10, color: '#64748b' }}>{data.sublabel || 'VPC Network'}</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        {(Array.isArray(data.subnets) ? data.subnets : ['Private Subnet 10.0.1.0/24', 'Private Subnet 10.0.2.0/24']).map((sub, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              padding: '8px 10px',
              borderRadius: 6,
              backgroundColor: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid #1e293b',
              fontSize: 10,
              color: '#94a3b8',
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
          >
            <Lock size={12} color="#0284c7" />
            <span>{sub}</span>
          </div>
        ))}
      </div>

      <Handle type="source" position={Position.Bottom} style={{ background: '#64748b', width: 6, height: 6 }} />
    </div>
  );
});

// 4. IAM Role Node
export const IamRoleNode = memo(({ data }: { data: NodeData }) => {
  return (
    <div
      style={{
        padding: '8px 12px',
        borderRadius: 8,
        backgroundColor: '#090e17',
        border: '1px solid #1e293b',
        color: '#e2e8f0',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#64748b', width: 5, height: 5 }} />
      <UserCheck size={14} color="#94a3b8" />
      <div>
        <div style={{ fontSize: 11, fontWeight: 600 }}>{data.label}</div>
        <div style={{ fontSize: 9, color: '#64748b' }}>IAM Role</div>
      </div>
    </div>
  );
});
