import { useEffect, useRef, useState, useCallback } from 'react';
import type { PipelineEvent } from '../types';

export function useWebSocket(projectId: string | null) {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!projectId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws/projects/${projectId}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (event) => {
      try {
        const data: PipelineEvent = JSON.parse(event.data);
        setEvents((prev) => [...prev, data]);
      } catch {
        // Ignore non-JSON messages (like pong)
      }
    };

    // Keepalive
    const interval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 15000);

    return () => {
      clearInterval(interval);
      ws.close();
      wsRef.current = null;
    };
  }, [projectId]);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { events, connected, clearEvents };
}
