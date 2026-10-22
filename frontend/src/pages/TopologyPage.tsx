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
import { LatencySparkline } from '../components/LatencySparkline';

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
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [filterLayer, setFilterLayer] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [streamMode, setStreamMode] = useState<'sse' | 'polling' | 'connecting'>('connecting');
  const [lastEventTime, setLastEventTime] = useState<string | null>(null);

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

        // Fetch current health state snapshot
        let healthMap = new Map<string, any>();
        try {
          const hResp = await fetch('/api/monitor/status');
          if (hResp.ok) {
            const hList = await hResp.json();
            for (const h of hList) {
              healthMap.set(h.service_id, h);
            }
          }
        } catch {
          // ignore monitor status fetch error on boot
        }

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

          const healthRec = healthMap.get(n.id);

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
              healthStatus: healthRec ? healthRec.status : (isCritical ? 'healthy' : undefined),
              latency_ms: healthRec?.response_time_ms,
              baseline_latency_ms: healthRec?.baseline_latency_ms,
              rolling_latencies: healthRec?.rolling_latencies || [],
              error_rate: healthRec?.error_rate,
              consecutive_failures: healthRec?.consecutive_failures,
              alertBadge: healthRec?.status === 'unavailable' || healthRec?.status === 'unhealthy',
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

  // Live SSE connection with automatic 3s polling fallback
  useEffect(() => {
    let eventSource: EventSource | null = null;
    let pollInterval: ReturnType<typeof setInterval> | null = null;
    let isMounted = true;

    const updateNodeHealth = (serviceId: string, payload: any) => {
      setLastEventTime(new Date().toLocaleTimeString());
      setNodes((prevNodes) =>
        prevNodes.map((n) => {
          if (n.id === serviceId) {
            const currentData = n.data || {};
            const prevRolling = (currentData.rolling_latencies as number[]) || [];
            let updatedRolling = payload.rolling_latencies;
            if (!updatedRolling) {
              if (payload.latency_ms !== undefined && payload.latency_ms !== null) {
                updatedRolling = [...prevRolling.slice(-19), payload.latency_ms];
              } else {
                updatedRolling = prevRolling;
              }
            }

            return {
              ...n,
              data: {
                ...currentData,
                healthStatus: payload.status ?? currentData.healthStatus,
                latency_ms: payload.latency_ms !== undefined ? payload.latency_ms : currentData.latency_ms,
                baseline_latency_ms: payload.baseline_latency_ms !== undefined ? payload.baseline_latency_ms : currentData.baseline_latency_ms,
                rolling_latencies: updatedRolling,
                error_rate: payload.error_rate !== undefined ? payload.error_rate : currentData.error_rate,
                consecutive_failures: payload.consecutive_failures !== undefined ? payload.consecutive_failures : currentData.consecutive_failures,
                alertBadge: payload.status === 'unavailable' || payload.status === 'unhealthy',
              },
            };
          }
          return n;
        })
      );
    };

    const startPolling = () => {
      if (pollInterval || !isMounted) return;
      setStreamMode('polling');
      const poll = async () => {
        try {
          const res = await fetch('/api/monitor/status');
          if (res.ok && isMounted) {
            const list = await res.json();
            for (const item of list) {
              updateNodeHealth(item.service_id, {
                status: item.status,
                latency_ms: item.response_time_ms,
                baseline_latency_ms: item.baseline_latency_ms,
                rolling_latencies: item.rolling_latencies,
                error_rate: item.error_rate,
                consecutive_failures: item.consecutive_failures,
              });
            }
          }
        } catch (err) {
          console.warn('[Monitor] Polling error:', err);
        }
      };
      poll();
      pollInterval = setInterval(poll, 3000);
    };

    const connectSSE = () => {
      try {
        eventSource = new EventSource('/api/monitor/events');

        eventSource.onopen = () => {
          if (isMounted) {
            setStreamMode('sse');
            if (pollInterval) {
              clearInterval(pollInterval);
              pollInterval = null;
            }
          }
        };

        eventSource.onmessage = (e) => {
          if (!isMounted) return;
          try {
            const evt = JSON.parse(e.data);
            if (evt && evt.payload && evt.payload.service_id) {
              updateNodeHealth(evt.payload.service_id, evt.payload);
            }
          } catch {
            // Ignore keep-alive or malformed frames
          }
        };

        eventSource.onerror = (err) => {
          console.warn('[Monitor] SSE connection error, switching to polling:', err);
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          if (isMounted) {
            startPolling();
          }
        };
      } catch (err) {
        console.warn('[Monitor] Could not initialize EventSource:', err);
        if (isMounted) {
          startPolling();
        }
      }
    };

    connectSSE();

    return () => {
      isMounted = false;
      if (eventSource) {
        eventSource.close();
      }
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [setNodes]);

  // Handle node selection
  const handleNodeClick = (_: any, node: Node) => {
    setSelectedNodeId(node.id);
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

  // Derive active selected node with live telemetry
  const activeFlowNode = selectedNodeId ? nodes.find((n) => n.id === selectedNodeId) : null;
  const activeRawNode = selectedNodeId ? rawNodes.find((n) => n.id === selectedNodeId) : null;
  const selectedNode = activeFlowNode
    ? {
        id: activeFlowNode.id,
        type: activeFlowNode.type,
        data: activeFlowNode.data,
        raw: activeRawNode,
        label: (activeFlowNode.data?.label as string) || activeRawNode?.label || 'Microservice',
        properties: activeRawNode?.properties || {},
        healthStatus: (activeFlowNode.data?.healthStatus as string) || 'healthy',
        latency_ms: activeFlowNode.data?.latency_ms as number | undefined,
        baseline_latency_ms: activeFlowNode.data?.baseline_latency_ms as number | undefined,
        rolling_latencies: (activeFlowNode.data?.rolling_latencies as number[]) || [],
        error_rate: activeFlowNode.data?.error_rate as number | undefined,
        consecutive_failures: activeFlowNode.data?.consecutive_failures as number | undefined,
      }
    : null;

  // Filtered nodes based on search and layer
  const filteredNodes = nodes.filter((n) => {
    const matchesSearch =
      n.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
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
        </div>

        {/* Right: Live Monitor Status & Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Live Telemetry Stream Indicator */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 10px',
              borderRadius: 20,
              backgroundColor:
                streamMode === 'sse'
                  ? 'rgba(16, 185, 129, 0.12)'
                  : streamMode === 'polling'
                  ? 'rgba(245, 158, 11, 0.12)'
                  : 'rgba(100, 116, 139, 0.12)',
              border: `1px solid ${
                streamMode === 'sse'
                  ? '#10b981'
                  : streamMode === 'polling'
                  ? '#f59e0b'
                  : '#334155'
              }`,
              fontSize: 11,
              fontWeight: 600,
              color:
                streamMode === 'sse'
                  ? '#10b981'
                  : streamMode === 'polling'
                  ? '#f59e0b'
                  : '#94a3b8',
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                backgroundColor:
                  streamMode === 'sse'
                    ? '#10b981'
                    : streamMode === 'polling'
                    ? '#f59e0b'
                    : '#94a3b8',
                boxShadow:
                  streamMode === 'sse'
                    ? '0 0 8px #10b981'
                    : streamMode === 'polling'
                    ? '0 0 8px #f59e0b'
                    : 'none',
              }}
            />
            <span>
              {streamMode === 'sse'
                ? 'SSE Live Stream'
                : streamMode === 'polling'
                ? 'Polling (3s fallback)'
                : 'Connecting...'}
            </span>
            {lastEventTime && (
              <span style={{ fontSize: 10, color: '#64748b', marginLeft: 2 }}>({lastEventTime})</span>
            )}
          </div>

          {resetMessage && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                borderRadius: 6,
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                color: '#10b981',
                fontSize: 11,
                fontWeight: 600,
              }}
            >
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
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.18 }}
          minZoom={0.2}
          maxZoom={2}
          defaultEdgeOptions={{ type: 'smoothstep' }}
        >
          <Background color="#1e293b" gap={20} size={1} />
          <Controls style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }} />
          <MiniMap
            style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
            nodeColor={(n) => {
              const hs = n.data?.healthStatus as string | undefined;
              if (hs === 'unavailable' || hs === 'unhealthy') return '#ef4444';
              if (hs === 'degraded') return '#f59e0b';
              if (hs === 'healthy') return '#10b981';
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
                    backgroundColor:
                      selectedNode.healthStatus === 'unavailable' || selectedNode.healthStatus === 'unhealthy'
                        ? 'rgba(239, 68, 68, 0.2)'
                        : selectedNode.healthStatus === 'degraded'
                        ? 'rgba(245, 158, 11, 0.2)'
                        : 'rgba(6, 182, 212, 0.15)',
                    border: `1px solid ${
                      selectedNode.healthStatus === 'unavailable' || selectedNode.healthStatus === 'unhealthy'
                        ? '#ef4444'
                        : selectedNode.healthStatus === 'degraded'
                        ? '#f59e0b'
                        : 'rgba(6, 182, 212, 0.4)'
                    }`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color:
                      selectedNode.healthStatus === 'unavailable' || selectedNode.healthStatus === 'unhealthy'
                        ? '#ef4444'
                        : selectedNode.healthStatus === 'degraded'
                        ? '#f59e0b'
                        : '#06b6d4',
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
                onClick={() => setSelectedNodeId(null)}
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
              {/* Live Telemetry Sparkline */}
              <div>
                <div
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    color: '#94a3b8',
                    textTransform: 'uppercase',
                    marginBottom: 8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <span>Live Latency Sparkline</span>
                  <span style={{ fontSize: 10, color: '#64748b', textTransform: 'none' }}>
                    simulated / emulator time
                  </span>
                </div>
                <LatencySparkline
                  latencies={selectedNode.rolling_latencies}
                  baseline={selectedNode.baseline_latency_ms}
                  status={selectedNode.healthStatus}
                  width={342}
                  height={65}
                />
              </div>

              {/* Node Metadata & Telemetry */}
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
                    <span style={{ color: '#64748b' }}>Health Status:</span>{' '}
                    <span
                      style={{
                        color:
                          selectedNode.healthStatus === 'healthy'
                            ? '#10b981'
                            : selectedNode.healthStatus === 'degraded'
                            ? '#f59e0b'
                            : selectedNode.healthStatus === 'unavailable' || selectedNode.healthStatus === 'unhealthy'
                            ? '#ef4444'
                            : '#94a3b8',
                        fontWeight: 700,
                      }}
                    >
                      {selectedNode.healthStatus.toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>Current Latency:</span>{' '}
                    <span style={{ color: '#38bdf8', fontWeight: 600 }}>
                      {selectedNode.latency_ms !== undefined && selectedNode.latency_ms !== null
                        ? `${selectedNode.latency_ms.toFixed(1)}ms`
                        : 'pending'}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>Baseline Latency:</span>{' '}
                    <span style={{ color: '#10b981', fontWeight: 600 }}>
                      {selectedNode.baseline_latency_ms !== undefined && selectedNode.baseline_latency_ms !== null
                        ? `${selectedNode.baseline_latency_ms.toFixed(1)}ms`
                        : 'calibrating'}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>Error Rate:</span>{' '}
                    <span
                      style={{
                        color: selectedNode.error_rate && selectedNode.error_rate > 0 ? '#ef4444' : '#10b981',
                        fontWeight: 600,
                      }}
                    >
                      {selectedNode.error_rate !== undefined
                        ? `${(selectedNode.error_rate * 100).toFixed(1)}%`
                        : '0.0%'}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>Consecutive Fails:</span>{' '}
                    <span
                      style={{
                        color:
                          selectedNode.consecutive_failures && selectedNode.consecutive_failures > 0
                            ? '#ef4444'
                            : '#94a3b8',
                        fontWeight: 600,
                      }}
                    >
                      {selectedNode.consecutive_failures ?? 0}
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
