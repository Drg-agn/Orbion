import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * WebSocket Hook for SkyGuard AI Telemetry Stream.
 * Supports switching between default demo stream and user-uploaded sessions.
 */
export function useLiveStream(sessionId = null) {
  const [isConnected, setIsConnected] = useState(false);
  const [latestPacket, setLatestPacket] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [historyByStation, setHistoryByStation] = useState({});
  const [streamProgress, setStreamProgress] = useState({ current: 0, total: 100, percent: 0 });
  const [isPaused, setIsPaused] = useState(false);

  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const buildWsUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const defaultWsUrl = `${protocol}//${window.location.host}/stream`;
    const envWsUrl = import.meta.env.VITE_WS_URL;
    const base = envWsUrl || (window.location.port === '5173' ? 'ws://localhost:8000/stream' : defaultWsUrl);
    return sessionId ? `${base}?session_id=${encodeURIComponent(sessionId)}` : base;
  }, [sessionId]);

  const connect = useCallback(() => {
    const wsUrl = buildWsUrl();

    try {
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        console.log(`[WebSocket Hook] Connected to stream: ${wsUrl}`);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === 'telemetry') {
            const result = msg.data;
            setLatestPacket(result);

            if (msg.progress) {
              setStreamProgress(msg.progress);
            }

            const sid = result.station_id;
            const newPoint = {
              timestamp: result.timestamp.split(' ')[1] || result.timestamp,
              temperature: result.reading.temperature,
              pressure: result.reading.pressure,
              humidity: result.reading.humidity,
              dew_point: result.reading.dew_point,
              hasAlert: !!result.alert,
              classification: result.alert?.classification,
              severity: result.alert?.severity
            };

            setHistoryByStation((prev) => {
              const currentList = prev[sid] || [];
              const updated = [...currentList, newPoint];
              if (updated.length > 35) updated.shift();
              return { ...prev, [sid]: updated };
            });

            if (result.alert) {
              setAlerts((prev) => [result.alert, ...prev.slice(0, 49)]);
            }
          } else if (msg.type === 'control') {
            if (msg.status === 'paused') setIsPaused(true);
            if (msg.status === 'resumed') setIsPaused(false);
          } else if (msg.type === 'error') {
            console.warn('[WebSocket Hook] Server notice:', msg.message);
          }
        } catch (err) {
          console.error('[WebSocket Hook] Error parsing message:', err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 2500);
      };

      ws.onerror = (err) => {
        console.warn('[WebSocket Hook] Socket encountered an error:', err);
        ws.close();
      };
    } catch (e) {
      console.error('[WebSocket Hook] Connection failed:', e);
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    }
  }, [buildWsUrl]);

  // Reconnect fresh whenever target session changes
  useEffect(() => {
    setLatestPacket(null);
    setAlerts([]);
    setHistoryByStation({});
    setStreamProgress({ current: 0, total: 100, percent: 0 });
    setIsPaused(false);

    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    if (socketRef.current) socketRef.current.close();

    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [sessionId, connect]);

  const sendCommand = useCallback((action, value = null) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ action, value }));
      if (action === 'pause') setIsPaused(true);
      if (action === 'resume') setIsPaused(false);
    }
  }, []);

  return {
    isConnected,
    isPaused,
    latestPacket,
    alerts,
    historyByStation,
    streamProgress,
    sendCommand
  };
}
