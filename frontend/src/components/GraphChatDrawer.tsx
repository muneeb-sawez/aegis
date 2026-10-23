import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  Send,
  Trash2,
  X,
  Bot,
  User,
  Plus,
  Link,
  Minimize2,
  Maximize2,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { apiUrl, getAuthHeaders } from '../config';

interface ActionItem {
  action?: string;
  action_type?: string;
  id?: string;
  node_id?: string;
  label?: string;
  source?: string;
  target?: string;
  old_target?: string;
  type?: string;
  edge_type?: string;
  success?: boolean;
  error?: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  actions?: ActionItem[];
  timestamp: number;
}

interface GraphChatDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onTopologyUpdated: (newNodes: any[], newEdges: any[], focusNodeId?: string) => void;
  onSelectNode?: (nodeId: string) => void;
  activeNodeId?: string | null;
}

const renderInlineTokens = (text: string, onSelectNode?: (nodeId: string) => void): React.ReactNode[] => {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let lastIdx = 0;
  let m: RegExpExecArray | null;

  while ((m = regex.exec(text)) !== null) {
    if (m.index > lastIdx) {
      parts.push(text.substring(lastIdx, m.index));
    }
    const token = m[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      const inner = token.slice(2, -2).replace(/`/g, '');
      parts.push(
        <strong key={m.index} style={{ color: '#f8fafc', fontWeight: 700 }}>
          {inner}
        </strong>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      const code = token.slice(1, -1);
      parts.push(
        <span
          key={m.index}
          onClick={() => onSelectNode && onSelectNode(code)}
          style={{
            fontFamily: 'monospace',
            fontSize: '11px',
            color: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.12)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '4px',
            padding: '1px 5px',
            margin: '0 2px',
            cursor: onSelectNode ? 'pointer' : 'default',
            display: 'inline-block',
            fontWeight: 600,
          }}
          title={onSelectNode ? `Click to inspect '${code}' in topology` : undefined}
        >
          {code}
        </span>
      );
    }
    lastIdx = m.index + token.length;
  }
  if (lastIdx < text.length) {
    parts.push(text.substring(lastIdx));
  }
  return parts;
};

const StructuredMessageView: React.FC<{
  content: string;
  onSelectNode?: (nodeId: string) => void;
}> = ({ content, onSelectNode }) => {
  const rawLines = content.split('\n');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {rawLines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={idx} style={{ height: 4 }} />;
        }

        // Section Headers (### or ####)
        if (trimmed.startsWith('#### ') || trimmed.startsWith('### ') || trimmed.startsWith('## ')) {
          const title = trimmed.replace(/^#{2,4}\s+/, '');
          return (
            <div
              key={idx}
              style={{
                fontSize: trimmed.startsWith('### ') ? 13 : 12,
                fontWeight: 700,
                color: '#38bdf8',
                marginTop: 6,
                marginBottom: 2,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                letterSpacing: '-0.2px',
              }}
            >
              <span>{renderInlineTokens(title, onSelectNode)}</span>
            </div>
          );
        }

        // Callout / Highlight Cards (👋, 💡, 💥, ✅, 🗑️, ✂️, ⚠️)
        if (
          trimmed.startsWith('👋') ||
          trimmed.startsWith('💡') ||
          trimmed.startsWith('💥') ||
          trimmed.startsWith('✅') ||
          trimmed.startsWith('🗑️') ||
          trimmed.startsWith('✂️') ||
          trimmed.startsWith('⚠️')
        ) {
          const isSuccess = trimmed.startsWith('✅');
          const isWarning = trimmed.startsWith('⚠️') || trimmed.startsWith('💥');

          return (
            <div
              key={idx}
              style={{
                padding: '6px 10px',
                borderRadius: 6,
                backgroundColor: isSuccess
                  ? 'rgba(16, 185, 129, 0.1)'
                  : isWarning
                  ? 'rgba(239, 68, 68, 0.1)'
                  : 'rgba(56, 189, 248, 0.08)',
                border: `1px solid ${
                  isSuccess
                    ? 'rgba(16, 185, 129, 0.25)'
                    : isWarning
                    ? 'rgba(239, 68, 68, 0.25)'
                    : 'rgba(56, 189, 248, 0.2)'
                }`,
                margin: '3px 0',
                fontSize: 12,
                lineHeight: '1.45',
              }}
            >
              {renderInlineTokens(trimmed, onSelectNode)}
            </div>
          );
        }

        // Bullet Items (- or *)
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          const bulletContent = trimmed.substring(2).trim();
          return (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 6,
                paddingLeft: 4,
                margin: '1px 0',
                fontSize: 12,
                lineHeight: '1.45',
              }}
            >
              <span style={{ color: '#06b6d4', marginTop: 1, fontSize: 11 }}>•</span>
              <div style={{ flex: 1, color: '#e2e8f0' }}>
                {renderInlineTokens(bulletContent, onSelectNode)}
              </div>
            </div>
          );
        }

        // Regular paragraph text
        return (
          <div key={idx} style={{ fontSize: 12.5, lineHeight: '1.45', color: '#e2e8f0' }}>
            {renderInlineTokens(trimmed, onSelectNode)}
          </div>
        );
      })}
    </div>
  );
};

export const GraphChatDrawer: React.FC<GraphChatDrawerProps> = ({
  projectId,
  isOpen,
  onClose,
  onTopologyUpdated,
  onSelectNode,
  activeNodeId,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [sessionId] = useState<string>(() => {
    const existing = sessionStorage.getItem(`aegis_graph_chat_sid_${projectId}`);
    if (existing) return existing;
    const newSid = `sess_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    sessionStorage.setItem(`aegis_graph_chat_sid_${projectId}`, newSid);
    return newSid;
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  // Load chat history from backend on initial mount
  useEffect(() => {
    let isMounted = true;
    const fetchHistory = async () => {
      try {
        const resp = await fetch(
          apiUrl(`/api/graph/chat/history?project_id=${projectId}&session_id=${sessionId}`),
          { headers: getAuthHeaders(projectId) }
        );
        if (resp.ok && isMounted) {
          const data = await resp.json();
          if (Array.isArray(data.messages) && data.messages.length > 0) {
            const mapped: ChatMessage[] = data.messages.map((m: any, idx: number) => ({
              id: `hist-${idx}-${m.timestamp || Date.now()}`,
              role: m.role,
              content: m.content,
              actions: m.actions,
              timestamp: m.timestamp || Date.now(),
            }));
            setMessages(mapped);
          } else {
            // Seed a friendly initial greeting
            setMessages([
              {
                id: 'welcome-1',
                role: 'assistant',
                content: `👋 **AEGIS Graph Copilot** connected for project **\`${projectId}\`**.

#### 🚀 What I Can Do:
- 🔍 **Explain Microservices** in this repo, architecture, blast radii, and health.
- ➕ **Add New Nodes** (e.g. \`Add redis-cache database\`).
- 🔗 **Connect & Rewire Nodes** (e.g. \`Connect checkoutservice to redis-cache\`).
- ✂️ **Change or Remove Connections** with full session memory.

💡 *Ask a question or tap a quick action above to begin!*`,
                timestamp: Date.now(),
              },
            ]);
          }
        }
      } catch {
        // Ignore initial fetch errors
      }
    };

    if (isOpen) {
      fetchHistory();
    }
    return () => {
      isMounted = false;
    };
  }, [projectId, sessionId, isOpen]);

  const handleSendMessage = async (textToSend?: string) => {
    const promptText = (textToSend !== undefined ? textToSend : input).trim();
    if (!promptText || isLoading) return;

    setInput('');

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: promptText,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const resp = await fetch(apiUrl('/api/graph/chat'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(projectId),
        },
        body: JSON.stringify({
          project_id: projectId,
          session_id: sessionId,
          message: promptText,
        }),
      });

      if (resp.ok) {
        const data = await resp.json();

        const assistantMsg: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: data.reply || 'Topology updated.',
          actions: data.executed_actions || data.actions || [],
          timestamp: Date.now(),
        };

        setMessages((prev) => [...prev, assistantMsg]);

        // If topology was mutated, push updates to parent canvas!
        if (data.nodes && data.edges) {
          // Identify if a node was just created to focus the canvas on it
          let focusId: string | undefined;
          const createdAction = (data.executed_actions || []).find(
            (a: any) => a.action === 'CREATE_NODE' || a.action_type === 'CREATE_NODE'
          );
          if (createdAction?.id || createdAction?.node_id) {
            focusId = createdAction.id || createdAction.node_id;
          }
          onTopologyUpdated(data.nodes, data.edges, focusId);
        }
      } else {
        const errData = await resp.json().catch(() => ({}));
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            role: 'assistant',
            content: `⚠️ Error communicating with copilot: ${errData.detail || 'Request failed'}.`,
            timestamp: Date.now(),
          },
        ]);
      }
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ Network error: ${e.message || 'Unable to reach backend'}.`,
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = async () => {
    try {
      await fetch(
        apiUrl(`/api/graph/chat/history?project_id=${projectId}&session_id=${sessionId}`),
        {
          method: 'DELETE',
          headers: getAuthHeaders(projectId),
        }
      );
    } catch {
      // ignore
    }
    setMessages([
      {
        id: `cleared-${Date.now()}`,
        role: 'assistant',
        content: `🧹 Memory cleared for project **\`${projectId}\`**. How can I assist you with the architecture?`,
        timestamp: Date.now(),
      },
    ]);
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'absolute',
        top: 60,
        right: 20,
        width: 440,
        height: isMinimized ? 52 : 'calc(100% - 80px)',
        maxHeight: isMinimized ? 52 : 750,
        backgroundColor: 'rgba(10, 16, 29, 0.94)',
        backdropFilter: 'blur(16px)',
        border: '1px solid #1e293b',
        borderRadius: 12,
        boxShadow: '0 12px 40px rgba(0, 0, 0, 0.65), 0 0 25px rgba(6, 182, 212, 0.15)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 100,
        overflow: 'hidden',
        transition: 'height 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: isMinimized ? 'none' : '1px solid #1e293b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#070b14',
          cursor: isMinimized ? 'pointer' : 'default',
        }}
        onClick={() => {
          if (isMinimized) setIsMinimized(false);
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 8,
              background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(6, 182, 212, 0.4)',
            }}
          >
            <Sparkles size={16} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.2px' }}>
                Graph AI Copilot
              </span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  padding: '1px 6px',
                  borderRadius: 4,
                  backgroundColor: 'rgba(6, 182, 212, 0.15)',
                  color: '#38bdf8',
                  border: '1px solid rgba(6, 182, 212, 0.3)',
                }}
              >
                LIVE REASONING
              </span>
            </div>
            <div style={{ fontSize: 11, color: '#64748b' }}>
              Project: <span style={{ color: '#94a3b8', fontFamily: 'monospace' }}>{projectId}</span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {!isMinimized && (
            <button
              onClick={handleClearHistory}
              title="Clear conversation & memory"
              style={{
                background: 'transparent',
                border: 'none',
                color: '#64748b',
                padding: 6,
                borderRadius: 6,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#64748b')}
            >
              <Trash2 size={15} />
            </button>
          )}

          <button
            onClick={() => setIsMinimized(!isMinimized)}
            title={isMinimized ? 'Expand' : 'Minimize'}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              padding: 6,
              borderRadius: 6,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#38bdf8')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#64748b')}
          >
            {isMinimized ? <Maximize2 size={15} /> : <Minimize2 size={15} />}
          </button>

          <button
            onClick={onClose}
            title="Close Assistant"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              padding: 6,
              borderRadius: 6,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#f8fafc')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#64748b')}
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Main Body (Hidden when minimized) */}
      {!isMinimized && (
        <>
          {/* Quick Action Suggestion Chips */}
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: '#0c1424',
              borderBottom: '1px solid #1e293b',
              display: 'flex',
              gap: 6,
              overflowX: 'auto',
              whiteSpace: 'nowrap',
              scrollbarWidth: 'none',
            }}
          >
            {[
              { label: '🔍 Explain Services', prompt: 'Explain what microservices are present in this repo and what they do' },
              { label: '➕ Add Redis Cache', prompt: 'Add a new database called redis-cache and connect it to checkoutservice' },
              { label: '⚡ Blast Radius', prompt: 'What happens if paymentservice or mysql goes down?' },
              { label: '🔗 Connect Nodes', prompt: 'Connect cartservice to redis-cache with DEPENDS_ON' },
            ].map((chip, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(chip.prompt)}
                disabled={isLoading}
                style={{
                  fontSize: 11,
                  padding: '4px 8px',
                  borderRadius: 12,
                  backgroundColor: '#111c33',
                  border: '1px solid #1e293b',
                  color: '#94a3b8',
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  transition: 'all 0.15s ease',
                  flexShrink: 0,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = '#38bdf8';
                  e.currentTarget.style.borderColor = '#0284c7';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = '#94a3b8';
                  e.currentTarget.style.borderColor = '#1e293b';
                }}
              >
                {chip.label}
              </button>
            ))}
          </div>

          {/* Conversation Stream */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '14px 16px',
              display: 'flex',
              flexDirection: 'column',
              gap: 14,
            }}
          >
            {messages.map((msg) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={msg.id}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    gap: 4,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                    {isUser ? (
                      <>
                        <span style={{ fontSize: 11, fontWeight: 600, color: '#64748b' }}>You</span>
                        <div
                          style={{
                            width: 18,
                            height: 18,
                            borderRadius: '50%',
                            backgroundColor: '#1e293b',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <User size={11} color="#94a3b8" />
                        </div>
                      </>
                    ) : (
                      <>
                        <div
                          style={{
                            width: 18,
                            height: 18,
                            borderRadius: '50%',
                            backgroundColor: '#06b6d4',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <Bot size={11} color="#ffffff" />
                        </div>
                        <span style={{ fontSize: 11, fontWeight: 600, color: '#38bdf8' }}>Copilot</span>
                      </>
                    )}
                  </div>

                  <div
                    style={{
                      maxWidth: '92%',
                      padding: '10px 14px',
                      borderRadius: isUser ? '12px 4px 12px 12px' : '4px 12px 12px 12px',
                      backgroundColor: isUser ? '#1e293b' : '#0d1829',
                      border: isUser ? '1px solid #334155' : '1px solid #1e293b',
                      color: '#f8fafc',
                      fontSize: 12.5,
                      lineHeight: '1.5',
                      wordBreak: 'break-word',
                      boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
                    }}
                  >
                    <StructuredMessageView content={msg.content} onSelectNode={onSelectNode} />

                    {/* Action Pill Badges (if any mutations occurred) */}
                    {msg.actions && msg.actions.length > 0 && (
                      <div
                        style={{
                          marginTop: 10,
                          paddingTop: 8,
                          borderTop: '1px dashed #1e293b',
                          display: 'flex',
                          flexWrap: 'wrap',
                          gap: 6,
                        }}
                      >
                        {msg.actions.map((act, actIdx) => {
                          const actType = act.action || act.action_type || '';
                          const isNode = actType.includes('NODE');
                          const isEdge = actType.includes('EDGE');
                          const nodeTarget = act.id || act.node_id;

                          return (
                            <div
                              key={actIdx}
                              onClick={() => {
                                if (nodeTarget && onSelectNode) {
                                  onSelectNode(nodeTarget);
                                }
                              }}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 5,
                                fontSize: 11,
                                padding: '3px 8px',
                                borderRadius: 6,
                                backgroundColor: act.success === false ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                                border: act.success === false ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(16, 185, 129, 0.4)',
                                color: act.success === false ? '#f87171' : '#34d399',
                                cursor: nodeTarget ? 'pointer' : 'default',
                                fontWeight: 600,
                              }}
                              title={nodeTarget ? `Click to inspect ${nodeTarget} in graph` : undefined}
                            >
                              {act.success === false ? (
                                <AlertCircle size={12} color="#f87171" />
                              ) : isNode ? (
                                <Plus size={12} color="#34d399" />
                              ) : isEdge ? (
                                <Link size={12} color="#34d399" />
                              ) : (
                                <CheckCircle2 size={12} color="#34d399" />
                              )}
                              <span>
                                {actType}:{' '}
                                {isNode ? (
                                  <strong>{nodeTarget}</strong>
                                ) : isEdge ? (
                                  <strong>{act.source} → {act.target || act.old_target}</strong>
                                ) : (
                                  act.action
                                )}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {isLoading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px' }}>
                <div
                  style={{
                    width: 18,
                    height: 18,
                    borderRadius: '50%',
                    backgroundColor: '#06b6d4',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Sparkles size={11} color="#ffffff" className="spin-pulse" />
                </div>
                <span style={{ fontSize: 12, color: '#38bdf8', fontStyle: 'italic' }}>
                  Analyzing topology & reasoning...
                </span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Box */}
          <div
            style={{
              padding: '12px 14px',
              backgroundColor: '#070b14',
              borderTop: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder={
                activeNodeId
                  ? `Ask about '${activeNodeId}', add nodes, or rewire connections...`
                  : 'Ask to explain microservices, add nodes, or connect...'
              }
              rows={1}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: 8,
                backgroundColor: '#0f172a',
                border: '1px solid #1e293b',
                color: '#f8fafc',
                fontSize: 12.5,
                outline: 'none',
                resize: 'none',
                minHeight: 38,
                maxHeight: 90,
                fontFamily: 'inherit',
              }}
            />

            <button
              onClick={() => handleSendMessage()}
              disabled={isLoading || !input.trim()}
              style={{
                width: 38,
                height: 38,
                borderRadius: 8,
                backgroundColor: input.trim() && !isLoading ? '#0284c7' : '#1e293b',
                border: 'none',
                color: input.trim() && !isLoading ? '#ffffff' : '#64748b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: input.trim() && !isLoading ? 'pointer' : 'not-allowed',
                transition: 'all 0.15s ease',
              }}
            >
              <Send size={16} />
            </button>
          </div>
        </>
      )}
    </div>
  );
};
