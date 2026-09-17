import React from 'react';
import { Radio } from 'lucide-react';

export default function StationHealth({ stations = [], selectedStationId, onSelectStation, latestPacket }) {
  const getHealthBadge = (score) => {
    if (score >= 80) {
      return {
        bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
        bar: 'bg-emerald-500',
        label: 'HEALTHY'
      };
    } else if (score >= 60) {
      return {
        bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        bar: 'bg-amber-500',
        label: 'WARNING'
      };
    } else if (score >= 30) {
      return {
        bg: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
        bar: 'bg-orange-500',
        label: 'DEGRADED'
      };
    } else {
      return {
        bg: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
        bar: 'bg-rose-500',
        label: 'CRITICAL'
      };
    }
  };

  return (
    <div className="p-4 rounded-xl bg-slate-900/60 backdrop-blur-md border border-slate-800/80 shadow-lg flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Radio className="w-5 h-5 text-cyan-400" />
          <h2 className="text-sm font-bold tracking-wide text-slate-100 uppercase">
            Station Fleet Health Status
          </h2>
        </div>
        <span className="text-xs text-slate-400 font-mono">
          Click station to inspect
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {stations.map((st) => {
          const sid = st?.id || 'UNKNOWN';
          const isSelected = sid === selectedStationId;
          const isCurrentlyTicking = latestPacket?.station_id === sid;
          const health = isCurrentlyTicking ? latestPacket.health_score : (st?.health_score ?? 100);
          const badge = getHealthBadge(health);

          // Safe metadata formatting for both preset stations and custom user-uploaded stations
          const displayName = st?.name || `Station ${sid}`;
          const coordText = (st?.latitude != null && st?.longitude != null)
            ? `${st.latitude.toFixed(2)}°N, ${st.longitude.toFixed(2)}°E`
            : 'Active Telemetry Channel';
          const elevText = st?.elevation != null ? `Elev: ${st.elevation}m` : 'Surface AWS';

          return (
            <div
              key={sid}
              onClick={() => onSelectStation(sid)}
              className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                isSelected
                  ? 'bg-slate-850 border-cyan-500/80 shadow-md shadow-cyan-500/10 ring-1 ring-cyan-500/40'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/40'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-sm font-bold text-slate-100">
                    {sid}
                  </span>
                  <span className="text-xs text-slate-400 font-sans truncate max-w-[120px]">
                    {displayName}
                  </span>
                </div>

                <div className="flex items-center space-x-1.5">
                  {isCurrentlyTicking && (
                    <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                  )}
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${badge.bg}`}>
                    {badge.label}
                  </span>
                </div>
              </div>

              {/* Health progress bar */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-slate-400">Sensor Health</span>
                  <span className="font-semibold text-slate-200">{health}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${badge.bar} transition-all duration-500`}
                    style={{ width: `${Math.min(100, Math.max(0, health))}%` }}
                  />
                </div>
              </div>

              {/* Coordinates / elevation */}
              <div className="mt-2 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] font-mono text-slate-400">
                <span>{coordText}</span>
                <span>{elevText}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
