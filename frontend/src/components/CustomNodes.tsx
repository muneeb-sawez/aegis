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

interface NodeData {
  label: string;
  sublabel?: string;
  iconType?: 'db' | 'k8s' | 'gateway' | 'internet' | 'dns' | 'waf' | 'vpc' | 'iam';
  status?: 'critical' | 'healthy' | 'warning';
  badge?: string;
  alertBadge?: boolean;
  subnets?: string[];
  metrics?: { p99?: number; err?: number };
}

// 1. Critical Highlighted Service/DB Node (Orange Glowing)
export const CriticalNode = memo(({ data }: { data: NodeData }) => {
  return (
    <div
      style={{
        minWidth: 175,
        padding: '12px 14px',
        borderRadius: 10,
        backgroundColor: '#0c1322',
        border: '1.5px solid #f97316',
        boxShadow: '0 0 18px rgba(249, 115, 22, 0.4), inset 0 0 10px rgba(249, 115, 22, 0.08)',
        color: '#f8fafc',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#f97316', width: 7, height: 7 }} />
      <Handle type="target" position={Position.Left} style={{ background: '#f97316', width: 7, height: 7 }} />
      
      {/* Alert exclamation badge */}
      {data.alertBadge && (
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
            backgroundColor: 'rgba(249, 115, 22, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#f97316',
          }}
        >
          {data.iconType === 'db' ? <Database size={18} /> : <Server size={18} />}
        </div>

        <div>
          <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: -0.2 }}>{data.label}</div>
          <div style={{ fontSize: 11, color: '#94a3b8' }}>{data.sublabel || 'Service'}</div>
        </div>
      </div>

      {data.badge && (
        <div
          style={{
            marginTop: 4,
            padding: '2px 8px',
            borderRadius: 4,
            backgroundColor: 'rgba(239, 68, 68, 0.2)',
            border: '1px solid rgba(239, 68, 68, 0.5)',
            color: '#f87171',
            fontSize: 9,
            fontWeight: 800,
            letterSpacing: 0.8,
            textAlign: 'center',
            textTransform: 'uppercase',
          }}
        >
          {data.badge}
        </div>
      )}

      <Handle type="source" position={Position.Right} style={{ background: '#f97316', width: 7, height: 7 }} />
      <Handle type="source" position={Position.Bottom} style={{ background: '#f97316', width: 7, height: 7 }} />
    </div>
  );
});

// 2. Standard Service / Database Node (Blue / Sleek Dark)
export const ServiceNode = memo(({ data }: { data: NodeData }) => {
  return (
    <div
      style={{
        minWidth: 155,
        padding: '10px 12px',
        borderRadius: 9,
        backgroundColor: '#0a101d',
        border: '1px solid #1e293b',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.35)',
        color: '#f8fafc',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        position: 'relative',
        transition: 'all 0.2s ease',
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: '#38bdf8', width: 6, height: 6 }} />
      <Handle type="target" position={Position.Top} style={{ background: '#38bdf8', width: 6, height: 6 }} />

      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 6,
          backgroundColor: 'rgba(56, 189, 248, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#38bdf8',
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

      <div>
        <div style={{ fontSize: 12, fontWeight: 600 }}>{data.label}</div>
        <div style={{ fontSize: 10, color: '#64748b' }}>{data.sublabel || 'Kubernetes'}</div>
      </div>

      <Handle type="source" position={Position.Right} style={{ background: '#38bdf8', width: 6, height: 6 }} />
      <Handle type="source" position={Position.Bottom} style={{ background: '#38bdf8', width: 6, height: 6 }} />
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

      {/* Subnet boxes inside VPC */}
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
