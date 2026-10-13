import React, { useState, useMemo } from 'react';
import { Radio, Search, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, X, Activity } from 'lucide-react';

export default function StationHealth({
  stations = [],
  allStations = [],
  selectedStationId,
  onSelectStation,
  latestPacket
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeFilter, setActiveFilter] = useState('all'); // 'all' | 'streaming' | 'selected'
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 12;

  // Build a lookup map of active streaming stations
  const activeStreamMap = useMemo(() => {
    const map = new Map();
    stations.forEach((st) => {
      const sid = typeof st === 'string' ? st : st.id;
      map.set(sid, st);
    });
    return map;
  }, [stations]);

  // Unified list of all station objects, preserving natural file order
  const fullList = useMemo(() => {
    if (allStations && allStations.length > 0) {
      return allStations.map((item) => {
        const sid = typeof item === 'string' ? item : item.id;
        const activeInfo = activeStreamMap.get(sid);
        return {
          id: sid,
          name: activeInfo?.name || `Station ${sid}`,
          isStreaming: activeStreamMap.has(sid),
          latitude: activeInfo?.latitude,
          longitude: activeInfo?.longitude,
          elevation: activeInfo?.elevation,
          health_score: activeInfo?.health_score ?? 100
        };
      });
    }

    return stations.map((st) => {
      const sid = typeof st === 'string' ? st : st.id;
      return {
        id: sid,
        name: st?.name || `Station ${sid}`,
        isStreaming: true,
        latitude: st?.latitude,
        longitude: st?.longitude,
        elevation: st?.elevation,
        health_score: st?.health_score ?? 100
      };
    });
  }, [allStations, stations, activeStreamMap]);

  // Filter based on search term and active filter tab
  const filteredStations = useMemo(() => {
    let list = fullList;

    if (activeFilter === 'streaming') {
      list = list.filter((st) => st.isStreaming);
    } else if (activeFilter === 'selected') {
      list = list.filter((st) => st.id === selectedStationId);
    }

    if (searchTerm.trim()) {
      const query = searchTerm.trim().toLowerCase();
      list = list.filter((st) =>
        st.id.toLowerCase().includes(query) || st.name.toLowerCase().includes(query)
      );
    }

    return list;
  }, [fullList, activeFilter, searchTerm, selectedStationId]);

  // Pagination calculations
  const totalPages = Math.max(1, Math.ceil(filteredStations.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const pagedStations = useMemo(() => {
    const start = (safePage - 1) * pageSize;
    return filteredStations.slice(start, start + pageSize);
  }, [filteredStations, safePage, pageSize]);

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1);
  };

  const clearSearch = () => {
    setSearchTerm('');
    setCurrentPage(1);
  };

  const getHealthBadge = (score, isStreaming) => {
    if (!isStreaming) {
      return {
        bg: 'bg-blue-500/10 text-blue-300 border-blue-500/30',
        bar: 'bg-blue-500',
        label: 'INDEXED'
      };
    }
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

  const streamingCount = fullList.filter((s) => s.isStreaming).length;

  return (
    <div className="p-4 rounded-xl bg-slate-900/60 backdrop-blur-md border border-slate-800/80 shadow-lg flex flex-col h-full">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between pb-3 mb-3 border-b border-slate-800 gap-2">
        <div className="flex items-center space-x-2">
          <Radio className="w-5 h-5 text-cyan-400" />
          <h2 className="text-sm font-bold tracking-wide text-slate-100 uppercase">
            Station Fleet Health Status
          </h2>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-300">
            {fullList.length.toLocaleString()} Stations
          </span>
        </div>
        <span className="text-xs text-slate-400 font-mono">
          Click station to inspect telemetry
        </span>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchTerm}
            onChange={handleSearchChange}
            placeholder={`Search ${fullList.length.toLocaleString()} stations (e.g. USC)...`}
            className="w-full pl-8 pr-7 py-1 text-xs bg-slate-950/70 border border-slate-700/80 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition"
          />
          {searchTerm && (
            <button
              onClick={clearSearch}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center space-x-1 text-[11px] font-mono">
          <button
            onClick={() => { setActiveFilter('all'); setCurrentPage(1); }}
            className={`px-2 py-1 rounded transition ${
              activeFilter === 'all'
                ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            All ({fullList.length.toLocaleString()})
          </button>
          <button
            onClick={() => { setActiveFilter('streaming'); setCurrentPage(1); }}
            className={`px-2 py-1 rounded transition flex items-center space-x-1 ${
              activeFilter === 'streaming'
                ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Live Stream ({streamingCount})</span>
          </button>
          {selectedStationId && (
            <button
              onClick={() => { setActiveFilter('selected'); setCurrentPage(1); }}
              className={`px-2 py-1 rounded transition ${
                activeFilter === 'selected'
                  ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              Selected ({selectedStationId})
            </button>
          )}
        </div>
      </div>

      {/* Station Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 flex-1">
        {pagedStations.length === 0 ? (
          <div className="col-span-full py-8 text-center text-xs text-slate-500 font-mono">
            No weather stations match "{searchTerm}". Try clearing search.
          </div>
        ) : (
          pagedStations.map((st) => {
            const sid = st.id;
            const isSelected = sid === selectedStationId;
            const isCurrentlyTicking = latestPacket?.station_id === sid;
            const health = isCurrentlyTicking
              ? latestPacket.health_score
              : (st.health_score ?? 100);
            const badge = getHealthBadge(health, st.isStreaming);

            const displayName = st.name || `Station ${sid}`;
            const coordText = (st.latitude != null && st.longitude != null)
              ? `${st.latitude.toFixed(2)}°N, ${st.longitude.toFixed(2)}°E`
              : st.isStreaming ? 'Active Telemetry Channel' : 'NOAA GHCN AWS';
            const elevText = st.elevation != null ? `Elev: ${st.elevation}m` : 'Surface AWS';

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
                    <span className="text-xs text-slate-400 font-sans truncate max-w-[110px]" title={displayName}>
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
          })
        )}
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="mt-3 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-slate-400">
          <div>
            Showing <span className="text-slate-200 font-semibold">{((safePage - 1) * pageSize) + 1}</span>-
            <span className="text-slate-200 font-semibold">{Math.min(safePage * pageSize, filteredStations.length)}</span> of{' '}
            <span className="text-slate-200 font-semibold">{filteredStations.length.toLocaleString()}</span> stations
          </div>

          <div className="flex items-center space-x-1">
            <button
              onClick={() => setCurrentPage(1)}
              disabled={safePage === 1}
              className="p-1 rounded hover:bg-slate-800 text-slate-300 disabled:opacity-30 disabled:hover:bg-transparent"
              title="First Page"
            >
              <ChevronsLeft className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={safePage === 1}
              className="p-1 rounded hover:bg-slate-800 text-slate-300 disabled:opacity-30 disabled:hover:bg-transparent"
              title="Previous Page"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>

            <span className="px-2 py-0.5 rounded bg-slate-800/60 text-slate-200 text-xs">
              {safePage} / {totalPages.toLocaleString()}
            </span>

            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage === totalPages}
              className="p-1 rounded hover:bg-slate-800 text-slate-300 disabled:opacity-30 disabled:hover:bg-transparent"
              title="Next Page"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setCurrentPage(totalPages)}
              disabled={safePage === totalPages}
              className="p-1 rounded hover:bg-slate-800 text-slate-300 disabled:opacity-30 disabled:hover:bg-transparent"
              title="Last Page"
            >
              <ChevronsRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
