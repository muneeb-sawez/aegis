import React, { useState, useEffect } from 'react';
import {
  X,
  GitBranch,
  DownloadCloud,
  PlusCircle,
  CheckCircle2,
  AlertCircle,
  Layers,
  ChevronRight,
  Eye,
  EyeOff,
  Sparkles,
} from 'lucide-react';

interface IngestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onIngestionSuccess?: (data?: any) => void;
}

interface SampleRepo {
  slug: string;
  name: string;
  description: string;
  services_count: number;
  primary_language: string;
  yaml_preview: string;
}

export const IngestionModal: React.FC<IngestionModalProps> = ({
  isOpen,
  onClose,
  onIngestionSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<'sample' | 'custom' | 'external'>('sample');
  const [sampleRepos, setSampleRepos] = useState<SampleRepo[]>([]);
  const [selectedSample, setSelectedSample] = useState<string | null>(null);
  const [expandedYaml, setExpandedYaml] = useState<string | null>(null);

  // Custom form
  const [repoUrl, setRepoUrl] = useState('shop-sphere/ecommerce-core');
  const [yamlContent, setYamlContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [resultMessage, setResultMessage] = useState<any>(null);

  // External service form
  const [extName, setExtName] = useState('Stripe Payment Gateway');
  const [extCategory, setExtCategory] = useState('Payment Gateway');
  const [extEndpoint, setExtEndpoint] = useState('https://api.stripe.com/v1');
  const [dependentService, setDependentService] = useState('paymentservice');

  // Load sample repositories on open
  useEffect(() => {
    if (isOpen) {
      fetch('/api/ingest/sample-repos')
        .then((res) => (res.ok ? res.json() : []))
        .then((data) => setSampleRepos(data))
        .catch((err) => console.error('Failed to load sample repos:', err));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleIngestSample = async (slug: string) => {
    setIsLoading(true);
    setSelectedSample(slug);
    setResultMessage(null);
    try {
      const resp = await fetch('/api/ingest/repository', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: slug }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setResultMessage({ type: 'success', data });
        if (onIngestionSuccess) onIngestionSuccess(data);
      } else {
        setResultMessage({ type: 'error', message: data.detail || 'Ingestion failed' });
      }
    } catch (e: any) {
      setResultMessage({ type: 'error', message: e.message || 'Connection error' });
    } finally {
      setIsLoading(false);
      setSelectedSample(null);
    }
  };

  const handleIngestCustom = async () => {
    setIsLoading(true);
    setResultMessage(null);
    try {
      const resp = await fetch('/api/ingest/repository', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repoUrl || undefined,
          compose_yaml_content: yamlContent || undefined,
        }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setResultMessage({ type: 'success', data });
        if (onIngestionSuccess) onIngestionSuccess(data);
      } else {
        setResultMessage({ type: 'error', message: data.detail || 'Ingestion failed' });
      }
    } catch (e: any) {
      setResultMessage({ type: 'error', message: e.message || 'Connection error' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegisterExternal = async () => {
    setIsLoading(true);
    setResultMessage(null);
    try {
      const resp = await fetch('/api/graph/external-service', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: extName,
          category: extCategory,
          endpoint_url: extEndpoint,
          dependent_service_id: dependentService,
        }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setResultMessage({ type: 'success', data });
        if (onIngestionSuccess) onIngestionSuccess(data);
      } else {
        setResultMessage({ type: 'error', message: data.detail || 'Registration failed' });
      }
    } catch (e: any) {
      setResultMessage({ type: 'error', message: e.message || 'Connection error' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        backdropFilter: 'blur(10px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
      }}
    >
      <div
        style={{
          width: 860,
          maxHeight: '92vh',
          backgroundColor: '#070d18',
          border: '1px solid #1e293b',
          borderRadius: 16,
          boxShadow: '0 25px 65px rgba(0, 0, 0, 0.9)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 24px',
            borderBottom: '1px solid #1e293b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: '#0a101f',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
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
              }}
            >
              <GitBranch size={18} />
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 800, color: '#f8fafc', letterSpacing: -0.2 }}>
                AEGIS — Repository & Topology Ingestion
              </div>
              <div style={{ fontSize: 11, color: '#64748b' }}>
                Ingest live Git repositories, parse Docker Compose manifests, or register external SaaS dependencies
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: 6,
              borderRadius: 6,
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Tab Bar */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid #1e293b',
            backgroundColor: '#080e1b',
            padding: '0 24px',
          }}
        >
          <button
            onClick={() => {
              setActiveTab('sample');
              setResultMessage(null);
            }}
            style={{
              padding: '12px 18px',
              fontSize: 12,
              fontWeight: 600,
              color: activeTab === 'sample' ? '#38bdf8' : '#64748b',
              borderBottom: activeTab === 'sample' ? '2px solid #38bdf8' : '2px solid transparent',
              background: 'none',
              borderTop: 'none',
              borderLeft: 'none',
              borderRight: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <Sparkles size={14} />
            Test Repositories (One-Click)
          </button>
          <button
            onClick={() => {
              setActiveTab('custom');
              setResultMessage(null);
            }}
            style={{
              padding: '12px 18px',
              fontSize: 12,
              fontWeight: 600,
              color: activeTab === 'custom' ? '#38bdf8' : '#64748b',
              borderBottom: activeTab === 'custom' ? '2px solid #38bdf8' : '2px solid transparent',
              background: 'none',
              borderTop: 'none',
              borderLeft: 'none',
              borderRight: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <DownloadCloud size={14} />
            Custom GitHub / Docker Compose
          </button>
          <button
            onClick={() => {
              setActiveTab('external');
              setResultMessage(null);
            }}
            style={{
              padding: '12px 18px',
              fontSize: 12,
              fontWeight: 600,
              color: activeTab === 'external' ? '#38bdf8' : '#64748b',
              borderBottom: activeTab === 'external' ? '2px solid #38bdf8' : '2px solid transparent',
              background: 'none',
              borderTop: 'none',
              borderLeft: 'none',
              borderRight: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <PlusCircle size={14} />
            Register External SaaS Vendor
          </button>
        </div>

        {/* Tab Content */}
        <div style={{ padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* TAB 1: Sample Made-Up Repositories */}
          {activeTab === 'sample' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div
                style={{
                  fontSize: 12,
                  color: '#94a3b8',
                  lineHeight: 1.5,
                  backgroundColor: '#0d1527',
                  padding: '12px 16px',
                  borderRadius: 8,
                  border: '1px solid #1e293b',
                }}
              >
                Select any verified test repository below to simulate immediate manifest ingestion. AEGIS parses the multi-service topology, detects dependency directions, and merges the nodes into the active graph.
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                {sampleRepos.map((repo) => (
                  <div
                    key={repo.slug}
                    style={{
                      backgroundColor: '#0a1224',
                      border: '1px solid #1e293b',
                      borderRadius: 12,
                      padding: '16px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: 12,
                      transition: 'border-color 0.2s',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span
                          style={{
                            fontSize: 10,
                            fontFamily: 'JetBrains Mono, monospace',
                            color: '#38bdf8',
                            backgroundColor: 'rgba(56, 189, 248, 0.1)',
                            padding: '3px 8px',
                            borderRadius: 4,
                            border: '1px solid rgba(56, 189, 248, 0.25)',
                          }}
                        >
                          {repo.slug}
                        </span>
                        <span
                          style={{
                            fontSize: 11,
                            color: '#10b981',
                            fontWeight: 600,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          <Layers size={13} />
                          {repo.services_count} Services
                        </span>
                      </div>

                      <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc', marginTop: 10 }}>
                        {repo.name}
                      </div>

                      <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4, lineHeight: 1.4 }}>
                        {repo.description}
                      </div>

                      <div style={{ fontSize: 10, color: '#64748b', marginTop: 8, display: 'flex', gap: 6 }}>
                        <span style={{ color: '#94a3b8' }}>Stack:</span>
                        <span>{repo.primary_language}</span>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: 8, paddingTop: 6, borderTop: '1px solid #152238' }}>
                      <button
                        onClick={() => handleIngestSample(repo.slug)}
                        disabled={isLoading}
                        style={{
                          flex: 1,
                          padding: '8px 12px',
                          borderRadius: 6,
                          backgroundColor: '#0284c7',
                          border: 'none',
                          color: '#ffffff',
                          fontSize: 11,
                          fontWeight: 700,
                          cursor: isLoading ? 'not-allowed' : 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: 6,
                        }}
                      >
                        {selectedSample === repo.slug ? 'Ingesting...' : 'Ingest Topology'}
                        <ChevronRight size={14} />
                      </button>

                      <button
                        onClick={() =>
                          setExpandedYaml(expandedYaml === repo.slug ? null : repo.slug)
                        }
                        style={{
                          padding: '8px 10px',
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
                        title="Toggle Manifest Preview"
                      >
                        {expandedYaml === repo.slug ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    </div>

                    {expandedYaml === repo.slug && (
                      <pre
                        style={{
                          margin: 0,
                          padding: 10,
                          borderRadius: 6,
                          backgroundColor: '#050912',
                          color: '#94a3b8',
                          fontSize: 10,
                          fontFamily: 'JetBrains Mono, monospace',
                          overflowX: 'auto',
                          maxHeight: 140,
                          border: '1px solid #1e293b',
                        }}
                      >
                        {repo.yaml_preview}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: Custom GitHub Repo or Docker Compose */}
          {activeTab === 'custom' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc', display: 'block', marginBottom: 6 }}>
                  GitHub Repository Slug or URL (REST API Ingestion)
                </label>
                <input
                  type="text"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="e.g. shop-sphere/ecommerce-core or GoogleCloudPlatform/microservices-demo"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 8,
                    backgroundColor: '#0f172a',
                    border: '1px solid #1e293b',
                    color: '#f8fafc',
                    fontSize: 12,
                    fontFamily: 'JetBrains Mono, monospace',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ textAlign: 'center', fontSize: 11, color: '#475569', fontWeight: 600 }}>
                — OR PASTE RAW DOCKER COMPOSE MANIFEST —
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc' }}>
                    docker-compose.yml Content
                  </label>
                  <button
                    onClick={() => {
                      setYamlContent(`version: '3.8'\nservices:\n  gateway:\n    image: nginx:alpine\n    ports:\n      - "80:80"\n    depends_on:\n      - auth-service\n      - order-service\n  auth-service:\n    image: auth:v1\n    depends_on:\n      - redis\n  order-service:\n    image: order:v1\n    depends_on:\n      - postgres\n  redis:\n    image: redis:alpine\n  postgres:\n    image: postgres:15\n`);
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#38bdf8',
                      fontSize: 11,
                      cursor: 'pointer',
                      textDecoration: 'underline',
                    }}
                  >
                    Insert Example YAML
                  </button>
                </div>
                <textarea
                  rows={6}
                  value={yamlContent}
                  onChange={(e) => setYamlContent(e.target.value)}
                  placeholder="Paste docker-compose.yml here..."
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 8,
                    backgroundColor: '#050912',
                    border: '1px solid #1e293b',
                    color: '#f8fafc',
                    fontSize: 11,
                    fontFamily: 'JetBrains Mono, monospace',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <button
                onClick={handleIngestCustom}
                disabled={isLoading}
                style={{
                  padding: '10px 20px',
                  borderRadius: 8,
                  backgroundColor: '#0284c7',
                  border: 'none',
                  color: '#ffffff',
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                }}
              >
                {isLoading ? 'Scanning & Ingesting...' : 'Scan Repository & Update Graph'}
              </button>
            </div>
          )}

          {/* TAB 3: Register External Service */}
          {activeTab === 'external' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div
                style={{
                  fontSize: 12,
                  color: '#94a3b8',
                  lineHeight: 1.5,
                  backgroundColor: '#0d1527',
                  padding: '12px 16px',
                  borderRadius: 8,
                  border: '1px solid #1e293b',
                }}
              >
                Register third-party cloud services and APIs (e.g., payment gateways, email delivery, IDPs) that cannot be discovered from code manifests. AEGIS will persist the external node and connect it to your internal service.
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc', display: 'block', marginBottom: 6 }}>
                    External Vendor / Service Name
                  </label>
                  <input
                    type="text"
                    value={extName}
                    onChange={(e) => setExtName(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: 8,
                      backgroundColor: '#0f172a',
                      border: '1px solid #1e293b',
                      color: '#f8fafc',
                      fontSize: 12,
                      outline: 'none',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc', display: 'block', marginBottom: 6 }}>
                    Service Category
                  </label>
                  <input
                    type="text"
                    value={extCategory}
                    onChange={(e) => setExtCategory(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: 8,
                      backgroundColor: '#0f172a',
                      border: '1px solid #1e293b',
                      color: '#f8fafc',
                      fontSize: 12,
                      outline: 'none',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc', display: 'block', marginBottom: 6 }}>
                    Endpoint / API URL
                  </label>
                  <input
                    type="text"
                    value={extEndpoint}
                    onChange={(e) => setExtEndpoint(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: 8,
                      backgroundColor: '#0f172a',
                      border: '1px solid #1e293b',
                      color: '#f8fafc',
                      fontSize: 12,
                      fontFamily: 'JetBrains Mono, monospace',
                      outline: 'none',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc', display: 'block', marginBottom: 6 }}>
                    Dependent Internal Service
                  </label>
                  <input
                    type="text"
                    value={dependentService}
                    onChange={(e) => setDependentService(e.target.value)}
                    placeholder="e.g. paymentservice"
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: 8,
                      backgroundColor: '#0f172a',
                      border: '1px solid #1e293b',
                      color: '#f8fafc',
                      fontSize: 12,
                      fontFamily: 'JetBrains Mono, monospace',
                      outline: 'none',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>
              </div>

              <button
                onClick={handleRegisterExternal}
                disabled={isLoading}
                style={{
                  padding: '10px 20px',
                  borderRadius: 8,
                  backgroundColor: '#0284c7',
                  border: 'none',
                  color: '#ffffff',
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                }}
              >
                {isLoading ? 'Registering...' : 'Register External Service'}
              </button>
            </div>
          )}

          {/* Result Banner */}
          {resultMessage && (
            <div
              style={{
                padding: '14px 18px',
                borderRadius: 10,
                backgroundColor: resultMessage.type === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                border: `1px solid ${resultMessage.type === 'success' ? '#10b981' : '#ef4444'}`,
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {resultMessage.type === 'success' ? (
                  <CheckCircle2 size={18} color="#10b981" />
                ) : (
                  <AlertCircle size={18} color="#ef4444" />
                )}
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: 700,
                    color: resultMessage.type === 'success' ? '#10b981' : '#ef4444',
                  }}
                >
                  {resultMessage.type === 'success' ? 'Ingestion Completed' : 'Ingestion Error'}
                </span>
              </div>
              <div style={{ fontSize: 12, color: '#f8fafc' }}>
                {resultMessage.type === 'success'
                  ? resultMessage.data.message
                  : resultMessage.message}
              </div>

              {resultMessage.type === 'success' && resultMessage.data.services_discovered && (
                <div style={{ fontSize: 11, color: '#94a3b8', display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                  <span style={{ fontWeight: 600, color: '#f8fafc' }}>Discovered Services:</span>
                  {resultMessage.data.services_discovered.map((s: string) => (
                    <span
                      key={s}
                      style={{
                        backgroundColor: '#0f172a',
                        padding: '2px 8px',
                        borderRadius: 4,
                        border: '1px solid #1e293b',
                        color: '#38bdf8',
                        fontFamily: 'JetBrains Mono, monospace',
                      }}
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
