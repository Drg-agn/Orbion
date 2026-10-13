import React, { useState, useCallback, useRef } from 'react';
import { UploadCloud, FileCheck2, XCircle, Loader2, RefreshCcw, Sparkles } from 'lucide-react';
import { uploadWeatherFile } from '../api/client';

export default function FileUpload({ onSessionReady, onUseDemoData, onSelectStation, selectedStationId }) {
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState('idle'); // idle | uploading | success | error
  const [errorMsg, setErrorMsg] = useState('');
  const [meta, setMeta] = useState(null);
  const inputRef = useRef(null);

  const handleFile = useCallback(async (file) => {
    if (!file) return;
    setStatus('uploading');
    setErrorMsg('');
    try {
      const result = await uploadWeatherFile(file);
      setMeta(result);
      setStatus('success');
      onSessionReady?.(result.session_id, result);
    } catch (err) {
      setStatus('error');
      setErrorMsg(err.message || 'Upload failed.');
    }
  }, [onSessionReady]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFile(e.dataTransfer.files?.[0]);
  }, [handleFile]);

  const onBrowse = (e) => {
    handleFile(e.target.files?.[0]);
    e.target.value = '';
  };

  const reset = () => {
    setStatus('idle');
    setMeta(null);
    setErrorMsg('');
    onUseDemoData?.();
  };

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-4 shadow-lg backdrop-blur-md">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Analyze Your Own Weather Dataset
          </h3>
        </div>
        {status === 'success' && (
          <button
            onClick={reset}
            className="flex items-center space-x-1.5 text-xs font-mono text-cyan-400 hover:text-cyan-300 bg-cyan-950/40 border border-cyan-500/30 px-2.5 py-1 rounded-lg transition"
          >
            <RefreshCcw className="w-3.5 h-3.5" />
            <span>Switch to Demo Replay</span>
          </button>
        )}
      </div>

      {status !== 'success' && (
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`cursor-pointer border-2 border-dashed rounded-xl px-4 py-6 flex flex-col items-center justify-center text-center transition-all ${
            isDragging
              ? 'border-cyan-400 bg-cyan-500/10'
              : 'border-slate-700 hover:border-slate-500 hover:bg-slate-800/30'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.txt"
            className="hidden"
            onChange={onBrowse}
          />
          {status === 'uploading' ? (
            <>
              <Loader2 className="w-7 h-7 text-cyan-400 animate-spin mb-2" />
              <p className="text-xs font-medium text-slate-200">
                Streaming & normalizing weather data (up to 500MB)...
              </p>
              <p className="text-[11px] text-slate-400 mt-1">
                Auto-detecting NOAA GHCN, Jena Climate, or standard AWS formats
              </p>
            </>
          ) : (
            <>
              <UploadCloud className="w-7 h-7 text-cyan-400/80 mb-2" />
              <p className="text-xs font-semibold text-slate-200">
                Drop your weather CSV file here or <span className="text-cyan-400 underline">browse</span>
              </p>
              <p className="text-[11px] text-slate-400 mt-1 max-w-xl">
                Supports up to 500MB. Auto-detects NOAA GHCN (<code className="font-mono text-cyan-300">station_code, weather_d, element_type</code>), Jena Climate, or standard columns (<code className="font-mono text-cyan-300">timestamp, station_id, temp, humidity, pressure</code>).
              </p>
            </>
          )}
        </div>
      )}

      {status === 'error' && (
        <div className="mt-3 flex items-start space-x-2 text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg p-3">
          <XCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Upload failed: </span>
            <span>{errorMsg}</span>
          </div>
        </div>
      )}

      {status === 'success' && meta && (
        <div className="flex items-start space-x-3 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3.5">
          <FileCheck2 className="w-5 h-5 flex-shrink-0 mt-0.5 text-emerald-400" />
          <div className="space-y-1">
            <p className="font-semibold text-emerald-300 text-sm">
              {meta.filename} — Successfully analyzed and streaming live!
            </p>
            <p className="text-slate-300">
              Detected <span className="font-mono font-semibold text-emerald-200">{(meta.total_stations_count || meta.stations.length).toLocaleString()}</span> total stations in dataset.
              Streaming live primary channels ({meta.stations.length} stations, click to inspect):
            </p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {meta.stations.map((stId) => (
                <button
                  key={stId}
                  onClick={() => onSelectStation?.(stId)}
                  className={`px-2 py-0.5 rounded font-mono text-[11px] transition-all cursor-pointer ${
                    selectedStationId === stId
                      ? 'bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/30'
                      : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
                  }`}
                  title={`View Live Chart for ${stId}`}
                >
                  {stId}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
