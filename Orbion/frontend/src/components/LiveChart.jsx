import React, { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  Dot
} from 'recharts';
import { Activity, Thermometer, Droplets, Gauge } from 'lucide-react';

const CustomDot = (props) => {
  const { cx, cy, payload } = props;
  if (!payload || !payload.hasAlert) {
    return null;
  }
  const isFault = payload.classification === 'sensor_fault';
  const fillColor = isFault ? '#f43f5e' : '#38bdf8'; // rose-500 or cyan-400

  return (
    <svg x={cx - 6} y={cy - 6} width={12} height={12}>
      <circle cx={6} cy={6} r={5} fill={fillColor} stroke="#ffffff" strokeWidth={1.5} />
    </svg>
  );
};

export default function LiveChart({ data = [], activeStationId = 'A01' }) {
  const [selectedMetric, setSelectedMetric] = useState('all'); // 'all', 'temp', 'pressure', 'humidity'

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload;
      return (
        <div className="bg-slate-900/95 border border-slate-700 p-3 rounded-lg shadow-xl text-xs font-mono space-y-1">
          <p className="text-slate-400 font-semibold border-b border-slate-800 pb-1 mb-1">
            Time: {label}
          </p>
          <div className="flex items-center space-x-2 text-rose-400">
            <Thermometer className="w-3.5 h-3.5" />
            <span>Temp: {p.temperature?.toFixed(1)}°C (Td: {p.dew_point?.toFixed(1)}°C)</span>
          </div>
          <div className="flex items-center space-x-2 text-sky-400">
            <Gauge className="w-3.5 h-3.5" />
            <span>Pressure: {p.pressure?.toFixed(1)} hPa</span>
          </div>
          <div className="flex items-center space-x-2 text-emerald-400">
            <Droplets className="w-3.5 h-3.5" />
            <span>Humidity: {p.humidity?.toFixed(1)}%</span>
          </div>
          {p.hasAlert && (
            <div className={`mt-2 pt-1 border-t border-slate-800 font-bold ${
              p.classification === 'sensor_fault' ? 'text-rose-400' : 'text-blue-400'
            }`}>
              ★ {p.classification === 'sensor_fault' ? 'SENSOR FAULT' : 'WEATHER EVENT'}
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="p-4 rounded-xl bg-slate-900/60 backdrop-blur-md border border-slate-800/80 shadow-lg flex flex-col h-full">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4 pb-2 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Activity className="w-5 h-5 text-cyan-400" />
          <h2 className="text-sm font-bold tracking-wide text-slate-100 uppercase">
            Live Telemetry Stream — Station {activeStationId}
          </h2>
          <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono animate-pulse">
            LIVE 10-MIN REPLAY
          </span>
        </div>

        {/* Metric Switcher */}
        <div className="flex items-center space-x-1 bg-slate-950/80 p-1 rounded-lg border border-slate-800 text-xs">
          <button
            onClick={() => setSelectedMetric('all')}
            className={`px-2.5 py-1 rounded-md transition ${selectedMetric === 'all' ? 'bg-slate-800 text-slate-100 font-medium' : 'text-slate-400 hover:text-slate-200'}`}
          >
            All
          </button>
          <button
            onClick={() => setSelectedMetric('temp')}
            className={`px-2.5 py-1 rounded-md transition ${selectedMetric === 'temp' ? 'bg-rose-500/20 text-rose-300 font-medium' : 'text-slate-400 hover:text-rose-300'}`}
          >
            Temp & Dew Point
          </button>
          <button
            onClick={() => setSelectedMetric('pressure')}
            className={`px-2.5 py-1 rounded-md transition ${selectedMetric === 'pressure' ? 'bg-sky-500/20 text-sky-300 font-medium' : 'text-slate-400 hover:text-sky-300'}`}
          >
            Pressure
          </button>
          <button
            onClick={() => setSelectedMetric('humidity')}
            className={`px-2.5 py-1 rounded-md transition ${selectedMetric === 'humidity' ? 'bg-emerald-500/20 text-emerald-300 font-medium' : 'text-slate-400 hover:text-emerald-300'}`}
          >
            Humidity
          </button>
        </div>
      </div>

      <div className="w-full flex-1 min-h-[320px]">
        {data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500 font-mono text-xs">
            Connecting and accumulating telemetry buffer...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="timestamp" stroke="#64748b" tick={{ fontSize: 11 }} />
              <YAxis stroke="#64748b" domain={['auto', 'auto']} tick={{ fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '12px' }} />

              {(selectedMetric === 'all' || selectedMetric === 'temp') && (
                <>
                  <Line
                    type="monotone"
                    dataKey="temperature"
                    name="Air Temp (°C)"
                    stroke="#f43f5e"
                    strokeWidth={2}
                    dot={<CustomDot />}
                    activeDot={{ r: 5 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="dew_point"
                    name="Dew Point Td (°C)"
                    stroke="#fb923c"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    dot={false}
                  />
                </>
              )}

              {(selectedMetric === 'all' || selectedMetric === 'pressure') && (
                <Line
                  type="monotone"
                  dataKey="pressure"
                  name="Pressure (hPa)"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  dot={<CustomDot />}
                  activeDot={{ r: 5 }}
                />
              )}

              {(selectedMetric === 'all' || selectedMetric === 'humidity') && (
                <Line
                  type="monotone"
                  dataKey="humidity"
                  name="Relative Humidity (%)"
                  stroke="#34d399"
                  strokeWidth={2}
                  dot={<CustomDot />}
                  activeDot={{ r: 5 }}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
      <div className="mt-2 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center space-x-3">
          <span className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block border border-white"></span>
            <span>Sensor Fault Point</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 inline-block border border-white"></span>
            <span>Genuine Weather Event Point</span>
          </span>
        </div>
        <span className="font-mono text-slate-500">Magnus-Tetens Dew Point Enabled</span>
      </div>
    </div>
  );
}
