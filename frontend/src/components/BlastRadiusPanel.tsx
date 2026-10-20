import React, { useState } from 'react';
import {
  X,
  AlertCircle,
  Users,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Activity,
  Play,
  RotateCcw,
  Zap,
  CheckCircle2,
  FileText,
} from 'lucide-react';

interface BlastRadiusPanelProps {
  onClose?: () => void;
  onSimulatePR: (prId: string) => void;
  onInjectFault: () => void;
  onHealAction: () => void;
  onCommitIncident: () => void;
  onReset: () => void;
  simResult: any;
  faultActive: boolean;
  healed: boolean;
  committed: boolean;
  onOpenReport: () => void;
}

export const BlastRadiusPanel: React.FC<BlastRadiusPanelProps> = ({
  onClose,
  onSimulatePR,
  onInjectFault,
  onHealAction,
  onCommitIncident,
  onReset,
  simResult,
  faultActive,
  healed,
  committed,
  onOpenReport,
}) => {
  const [selectedPR, setSelectedPR] = useState('PR-142');
  const [isActionsOpen, setIsActionsOpen] = useState(true);

  const riskScore = simResult?.risk_score !== undefined ? Number(simResult.risk_score) : null;
  const verdict = simResult?.verdict ?? (riskScore !== null ? (riskScore >= 70 ? 'Blocked' : riskScore >= 40 ? 'Warn' : 'Approved') : 'Ready');

  return (
    <div
      style={{
        width: 380,
        height: '100%',
        backgroundColor: '#070c16',
        borderLeft: '1px solid #1e293b',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '-8px 0 24px rgba(0, 0, 0, 0.5)',
        zIndex: 20,
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '18px 20px',
          borderBottom: '1px solid #1e293b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ fontSize: 16, fontWeight: 700, color: '#f8fafc' }}>
          Blast Radius Analysis
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              padding: 4,
            }}
          >
            <X size={18} />
          </button>
        )}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
        {/* Critical Path Detected Tag */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 7,
            padding: '4px 10px',
            borderRadius: 6,
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            color: '#f87171',
            fontSize: 10,
            fontWeight: 800,
            letterSpacing: 0.8,
            marginBottom: 12,
            textTransform: 'uppercase',
          }}
        >
          <span className="pulse-indicator" />
          ANALYSIS VERDICT: {verdict.toUpperCase()}
        </div>

        {/* Path Breadcrumbs */}
        <div
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: '#f8fafc',
            fontFamily: 'JetBrains Mono, monospace',
            marginBottom: 6,
          }}
        >
          {simResult?.target_service ? `Target: ${simResult.target_service}` : 'paymentservice'}
        </div>
        <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.4, marginBottom: 20 }}>
          {simResult?.summary || 'Calculated dynamic blast radius based on graph traversal of upstream callers.'}
        </div>

        {/* Metric Cards Stack */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 20 }}>
          {/* 1. Risk Score */}
          <div
            style={{
              padding: '12px 14px',
              borderRadius: 8,
              backgroundColor: '#0a101d',
              border: '1px solid #1e293b',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#94a3b8' }}>
                <ShieldCheck size={14} color="#38bdf8" />
                <span>Risk Score</span>
              </div>
              <span style={{ fontSize: 10, color: riskScore !== null && riskScore >= 70 ? '#ef4444' : '#10b981', fontWeight: 700 }}>
                {riskScore !== null ? (riskScore >= 70 ? 'High Risk' : riskScore >= 40 ? 'Moderate Risk' : 'Low Risk') : 'Pending'}
              </span>
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#f8fafc', marginBottom: 8 }}>
              {riskScore !== null ? `${riskScore.toFixed(1)} / 100` : '--'}
            </div>
            <div style={{ width: '100%', height: 4, backgroundColor: '#1e293b', borderRadius: 2 }}>
              <div
                style={{
                  width: `${Math.min(100, Math.max(0, riskScore ?? 0))}%`,
                  height: '100%',
                  backgroundColor: riskScore !== null && riskScore >= 70 ? '#ef4444' : '#38bdf8',
                  borderRadius: 2,
                  boxShadow: '0 0 8px #38bdf8',
                }}
              />
            </div>
          </div>

          {/* 2. Impacted Callers */}
          <div
            style={{
              padding: '12px 14px',
              borderRadius: 8,
              backgroundColor: '#0a101d',
              border: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>
                <Users size={14} color="#38bdf8" />
                <span>Impacted Callers</span>
              </div>
              <div style={{ fontSize: 18, fontWeight: 800, color: '#f8fafc' }}>
                {simResult?.blast_details?.length ?? 0} <span style={{ fontSize: 11, fontWeight: 500, color: '#64748b' }}>Services</span>
              </div>
            </div>
            {/* Sparkline mini SVG */}
            <svg width="70" height="30" viewBox="0 0 70 30" fill="none">
              <path
                d="M2 24L14 18L26 22L38 10L50 16L68 6"
                stroke="#10b981"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>

          {/* 3. Service Ownership */}
          <div
            style={{
              padding: '12px 14px',
              borderRadius: 8,
              backgroundColor: '#0a101d',
              border: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 2 }}>Target Service</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
                {simResult?.target_service ?? 'paymentservice'}
              </div>
              <div style={{ fontSize: 10, color: '#64748b' }}>
                {simResult?.author ? `Author: ${simResult.author}` : 'Core Tier 1 Service'}
              </div>
            </div>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                backgroundColor: 'rgba(56, 189, 248, 0.1)',
                border: '1px solid #0284c7',
                color: '#38bdf8',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 10,
                fontWeight: 800,
              }}
            >
              {(simResult?.target_service ? simResult.target_service.slice(0, 2).toUpperCase() : 'PS')}
            </div>
          </div>

          {/* 4. Potential Impact */}
          <div
            style={{
              padding: '12px 14px',
              borderRadius: 8,
              backgroundColor: '#0a101d',
              border: '1px solid #1e293b',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#94a3b8' }}>
                <AlertCircle size={14} color={verdict === 'Blocked' ? '#ef4444' : verdict === 'Warn' ? '#f97316' : '#10b981'} />
                <span>Potential Impact ⓘ</span>
              </div>
              <span
                style={{
                  fontSize: 9,
                  fontWeight: 800,
                  backgroundColor: verdict === 'Blocked' ? 'rgba(239, 68, 68, 0.2)' : verdict === 'Warn' ? 'rgba(249, 115, 22, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                  color: verdict === 'Blocked' ? '#f87171' : verdict === 'Warn' ? '#fb923c' : '#34d399',
                  padding: '1px 6px',
                  borderRadius: 4,
                  textTransform: 'uppercase',
                }}
              >
                {verdict === 'Blocked' ? 'High Impact' : verdict === 'Warn' ? 'Moderate Impact' : verdict === 'Approved' ? 'Low Impact' : 'Awaiting Simulation'}
              </span>
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.4 }}>
              {simResult?.recommendation ?? 'No simulation executed yet. Select a change and run analysis.'}
            </div>
          </div>
        </div>

        {/* View Risk Report Collapsible */}
        <button
          onClick={onOpenReport}
          style={{
            width: '100%',
            padding: '10px 14px',
            borderRadius: 8,
            backgroundColor: 'rgba(30, 41, 59, 0.6)',
            border: '1px solid #1e293b',
            color: '#f8fafc',
            fontSize: 12,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            marginBottom: 20,
            transition: 'background 0.2s',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileText size={15} color="#38bdf8" />
            <span>View Risk Report</span>
          </div>
          <ChevronDown size={15} color="#94a3b8" />
        </button>

        {/* Mission Control Live Actions (Interactive Engine) */}
        <div
          style={{
            padding: '14px',
            borderRadius: 10,
            backgroundColor: '#090e18',
            border: '1px solid #1e293b',
          }}
        >
          <div
            onClick={() => setIsActionsOpen(!isActionsOpen)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              marginBottom: isActionsOpen ? 12 : 0,
            }}
          >
            <div style={{ fontSize: 12, fontWeight: 700, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Zap size={14} />
              <span>Interactive Closed Loop</span>
            </div>
            {isActionsOpen ? <ChevronUp size={14} color="#64748b" /> : <ChevronDown size={14} color="#64748b" />}
          </div>

          {isActionsOpen && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {/* PR Selector */}
              <div>
                <label style={{ fontSize: 10, color: '#64748b', display: 'block', marginBottom: 4 }}>
                  Select Pull Request:
                </label>
                <select
                  value={selectedPR}
                  onChange={(e) => {
                    setSelectedPR(e.target.value);
                    onSimulatePR(e.target.value);
                  }}
                  style={{
                    width: '100%',
                    padding: '6px 8px',
                    borderRadius: 6,
                    backgroundColor: '#0f172a',
                    border: '1px solid #334155',
                    color: '#f8fafc',
                    fontSize: 11,
                    outline: 'none',
                  }}
                >
                  <option value="PR-142">PR #142 (Breaking Payment Schema)</option>
                  <option value="PR-010">PR #010 (Safe Cart Feature)</option>
                  <option value="PR-077">PR #077 (Cyclic Shipping Dependency)</option>
                  <option value="PR-055">PR #055 (Moderate Recommendation)</option>
                </select>
              </div>

              {/* Action Buttons */}
              <button
                onClick={() => onSimulatePR(selectedPR)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 6,
                  backgroundColor: '#0284c7',
                  border: 'none',
                  color: '#fff',
                  fontSize: 11,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  cursor: 'pointer',
                }}
              >
                <Play size={13} />
                <span>1. Run Pre-Ship Simulation (Score: {riskScore})</span>
              </button>

              <button
                onClick={onInjectFault}
                style={{
                  padding: '8px 12px',
                  borderRadius: 6,
                  backgroundColor: faultActive ? '#7f1d1d' : 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid #ef4444',
                  color: '#fca5a5',
                  fontSize: 11,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  cursor: 'pointer',
                }}
              >
                <Activity size={13} />
                <span>2. Inject Pool Exhaustion Fault</span>
              </button>

              <button
                onClick={onHealAction}
                style={{
                  padding: '8px 12px',
                  borderRadius: 6,
                  backgroundColor: healed ? 'rgba(16, 185, 129, 0.2)' : 'rgba(30, 41, 59, 0.8)',
                  border: healed ? '1px solid #10b981' : '1px solid #334155',
                  color: healed ? '#34d399' : '#94a3b8',
                  fontSize: 11,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  cursor: 'pointer',
                }}
              >
                <CheckCircle2 size={13} color={healed ? '#10b981' : '#94a3b8'} />
                <span>3. Guarded Heal (Scale Pool to 150)</span>
              </button>

              <button
                onClick={onCommitIncident}
                style={{
                  padding: '8px 12px',
                  borderRadius: 6,
                  backgroundColor: committed ? 'rgba(168, 85, 247, 0.2)' : 'rgba(30, 41, 59, 0.8)',
                  border: committed ? '1px solid #a855f7' : '1px solid #334155',
                  color: committed ? '#c084fc' : '#94a3b8',
                  fontSize: 11,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  cursor: 'pointer',
                }}
              >
                <Zap size={13} color={committed ? '#c084fc' : '#94a3b8'} />
                <span>4. Commit Incident (+5 Risk Delta)</span>
              </button>

              <button
                onClick={onReset}
                style={{
                  padding: '6px 10px',
                  borderRadius: 6,
                  backgroundColor: 'transparent',
                  border: '1px solid #334155',
                  color: '#64748b',
                  fontSize: 10,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 5,
                  cursor: 'pointer',
                  marginTop: 4,
                }}
              >
                <RotateCcw size={11} />
                <span>Reset Demo Baseline</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
