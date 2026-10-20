import React, { useState, useEffect } from 'react';
import {
  FolderGit2,
  FileCode,
  Globe,
  UploadCloud,
  CheckCircle,
  AlertTriangle,
  Play,
  ArrowRight,
  Layers,
} from 'lucide-react';

interface IngestPageProps {
  onNavigate?: (page: string) => void;
}

export const IngestPage: React.FC<IngestPageProps> = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState<'catalog' | 'github' | 'yaml' | 'external'>('catalog');
  const [sampleRepos, setSampleRepos] = useState<any[]>([]);
  const [githubUrl, setGithubUrl] = useState('GoogleCloudPlatform/microservices-demo');
  const [githubBranch, setGithubBranch] = useState('main');
  const [githubPath, setGithubPath] = useState('docker-compose.yml');
  const [githubToken, setGithubToken] = useState('');
  const [rawYaml, setRawYaml] = useState(`version: '3.8'
services:
  frontend:
    image: boutique/frontend:v1
    ports:
      - "8080:8080"
    environment:
      - PRODUCT_CATALOG_SERVICE_ADDR=productcatalogservice:3550
      - CURRENCY_SERVICE_ADDR=currencyservice:7000
      - CART_SERVICE_ADDR=cartservice:7070
      - RECOMMENDATION_SERVICE_ADDR=recommendationservice:8080
      - SHIPPING_SERVICE_ADDR=shippingservice:50051
      - CHECKOUT_SERVICE_ADDR=checkoutservice:5050
      - AD_SERVICE_ADDR=adservice:9555
  checkoutservice:
    image: boutique/checkout:v1
    environment:
      - PAYMENT_SERVICE_ADDR=paymentservice:50051
      - EMAIL_SERVICE_ADDR=emailservice:5000
  paymentservice:
    image: boutique/payment:v1
    environment:
      - DB_HOST=postgres-payment:5432
`);
  const [extName, setExtName] = useState('Stripe Payment Gateway');
  const [extCategory, setExtCategory] = useState('Billing / SaaS API');
  const [extConsumer, setExtConsumer] = useState('paymentservice');

  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSamples = async () => {
      try {
        const resp = await fetch('/api/ingest/sample-repos');
        if (resp.ok) {
          const data = await resp.json();
          setSampleRepos(data);
        }
      } catch (e) {
        console.error('Fetch samples error:', e);
      }
    };
    fetchSamples();
  }, []);

  const handleIngestSample = async (slug: string) => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const resp = await fetch('/api/ingest/repository', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: 'sample',
          sample_slug: slug,
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        setResult(data);
      } else {
        const err = await resp.json().catch(() => null);
        setError(err?.detail || 'Failed to ingest sample repository.');
      }
    } catch (e: any) {
      setError(e.message || 'Error communicating with Ingestion API.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleIngestGithub = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const resp = await fetch('/api/ingest/repository', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: 'github',
          repository_url: githubUrl,
          branch: githubBranch,
          file_path: githubPath,
          github_token: githubToken || undefined,
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        setResult(data);
      } else {
        const err = await resp.json().catch(() => null);
        setError(err?.detail || 'Failed to fetch repository from GitHub.');
      }
    } catch (e: any) {
      setError(e.message || 'Error communicating with GitHub ingestion.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleIngestYaml = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const resp = await fetch('/api/ingest/repository', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: 'raw_yaml',
          raw_manifest: rawYaml,
        }),
      });

      if (resp.ok) {
        const data = await resp.json();
        setResult(data);
      } else {
        const err = await resp.json().catch(() => null);
        setError(err?.detail || 'Failed to parse manifest YAML.');
      }
    } catch (e: any) {
      setError(e.message || 'Error sending manifest YAML.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegisterExternal = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const resp = await fetch('/api/graph/external-service', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_name: extName,
          category: extCategory,
          dependent_service_id: extConsumer,
        }),
      });

      if (resp.ok) {
        await resp.json();
        setResult({
          status: 'success',
          services_detected: 1,
          edges_created: 1,
          message: `External service '${extName}' registered and linked to '${extConsumer}'.`,
        });
      } else {
        setError('Failed to register external cloud dependency.');
      }
    } catch (e: any) {
      setError(e.message || 'Error registering external service.');
    } finally {
      setIsLoading(false);
    }
  };

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
              backgroundColor: 'rgba(168, 85, 247, 0.15)',
              border: '1px solid rgba(168, 85, 247, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#c084fc',
            }}
          >
            <FolderGit2 size={22} />
          </div>
          <div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
              Microservice Topology Ingestion Hub
            </div>
            <div style={{ fontSize: 12, color: '#64748b' }}>
              Import infrastructure topologies from GitHub, Docker Compose manifests, or pre-bundled microservice catalogs
            </div>
          </div>
        </div>

        {result && (
          <button
            onClick={() => onNavigate && onNavigate('topology')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 16px',
              borderRadius: 8,
              backgroundColor: '#10b981',
              border: 'none',
              color: '#ffffff',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            <span>View Graph Topology</span>
            <ArrowRight size={14} />
          </button>
        )}
      </div>

      {error && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: 8,
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#f87171',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {result && (
        <div
          style={{
            padding: '14px 18px',
            borderRadius: 10,
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <CheckCircle size={20} color="#10b981" />
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#34d399' }}>
                Ingestion Succeeded: {result.services_detected || 0} Services Processed
              </div>
              <div style={{ fontSize: 11, color: '#cbd5e1' }}>{result.message}</div>
            </div>
          </div>
          <span style={{ fontSize: 11, color: '#64748b' }}>
            Edges: {result.edges_created || 0}
          </span>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid #1e293b', paddingBottom: 8 }}>
        {[
          { id: 'catalog', label: 'Pre-Bundled Catalogs', icon: Layers },
          { id: 'github', label: 'GitHub Repository URL', icon: FolderGit2 },
          { id: 'yaml', label: 'Raw Manifest Editor', icon: FileCode },
          { id: 'external', label: 'Register SaaS / Cloud API', icon: Globe },
        ].map((t) => {
          const Icon = t.icon;
          const isSelected = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id as any)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 16px',
                borderRadius: 8,
                border: 'none',
                backgroundColor: isSelected ? '#1e293b' : 'transparent',
                color: isSelected ? '#38bdf8' : '#94a3b8',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <Icon size={14} />
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Pre-Bundled Catalogs */}
      {activeTab === 'catalog' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
          {(sampleRepos.length > 0 ? sampleRepos : [
            {
              slug: 'google-online-boutique',
              name: 'Google Online Boutique',
              description: '11 cloud-native microservices with gRPC communication and PostgreSQL.',
              services_count: 11,
              primary_language: 'Go / Python / Java',
            },
            {
              slug: 'sock-shop',
              name: 'Weaveworks Sock Shop',
              description: 'E-commerce microservices with MongoDB, RabbitMQ and Node.js.',
              services_count: 8,
              primary_language: 'Node.js / Java',
            },
            {
              slug: 'bank-of-anthos',
              name: 'Bank of Anthos',
              description: 'Financial ledger with JWT authentication and balance ledgers.',
              services_count: 9,
              primary_language: 'Java / Python',
            },
          ]).map((s) => (
            <div
              key={s.slug}
              style={{
                backgroundColor: '#0c1322',
                borderRadius: 12,
                border: '1px solid #1e293b',
                padding: 20,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: 16,
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>{s.name}</div>
                  <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 4, backgroundColor: '#1e293b', color: '#38bdf8' }}>
                    {s.services_count} Services
                  </span>
                </div>
                <p style={{ fontSize: 12, color: '#94a3b8', margin: 0, lineHeight: 1.4 }}>
                  {s.description}
                </p>
                <div style={{ fontSize: 11, color: '#64748b' }}>
                  Stack: {s.primary_language}
                </div>
              </div>

              <button
                onClick={() => handleIngestSample(s.slug)}
                disabled={isLoading}
                style={{
                  padding: '10px 14px',
                  borderRadius: 8,
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  color: '#f8fafc',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                }}
              >
                <UploadCloud size={14} color="#38bdf8" />
                <span>{isLoading ? 'Loading...' : 'Load Into Active Graph'}</span>
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Tab 2: GitHub URL */}
      {activeTab === 'github' && (
        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 24, maxWidth: 650, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
            Import from GitHub Repository (Read-Only)
          </div>

          <div>
            <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Repository Identifier (owner/repo)</label>
            <input
              type="text"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="GoogleCloudPlatform/microservices-demo"
              style={{ width: '100%', padding: '10px 12px', borderRadius: 8, backgroundColor: '#070b14', border: '1px solid #1e293b', color: '#f8fafc', fontSize: 12 }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Branch / Tag</label>
              <input
                type="text"
                value={githubBranch}
                onChange={(e) => setGithubBranch(e.target.value)}
                placeholder="main"
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, backgroundColor: '#070b14', border: '1px solid #1e293b', color: '#f8fafc', fontSize: 12 }}
              />
            </div>
            <div>
              <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Manifest Path</label>
              <input
                type="text"
                value={githubPath}
                onChange={(e) => setGithubPath(e.target.value)}
                placeholder="docker-compose.yml"
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, backgroundColor: '#070b14', border: '1px solid #1e293b', color: '#f8fafc', fontSize: 12 }}
              />
            </div>
          </div>

          <div>
            <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Personal Access Token (Optional, for private repos)</label>
            <input
              type="password"
              value={githubToken}
              onChange={(e) => setGithubToken(e.target.value)}
              placeholder="ghp_..."
              style={{ width: '100%', padding: '10px 12px', borderRadius: 8, backgroundColor: '#070b14', border: '1px solid #1e293b', color: '#f8fafc', fontSize: 12 }}
            />
            <span style={{ fontSize: 10, color: '#64748b', display: 'block', marginTop: 4 }}>
              🔒 Security guarantee: Tokens are used strictly in-memory for read-only repository fetching and are never logged or stored.
            </span>
          </div>

          <button
            onClick={handleIngestGithub}
            disabled={isLoading}
            style={{
              padding: '12px 16px',
              borderRadius: 8,
              backgroundColor: '#3b82f6',
              border: 'none',
              color: '#ffffff',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              marginTop: 8,
            }}
          >
            <UploadCloud size={14} />
            <span>{isLoading ? 'Fetching Repository...' : 'Fetch & Ingest GitHub Repository'}</span>
          </button>
        </div>
      )}

      {/* Tab 3: YAML Editor */}
      {activeTab === 'yaml' && (
        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
            Raw Docker Compose / Manifest YAML
          </div>

          <textarea
            value={rawYaml}
            onChange={(e) => setRawYaml(e.target.value)}
            rows={14}
            style={{
              width: '100%',
              padding: 14,
              borderRadius: 8,
              backgroundColor: '#070b14',
              border: '1px solid #1e293b',
              color: '#f8fafc',
              fontFamily: 'monospace',
              fontSize: 12,
              outline: 'none',
              lineHeight: 1.4,
            }}
          />

          <button
            onClick={handleIngestYaml}
            disabled={isLoading}
            style={{
              padding: '10px 16px',
              borderRadius: 8,
              backgroundColor: '#3b82f6',
              border: 'none',
              color: '#ffffff',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              alignSelf: 'flex-start',
            }}
          >
            <Play size={14} fill="#ffffff" />
            <span>{isLoading ? 'Parsing Manifest...' : 'Build Graph From YAML'}</span>
          </button>
        </div>
      )}

      {/* Tab 4: Register External Cloud Service */}
      {activeTab === 'external' && (
        <div style={{ backgroundColor: '#0c1322', borderRadius: 12, border: '1px solid #1e293b', padding: 24, maxWidth: 650, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
            Register External Cloud Provider / SaaS Dependency
          </div>

          <div>
            <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Vendor / API Name</label>
            <input
              type="text"
              value={extName}
              onChange={(e) => setExtName(e.target.value)}
              placeholder="e.g. Stripe Gateway, AWS S3, SendGrid"
              style={{ width: '100%', padding: '10px 12px', borderRadius: 8, backgroundColor: '#070b14', border: '1px solid #1e293b', color: '#f8fafc', fontSize: 12 }}
            />
          </div>

          <div>
            <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Service Category</label>
            <input
              type="text"
              value={extCategory}
              onChange={(e) => setExtCategory(e.target.value)}
              placeholder="Payment API, Email Delivery, Cloud Storage"
              style={{ width: '100%', padding: '10px 12px', borderRadius: 8, backgroundColor: '#070b14', border: '1px solid #1e293b', color: '#f8fafc', fontSize: 12 }}
            />
          </div>

          <div>
            <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Dependent Internal Microservice</label>
            <input
              type="text"
              value={extConsumer}
              onChange={(e) => setExtConsumer(e.target.value)}
              placeholder="paymentservice"
              style={{ width: '100%', padding: '10px 12px', borderRadius: 8, backgroundColor: '#070b14', border: '1px solid #1e293b', color: '#f8fafc', fontSize: 12 }}
            />
          </div>

          <button
            onClick={handleRegisterExternal}
            disabled={isLoading}
            style={{
              padding: '12px 16px',
              borderRadius: 8,
              backgroundColor: '#10b981',
              border: 'none',
              color: '#ffffff',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              marginTop: 8,
            }}
          >
            <Globe size={14} />
            <span>Register & Connect External SaaS Node</span>
          </button>
        </div>
      )}
    </div>
  );
};
