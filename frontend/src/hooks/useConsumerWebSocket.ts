import { useEffect, useRef, useState, useCallback } from "react";
import { toast } from "sonner";

export interface LiveSnapshot {
  timestamp: string;
  cluster_id: string;
  group_id: string;
  state: string;
  member_count: number;
  topic_count: number;
  partition_assignor: string | null;
  lag_stats: {
    total_lag: number;
    mean_lag: number;
    p50_lag: number;
    p95_lag: number;
    max_lag: number;
    partition_count: number;
  };
  partitions: Array<{
    topic: string;
    partition: number;
    lag: number | null;
    committed_offset: number | null;
    latest_offset: number | null;
    assigned_member_id: string | null;
  }>;
  members: Array<{
    member_id: string;
    client_id: string;
    partition_count: number;
  }>;
  fairness_gini: number;
  stuck_count: number;
  is_rebalancing: boolean;
  has_lag_spike: boolean;
}

export interface LiveStreamEvent {
  type: "connected" | "snapshot" | "error" | "heartbeat";
  data: LiveSnapshot | null;
  message: string | null;
}

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

interface UseConsumerWebSocketOptions {
  clusterId: string;
  groupId: string;
  interval?: number;
  autoConnect?: boolean;
}

export function useConsumerWebSocket({
  clusterId,
  groupId,
  interval = 10,
  autoConnect = true,
}: UseConsumerWebSocketOptions) {
  const [snapshot, setSnapshot] = useState<LiveSnapshot | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [events, setEvents] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | undefined>(undefined);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // 파라미터 유효성 체크
  const isValid = clusterId && groupId;

  const getWebSocketUrl = useCallback(() => {
    // 환경 변수에서 WebSocket URL 가져오기 (있으면 사용, 없으면 자동 감지)
    const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL;
    
    if (wsBaseUrl) {
      return `${wsBaseUrl}/ws/consumers/groups/${groupId}/live?cluster_id=${clusterId}&interval=${interval}`;
    }
    
    // Fallback: 자동 감지 (개발 환경)
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host.replace(":5173", ":8000"); // Vite dev → Backend
    return `${protocol}//${host}/ws/consumers/groups/${groupId}/live?cluster_id=${clusterId}&interval=${interval}`;
  }, [clusterId, groupId, interval]);

  const connect = useCallback(() => {
    if (!isValid) {
      console.error("WebSocket: clusterId and groupId are required");
      setStatus("error");
      setEvents(["Error: Missing clusterId or groupId"]);
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setStatus("connecting");
    const ws = new WebSocket(getWebSocketUrl());
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connected:", groupId);
      setStatus("connected");
      reconnectAttempts.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data: LiveStreamEvent = JSON.parse(event.data);

        if (data.type === "connected") {
          console.log("WebSocket handshake:", data.message);
        } else if (data.type === "snapshot" && data.data) {
          setSnapshot(data.data);
          if (data.message) {
            setEvents((prev) => [...prev.slice(-4), data.message!]);
          }
        } else if (data.type === "error") {
          console.error("WebSocket error event:", data.message);
          toast.error(data.message || "Unknown error");
        }
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setStatus("error");
    };

    ws.onclose = (event) => {
      console.log("WebSocket closed:", event.code, event.reason);
      setStatus("disconnected");
      wsRef.current = null;

      // 자동 재연결 (지수 백오프)
      if (autoConnect && reconnectAttempts.current < maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectAttempts.current += 1;
        
        console.log(
          `Reconnecting in ${delay / 1000}s (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})`
        );

        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      } else if (reconnectAttempts.current >= maxReconnectAttempts) {
        toast.error("Failed to connect to real-time monitoring. Please refresh the page.");
      }
    };
  }, [getWebSocketUrl, groupId, autoConnect, isValid]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus("disconnected");
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    snapshot,
    status,
    events,
    connect,
    disconnect,
    isConnected: status === "connected",
  };
}
