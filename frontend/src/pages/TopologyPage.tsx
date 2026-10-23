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
  KeyRound,
  Sparkles,
  Loader2,
} from 'lucide-react';
import {
  CriticalNode,
  ServiceNode,
  VpcGroupNode,
  IamRoleNode,
} from '../components/CustomNodes';
import { LiveBeatEdge } from '../components/LiveBeatEdge';
import { LatencySparkline } from '../components/LatencySparkline';
import { GraphChatDrawer } from '../components/GraphChatDrawer';
import {
  getActiveProjectId,
  setActiveProjectId,
  getAuthHeaders,
  apiUrl,
} from '../config';

const nodeTypes = {
  criticalNode: CriticalNode,
  serviceNode: ServiceNode,
  vpcGroupNode: VpcGroupNode,
  iamRoleNode: IamRoleNode,
};

const edgeTypes = {
  liveBeatEdge: LiveBeatEdge,
};

const knownMap: Record<string, { x: number; y: number; type?: string }> = {
  // Online Boutique / Core Demo Topology
  'internet': { x: 440, y: 30, type: 'serviceNode' },
  'route53': { x: 250, y: 90, type: 'serviceNode' },
  'waf': { x: 630, y: 90, type: 'serviceNode' },
  'prod-db': { x: 170, y: 200, type: 'criticalNode' },
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

  // Spring Petclinic Java Microservices Architecture Layout
  'api-gateway': { x: 420, y: 50, type: 'criticalNode' },
  'customers-service': { x: 180, y: 220, type: 'criticalNode' },
  'visits-service': { x: 420, y: 220, type: 'criticalNode' },
  'vets-service': { x: 660, y: 220, type: 'criticalNode' },
  'genai-service': { x: 900, y: 220, type: 'serviceNode' },
  'mysql-customers': { x: 180, y: 410, type: 'serviceNode' },
  'mysql-visits': { x: 420, y: 410, type: 'serviceNode' },
  'mysql-vets': { x: 660, y: 410, type: 'serviceNode' },
  'config-server': { x: 180, y: 50, type: 'serviceNode' },
  'discovery-server': { x: 660, y: 50, type: 'serviceNode' },
  'admin-server': { x: 900, y: 50, type: 'serviceNode' },
  'tracing-server': { x: 900, y: 410, type: 'serviceNode' },
  'prometheus-server': { x: 1080, y: 140, type: 'serviceNode' },
  'grafana-server': { x: 1080, y: 280, type: 'serviceNode' },
};

interface BlastContext {
  target_service: string;
  upstream_callers: string[];
  risk_score?: number;
  verdict?: string;
  pr_number?: number;
  pr_title?: string;
  breaking_changes?: string[];
  timestamp?: number;
}

const getStoredBlastContext = (): BlastContext | null => {
  try {
    const raw = localStorage.getItem('aegis_blast_context');
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
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
  const [activeProjectId, setActiveProjectIdState] = useState<string>(getActiveProjectId());
  const [projectsList, setProjectsList] = useState<any[]>([]);
  const [blastContext, setBlastContext] = useState<BlastContext | null>(getStoredBlastContext);
  const [isChatOpen, setIsChatOpen] = useState(false);

  const loadTopology = useCallback(async (targetPid?: string, overrideBlast?: BlastContext | null) => {
    const pid = targetPid || activeProjectId;
    setIsLoading(true);
    try {
      const resp = await fetch(apiUrl(`/api/graph/topology?project_id=${pid}`), {
        headers: getAuthHeaders(pid),
      });
      if (resp.ok) {
        const data = await resp.json();
        const topoNodes = data.nodes || [];
        const topoEdges = data.edges || [];
        setRawNodes(topoNodes);
        setRawEdges(topoEdges);

        // Fetch current health state snapshot for active project
        let healthMap = new Map<string, any>();
        try {
          const hResp = await fetch(apiUrl(`/api/monitor/status?project_id=${pid}`), {
            headers: getAuthHeaders(pid),
          });
          if (hResp.ok) {
            const hList = await hResp.json();
            for (const h of hList) {
              healthMap.set(h.service_id, h);
            }
          }
        } catch {
          // ignore monitor status fetch error on boot
        }

        const currentBlast = overrideBlast !== undefined ? overrideBlast : getStoredBlastContext();
        const blastTarget = (
          currentBlast?.target_service ||
          (currentBlast as any)?.target ||
          (currentBlast as any)?.service_id ||
          ''
        ).toLowerCase();

        const rawBlastCallers = currentBlast?.upstream_callers || (currentBlast as any)?.callers || [];
        const blastCallers: string[] = Array.isArray(rawBlastCallers)
          ? rawBlastCallers.map((c: any) => String(c).toLowerCase())
          : [];

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
            if (n.label === 'Database' || n.id.includes('mysql') || n.id.includes('postgres')) nodeType = 'serviceNode';
            else if (n.label === 'ExternalService' || n.id.startsWith('ext-')) nodeType = 'serviceNode';
            else if (n.id.includes('gateway') || n.id.includes('checkout') || n.id.includes('payment') || n.id.includes('customer') || n.id.includes('visit')) nodeType = 'criticalNode';
          }

          const isCritical = nodeType === 'criticalNode';
          const isExternal = n.label === 'ExternalService' || n.id.startsWith('ext-');
          const isDb = n.label === 'Database' || n.id.includes('mysql') || n.id.includes('postgres') || n.id.includes('redis');

          const isBlastTarget = Boolean(blastTarget && n.id.toLowerCase() === blastTarget);
          const isBlastImpacted = Boolean(blastCallers.includes(n.id.toLowerCase()));

          if (isBlastTarget || isBlastImpacted) {
            nodeType = 'criticalNode';
          }

          const badge = isBlastTarget
            ? `🎯 TARGET (${(currentBlast?.verdict || 'BLOCKED').toUpperCase()})`
            : isBlastImpacted
            ? '💥 BLAST CALLER (HOP 1)'
            : isCritical
            ? 'CRITICAL'
            : isExternal
            ? 'EXTERNAL'
            : isDb
            ? 'DATABASE'
            : undefined;

          const iconType = isDb ? 'db' : (isExternal || n.id.includes('gateway')) ? 'gateway' : 'service';
          const healthRec = healthMap.get(n.id);

          return {
            id: n.id,
            type: nodeType,
            position: pos,
            data: {
              raw: n,
              label: n.id,
              sublabel: isBlastTarget
                ? 'Target Service (Risk Floor)'
                : isBlastImpacted
                ? 'Upstream Blast Impact'
                : (n.properties?.name || n.properties?.technology || n.label || 'Service'),
              iconType,
              status: isBlastTarget || isCritical ? 'critical' : 'normal',
              badge,
              subnets: isExternal ? ['Public Internet / SaaS'] : ['Private Subnet 10.0.1.0/24', 'Public Subnet 10.0.2.0/24'],
              healthStatus: isBlastTarget
                ? 'unavailable'
                : isBlastImpacted
                ? 'degraded'
                : healthRec ? healthRec.status : (isCritical ? 'healthy' : undefined),
              isBlastTarget,
              isBlastImpacted,
              blastVerdict: currentBlast?.verdict || 'Blocked',
              blastRisk: currentBlast?.risk_score,
              blastReason: isBlastTarget
                ? (currentBlast?.breaking_changes && currentBlast.breaking_changes.length > 0
                    ? `🚨 Breaking Contract Diff: ${currentBlast.breaking_changes.join('; ')}. Upstream callers will fail deserialization.`
                    : `🚨 Breaking API schema contract change detected in PR #${currentBlast?.pr_number || '3'}.`)
                : isBlastImpacted
                ? `⚠️ Upstream caller directly calling '${blastTarget}'. Will fail at runtime due to breaking contract diff in PR #${currentBlast?.pr_number || '3'}.`
                : undefined,
              blastPrNumber: currentBlast?.pr_number,
              blastPrTitle: currentBlast?.pr_title,
              latency_ms: healthRec?.response_time_ms,
              baseline_latency_ms: healthRec?.baseline_latency_ms,
              rolling_latencies: healthRec?.rolling_latencies || [],
              error_rate: healthRec?.error_rate,
              consecutive_failures: healthRec?.consecutive_failures,
              alertBadge: isBlastTarget || isBlastImpacted || healthRec?.status === 'unavailable' || healthRec?.status === 'unhealthy',
            },
          };
        });

        const flowEdges: Edge[] = topoEdges.map((e: any, idx: number) => {
          const isBlastPath = Boolean(
            blastTarget && blastCallers.length > 0 &&
            ((blastCallers.includes(String(e.source).toLowerCase()) && String(e.target).toLowerCase() === blastTarget) ||
             (String(e.source).toLowerCase() === blastTarget && blastCallers.includes(String(e.target).toLowerCase())))
          );

          const isCritical = (e.type === 'CALLS' && (
            e.source.includes('checkout') ||
            e.target.includes('payment') ||
            e.target.includes('prod-db') ||
            e.source.includes('gateway') ||
            e.source.includes('api-gateway')
          )) || isBlastPath;
          const isContainment = e.type === 'CONTAINS' || e.type === 'HOSTED_ON';

          const srcRec = healthMap.get(e.source);
          const tgtRec = healthMap.get(e.target);
          const srcHealth = srcRec ? srcRec.status : (isCritical ? 'healthy' : undefined);
          const tgtHealth = tgtRec ? tgtRec.status : undefined;

          const isCallOrDepends = e.type === 'CALLS' || e.type === 'DEPENDS_ON' || isBlastPath;
          const isLive = isBlastPath || (isCallOrDepends && (srcHealth === 'healthy' || tgtHealth === 'healthy' || isCritical));
          const status = isBlastPath
            ? 'unavailable'
            : (srcHealth === 'unavailable' || tgtHealth === 'unavailable')
            ? 'unavailable'
            : (srcHealth === 'degraded' || tgtHealth === 'degraded')
            ? 'degraded'
            : isLive
            ? 'healthy'
            : 'unconfigured';

          return {
            id: `edge-${idx}-${e.source}-${e.target}`,
            source: e.source,
            target: e.target,
            type: isContainment ? 'smoothstep' : 'liveBeatEdge',
            className: isBlastPath ? 'edge-blast-path' : isCritical ? 'edge-critical' : isContainment ? 'edge-containment' : 'edge-dependency',
            animated: isCritical || isBlastPath,
            data: {
              isLive,
              isBlastPath,
              status,
              sourceHealth: isBlastPath ? 'degraded' : srcHealth,
              targetHealth: isBlastPath ? 'unavailable' : tgtHealth,
              isCritical,
              label: isBlastPath ? 'BLAST FLOW' : e.type,
            },
            style: {
              stroke: isBlastPath ? '#ef4444' : isCritical ? '#06b6d4' : isContainment ? '#475569' : '#10b981',
              strokeWidth: isBlastPath ? 3.5 : isCritical ? 2.2 : 1.5,
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
  }, [activeProjectId, setNodes, setEdges]);

  const handleClearBlast = () => {
    localStorage.removeItem('aegis_blast_context');
    setBlastContext(null);
    window.dispatchEvent(new CustomEvent('aegis_blast_context_changed', { detail: null }));

    // Instant zero-latency visual reset of nodes and edges
    setNodes((prevNodes) =>
      prevNodes.map((n) => {
        const isBlast = n.data?.isBlastTarget || n.data?.isBlastImpacted;
        if (!isBlast) return n;
        const known = knownMap[n.id];
        const isCritical = (known && known.type === 'criticalNode') ||
          n.id.includes('gateway') ||
          n.id.includes('customer') ||
          n.id.includes('checkout') ||
          n.id.includes('payment');
        return {
          ...n,
          type: isCritical ? 'criticalNode' : 'serviceNode',
          data: {
            ...n.data,
            isBlastTarget: false,
            isBlastImpacted: false,
            blastVerdict: undefined,
            blastRisk: undefined,
            blastReason: undefined,
            blastPrNumber: undefined,
            blastPrTitle: undefined,
            badge: isCritical ? 'CRITICAL' : undefined,
            sublabel: ((n.data as any)?.raw?.properties?.name || (n.data as any)?.raw?.label || 'Microservice'),
            healthStatus: 'healthy',
            status: isCritical ? 'critical' : 'normal',
            alertBadge: false,
          },
        };
      })
    );

    setEdges((prevEdges) =>
      prevEdges.map((e) => {
        if (!e.data?.isBlastPath) return e;
        const isCritical = e.data?.isCritical;
        return {
          ...e,
          className: isCritical ? 'edge-critical' : 'edge-dependency',
          data: {
            ...e.data,
            isBlastPath: false,
            status: 'healthy',
            label: 'CALLS',
          },
          style: {
            ...e.style,
            stroke: isCritical ? '#06b6d4' : '#10b981',
            strokeWidth: isCritical ? 2.2 : 1.5,
          },
        };
      })
    );

    loadTopology(activeProjectId, null);
  };

  useEffect(() => {
    const onBlastChanged = (e: any) => {
      const updated = e.detail !== undefined ? e.detail : getStoredBlastContext();
      setBlastContext(updated);
      loadTopology(activeProjectId, updated);
    };
    window.addEventListener('aegis_blast_context_changed', onBlastChanged);
    return () => window.removeEventListener('aegis_blast_context_changed', onBlastChanged);
  }, [loadTopology, activeProjectId]);

  useEffect(() => {
    loadTopology(activeProjectId);
  }, [loadTopology, activeProjectId]);

  useEffect(() => {
    const onProjChanged = (e: any) => {
      const newPid = e.detail?.projectId || getActiveProjectId();
      setActiveProjectIdState(newPid);
      loadTopology(newPid);
    };
    window.addEventListener('aegis_project_changed', onProjChanged);
    return () => window.removeEventListener('aegis_project_changed', onProjChanged);
  }, [loadTopology]);

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const resp = await fetch(apiUrl('/api/projects'));
        if (resp.ok) {
          const list = await resp.json();
          setProjectsList(list);
        }
      } catch (err) {
        console.error('Failed to load projects list in topology:', err);
      }
    };
    fetchProjects();
  }, [activeProjectId]);

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

      // Dynamically update connected edges with real-time live beat status
      setEdges((prevEdges) =>
        prevEdges.map((edge) => {
          if (edge.source === serviceId || edge.target === serviceId) {
            const edgeData = (edge.data || {}) as any;
            const updatedSrcHealth = edge.source === serviceId ? payload.status : edgeData.sourceHealth;
            const updatedTgtHealth = edge.target === serviceId ? payload.status : edgeData.targetHealth;
            const isLive = updatedSrcHealth === 'healthy' || updatedTgtHealth === 'healthy' || edgeData.isCritical;
            const status = (updatedSrcHealth === 'unavailable' || updatedTgtHealth === 'unavailable')
              ? 'unavailable'
              : (updatedSrcHealth === 'degraded' || updatedTgtHealth === 'degraded')
              ? 'degraded'
              : isLive
              ? 'healthy'
              : 'unconfigured';

            return {
              ...edge,
              data: {
                ...edgeData,
                isLive,
                status,
                sourceHealth: updatedSrcHealth,
                targetHealth: updatedTgtHealth,
                pulseTrigger: (edgeData.pulseTrigger || 0) + 1,
              },
            };
          }
          return edge;
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
      const resp = await fetch(apiUrl(`/api/reset?project_id=${activeProjectId}`), {
        method: 'POST',
        headers: getAuthHeaders(activeProjectId),
      });
      if (resp.ok) {
        const data = await resp.json();
        setResetMessage(`Reset successfully: ${data.node_count} nodes, ${data.edge_count} edges.`);
        handleClearBlast();
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
        isBlastTarget: activeFlowNode.data?.isBlastTarget as boolean | undefined,
        isBlastImpacted: activeFlowNode.data?.isBlastImpacted as boolean | undefined,
        blastVerdict: activeFlowNode.data?.blastVerdict as string | undefined,
        blastRisk: activeFlowNode.data?.blastRisk as number | undefined,
        blastReason: activeFlowNode.data?.blastReason as string | undefined,
        blastPrNumber: activeFlowNode.data?.blastPrNumber as number | undefined,
        blastPrTitle: activeFlowNode.data?.blastPrTitle as string | undefined,
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
        {/* Left: Project Selector, Search & Layer Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          {/* Multi-Project Context Dropdown */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '5px 12px',
              borderRadius: 6,
              backgroundColor: '#070b14',
              border: '1px solid #1e293b',
              boxShadow: '0 0 10px rgba(56, 189, 248, 0.1)',
            }}
          >
            <KeyRound size={13} color="#38bdf8" />
            <span style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>Active Graph:</span>
            <select
              value={activeProjectId}
              onChange={(e) => {
                const newPid = e.target.value;
                setActiveProjectId(newPid);
                setActiveProjectIdState(newPid);
                loadTopology(newPid);
              }}
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                color: '#38bdf8',
                fontSize: 12,
                fontWeight: 700,
                fontFamily: 'monospace',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              {projectsList.length > 0 ? (
                projectsList.map((p) => (
                  <option key={p.project_id} value={p.project_id} style={{ backgroundColor: '#0a101d', color: '#f8fafc' }}>
                    {p.name} ({p.node_count ?? '?'} nodes) {p.repo_full_name ? `• ${p.repo_full_name}` : ''}
                  </option>
                ))
              ) : (
                <option value={activeProjectId} style={{ backgroundColor: '#0a101d', color: '#f8fafc' }}>
                  {activeProjectId}
                </option>
              )}
            </select>
          </div>

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

          {blastContext && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '4px 10px',
                borderRadius: 6,
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#fca5a5',
                fontSize: 11,
                fontWeight: 600,
              }}
            >
              <Flame size={13} color="#ef4444" />
              <span>PR #{blastContext.pr_number || '3'} Risk Blast</span>
              <button
                onClick={handleClearBlast}
                title="Clear Blast Highlighting and return to normal view"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 3,
                  background: 'rgba(239, 68, 68, 0.25)',
                  border: '1px solid rgba(239, 68, 68, 0.6)',
                  color: '#fee2e2',
                  cursor: 'pointer',
                  fontSize: 11,
                  fontWeight: 700,
                  borderRadius: 4,
                  padding: '2px 8px',
                  transition: 'background 0.2s',
                }}
              >
                Clear (Normal View) ✕
              </button>
            </div>
          )}

          <button
            onClick={() => loadTopology(activeProjectId)}
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
              cursor: isLoading ? 'not-allowed' : 'pointer',
              opacity: isLoading ? 0.75 : 1,
            }}
          >
            {isLoading ? <Loader2 size={12} className="animate-spin" color="#38bdf8" /> : <Network size={12} color="#38bdf8" />}
            <span>{isLoading ? 'Loading Graph...' : 'Refresh Graph'}</span>
          </button>

          <button
            onClick={() => setIsChatOpen(!isChatOpen)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 14px',
              borderRadius: 6,
              background: isChatOpen
                ? 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)'
                : 'linear-gradient(135deg, rgba(6, 182, 212, 0.15) 0%, rgba(59, 130, 246, 0.15) 100%)',
              border: `1px solid ${isChatOpen ? '#38bdf8' : 'rgba(6, 182, 212, 0.4)'}`,
              color: isChatOpen ? '#ffffff' : '#38bdf8',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: isChatOpen ? '0 0 16px rgba(56, 189, 248, 0.4)' : 'none',
              transition: 'all 0.2s ease',
            }}
          >
            <Sparkles size={13} color={isChatOpen ? '#ffffff' : '#38bdf8'} />
            <span>{isChatOpen ? 'Close Copilot' : 'AI Copilot'}</span>
          </button>
        </div>
      </div>

      {/* Main Graph Canvas Area */}
      <div style={{ flex: 1, position: 'relative', width: '100%', height: '100%', backgroundColor: '#060a12' }}>
        {/* Visual Graph Loading Overlay */}
        {isLoading && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              zIndex: 35,
              backgroundColor: 'rgba(6, 10, 18, 0.78)',
              backdropFilter: 'blur(8px)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 20,
              pointerEvents: 'all',
            }}
          >
            {/* Concentric Multi-Ring Radar Loader */}
            <div
              style={{
                position: 'relative',
                width: 96,
                height: 96,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {/* Outer spinning ring */}
              <div
                className="animate-spin-slow"
                style={{
                  position: 'absolute',
                  inset: 0,
                  borderRadius: '50%',
                  border: '3px solid rgba(56, 189, 248, 0.15)',
                  borderTopColor: '#38bdf8',
                  borderRightColor: '#0284c7',
                  boxShadow: '0 0 24px rgba(56, 189, 248, 0.35)',
                }}
              />
              {/* Middle counter-spinning ring */}
              <div
                className="animate-spin-reverse"
                style={{
                  position: 'absolute',
                  inset: 12,
                  borderRadius: '50%',
                  border: '2px dashed rgba(6, 182, 212, 0.45)',
                  borderBottomColor: '#06b6d4',
                }}
              />
              {/* Center glowing network hub */}
              <div
                className="animate-radar"
                style={{
                  width: 50,
                  height: 50,
                  borderRadius: '50%',
                  backgroundColor: 'rgba(56, 189, 248, 0.12)',
                  border: '1px solid rgba(56, 189, 248, 0.4)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Network size={24} color="#38bdf8" />
              </div>
            </div>

            <div style={{ textAlign: 'center', maxWidth: 380 }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#f8fafc', marginBottom: 6 }}>
                Loading Architecture Topology...
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5, marginBottom: 14 }}>
                Synthesizing microservices, dependencies, and live telemetry for{' '}
                <strong style={{ color: '#38bdf8', fontFamily: 'monospace' }}>{activeProjectId}</strong>
              </div>

              {/* Shimmer progress bar */}
              <div
                style={{
                  width: 240,
                  height: 4,
                  borderRadius: 2,
                  backgroundColor: '#1e293b',
                  overflow: 'hidden',
                  margin: '0 auto',
                  position: 'relative',
                }}
              >
                <div
                  style={{
                    width: '100%',
                    height: '100%',
                    background: 'linear-gradient(90deg, transparent, #38bdf8, #06b6d4, transparent)',
                    animation: 'shimmer 1.6s infinite linear',
                    backgroundSize: '200% 100%',
                  }}
                />
              </div>
            </div>
          </div>
        )}
        <ReactFlow
          nodes={filteredNodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
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
              {/* Active PR Blast / Breaking Change Reason Alert */}
              {(selectedNode.isBlastTarget || selectedNode.isBlastImpacted) && (
                <div
                  style={{
                    padding: 14,
                    borderRadius: 10,
                    backgroundColor: 'rgba(239, 68, 68, 0.15)',
                    border: '1.5px solid #ef4444',
                    boxShadow: '0 0 20px rgba(239, 68, 68, 0.25)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 8,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Flame size={16} color="#ef4444" />
                      <span style={{ fontSize: 12, fontWeight: 800, color: '#fca5a5', textTransform: 'uppercase' }}>
                        {selectedNode.isBlastTarget ? '🎯 PR Target (Breaking Contract)' : '💥 Upstream Caller in Blast Radius'}
                      </span>
                    </div>
                    {selectedNode.blastVerdict && (
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 800,
                          padding: '2px 8px',
                          borderRadius: 6,
                          backgroundColor: '#ef4444',
                          color: '#fff',
                        }}
                      >
                        {selectedNode.blastVerdict.toUpperCase()}
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: 12, color: '#f8fafc', lineHeight: 1.5, fontWeight: 500 }}>
                    {selectedNode.blastReason || (
                      selectedNode.isBlastTarget
                        ? `Breaking API contract diff detected in PR #${selectedNode.blastPrNumber || '3'}. Downstream consumers relying on removed fields will fail.`
                        : `Direct upstream caller of modified service. Will experience deserialization crashes at runtime.`
                    )}
                  </div>

                  {selectedNode.blastRisk !== undefined && (
                    <div style={{ fontSize: 11, color: '#fca5a5', display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 }}>
                      <span>Predicted Risk Score:</span>
                      <strong style={{ color: '#ef4444', fontSize: 13 }}>{Number(selectedNode.blastRisk).toFixed(1)} / 100</strong>
                      {selectedNode.blastPrNumber && (
                        <span style={{ color: '#94a3b8' }}>• Evaluated on PR #{selectedNode.blastPrNumber}</span>
                      )}
                    </div>
                  )}
                </div>
              )}

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
                      {selectedNode.error_rate !== undefined && selectedNode.error_rate !== null
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

        {/* Floating Copilot Launcher Pill (Bottom-Right) */}
        {!isChatOpen && (
          <button
            onClick={() => setIsChatOpen(true)}
            style={{
              position: 'absolute',
              bottom: 24,
              right: 24,
              zIndex: 40,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 18px',
              borderRadius: 30,
              background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)',
              border: '1px solid rgba(255, 255, 255, 0.25)',
              color: '#ffffff',
              fontSize: 13,
              fontWeight: 700,
              boxShadow: '0 8px 24px rgba(6, 182, 212, 0.45)',
              cursor: 'pointer',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
              e.currentTarget.style.boxShadow = '0 12px 28px rgba(6, 182, 212, 0.6)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0) scale(1)';
              e.currentTarget.style.boxShadow = '0 8px 24px rgba(6, 182, 212, 0.45)';
            }}
          >
            <Sparkles size={16} />
            <span>AI Copilot</span>
          </button>
        )}

        {/* AI Graph Copilot Drawer */}
        <GraphChatDrawer
          projectId={activeProjectId}
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
          onTopologyUpdated={(_newNodes: any[], _newEdges: any[], focusNodeId?: string) => {
            loadTopology(activeProjectId);
            if (focusNodeId) {
              setSelectedNodeId(focusNodeId);
            }
          }}
          onSelectNode={(nodeId: string) => setSelectedNodeId(nodeId)}
          activeNodeId={selectedNodeId}
        />
      </div>
    </div>
  );
};
