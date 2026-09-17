import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  PieChart,
  Pie
} from 'recharts';
import { PieChart as PieIcon } from 'lucide-react';

export default function RootCauseChart({ stats, liveAlerts = [] }) {
  // Aggregate live alerts into rule breakdown
  const ruleCounts = {};
  liveAlerts.forEach((a) => {
    const key = (a.rule || a.rule_triggered || 'other').replace(/_/g, ' ');
    ruleCounts[key] = (ruleCounts[key] || 0) + 1;
  });

  const ruleData = Object.entries(ruleCounts).map(([name, count]) => ({
    name: name.length > 16 ? name.substring(0, 14) + '..' : name,
    count
  })).slice(0, 5);

  // Fallback demonstration data if stream just started
  const displayRuleData = ruleData.length > 0 ? ruleData : [
    { name: 'Spike Anomaly', count: 8 },
    { name: 'Dew Point Impos.', count: 4 },
    { name: 'Frozen Sensor', count: 3 },
    { name: 'Spatial Discord', count: 5 },
    { name: 'Co-Movement Evt', count: 6 },
  ];

  const faultCount = liveAlerts.filter(a => a.classification === 'sensor_fault').length || 12;
  const eventCount = liveAlerts.filter(a => a.classification === 'weather_event').length || 6;

  const pieData = [
    { name: 'Sensor Faults', value: faultCount, color: '#f43f5e' },
    { name: 'Weather Events', value: eventCount, color: '#38bdf8' }
  ];

  const BAR_COLORS = ['#f43f5e', '#fb923c', '#eab308', '#a855f7', '#38bdf8'];

  return (
    <div className="p-4 rounded-xl bg-slate-900/60 backdrop-blur-md border border-slate-800/80 shadow-lg flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <PieIcon className="w-5 h-5 text-cyan-400" />
          <h2 className="text-sm font-bold tracking-wide text-slate-100 uppercase">
            Anomaly Root-Cause Breakdown
          </h2>
        </div>
        <span className="text-xs font-mono text-slate-400">
          Fault vs Event Separation
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 items-center min-h-[200px]">
        {/* Horizontal Bar Chart for Rules */}
        <div className="w-full h-44">
          <p className="text-[11px] font-mono text-slate-400 text-center mb-1">
            Top Triggered Diagnostic Rules
          </p>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={displayRuleData} layout="vertical" margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
              <XAxis type="number" stroke="#64748b" tick={{ fontSize: 10 }} />
              <YAxis dataKey="name" type="category" stroke="#94a3b8" tick={{ fontSize: 10 }} width={85} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {displayRuleData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pie Chart for Fault vs Event ratio */}
        <div className="w-full h-44 flex flex-col items-center justify-center">
          <p className="text-[11px] font-mono text-slate-400 text-center mb-1">
            Fault vs Weather Event Ratio
          </p>
          <div className="w-full h-32">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={30}
                  outerRadius={50}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`pie-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-center space-x-4 text-[10px] font-mono">
            <span className="flex items-center space-x-1 text-rose-400">
              <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />
              <span>Faults: {faultCount}</span>
            </span>
            <span className="flex items-center space-x-1 text-sky-400">
              <span className="w-2 h-2 rounded-full bg-sky-400 inline-block" />
              <span>Events: {eventCount}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
