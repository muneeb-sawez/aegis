import React, { useState } from 'react';
import { X, ShieldAlert, Play } from 'lucide-react';

interface PredictModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRiskAssessed?: (result: any) => void;
}

export const PredictModal: React.FC<PredictModalProps> = ({ isOpen, onClose, onRiskAssessed }) => {
  const [selectedService, setSelectedService] = useState('paymentservice');
  const [changeType, setChangeType] = useState('api_breaking');
  const [description, setDescription] = useState('Remove transaction_id field from charge response');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  if (!isOpen) return null;

  const handleRunAnalysis = async () => {
    setIsLoading(true);
    try {
      const resp = await fetch('/api/predict/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_id: selectedService,
          change_type: changeType,
          change_title: `Change to ${selectedService}`,
          description: description,
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setResult(data);
        if (onRiskAssessed) onRiskAssessed(data);
      }
    } catch (e) {
      console.error('PREDICT error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
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
          maxHeight: '90vh',
          backgroundColor: '#0a101d',
          border: '1px solid #1e293b',
          borderRadius: 14,
          boxShadow: '0 25px 60px rgba(0, 0, 0, 0.85)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
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
            <ShieldAlert size={20} color="#38bdf8" />
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#f8fafc' }}>
                PREDICT — Pre-Deployment Change-Risk Intelligence
              </div>
              <div style={{ fontSize: 11, color: '#64748b' }}>
                Simulate proposed code, contract, or dependency changes before merge
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 18 }}>
          {/* Form */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 14,
              padding: '16px',
              borderRadius: 10,
              backgroundColor: '#070c16',
              border: '1px solid #1e293b',
            }}
          >
            <div>
              <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 5 }}>
                Target Microservice:
              </label>
              <select
                value={selectedService}
                onChange={(e) => setSelectedService(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  borderRadius: 6,
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  color: '#f8fafc',
                  fontSize: 12,
                  outline: 'none',
                }}
              >
                <option value="paymentservice">paymentservice (Payment Gateway)</option>
                <option value="checkoutservice">checkoutservice (Checkout Flow)</option>
                <option value="cartservice">cartservice (Shopping Cart)</option>
                <option value="orderservice">orderservice (Order Processing)</option>
                <option value="recommendationservice">recommendationservice (Product Recs)</option>
                <option value="shippingservice">shippingservice (Fulfillment)</option>
                <option value="emailservice">emailservice (Notifications)</option>
                <option value="frontend">frontend (API Gateway)</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 5 }}>
                Proposed Change Type:
              </label>
              <select
                value={changeType}
                onChange={(e) => {
                  setChangeType(e.target.value);
                  if (e.target.value === 'api_breaking') {
                    setDescription('Remove transaction_id field from charge response');
                  } else if (e.target.value === 'additive_safe') {
                    setDescription('Add optional discount_code string field to response schema');
                  } else if (e.target.value === 'dependency_cycle') {
                    setDescription('Introduce circular reverse dependency from shippingservice to caller');
                  }
                }}
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  borderRadius: 6,
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  color: '#f8fafc',
                  fontSize: 12,
                  outline: 'none',
                }}
              >
                <option value="api_breaking">Breaking API Contract (Removes Required Field)</option>
                <option value="additive_safe">Backwards-Compatible Additive Field (Safe)</option>
                <option value="dependency_cycle">Architectural Reverse Call (Causes Cycle)</option>
              </select>
            </div>

            <div style={{ gridColumn: 'span 2' }}>
              <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 5 }}>
                Change Description:
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  borderRadius: 6,
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  color: '#f8fafc',
                  fontSize: 12,
                  outline: 'none',
                }}
              />
            </div>

            <div style={{ gridColumn: 'span 2', display: 'flex', justifyContent: 'flex-end', marginTop: 4 }}>
              <button
                onClick={handleRunAnalysis}
                disabled={isLoading}
                style={{
                  padding: '8px 18px',
                  borderRadius: 6,
                  backgroundColor: '#0284c7',
                  border: 'none',
                  color: '#fff',
                  fontSize: 12,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                }}
              >
                <Play size={14} />
                <span>{isLoading ? 'Traversing Graph...' : 'Run PREDICT Risk Analysis'}</span>
              </button>
            </div>
          </div>

          {/* Results View */}
          {result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Score Header Card */}
              <div
                style={{
                  padding: '16px 20px',
                  borderRadius: 10,
                  backgroundColor: '#070c16',
                  border: result.verdict === 'Blocked' ? '1px solid #ef4444' : result.verdict === 'Warn' ? '1px solid #f97316' : '1px solid #10b981',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span
                      style={{
                        padding: '3px 8px',
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 800,
                        backgroundColor: result.verdict === 'Blocked' ? 'rgba(239, 68, 68, 0.2)' : result.verdict === 'Warn' ? 'rgba(249, 115, 22, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                        color: result.verdict === 'Blocked' ? '#f87171' : result.verdict === 'Warn' ? '#fb923c' : '#34d399',
                        textTransform: 'uppercase',
                      }}
                    >
                      {result.verdict === 'Blocked' ? 'High Risk — Deployment Blocked' : result.verdict === 'Warn' ? 'Moderate Risk — Review Required' : 'Low Risk — Approved'}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 6 }}>
                    {result.recommendation}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 28, fontWeight: 900, color: '#f8fafc' }}>
                    {result.risk_score} <span style={{ fontSize: 13, fontWeight: 500, color: '#64748b' }}>/ 100</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#64748b' }}>0.35B + 0.30C + 0.15D + 0.20H</div>
                </div>
              </div>

              {/* Component breakdown */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                <div style={{ padding: '10px', borderRadius: 8, backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: 10, color: '#64748b' }}>Blast Radius (B)</div>
                  <div style={{ fontSize: 18, fontWeight: 800, color: '#f8fafc', marginTop: 2 }}>
                    {result.breakdown.blast_score}
                  </div>
                  <div style={{ fontSize: 9, color: '#94a3b8' }}>Weight 0.35</div>
                </div>

                <div style={{ padding: '10px', borderRadius: 8, backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: 10, color: '#64748b' }}>Contract Diff (C)</div>
                  <div style={{ fontSize: 18, fontWeight: 800, color: result.breakdown.contract_score > 0 ? '#f87171' : '#10b981', marginTop: 2 }}>
                    {result.breakdown.contract_score}
                  </div>
                  <div style={{ fontSize: 9, color: '#94a3b8' }}>Weight 0.30</div>
                </div>

                <div style={{ padding: '10px', borderRadius: 8, backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: 10, color: '#64748b' }}>Cycle Penalty (D)</div>
                  <div style={{ fontSize: 18, fontWeight: 800, color: result.breakdown.cycle_score > 0 ? '#f87171' : '#10b981', marginTop: 2 }}>
                    {result.breakdown.cycle_score}
                  </div>
                  <div style={{ fontSize: 9, color: '#94a3b8' }}>Weight 0.15</div>
                </div>

                <div style={{ padding: '10px', borderRadius: 8, backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: 10, color: '#64748b' }}>Incident History (H)</div>
                  <div style={{ fontSize: 18, fontWeight: 800, color: '#c084fc', marginTop: 2 }}>
                    {result.breakdown.history_score}
                  </div>
                  <div style={{ fontSize: 9, color: '#94a3b8' }}>Weight 0.20 ({result.incident_count_30d} incs)</div>
                </div>
              </div>

              {/* Upstream Callers Traversal Details */}
              <div style={{ padding: '12px 16px', borderRadius: 8, backgroundColor: '#070c16', border: '1px solid #1e293b' }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc', marginBottom: 8 }}>
                  Upstream Affected Callers (Traversed Backwards along CALLS):
                </div>
                {result.blast_details.length > 0 ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {result.blast_details.map((caller: any, idx: number) => (
                      <div
                        key={idx}
                        style={{
                          padding: '6px 10px',
                          borderRadius: 6,
                          backgroundColor: '#0f172a',
                          border: caller.severity_halo === 'red' ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(249, 115, 22, 0.4)',
                          fontSize: 11,
                          color: '#e2e8f0',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                        }}
                      >
                        <span style={{ fontWeight: 600 }}>{caller.node}</span>
                        <span style={{ fontSize: 9, color: '#64748b' }}>(Hop {caller.hops}, Weight {caller.impact_weight})</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: 11, color: '#64748b' }}>No upstream callers affected (leaf service).</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
