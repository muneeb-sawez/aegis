import React, { useState, useEffect, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Network,
  RotateCcw,
  Search,
  Server,
  Activity,
  CheckCircle,
  Flame,
} from 'lucide-react';
import {
  CriticalNode,
  ServiceNode,
  VpcGroupNode,
  IamRoleNode,
} from '../components/CustomNodes';

const nodeTypes = {
  criticalNode: CriticalNode,
  serviceNode: ServiceNode,
  vpcGroupNode: VpcGroupNode,
  iamRoleNode: IamRoleNode,
};

interface TopologyPageProps {
  onNavigate?: (page: string, serviceId?: string) => void;
}

export const TopologyPage: React.FC<TopologyPageProps> = ({ onNavigate }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [rawNodes, setRawNodes] = useState<any[]>([]);
  const [rawEdges, setRawEdges] = useState<any[]>([]);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [filterLayer, setFilterLayer] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);

  const loadTopology = useCallback(async () => {
    setIsLoading(true);
    try {
      const resp = await fetch('/api/graph/topology');
      if (resp.ok) {
        const data = await resp.json();
        const topoNodes = data.nodes || [];
        const topoEdges = data.edges || [];
        setRawNodes(topoNodes);
        setRawEdges(topoEdges);

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

        const cols = Math.min(5, Math.max(3, Math.ceil(Math.sqrt(topoNodes.length))));

        const flowNodes: Node[] = topoNodes.map((n: any, idx: number) => {
          const known = knownMap[n.id];
          const col = idx % cols;
          const row = Math.floor(idx / cols);
          let pos = { x: 80 + col * 240, y: 60 + row * 160 };
          let nodeType = 'serviceNode';

          if (known) {
            pos = { x: known.x, y: known.y };
            if (known.type) nodeType = known.type;
          } else {
            if (n.label === 'Database') nodeType = 'serviceNode';
            else if (n.label === 'ExternalService' || n.id.startsWith('ext-')) nodeType = 'serviceNode';
            else if (n.id.includes('gateway') || n.id.includes('checkout') || n.id.includes('payment')) nodeType = 'criticalNode';
          }

          const isCritical = nodeType === 'criticalNode';
          const isExternal = n.label === 'ExternalService' || n.id.startsWith('ext-');
          const isDb = n.label === 'Database';

          const badge = isCritical ? 'CRITICAL' : isExternal ? 'EXTERNAL' : isDb ? 'DATABASE' : undefined;
          const iconType = isDb ? 'db' : (isExternal || n.id.includes('gateway')) ? 'gateway' : 'service';

          return {
            id: n.id,
            type: nodeType,
            position: pos,
            data: {
              raw: n,
              label: n.id,
              sublabel: n.properties?.name || n.label || 'Service',
              iconType,
              status: isCritical ? 'critical' : 'normal',
              badge,
              subnets: isExternal ? ['Public Internet / SaaS'] : ['Private Subnet 10.0.1.0/24', 'Public Subnet 10.0.2.0/24'],
            },
          };
        });

        const flowEdges: Edge[] = topoEdges.map((e: any, idx: number) => {
          const isCritical = e.type === 'CALLS' && (e.source.includes('checkout') || e.target.includes('payment') || e.target.includes('prod-db'));
          const isContainment = e.type === 'CONTAINS' || e.type === 'HOSTED_ON';

          return {
            id: `edge-${idx}-${e.source}-${e.target}`,
            source: e.source,
            target: e.target,
            className: isCritical ? 'edge-critical' : isContainment ? 'edge-containment' : 'edge-dependency',
            animated: isCritical,
            style: {
              stroke: isCritical ? '#f97316' : isContainment ? '#475569' : '#06b6d4',
              strokeWidth: isCritical ? 2.5 : 1.5,
              strokeDasharray: isContainment ? '5,5' : undefined,
            },
          };
        });

        setNodes(flowNodes);
        setEdges(flowEdges);
      }
    } catch (e) {
      console.error('Failed to load topology:', e);
    } finally {
      setIsLoading(false);
    }
  }, [setNodes, setEdges]);

  useEffect(() => {
    loadTopology();
  }, [loadTopology]);

  // Handle node selection
  const handleNodeClick = (_: any, node: Node) => {
    const raw = rawNodes.find((n) => n.id === node.id);
    setSelectedNode(raw || node.data);
  };

  const handleResetBaseline = async () => {
    setIsLoading(true);
    setResetMessage(null);
    try {
      const resp = await fetch('/api/reset', { method: 'POST' });
      if (resp.ok) {
        const data = await resp.json();
        setResetMessage(`Reset successfully: ${data.node_count} nodes, ${data.edge_count} edges.`);
        await loadTopology();
      }
    } catch (e) {
      console.error('Reset baseline error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  // Filtered nodes based on search and layer
  const filteredNodes = nodes.filter((n) => {
    const matchesSearch = n.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (n.data?.label && String(n.data.label).toLowerCase().includes(searchQuery.toLowerCase()));
    
    if (!matchesSearch) return false;

    if (filterLayer === 'all') return true;
    if (filterLayer === 'services') return n.type === 'serviceNode' || n.type === 'criticalNode';
    if (filterLayer === 'critical') return n.type === 'criticalNode';
    if (filterLayer === 'vpc') return n.type === 'vpcGroupNode' || n.id.includes('vpc');
    if (filterLayer === 'iam') return n.type === 'iamRoleNode' || n.id.includes('role');
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative', overflow: 'hidden' }}>
      {/* Top Filter & Command Toolbar */}
      <div
        style={{
          padding: '12px 24px',
          backgroundColor: '#0a101d',
          borderBottom: '1px solid #1e293b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
          zIndex: 10,
        }}
      >
        {/* Left: Search & Layer Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search size={14} color="#64748b" style={{ position: 'absolute', left: 10 }} />
            <input
              type="text"
              placeholder="Search nodes in graph..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                padding: '6px 10px 6px 30px',
                backgroundColor: '#0f172a',
                border: '1px solid #1e293b',
                borderRadius: 6,
                color: '#f8fafc',
                fontSize: 12,
                outline: 'none',
                width: 220,
              }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 4, backgroundColor: '#0f172a', padding: 2, borderRadius: 6, border: '1px solid #1e293b' }}>
            {[
              { id: 'all', label: 'All Layers' },
              { id: 'services', label: 'Microservices' },
              { id: 'critical', label: 'Critical Path' },
              { id: 'vpc', label: 'VPC' },
              { id: 'iam', label: 'IAM Roles' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setFilterLayer(tab.id)}
                style={{
                  padding: '4px 10px',
                  borderRadius: 4,
                  border: 'none',
                  backgroundColor: filterLayer === tab.id ? '#1e293b' : 'transparent',
                  color: filterLayer === tab.id ? '#38bdf8' : '#94a3b8',
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#64748b' }}>
            <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', backgroundColor: '#10b981' }} />
            <span>{rawNodes.length} Nodes</span>
            <span>•</span>
            <span>{rawEdges.length} Graph Edges</span>
          </div>
        </div>

        {/* Right: Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {resetMessage && (
            <div style={{ fontSize: 11, color: '#10b981', display: 'flex', alignItems: 'center', gap: 4 }}>
              <CheckCircle size={12} />
              <span>{resetMessage}</span>
            </div>
          )}

          <button
            onClick={handleResetBaseline}
            disabled={isLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 12px',
              borderRadius: 6,
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#f87171',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={12} />
            <span>Reset Demo Baseline</span>
          </button>

          <button
            onClick={loadTopology}
            disabled={isLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 12px',
              borderRadius: 6,
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              color: '#f8fafc',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Network size={12} color="#38bdf8" />
            <span>Refresh Graph</span>
          </button>
        </div>
      </div>

      {/* Main Graph Canvas Area */}
      <div style={{ flex: 1, position: 'relative', width: '100%', height: '100%', backgroundColor: '#060a12' }}>
        <ReactFlow
          nodes={filteredNodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          fitView
          minZoom={0.2}
          maxZoom={1.8}
        >
          <Background color="#1e293b" gap={20} size={1} />
          <Controls style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }} />
          <MiniMap
            style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
            nodeColor={(n) => {
              if (n.type === 'criticalNode') return '#f97316';
              if (n.type === 'vpcGroupNode') return '#06b6d4';
              if (n.type === 'iamRoleNode') return '#8b5cf6';
              return '#3b82f6';
            }}
          />
        </ReactFlow>

        {/* Slide-Out Node Inspector Drawer */}
        {selectedNode && (
          <div
            style={{
              position: 'absolute',
              top: 16,
              right: 16,
              width: 380,
              maxHeight: 'calc(100% - 32px)',
              backgroundColor: '#0c1322',
              border: '1px solid #1e293b',
              borderRadius: 12,
              boxShadow: '0 10px 40px rgba(0,0,0,0.7)',
              zIndex: 30,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              backdropFilter: 'blur(12px)',
            }}
          >
            {/* Drawer Header */}
            <div
              style={{
                padding: '14px 18px',
                borderBottom: '1px solid #1e293b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                backgroundColor: '#0f172a',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    backgroundColor: 'rgba(6, 182, 212, 0.15)',
                    border: '1px solid rgba(6, 182, 212, 0.4)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#06b6d4',
                  }}
                >
                  <Server size={16} />
                </div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>{selectedNode.id}</div>
                  <div style={{ fontSize: 11, color: '#64748b' }}>{selectedNode.label || 'Microservice Node'}</div>
                </div>
              </div>

              <button
                onClick={() => setSelectedNode(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#64748b',
                  fontSize: 18,
                  cursor: 'pointer',
                  padding: 4,
                }}
              >
                ✕
              </button>
            </div>

            {/* Drawer Body */}
            <div style={{ padding: 18, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Properties Card */}
              <div style={{ backgroundColor: '#070b14', padding: 12, borderRadius: 8, border: '1px solid #1e293b' }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 8 }}>
                  Node Metadata & Telemetry
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 11 }}>
                  <div>
                    <span style={{ color: '#64748b' }}>Type:</span>{' '}
                    <span style={{ color: '#f8fafc', fontWeight: 600 }}>{selectedNode.label || 'Service'}</span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>Tier:</span>{' '}
                    <span style={{ color: '#38bdf8', fontWeight: 600 }}>Core Microservice</span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>p99 Latency:</span>{' '}
                    <span style={{ color: '#10b981', fontWeight: 600 }}>
                      {selectedNode.properties?.p99_ms ? `${selectedNode.properties.p99_ms}ms` : '38ms (baseline)'}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>Error Rate:</span>{' '}
                    <span style={{ color: '#10b981', fontWeight: 600 }}>
                      {selectedNode.properties?.error_rate !== undefined ? `${(selectedNode.properties.error_rate * 100).toFixed(1)}%` : '0.01%'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Connected Relationships */}
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 8 }}>
                  Graph Topology Connections
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {rawEdges
                    .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                    .slice(0, 6)
                    .map((e, idx) => {
                      const isOutgoing = e.source === selectedNode.id;
                      return (
                        <div
                          key={idx}
                          style={{
                            padding: '6px 10px',
                            borderRadius: 6,
                            backgroundColor: '#0f172a',
                            border: '1px solid #1e293b',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            fontSize: 11,
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span style={{ color: isOutgoing ? '#f97316' : '#06b6d4', fontWeight: 600 }}>
                              {isOutgoing ? 'OUTGOING' : 'INBOUND'}
                            </span>
                            <span style={{ color: '#64748b' }}>({e.type || 'CALLS'})</span>
                          </div>
                          <span style={{ color: '#f8fafc', fontWeight: 600 }}>
                            {isOutgoing ? e.target : e.source}
                          </span>
                        </div>
                      );
                    })}
                </div>
              </div>

              {/* Action Shortcuts */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 }}>
                <button
                  onClick={() => onNavigate && onNavigate('predict', selectedNode.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    padding: '8px 12px',
                    borderRadius: 6,
                    backgroundColor: 'rgba(249, 115, 22, 0.15)',
                    border: '1px solid rgba(249, 115, 22, 0.4)',
                    color: '#f97316',
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  <Activity size={14} />
                  <span>Analyze Change Risk in PREDICT</span>
                </button>

                <button
                  onClick={() => onNavigate && onNavigate('chaos', selectedNode.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    padding: '8px 12px',
                    borderRadius: 6,
                    backgroundColor: 'rgba(239, 68, 68, 0.15)',
                    border: '1px solid rgba(239, 68, 68, 0.4)',
                    color: '#f87171',
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  <Flame size={14} />
                  <span>Inject Chaos Experiment</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
