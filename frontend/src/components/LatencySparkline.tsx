import React from 'react';

interface LatencySparklineProps {
  latencies?: number[];
  baseline?: number;
  width?: number;
  height?: number;
  status?: string;
}

export const LatencySparkline: React.FC<LatencySparklineProps> = ({
  latencies = [],
  baseline,
  width = 330,
  height = 65,
  status = 'healthy',
}) => {
  if (!latencies || latencies.length === 0) {
    return (
      <div
        style={{
          width,
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgba(15, 23, 42, 0.6)',
          borderRadius: 8,
          border: '1px dashed #334155',
          color: '#64748b',
          fontSize: 11,
          fontFamily: 'JetBrains Mono, monospace',
        }}
      >
        Waiting for probe telemetry...
      </div>
    );
  }

  const strokeColor =
    status === 'unavailable' || status === 'unhealthy'
      ? '#ef4444'
      : status === 'degraded'
      ? '#f59e0b'
      : '#10b981';

  const fillColor =
    status === 'unavailable' || status === 'unhealthy'
      ? 'rgba(239, 68, 68, 0.15)'
      : status === 'degraded'
      ? 'rgba(245, 158, 11, 0.15)'
      : 'rgba(16, 185, 129, 0.15)';

  const minVal = Math.min(...latencies, baseline ?? Infinity, 0);
  const maxVal = Math.max(...latencies, baseline ? baseline * 1.5 : 100, 10);
  const range = maxVal - minVal || 1;

  const paddingX = 10;
  const paddingY = 8;
  const effectiveWidth = width - paddingX * 2;
  const effectiveHeight = height - paddingY * 2;

  const points = latencies.map((val, idx) => {
    const x = paddingX + (idx / Math.max(1, latencies.length - 1)) * effectiveWidth;
    const y = height - paddingY - ((val - minVal) / range) * effectiveHeight;
    return { x, y, val };
  });

  const pathD = points.reduce((acc, p, idx) => `${acc} ${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`, '');
  const areaD = `${pathD} L ${points[points.length - 1].x.toFixed(1)} ${height - paddingY} L ${points[0].x.toFixed(1)} ${height - paddingY} Z`;

  const baselineY =
    baseline !== undefined && baseline !== null
      ? height - paddingY - ((baseline - minVal) / range) * effectiveHeight
      : null;

  const latestVal = latencies[latencies.length - 1];

  return (
    <div
      style={{
        backgroundColor: '#070b14',
        padding: '10px 12px',
        borderRadius: 8,
        border: '1px solid #1e293b',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11 }}>
        <span style={{ color: '#94a3b8', fontWeight: 600 }}>Rolling Latency Window</span>
        <span style={{ color: strokeColor, fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>
          {latestVal.toFixed(1)} ms
          {baseline ? ` (baseline ${baseline.toFixed(1)} ms)` : ''}
        </span>
      </div>

      <svg width={width} height={height} style={{ overflow: 'visible' }}>
        {/* Baseline horizontal dashed line */}
        {baselineY !== null && (
          <line
            x1={paddingX}
            y1={baselineY}
            x2={width - paddingX}
            y2={baselineY}
            stroke="#64748b"
            strokeDasharray="3 3"
            strokeWidth={1}
          />
        )}

        {/* Gradient fill area under curve */}
        <path d={areaD} fill={fillColor} />

        {/* Primary trend line */}
        <path d={pathD} fill="none" stroke={strokeColor} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />

        {/* Highlight latest point */}
        {points.length > 0 && (
          <circle
            cx={points[points.length - 1].x}
            cy={points[points.length - 1].y}
            r={3.5}
            fill={strokeColor}
            stroke="#070b14"
            strokeWidth={1.5}
          />
        )}
      </svg>
    </div>
  );
};
