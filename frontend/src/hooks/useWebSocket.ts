/**
 * useWebSocket — React hook for real-time server events.
 *
 * Connects to the backend WebSocket endpoint with JWT authentication,
 * handles automatic reconnection with exponential back-off,
 * and exposes typed event dispatching via an on/off API.
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useAuthStore } from '../stores/authStore';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type WSEventType =
  | 'execution.status_changed'
  | 'execution.log'
  | 'notification'
  | 'trigger.fired'
  | 'pong';

export interface WSEvent<T = unknown> {
  type: WSEventType;
  payload: T;
}

export interface ExecutionStatusPayload {
  execution_id: string;
  status: string;
  workflow_id?: string;
}

export interface ExecutionLogPayload {
  execution_id: string;
  level: string;
  message: string;
  timestamp: string;
}

export interface NotificationPayload {
  title: string;
  message: string;
  priority?: string;
  metadata?: Record<string, unknown>;
}

export interface TriggerFiredPayload {
  trigger_id: string;
  workflow_id: string;
  execution_id: string;
}

type Listener = (payload: unknown) => void;

export type WSReadyState = 'connecting' | 'open' | 'closing' | 'closed';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BASE_RECONNECT_MS = 1_000;
const MAX_RECONNECT_MS = 30_000;
const PING_INTERVAL_MS = 25_000;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useWebSocket() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const wsRef = useRef<WebSocket | null>(null);
  const listenersRef = useRef<Map<string, Set<Listener>>>(new Map());
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const unmounted = useRef(false);

  const [readyState, setReadyState] = useState<WSReadyState>('closed');

  // ---- helpers ----------------------------------------------------------

  const clearTimers = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    if (pingTimer.current) {
      clearInterval(pingTimer.current);
      pingTimer.current = null;
    }
  }, []);

  const emit = useCallback((type: string, payload: unknown) => {
    const set = listenersRef.current.get(type);
    if (set) {
      set.forEach((fn) => {
        try {
          fn(payload);
        } catch (err) {
          console.error(`[ws] listener error for "${type}":`, err);
        }
      });
    }
  }, []);

  // ---- connect ----------------------------------------------------------

  const connect = useCallback(() => {
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken || unmounted.current) return;

    // Determine WebSocket URL
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = window.location.host;
    const url = `${proto}://${host}/ws?token=${encodeURIComponent(accessToken)}`;

    setReadyState('connecting');

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (unmounted.current) {
        ws.close();
        return;
      }
      reconnectAttempt.current = 0;
      setReadyState('open');

      // Start keepalive pings
      pingTimer.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, PING_INTERVAL_MS);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WSEvent;
        emit(msg.type, msg.payload ?? msg);
      } catch {
        // non-JSON frame — ignore
      }
    };

    ws.onclose = () => {
      setReadyState('closed');
      clearTimers();

      if (unmounted.current) return;

      // Exponential back-off reconnect
      const delay = Math.min(
        BASE_RECONNECT_MS * 2 ** reconnectAttempt.current,
        MAX_RECONNECT_MS,
      );
      reconnectAttempt.current += 1;
      reconnectTimer.current = setTimeout(() => {
        if (!unmounted.current) connect();
      }, delay);
    };

    ws.onerror = () => {
      // onclose will fire after this — reconnection happens there
    };
  }, [clearTimers, emit]);

  // ---- lifecycle --------------------------------------------------------

  useEffect(() => {
    unmounted.current = false;

    if (isAuthenticated) {
      connect();
    }

    return () => {
      unmounted.current = true;
      clearTimers();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [isAuthenticated, connect, clearTimers]);

  // ---- public API -------------------------------------------------------

  const on = useCallback((type: WSEventType, listener: Listener) => {
    if (!listenersRef.current.has(type)) {
      listenersRef.current.set(type, new Set());
    }
    listenersRef.current.get(type)!.add(listener);

    // Return unsubscribe function
    return () => {
      listenersRef.current.get(type)?.delete(listener);
    };
  }, []);

  const off = useCallback((type: WSEventType, listener: Listener) => {
    listenersRef.current.get(type)?.delete(listener);
  }, []);

  return { readyState, on, off };
}
