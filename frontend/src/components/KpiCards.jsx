import React from 'react';
import { Activity, ShieldCheck, AlertTriangle, CloudLightning } from 'lucide-react';

export default function KpiCards({ metrics, liveAlerts = [] }) {
  // Count current session classifications
  const faultCount = liveAlerts.filter(a => a.classification === 'sensor_fault').length;
  const eventCount = liveAlerts.filter(a => a.classification === 'weather_event').length;

  const cards = [
    {
      title: 'Online Stations',
      value: metrics ? `${metrics.healthy_stations}/${metrics.total_stations}` : '6/6',
      sub: 'All telemetry channels active',
      icon: Activity,
      color: 'text-cyan-400',
      border: 'border-cyan-500/20',
      bg: 'bg-cyan-950/20',
    },
    {
      title: 'Network Health Score',
      value: metrics ? `${metrics.avg_health_score}%` : '98.5%',
      sub: 'Multi-station composite index',
      icon: ShieldCheck,
      color: 'text-emerald-400',
      border: 'border-emerald-500/20',
      bg: 'bg-emerald-950/20',
    },
    {
      title: 'Sensor Faults Flagged',
      value: faultCount || metrics?.total_faults || 0,
      sub: 'Isolated spikes, drifts & frozen',
      icon: AlertTriangle,
      color: 'text-rose-400',
      border: 'border-rose-500/20',
      bg: 'bg-rose-950/20',
    },
    {
      title: 'Weather Events Rescued',
      value: eventCount || metrics?.total_events || 0,
      sub: 'Coherent regional phenomena',
      icon: CloudLightning,
      color: 'text-blue-400',
      border: 'border-blue-500/20',
      bg: 'bg-blue-950/20',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`p-4 rounded-xl bg-slate-900/60 backdrop-blur-md border ${card.border} transition-all duration-200 hover:border-slate-700 shadow-lg`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {card.title}
              </span>
              <div className={`p-2 rounded-lg ${card.bg} ${card.color}`}>
                <Icon className="w-5 h-5" />
              </div>
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-bold font-mono text-slate-100">{card.value}</span>
            </div>
            <p className="mt-1 text-xs text-slate-400 font-sans">{card.sub}</p>
          </div>
        );
      })}
    </div>
  );
}
