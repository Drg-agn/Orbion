/**
 * Native REST API Client for SkyGuard AI (Orbion).
 * Zero external library dependencies (uses browser fetch API).
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

export async function fetchStations() {
  const res = await fetch(`${API_BASE}/api/stations`);
  if (!res.ok) throw new Error(`Failed to fetch stations: ${res.statusText}`);
  return res.json();
}

export async function fetchStationDetail(stationId) {
  const res = await fetch(`${API_BASE}/api/stations/${stationId}`);
  if (!res.ok) throw new Error(`Failed to fetch station ${stationId}: ${res.statusText}`);
  return res.json();
}

export async function fetchAlerts(limit = 50, stationId = null, classification = null) {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (stationId) params.append('station_id', stationId);
  if (classification) params.append('classification', classification);

  const res = await fetch(`${API_BASE}/api/alerts?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch alerts: ${res.statusText}`);
  return res.json();
}

export async function fetchAlertStats() {
  const res = await fetch(`${API_BASE}/api/alerts/stats`);
  if (!res.ok) throw new Error(`Failed to fetch alert stats: ${res.statusText}`);
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/api/metrics`);
  if (!res.ok) throw new Error(`Failed to fetch metrics: ${res.statusText}`);
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error(`Failed to check health: ${res.statusText}`);
  return res.json();
}

export async function uploadWeatherFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const errBody = await res.json();
      detail = errBody.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }

  return res.json();
}
