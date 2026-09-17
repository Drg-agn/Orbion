import React from 'react';
import { Navigation } from 'lucide-react';

export default function StationMap({ stations = [], selectedStationId, onSelectStation, latestPacket }) {
  const hasCoordinates = stations.length > 0 && stations.some(s => s.latitude != null && s.longitude != null);

  const lats = stations.map(s => s.latitude || 28.6);
  const lons = stations.map(s => s.longitude || 77.2);
  const minLat = Math.min(...lats, 28.55);
  const maxLat = Math.max(...lats, 28.70);
  const minLon = Math.min(...lons, 77.15);
  const maxLon = Math.max(...lons, 77.27);

  const getCoordinates = (st, index, total) => {
    const width = 340;
    const height = 240;
    const padding = 35;

    if (hasCoordinates && st.latitude != null && st.longitude != null) {
      const x = padding + ((st.longitude - minLon) / (maxLon - minLon || 1)) * (width - 2 * padding);
      const y = height - (padding + ((st.latitude - minLat) / (maxLat - minLat || 1)) * (height - 2 * padding));
      return { x, y };
    }

    // Dynamic geometric mesh layout for uploaded datasets without GPS coordinates
    const centerX = width / 2;
    const centerY = height / 2;
    const radiusX = (width / 2) - padding - 10;
    const radiusY = (height / 2) - padding - 5;
    const angle = (index / (total || 1)) * 2 * Math.PI - Math.PI / 2;

    return {
      x: centerX + radiusX * Math.cos(angle),
      y: centerY + radiusY * Math.sin(angle)
    };
  };

  return (
    <div className="p-4 rounded-xl bg-slate-900/60 backdrop-blur-md border border-slate-800/80 shadow-lg flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Navigation className="w-5 h-5 text-cyan-400" />
          <h2 className="text-sm font-bold tracking-wide text-slate-100 uppercase">
            Spatial Sensor Network (Mesh)
          </h2>
        </div>
        <span className="text-xs font-mono text-cyan-400">
          {hasCoordinates ? '100km Geo Coherence' : 'Active Network Topology'}
        </span>
      </div>

      <div className="relative w-full flex-1 flex items-center justify-center min-h-[260px] bg-slate-950/60 rounded-lg border border-slate-800/60 overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b15_1px,transparent_1px),linear-gradient(to_bottom,#1e293b15_1px,transparent_1px)] bg-[size:24px_24px]" />

        <svg className="w-full h-full max-w-[420px] max-h-[260px]" viewBox="0 0 340 240">
          {/* Inter-station links */}
          {stations.map((st1, i) => {
            const p1 = getCoordinates(st1, i, stations.length);
            return stations.slice(i + 1).map((st2, j) => {
              const p2 = getCoordinates(st2, i + 1 + j, stations.length);
              return (
                <line
                  key={`${st1.id}-${st2.id}`}
                  x1={p1.x}
                  y1={p1.y}
                  x2={p2.x}
                  y2={p2.y}
                  stroke="#1e293b"
                  strokeWidth="1"
                  strokeDasharray="2 3"
                />
              );
            });
          })}

          {/* Station Nodes */}
          {stations.map((st, idx) => {
            const sid = st.id || `S${idx}`;
            const pos = getCoordinates(st, idx, stations.length);
            const isSelected = sid === selectedStationId;
            const isTicking = latestPacket?.station_id === sid;
            const health = isTicking ? latestPacket.health_score : (st.health_score ?? 100);

            let strokeColor = '#10b981';
            let fillColor = '#065f46';
            if (health < 60) {
              strokeColor = '#f43f5e';
              fillColor = '#881337';
            } else if (health < 80) {
              strokeColor = '#f59e0b';
              fillColor = '#78350f';
            }

            return (
              <g
                key={sid}
                className="cursor-pointer transition-transform hover:scale-110"
                onClick={() => onSelectStation(sid)}
              >
                {isTicking && (
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={14}
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth="1.5"
                    className="animate-ping opacity-60"
                  />
                )}

                {isSelected && (
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={12}
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth="2"
                  />
                )}

                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={7}
                  fill={fillColor}
                  stroke={strokeColor}
                  strokeWidth="2"
                />

                <text
                  x={pos.x}
                  y={pos.y - 11}
                  textAnchor="middle"
                  fill={isSelected ? '#38bdf8' : '#94a3b8'}
                  fontSize="9"
                  fontFamily="monospace"
                  fontWeight={isSelected ? 'bold' : 'normal'}
                >
                  {sid}
                </text>
              </g>
            );
          })}
        </svg>

        <div className="absolute bottom-2 left-3 flex items-center space-x-3 text-[10px] font-mono text-slate-400 bg-slate-900/80 px-2.5 py-1 rounded border border-slate-800">
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
            <span>Coherent / Normal</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />
            <span>Isolated Fault</span>
          </span>
        </div>
      </div>
    </div>
  );
}
