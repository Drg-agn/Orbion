import React, { useState, useEffect } from 'react';
import { useLiveStream } from '../hooks/useLiveStream';
import { fetchStations, fetchMetrics, fetchStationDetail, fetchAlerts } from '../api/client';

import FileUpload from '../components/FileUpload';
import KpiCards from '../components/KpiCards';
import LiveChart from '../components/LiveChart';
import AlertFeed from '../components/AlertFeed';
import StationHealth from '../components/StationHealth';
import StationMap from '../components/StationMap';
import RootCauseChart from '../components/RootCauseChart';

import { Play, Pause, RotateCcw, Zap } from 'lucide-react';

export default function Dashboard() {
  const [sessionId, setSessionId] = useState(null); // null = default demo stream
  const [sessionMeta, setSessionMeta] = useState(null);

  const {
    isConnected,
    isPaused,
    latestPacket,
    alerts,
    historyByStation,
    streamProgress,
    sendCommand
  } = useLiveStream(sessionId);

  const [stations, setStations] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [selectedStationId, setSelectedStationId] = useState('A01');
  const [speed, setSpeed] = useState(0.6);

  // Pre-hydrated state for instant display before WebSocket packets accumulate
  const [initialAlerts, setInitialAlerts] = useState([]);
  const [initialHistory, setInitialHistory] = useState({});

  useEffect(() => {
    async function loadInitData() {
      try {
        const [stData, metData, alData, stationDetail] = await Promise.all([
          fetchStations(),
          fetchMetrics(),
          fetchAlerts(30).catch(() => []),
          fetchStationDetail('A01').catch(() => null)
        ]);
        setStations(stData);
        setMetrics(metData);
        if (alData?.length) setInitialAlerts(alData);
        if (stationDetail?.readings?.length) {
          const formatted = stationDetail.readings.map((r) => ({
            timestamp: r.timestamp.split(' ')[1] || r.timestamp,
            temperature: r.temperature,
            pressure: r.pressure,
            humidity: r.humidity,
            dew_point: r.dew_point,
            hasAlert: false
          }));
          setInitialHistory((prev) => ({ ...prev, A01: formatted }));
        }
      } catch (err) {
        console.warn('Initial data fetch notice:', err);
      }
    }
    loadInitData();
  }, []);

  // Fetch initial history if user selects a different station before live ticks accumulate
  useEffect(() => {
    if (!sessionId && selectedStationId && !historyByStation[selectedStationId]?.length && !initialHistory[selectedStationId]?.length) {
      fetchStationDetail(selectedStationId)
        .then((detail) => {
          if (detail?.readings?.length) {
            const formatted = detail.readings.map((r) => ({
              timestamp: r.timestamp.split(' ')[1] || r.timestamp,
              temperature: r.temperature,
              pressure: r.pressure,
              humidity: r.humidity,
              dew_point: r.dew_point,
              hasAlert: false
            }));
            setInitialHistory((prev) => ({ ...prev, [selectedStationId]: formatted }));
          }
        })
        .catch(() => {});
    }
  }, [selectedStationId, sessionId, historyByStation, initialHistory]);

  const handleSessionReady = (newSessionId, meta) => {
    setSessionId(newSessionId);
    setSessionMeta(meta);
    if (meta?.stations?.length) {
      setSelectedStationId(meta.stations[0]);
    }
  };

  const handleUseDemoData = () => {
    setSessionId(null);
    setSessionMeta(null);
    setSelectedStationId('A01');
  };

  // Determine active stations to display in Fleet Health and Map
  const activeStations = sessionId
    ? (sessionMeta?.stations || []).map((id) => ({ id, name: `Station ${id}` }))
    : stations;

  // Auto-switch selectedStationId if current selection is absent in the active dataset
  useEffect(() => {
    if (activeStations.length > 0 && !activeStations.some((s) => s.id === selectedStationId)) {
      setSelectedStationId(activeStations[0].id);
    }
  }, [activeStations, selectedStationId]);

  const handleTogglePause = () => {
    if (isPaused) {
      sendCommand('resume');
    } else {
      sendCommand('pause');
    }
  };

  const handleReset = () => {
    sendCommand('reset');
  };

  const handleSpeedChange = (newSpeed) => {
    setSpeed(newSpeed);
    sendCommand('speed', newSpeed);
  };

  const liveHistory = historyByStation[selectedStationId] || [];
  const currentStationHistory = liveHistory.length > 0 ? liveHistory : (initialHistory[selectedStationId] || []);
  const displayAlerts = alerts.length > 0 ? alerts : initialAlerts;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 bg-slate-950/85 backdrop-blur-md border-b border-slate-800 px-4 lg:px-6 py-3">
        <div className="max-w-[1600px] mx-auto flex flex-wrap items-center justify-between gap-3">
          {/* Title & Brand */}
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-base font-bold tracking-tight text-white">
                  SkyGuard AI <span className="text-cyan-400 font-mono text-sm">(Orbion)</span>
                </h1>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                  sessionId
                    ? 'bg-purple-500/10 text-purple-300 border-purple-500/30'
                    : 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20'
                }`}>
                  {sessionId ? 'USER DATASET STREAM' : 'DEMO REPLAY'}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                {sessionId
                  ? `Live analysis of ${sessionMeta?.filename || 'uploaded file'}`
                  : 'Real-Time AWS Sensor Fault vs. Genuine Weather Event Classifier'}
              </p>
            </div>
          </div>

          {/* Replay Stream Controls */}
          <div className="flex items-center space-x-2 bg-slate-900/90 border border-slate-800 p-1.5 rounded-xl">
            {/* Connection Status */}
            <div className="flex items-center space-x-1.5 px-2.5 py-1 text-xs font-mono border-r border-slate-800">
              {isConnected ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-emerald-400">STREAM ACTIVE</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  <span className="text-rose-400">CONNECTING...</span>
                </>
              )}
            </div>

            {/* Play/Pause */}
            <button
              onClick={handleTogglePause}
              className={`flex items-center space-x-1 px-3 py-1 text-xs font-medium rounded-lg transition ${
                isPaused
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
              }`}
            >
              {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
              <span>{isPaused ? 'Resume' : 'Pause'}</span>
            </button>

            {/* Reset */}
            <button
              onClick={handleReset}
              title="Reset Replay Stream"
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>

            {/* Playback speed selector */}
            <div className="flex items-center space-x-1 pl-1 text-[11px] font-mono">
              <button
                onClick={() => handleSpeedChange(1.0)}
                className={`px-1.5 py-0.5 rounded ${speed === 1.0 ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400 hover:text-slate-200'}`}
              >
                1x
              </button>
              <button
                onClick={() => handleSpeedChange(0.5)}
                className={`px-1.5 py-0.5 rounded ${speed === 0.5 ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400 hover:text-slate-200'}`}
              >
                2x
              </button>
              <button
                onClick={() => handleSpeedChange(0.2)}
                className={`px-1.5 py-0.5 rounded ${speed === 0.2 ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400 hover:text-slate-200'}`}
              >
                5x
              </button>
            </div>
          </div>
        </div>

        {/* Stream Progress Bar */}
        <div className="max-w-[1600px] mx-auto mt-2 w-full bg-slate-900 h-1 rounded-full overflow-hidden">
          <div
            className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full transition-all duration-300"
            style={{ width: `${streamProgress.percent || 0}%` }}
          />
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto p-4 lg:p-6 space-y-6">
        {/* Upload Section */}
        <FileUpload
          onSessionReady={handleSessionReady}
          onUseDemoData={handleUseDemoData}
        />

        {/* KPI Cards */}
        <KpiCards metrics={metrics} liveAlerts={displayAlerts} />

        {/* Center Grid: Live Chart & Alert Feed */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          <div className="lg:col-span-7 xl:col-span-8 min-h-[420px]">
            <LiveChart
              data={currentStationHistory}
              activeStationId={selectedStationId}
            />
          </div>
          <div className="lg:col-span-5 xl:col-span-4 min-h-[420px]">
            <AlertFeed alerts={displayAlerts} />
          </div>
        </div>

        {/* Bottom Grid: Station Fleet Health, Spatial Map & Root Cause */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-6 items-stretch">
          <div className="lg:col-span-5">
            <StationHealth
              stations={activeStations}
              selectedStationId={selectedStationId}
              onSelectStation={setSelectedStationId}
              latestPacket={latestPacket}
            />
          </div>
          <div className="lg:col-span-4">
            <StationMap
              stations={activeStations}
              selectedStationId={selectedStationId}
              onSelectStation={setSelectedStationId}
              latestPacket={latestPacket}
            />
          </div>
          <div className="lg:col-span-3">
            <RootCauseChart
              stats={metrics}
              liveAlerts={displayAlerts}
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 px-6 py-3 text-center text-xs font-mono text-slate-500">
        SkyGuard AI — Meteorological Autonomous Sensor Quality Assurance System • Built with FastAPI & React Vite
      </footer>
    </div>
  );
}
