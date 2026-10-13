import React from 'react';
import { AlertCircle, CloudLightning, ShieldAlert, CheckCircle2 } from 'lucide-react';

export default function AlertFeed({ alerts = [] }) {
  return (
    <div className="p-4 rounded-xl bg-slate-900/60 backdrop-blur-md border border-slate-800/80 shadow-lg flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="w-5 h-5 text-rose-400" />
          <h2 className="text-sm font-bold tracking-wide text-slate-100 uppercase">
            Explainable Anomaly & Event Feed
          </h2>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
          {alerts.length} Records
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2.5 max-h-[420px] pr-1">
        {alerts.length === 0 ? (
          <div className="h-48 flex flex-col items-center justify-center text-slate-500 space-y-2 text-xs">
            <CheckCircle2 className="w-8 h-8 text-emerald-500/40" />
            <p>All stations nominal. Zero anomalies detected in current stream window.</p>
          </div>
        ) : (
          alerts.map((alert, idx) => {
            const isFault = alert.classification === 'sensor_fault';
            const isCritical = alert.severity === 'critical';

            return (
              <div
                key={alert.id || idx}
                className={`p-3 rounded-lg border transition-all ${
                  isFault
                    ? isCritical
                      ? 'bg-rose-950/20 border-rose-500/30 hover:border-rose-500/50'
                      : 'bg-amber-950/20 border-amber-500/30 hover:border-amber-500/50'
                    : 'bg-blue-950/20 border-blue-500/30 hover:border-blue-500/50'
                }`}
              >
                {/* Header row */}
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center space-x-2">
                    {isFault ? (
                      <span className="flex items-center space-x-1 text-[11px] font-bold px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                        <AlertCircle className="w-3 h-3 mr-0.5" />
                        SENSOR FAULT
                      </span>
                    ) : (
                      <span className="flex items-center space-x-1 text-[11px] font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                        <CloudLightning className="w-3 h-3 mr-0.5" />
                        GENUINE WEATHER EVENT
                      </span>
                    )}
                    <span className="font-mono text-xs font-semibold text-slate-200">
                      Station {alert.station_id}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2 text-[11px] font-mono text-slate-400">
                    <span>Conf: {Math.round(alert.confidence * 100)}%</span>
                    <span>•</span>
                    <span>{alert.timestamp?.split(' ')[1] || alert.timestamp}</span>
                  </div>
                </div>

                {/* Plain-language explanation */}
                <p className="text-xs text-slate-300 leading-relaxed font-sans mb-1.5">
                  {alert.reason}
                </p>

                {/* Badges footer */}
                <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
                  {alert.suspect_sensor && alert.suspect_sensor !== 'none' && (
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-rose-300 border border-rose-500/20">
                      Suspect: {alert.suspect_sensor.toUpperCase()}
                    </span>
                  )}
                  <span className="px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700">
                    Rule: {alert.rule || alert.rule_triggered}
                  </span>
                  <span className={`px-1.5 py-0.5 rounded uppercase font-semibold ${
                    isCritical ? 'bg-rose-500/10 text-rose-400' : 'bg-amber-500/10 text-amber-400'
                  }`}>
                    {alert.severity}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
