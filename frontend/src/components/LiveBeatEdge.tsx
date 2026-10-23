import React, { memo } from 'react';
import { BaseEdge, getBezierPath, type EdgeProps } from '@xyflow/react';

export interface LiveBeatEdgeData {
  isLive?: boolean;
  isBlastPath?: boolean;
  status?: 'healthy' | 'degraded' | 'unavailable' | 'unconfigured';
  sourceHealth?: string;
  targetHealth?: string;
  latency_ms?: number;
  isCritical?: boolean;
  pulseTrigger?: number; // Monotonically increasing counter on probe events
  label?: string;
}

export const LiveBeatEdge: React.FC<EdgeProps> = memo(({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
}) => {
  const edgeData = (data || {}) as LiveBeatEdgeData;

  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const isLive = edgeData.isLive ?? false;
  const isCritical = edgeData.isCritical ?? false;
  const isBlastPath = edgeData.isBlastPath ?? false;
  const status = edgeData.status || (isLive ? 'healthy' : 'unconfigured');

  // Determine theme colors based on live status
  let strokeColor = '#334155'; // default muted slate for dormant
  let particleColor = '#10b981'; // emerald
  let glowColor = 'rgba(16, 185, 129, 0.6)';
  let speed = 1.6; // duration in seconds for one full loop

  if (isBlastPath) {
    strokeColor = '#ef4444'; // glowing red blast stream
    particleColor = '#fca5a5';
    glowColor = 'rgba(239, 68, 68, 0.9)';
    speed = 0.9;
  } else if (status === 'healthy' || isLive) {
    if (isCritical) {
      strokeColor = '#06b6d4'; // bright cyan for critical/gateway
      particleColor = '#38bdf8';
      glowColor = 'rgba(56, 189, 248, 0.7)';
      speed = 1.3;
    } else {
      strokeColor = '#10b981'; // vibrant emerald
      particleColor = '#34d399';
      glowColor = 'rgba(16, 185, 129, 0.7)';
      speed = 1.7;
    }
  } else if (status === 'degraded') {
    strokeColor = '#f59e0b';
    particleColor = '#fbbf24';
    glowColor = 'rgba(245, 158, 11, 0.7)';
    speed = 2.8;
  } else if (status === 'unavailable') {
    strokeColor = '#ef4444';
    particleColor = '#f87171';
    glowColor = 'rgba(239, 68, 68, 0.7)';
    speed = 0; // halted
  }

  const filterId = `beat-glow-${id.replace(/[^a-zA-Z0-9-_]/g, '_')}`;

  return (
    <>
      <defs>
        <filter id={filterId} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Background ambient glow track when live */}
      {isLive && (
        <path
          d={edgePath}
          fill="none"
          stroke={glowColor}
          strokeWidth={4}
          strokeOpacity={0.25}
          strokeLinecap="round"
        />
      )}

      {/* Main Base Edge line */}
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          stroke: isLive ? strokeColor : (style.stroke || strokeColor),
          strokeWidth: isLive ? 2.2 : 1.4,
          strokeDasharray: !isLive && status === 'unavailable' ? '4 4' : undefined,
          transition: 'stroke 0.4s ease, stroke-width 0.4s ease',
        }}
      />

      {/* Real-time Moving Beats (Dots flowing from source to target) */}
      {isLive && speed > 0 && (
        <g className="live-beat-particles">
          {/* First Particle Dot */}
          <circle r="4" fill={particleColor} filter={`url(#${filterId})`}>
            <animateMotion
              dur={`${speed}s`}
              repeatCount="indefinite"
              path={edgePath}
              rotate="auto"
            />
          </circle>
          {/* Inner bright core for particle 1 */}
          <circle r="2" fill="#ffffff" opacity="0.95">
            <animateMotion
              dur={`${speed}s`}
              repeatCount="indefinite"
              path={edgePath}
              rotate="auto"
            />
          </circle>

          {/* Second Particle Dot (staggered by 50% for continuous flow) */}
          <circle r="3.5" fill={particleColor} opacity="0.85" filter={`url(#${filterId})`}>
            <animateMotion
              dur={`${speed}s`}
              begin={`${speed / 2}s`}
              repeatCount="indefinite"
              path={edgePath}
              rotate="auto"
            />
          </circle>
          <circle r="1.5" fill="#ffffff" opacity="0.9">
            <animateMotion
              dur={`${speed}s`}
              begin={`${speed / 2}s`}
              repeatCount="indefinite"
              path={edgePath}
              rotate="auto"
            />
          </circle>
        </g>
      )}
    </>
  );
});

LiveBeatEdge.displayName = 'LiveBeatEdge';
