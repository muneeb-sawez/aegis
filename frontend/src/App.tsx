import { useState, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  type Edge,
  type Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  Network,
  Shield,
  Activity,
  GitBranch,
  Box,
  Terminal,
  X,
  RotateCcw,
} from 'lucide-react';

import {
  CriticalNode,
  ServiceNode,
  VpcGroupNode,
  IamRoleNode,
} from './components/CustomNodes';
import { BlastRadiusPanel } from './components/BlastRadiusPanel';
import { BottomLayerCards } from './components/BottomLayerCards';
import { PredictModal } from './components/PredictModal';
import { MonitorModal } from './components/MonitorModal';
import { IngestionModal } from './components/IngestionModal';

// Node types registry for React Flow
const nodeTypes = {
  criticalNode: CriticalNode,
  serviceNode: ServiceNode,
  vpcGroupNode: VpcGroupNode,
  iamRoleNode: IamRoleNode,
};

// Initial nodes mapped with high-fidelity coordinates
const initialNodes: Node[] = [
  // 1. Ingress / Network Layer
  {
    id: 'internet',
    type: 'serviceNode',
    position: { x: 440, y: 30 },
    data: { label: 'Internet', sublabel: 'Public Gateway', iconType: 'internet' },
  },
  {
    id: 'route53',
    type: 'serviceNode',
    position: { x: 250, y: 90 },
    data: { label: 'Route 53', sublabel: 'DNS', iconType: 'dns' },
  },
  {
    id: 'waf',
    type: 'serviceNode',
    position: { x: 630, y: 90 },
    data: { label: 'WAF', sublabel: 'Web ACL', iconType: 'waf' },
  },

  // 2. Critical Path Services (Highlighted in glowing orange/crimson)
  {
    id: 'prod-db',
    type: 'criticalNode',
    position: { x: 170, y: 200 },
    data: {
      label: 'prod-db',
      sublabel: 'PostgreSQL',
      badge: 'CRITICAL',
      iconType: 'db',
      status: 'critical',
    },
  },
  {
    id: 'api-gateway',
    type: 'criticalNode',
    position: { x: 400, y: 150 },
    data: {
      label: 'API Gateway',
      sublabel: 'api-gateway',
      alertBadge: true,
      iconType: 'gateway',
      status: 'critical',
    },
  },
  {
    id: 'checkoutservice',
    type: 'criticalNode',
    position: { x: 580, y: 210 },
    data: {
      label: 'checkoutservice',
      sublabel: 'Kubernetes',
      badge: 'CRITICAL',
      alertBadge: true,
      iconType: 'k8s',
      status: 'critical',
    },
  },

  // 3. Database Replicas
  {
    id: 'db-replica-1',
    type: 'serviceNode',
    position: { x: 180, y: 360 },
    data: { label: 'db-replica-1', sublabel: 'PostgreSQL', iconType: 'db' },
  },
  {
    id: 'db-replica-2',
    type: 'serviceNode',
    position: { x: 300, y: 360 },
    data: { label: 'db-replica-2', sublabel: 'PostgreSQL', iconType: 'db' },
  },

  // 4. Internal Microservices
  {
    id: 'cartservice',
    type: 'serviceNode',
    position: { x: 480, y: 330 },
    data: { label: 'cartservice', sublabel: 'Service (Redis)', iconType: 'service' },
  },
  {
    id: 'paymentservice',
    type: 'criticalNode',
    position: { x: 620, y: 340 },
    data: {
      label: 'paymentservice',
      sublabel: 'Target Microservice',
      badge: 'TARGET',
      alertBadge: true,
      iconType: 'service',
      status: 'critical',
    },
  },
  {
    id: 'shippingservice',
    type: 'serviceNode',
    position: { x: 760, y: 330 },
    data: { label: 'shippingservice', sublabel: 'Service', iconType: 'service' },
  },

  // 5. External SaaS Vendors
  {
    id: 'stripe-gateway',
    type: 'serviceNode',
    position: { x: 740, y: 440 },
    data: { label: 'Stripe SaaS', sublabel: 'External API', iconType: 'internet' },
  },

  // 6. VPC Group Containment Boundary
  {
    id: 'prod-vpc',
    type: 'vpcGroupNode',
    position: { x: 450, y: 440 },
    data: {
      label: 'VPC: vpc-0a1b2c3d',
      cidr: '10.0.0.0/16',
      subnets: ['Private Subnet 10.0.1.0/24', 'Public Subnet 10.0.2.0/24'],
    },
  },

  // 7. IAM & Security Roles
  {
    id: 'app-role',
    type: 'iamRoleNode',
    position: { x: 340, y: 550 },
    data: {
      label: 'app-execution-role',
      roleType: 'ECS / EKS Task',
      policies: ['S3ReadOnly', 'CloudWatchLogsFullAccess'],
    },
  },
  {
    id: 'deploy-role',
    type: 'iamRoleNode',
    position: { x: 500, y: 550 },
    data: {
      label: 'ci-cd-deployer',
      roleType: 'GitHub Actions OIDC',
      policies: ['ECRFullAccess', 'K8sClusterAdmin'],
    },
  },
  {
    id: 'dba-role',
    type: 'iamRoleNode',
    position: { x: 660, y: 550 },
    data: {
      label: 'dba-maintenance-role',
      roleType: 'RDS IAM Auth',
      policies: ['AmazonRDSFullAccess'],
    },
  },
];

// Initial edges showing directional call flows
const initialEdges: Edge[] = [
  // Gateway & ingress routes
  { id: 'e-inet-r53', source: 'internet', target: 'route53', className: 'edge-dependency' },
  { id: 'e-inet-waf', source: 'internet', target: 'waf', className: 'edge-dependency' },
  { id: 'e-waf-gw', source: 'waf', target: 'api-gateway', className: 'edge-critical' },
  { id: 'e-r53-gw', source: 'route53', target: 'api-gateway', className: 'edge-critical' },

  // Critical path calls: API Gateway -> Checkout -> Payment
  { id: 'e-gw-chk', source: 'api-gateway', target: 'checkoutservice', className: 'edge-critical' },
  { id: 'e-gw-db', source: 'api-gateway', target: 'prod-db', className: 'edge-critical' },
  { id: 'e-chk-pay', source: 'checkoutservice', target: 'paymentservice', className: 'edge-critical' },
  { id: 'e-chk-cart', source: 'checkoutservice', target: 'cartservice', className: 'edge-dependency' },
  { id: 'e-chk-ship', source: 'checkoutservice', target: 'shippingservice', className: 'edge-dependency' },

  // External dependency
  { id: 'e-pay-stripe', source: 'paymentservice', target: 'stripe-gateway', className: 'edge-dependency' },

  // Database replicas
  { id: 'e-db-rep1', source: 'prod-db', target: 'db-replica-1', className: 'edge-dependency' },
  { id: 'e-db-rep2', source: 'prod-db', target: 'db-replica-2', className: 'edge-dependency' },

  // Containment boundary dashed edges
  { id: 'e-chk-vpc', source: 'checkoutservice', target: 'prod-vpc', className: 'edge-containment' },
  { id: 'e-vpc-app', source: 'prod-vpc', target: 'app-role', className: 'edge-containment' },
  { id: 'e-vpc-dep', source: 'prod-vpc', target: 'deploy-role', className: 'edge-containment' },
  { id: 'e-vpc-dba', source: 'prod-vpc', target: 'dba-role', className: 'edge-containment' },
];

export function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [activeTab, setActiveTab] = useState('canvas');
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [isPredictOpen, setIsPredictOpen] = useState(false);
  const [isMonitorOpen, setIsMonitorOpen] = useState(false);
  const [isIngestionOpen, setIsIngestionOpen] = useState(false);

  // Graph repository telemetry
  const [nodeCount, setNodeCount] = useState(54);
  const [edgeCount, setEdgeCount] = useState(142);

  // Operational State
  const [simResult, setSimResult] = useState<any>(null);
  const [faultActive, setFaultActive] = useState(false);
  const [healed, setHealed] = useState(false);
  const [committed, setCommitted] = useState(false);
  const [diagnosisLogs, setDiagnosisLogs] = useState<any[]>([]);

  // Load live graph topology and synchronize React Flow canvas
  const loadTopology = async () => {
    try {
      const resp = await fetch('/api/graph/topology');
      if (resp.ok) {
        const data = await resp.json();
        const topoNodes = data.nodes || [];
        const topoEdges = data.edges || [];
        setNodeCount(topoNodes.length);
        setEdgeCount(topoEdges.length);

        if (topoNodes.length > 0) {
          const knownMap: Record<string, { x: number; y: number; type?: string }> = {
            'internet': { x: 440, y: 30, type: 'serviceNode' },
            'route53': { x: 250, y: 90, type: 'serviceNode' },
            'waf': { x: 630, y: 90, type: 'serviceNode' },
            'prod-db': { x: 170, y: 200, type: 'criticalNode' },
            'api-gateway': { x: 400, y: 150, type: 'criticalNode' },
            'checkoutservice': { x: 580, y: 210, type: 'criticalNode' },
            'db-replica-1': { x: 180, y: 360, type: 'serviceNode' },
            'db-replica-2': { x: 300, y: 360, type: 'serviceNode' },
            'cartservice': { x: 480, y: 330, type: 'serviceNode' },
            'paymentservice': { x: 620, y: 340, type: 'criticalNode' },
            'shippingservice': { x: 760, y: 330, type: 'serviceNode' },
            'stripe-gateway': { x: 740, y: 440, type: 'serviceNode' },
            'prod-vpc': { x: 450, y: 440, type: 'vpcGroupNode' },
            'app-role': { x: 340, y: 550, type: 'iamRoleNode' },
            'deploy-role': { x: 500, y: 550, type: 'iamRoleNode' },
            'dba-role': { x: 660, y: 550, type: 'iamRoleNode' },
          };

          const dynamicNodes: Node[] = topoNodes.map((n: any, idx: number) => {
            const known = knownMap[n.id];
            let pos = { x: 140 + (idx % 5) * 160, y: 140 + Math.floor(idx / 5) * 110 };
            let nodeType = 'serviceNode';

            if (known) {
              pos = { x: known.x, y: known.y };
              if (known.type) nodeType = known.type;
            } else {
              if (n.label === 'Database') nodeType = 'serviceNode';
              else if (n.id.includes('gateway') || n.id.includes('checkout') || n.id.includes('payment')) nodeType = 'criticalNode';
            }

            const isCritical = nodeType === 'criticalNode';
            return {
              id: n.id,
              type: nodeType,
              position: pos,
              data: {
                label: n.id,
                sublabel: n.label || 'Service',
                iconType: n.label === 'Database' ? 'db' : (n.id.includes('gateway') ? 'gateway' : 'service'),
                status: isCritical ? 'critical' : 'normal',
                badge: isCritical ? 'CRITICAL' : (n.label === 'Database' ? 'DB' : undefined),
                subnets: ['Private Subnet 10.0.1.0/24', 'Public Subnet 10.0.2.0/24'],
              },
            };
          });

          const dynamicEdges: Edge[] = topoEdges.map((e: any, idx: number) => {
            const isCritical = e.type === 'CALLS';
            return {
              id: `e-${e.source}-${e.target}-${idx}`,
              source: e.source,
              target: e.target,
              className: isCritical ? 'edge-critical' : 'edge-dependency',
              animated: isCritical,
            };
          });

          setNodes(dynamicNodes);
          setEdges(dynamicEdges);
        }
      }
    } catch (e) {
      console.error('Topology load error:', e);
    }
  };

  // Simulation handler calling FastAPI backend
  const handleSimulatePR = async (prId: string) => {
    try {
      const resp = await fetch('/api/simulate-pr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pr_id: prId, target_service: 'paymentservice' }),
      });
      const data = await resp.json();
      setSimResult(data);
      await loadTopology();
    } catch (e) {
      console.error('Simulation error:', e);
    }
  };

  // Chaos injection handler
  const handleInjectFault = async () => {
    try {
      const resp = await fetch('/api/chaos/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fault_id: 'pool_exhaustion', target_service: 'paymentservice' }),
      });
      if (resp.ok) {
        setFaultActive(true);
        setHealed(false);
        const evResp = await fetch('/api/heal/events');
        if (evResp.ok) {
          const evData = await evResp.json();
          setDiagnosisLogs(evData);
        }
      }
    } catch (e) {
      console.error('Fault injection error:', e);
    }
  };

  // Guarded healing execution handler
  const handleHealAction = async () => {
    try {
      const resp = await fetch('/api/actuator/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'scale_pool',
          target: 'postgres-payment',
          params: { pool_size: 150 },
          rationale: 'Expand connection pool to relieve queue saturation',
        }),
      });
      if (resp.ok) {
        setHealed(true);
        setFaultActive(false);
      }
    } catch (e) {
      console.error('Heal action error:', e);
    }
  };

  // Closed loop memory commit handler (+5 score jump)
  const handleCommitIncident = async () => {
    try {
      const resp = await fetch('/api/memory/commit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_id: 'paymentservice',
          incident_description: 'PostgreSQL connection pool exhausted under spike',
          action_taken: 'scale_pool',
          outcome: 'success',
        }),
      });
      if (resp.ok) {
        setCommitted(true);
        await handleSimulatePR('PR-142');
      }
    } catch (e) {
      console.error('Commit error:', e);
    }
  };

  // Reset handler
  const handleReset = async () => {
    try {
      await fetch('/api/reset', { method: 'POST' });
      setFaultActive(false);
      setHealed(false);
      setCommitted(false);
      setDiagnosisLogs([]);
      await handleSimulatePR('PR-142');
      await loadTopology();
    } catch (e) {
      console.error('Reset error:', e);
    }
  };

  // Fast Ingestion of sample repository
  const handleQuickIngest = async (slug: string) => {
    try {
      const resp = await fetch('/api/ingest/repository', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: slug }),
      });
      if (resp.ok) {
        await loadTopology();
        alert(`Successfully scanned & ingested ${slug}! Graph updated.`);
      }
    } catch (e) {
      console.error('Quick ingest error:', e);
    }
  };

  // Highlight affected nodes when PREDICT runs
  const handleRiskAssessed = (result: any) => {
    setSimResult(result);
    const affectedNodeNames = new Set(result.blast_details?.map((c: any) => c.node) || []);
    setNodes((prevNodes) =>
      prevNodes.map((n) => {
        if (affectedNodeNames.has(n.id) || n.id === result.target_service) {
          return {
            ...n,
            type: 'criticalNode',
            data: { ...n.data, status: 'critical', badge: 'AFFECTED' },
          };
        }
        return n;
      })
    );
  };

  // Initial load
  useEffect(() => {
    handleSimulatePR('PR-142');
    loadTopology();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100vw', height: '100vh', backgroundColor: '#060a12', fontFamily: 'Inter, system-ui, sans-serif' }}>
      {/* 1. AEGIS Mission Control Top Header */}
      <header
        style={{
          height: 56,
          backgroundColor: '#080d1a',
          borderBottom: '1px solid #1e293b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 20px',
          zIndex: 30,
        }}
      >
        {/* Brand & Identity */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                backgroundColor: 'rgba(56, 189, 248, 0.15)',
                border: '1px solid #38bdf8',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#38bdf8',
                boxShadow: '0 0 12px rgba(56, 189, 248, 0.35)',
              }}
            >
              <Box size={18} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 18, fontWeight: 900, color: '#f8fafc', letterSpacing: '0.04em' }}>
                  AEGIS
                </span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    color: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.12)',
                    padding: '2px 7px',
                    borderRadius: 4,
                    border: '1px solid rgba(56, 189, 248, 0.25)',
                    letterSpacing: '0.05em',
                  }}
                >
                  PREDICT + MONITOR
                </span>
              </div>
              <div style={{ fontSize: 10, color: '#64748b', fontWeight: 500, letterSpacing: -0.1 }}>
                Autonomous Engineering Graph & Intelligence System
              </div>
            </div>
          </div>

          {/* Topology Badge */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 11,
              color: '#94a3b8',
              backgroundColor: '#0f172a',
              padding: '5px 12px',
              borderRadius: 6,
              border: '1px solid #1e293b',
            }}
          >
            <span style={{ color: '#38bdf8', fontWeight: 700 }}>{nodeCount} Nodes</span>
            <span style={{ color: '#475569' }}>•</span>
            <span style={{ color: '#94a3b8' }}>{edgeCount} Edges</span>
            <span style={{ color: '#475569' }}>•</span>
            <span style={{ color: '#10b981', fontWeight: 600 }}>NetworkX In-Memory</span>
          </div>
        </div>

        {/* Quick Action Navigation Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Quick Sample Repos Menu */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>Quick Repo:</span>
            <button
              onClick={() => handleQuickIngest('shop-sphere/ecommerce-core')}
              style={{
                padding: '5px 10px',
                borderRadius: 6,
                backgroundColor: '#0f172a',
                border: '1px solid #1e293b',
                color: '#38bdf8',
                fontSize: 11,
                cursor: 'pointer',
                fontFamily: 'JetBrains Mono, monospace',
              }}
              title="Ingest ShopSphere E-Commerce (11 Services)"
            >
              shop-sphere
            </button>
            <button
              onClick={() => handleQuickIngest('fintech-nexus/ledger-core')}
              style={{
                padding: '5px 10px',
                borderRadius: 6,
                backgroundColor: '#0f172a',
                border: '1px solid #1e293b',
                color: '#38bdf8',
                fontSize: 11,
                cursor: 'pointer',
                fontFamily: 'JetBrains Mono, monospace',
              }}
              title="Ingest Fintech Nexus Ledger (7 Services)"
            >
              fintech-nexus
            </button>
          </div>

          <div style={{ width: 1, height: 22, backgroundColor: '#1e293b' }} />

          {/* Action Modals Triggers */}
          <button
            onClick={() => setIsIngestionOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 12px',
              borderRadius: 6,
              backgroundColor: 'rgba(56, 189, 248, 0.1)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              color: '#38bdf8',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <GitBranch size={14} />
            Ingest Repos
          </button>

          <button
            onClick={() => setIsPredictOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 12px',
              borderRadius: 6,
              backgroundColor: 'rgba(249, 115, 22, 0.12)',
              border: '1px solid rgba(249, 115, 22, 0.3)',
              color: '#f97316',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Shield size={14} />
            Predict Risk
          </button>

          <button
            onClick={() => setIsMonitorOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 12px',
              borderRadius: 6,
              backgroundColor: faultActive ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.12)',
              border: faultActive ? '1px solid #ef4444' : '1px solid rgba(16, 185, 129, 0.3)',
              color: faultActive ? '#ef4444' : '#10b981',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Activity size={14} />
            {faultActive ? 'Monitor (Alerting)' : 'Monitor Health'}
          </button>

          <button
            onClick={handleReset}
            style={{
              padding: '6px 10px',
              borderRadius: 6,
              backgroundColor: '#0f172a',
              border: '1px solid #1e293b',
              color: '#94a3b8',
              fontSize: 11,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
            title="Reset Graph State"
          >
            <RotateCcw size={13} />
            Reset
          </button>
        </div>
      </header>

      {/* 2. Main Body (Navigation Sidebar + React Flow Canvas + Blast Radius Panel) */}
      <div style={{ display: 'flex', flex: 1, position: 'relative', overflow: 'hidden' }}>
        {/* Left Navigation Sidebar */}
        <nav
          style={{
            width: 200,
            backgroundColor: '#080d18',
            borderRight: '1px solid #1e293b',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: '16px 10px',
            zIndex: 20,
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {/* 1. Topology Canvas */}
            <button
              onClick={() => setActiveTab('canvas')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 12px',
                borderRadius: 7,
                backgroundColor: activeTab === 'canvas' ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                border: activeTab === 'canvas' ? '1px solid rgba(56, 189, 248, 0.3)' : '1px solid transparent',
                color: activeTab === 'canvas' ? '#38bdf8' : '#94a3b8',
                fontSize: 12,
                fontWeight: activeTab === 'canvas' ? 600 : 500,
                cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              <Network size={16} color={activeTab === 'canvas' ? '#38bdf8' : '#64748b'} />
              <span>Topology Canvas</span>
            </button>

            {/* 2. PREDICT Tab */}
            <button
              onClick={() => setIsPredictOpen(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 12px',
                borderRadius: 7,
                backgroundColor: 'rgba(249, 115, 22, 0.08)',
                border: '1px solid rgba(249, 115, 22, 0.2)',
                color: '#f97316',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              <Shield size={16} color="#f97316" />
              <span>PREDICT (Risk)</span>
            </button>

            {/* 3. MONITOR Tab */}
            <button
              onClick={() => setIsMonitorOpen(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 12px',
                borderRadius: 7,
                backgroundColor: faultActive ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.08)',
                border: faultActive ? '1px solid #ef4444' : '1px solid rgba(16, 185, 129, 0.2)',
                color: faultActive ? '#fca5a5' : '#34d399',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              <Activity size={16} color={faultActive ? '#ef4444' : '#10b981'} />
              <span>MONITOR (Health)</span>
            </button>

            {/* 4. Repository Ingestion Tab */}
            <button
              onClick={() => setIsIngestionOpen(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 12px',
                borderRadius: 7,
                backgroundColor: 'rgba(56, 189, 248, 0.08)',
                border: '1px solid rgba(56, 189, 248, 0.2)',
                color: '#38bdf8',
                fontSize: 12,
                fontWeight: 500,
                cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              <GitBranch size={16} color="#38bdf8" />
              <span>Git Repos & Ingest</span>
            </button>

            {/* 5. Diagnostic Terminal */}
            <button
              onClick={() => setIsReportOpen(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 12px',
                borderRadius: 7,
                backgroundColor: 'transparent',
                border: '1px solid transparent',
                color: '#94a3b8',
                fontSize: 12,
                fontWeight: 500,
                cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              <Terminal size={16} color="#64748b" />
              <span>Diagnosis Terminal</span>
            </button>
          </div>

          {/* SRE Review Scope Badge */}
          <div
            style={{
              padding: '10px 12px',
              borderRadius: 8,
              backgroundColor: '#0a101d',
              border: '1px solid #1e293b',
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
            }}
          >
            <div style={{ fontSize: 10, color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
              Scope: Phase 1
            </div>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#f8fafc' }}>
              Review 2 Mission
            </div>
            <div style={{ fontSize: 10, color: '#94a3b8', lineHeight: 1.3 }}>
              Seeded 54/142 Graph, Dynamic BFS, Real Formulas
            </div>
          </div>
        </nav>

        {/* Center Interactive Graph Canvas */}
        <div style={{ flex: 1, position: 'relative', height: '100%', backgroundColor: '#060a12' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            minZoom={0.2}
            maxZoom={1.5}
          >
            <Background color="#1e293b" gap={20} size={1} />
            <Controls
              style={{
                backgroundColor: '#0f172a',
                border: '1px solid #1e293b',
                borderRadius: 8,
                boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
                fill: '#94a3b8',
              }}
            />

            {/* Canvas Legend */}
            <div
              style={{
                position: 'absolute',
                bottom: 20,
                right: 20,
                padding: '10px 14px',
                borderRadius: 8,
                backgroundColor: 'rgba(10, 16, 28, 0.85)',
                border: '1px solid #1e293b',
                backdropFilter: 'blur(10px)',
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
                fontSize: 10,
                color: '#94a3b8',
                zIndex: 5,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ width: 16, height: 2, backgroundColor: '#f97316', boxShadow: '0 0 6px #f97316' }} />
                <span>Critical risk path</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ width: 16, height: 2, backgroundColor: '#334155' }} />
                <span>Dependency (CALLS)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ width: 16, height: 0, borderBottom: '2px dashed #64748b' }} />
                <span>Containment boundary</span>
              </div>
            </div>

            {/* MiniMap */}
            <MiniMap
              nodeStrokeWidth={3}
              style={{
                width: 140,
                height: 100,
                position: 'absolute',
                bottom: 20,
                left: 20,
              }}
            />
          </ReactFlow>
        </div>

        {/* Right Slide-Over Inspector */}
        <BlastRadiusPanel
          onSimulatePR={handleSimulatePR}
          onInjectFault={handleInjectFault}
          onHealAction={handleHealAction}
          onCommitIncident={handleCommitIncident}
          onReset={handleReset}
          simResult={simResult}
          faultActive={faultActive}
          healed={healed}
          committed={committed}
          onOpenReport={() => setIsReportOpen(true)}
        />
      </div>

      {/* 3. Bottom Layer Cards */}
      <BottomLayerCards
        nodeCount={nodeCount}
        edgeCount={edgeCount}
        riskScore={simResult?.risk_score ?? 13.4}
        riskCategory={simResult?.verdict ?? 'Approved'}
        activeAlertsCount={faultActive ? 1 : 0}
        onOpenPredict={() => setIsPredictOpen(true)}
        onOpenMonitor={() => setIsMonitorOpen(true)}
        onOpenIngest={() => setIsIngestionOpen(true)}
      />

      {/* 4. PREDICT Modal */}
      <PredictModal
        isOpen={isPredictOpen}
        onClose={() => setIsPredictOpen(false)}
        onRiskAssessed={handleRiskAssessed}
      />

      {/* 5. MONITOR Modal */}
      <MonitorModal
        isOpen={isMonitorOpen}
        onClose={() => setIsMonitorOpen(false)}
      />

      {/* 6. Repository Ingestion Modal */}
      <IngestionModal
        isOpen={isIngestionOpen}
        onClose={() => setIsIngestionOpen(false)}
        onIngestionSuccess={async () => {
          await loadTopology();
          await handleSimulatePR('PR-142');
        }}
      />

      {/* 7. Risk Report Terminal Drawer */}
      {isReportOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
          }}
        >
          <div
            style={{
              width: 820,
              maxHeight: '85vh',
              backgroundColor: '#0a101d',
              border: '1px solid #1e293b',
              borderRadius: 14,
              boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8)',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
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
                <Activity size={18} color="#38bdf8" />
                <span style={{ fontSize: 15, fontWeight: 700, color: '#f8fafc' }}>
                  Risk Intelligence & Diagnosis Report (PR #142)
                </span>
              </div>
              <button
                onClick={() => setIsReportOpen(false)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 18 }}>
              {/* Score Breakdown Row */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                <div style={{ padding: '12px', borderRadius: 8, backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: 10, color: '#64748b' }}>Blast Radius (B)</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: '#f8fafc', marginTop: 4 }}>
                    {simResult?.breakdown?.blast_score !== undefined ? Number(simResult.breakdown.blast_score).toFixed(1) : '--'}
                  </div>
                  <div style={{ fontSize: 9, color: '#94a3b8' }}>Weight: 0.35</div>
                </div>

                <div style={{ padding: '12px', borderRadius: 8, backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: 10, color: '#64748b' }}>Contract Diff (C)</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: '#f87171', marginTop: 4 }}>
                    {simResult?.breakdown?.contract_score !== undefined ? Number(simResult.breakdown.contract_score).toFixed(1) : '--'}
                  </div>
                  <div style={{ fontSize: 9, color: '#94a3b8' }}>Weight: 0.30</div>
                </div>

                <div style={{ padding: '12px', borderRadius: 8, backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: 10, color: '#64748b' }}>Cycle Penalty (D)</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: '#10b981', marginTop: 4 }}>
                    {simResult?.breakdown?.cycle_score !== undefined ? Number(simResult.breakdown.cycle_score).toFixed(1) : '--'}
                  </div>
                  <div style={{ fontSize: 9, color: '#94a3b8' }}>Weight: 0.15</div>
                </div>

                <div style={{ padding: '12px', borderRadius: 8, backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: 10, color: '#64748b' }}>Incident History (H)</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: committed ? '#c084fc' : '#94a3b8', marginTop: 4 }}>
                    {simResult?.breakdown?.history_score !== undefined ? Number(simResult.breakdown.history_score).toFixed(1) : (committed ? '25.0' : '0.0')}
                  </div>
                  <div style={{ fontSize: 9, color: '#94a3b8' }}>Weight: 0.20 ({committed ? '+5 pt jump' : 'Clean'})</div>
                </div>
              </div>

              {/* Streaming Diagnosis Terminal */}
              <div style={{ borderRadius: 10, backgroundColor: '#05080f', border: '1px solid #1e293b', overflow: 'hidden' }}>
                <div style={{ padding: '8px 14px', backgroundColor: '#0c1322', borderBottom: '1px solid #1e293b', display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: '#94a3b8' }}>
                  <Terminal size={14} color="#38bdf8" />
                  <span>Mission Control Streaming Terminal (SSE Reasoner)</span>
                </div>

                <div style={{ padding: '14px', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, lineHeight: 1.6, color: '#e2e8f0', maxHeight: 220, overflowY: 'auto' }}>
                  {diagnosisLogs.length > 0 ? (
                    diagnosisLogs.map((log, idx) => (
                      <div key={idx} style={{ marginBottom: 8 }}>
                        {log.type === 'thought' && (
                          <div style={{ color: '#38bdf8' }}>
                            <span style={{ color: '#64748b' }}>[THOUGHT]</span> {log.payload.message}
                          </div>
                        )}
                        {log.type === 'cypher' && (
                          <div style={{ color: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.08)', padding: '4px 8px', borderRadius: 4 }}>
                            <span style={{ color: '#64748b' }}>[CYPHER]</span> {log.payload.query}
                          </div>
                        )}
                        {log.type === 'candidates' && (
                          <div style={{ color: '#c084fc', marginTop: 4 }}>
                            <span style={{ color: '#64748b' }}>[CANDIDATES]</span> Ranked fix cards generated ({log.payload.candidates?.length} eligible plans).
                          </div>
                        )}
                        {log.type === 'result' && (
                          <div style={{ color: '#f59e0b', fontWeight: 600 }}>
                            <span style={{ color: '#64748b' }}>[RESULT]</span> {log.payload.hypothesis} (Confidence: {log.payload.confidence})
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div style={{ color: '#64748b' }}>
                      Ready. Click "Inject Pool Exhaustion Fault" on the right panel to stream live graph reasoning.
                    </div>
                  )}
                </div>
              </div>

              {/* Explanations List */}
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc', marginBottom: 8 }}>
                  Evidence & Graph Deductions:
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {(simResult?.explanation?.length ? simResult.explanation : ['No risk analysis executed yet. Run PR simulation or PREDICT analysis to compute deductions.']).map((exp: string, idx: number) => (
                    <div key={idx} style={{ padding: '8px 12px', borderRadius: 6, backgroundColor: '#0f172a', border: '1px solid #1e293b', fontSize: 11, color: '#94a3b8' }}>
                      • {exp}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
