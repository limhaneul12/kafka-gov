import { useEffect } from "react";
import { Activity, Wifi, WifiOff, AlertCircle } from "lucide-react";
import Badge from "../ui/Badge";
import { useConsumerWebSocket, type LiveSnapshot } from "../../hooks/useConsumerWebSocket";

interface LiveMonitoringProps {
  clusterId: string;
  groupId: string;
  onSnapshotUpdate?: (snapshot: LiveSnapshot) => void;
}

export default function LiveMonitoring({
  clusterId,
  groupId,
  onSnapshotUpdate,
}: LiveMonitoringProps) {
  const { snapshot, status, events, isConnected } = useConsumerWebSocket({
    clusterId,
    groupId,
    interval: 10,
    autoConnect: true,
  });

  // 상위 컴포넌트에 스냅샷 전달 (useEffect로 side effect 처리)
  useEffect(() => {
    if (snapshot && onSnapshotUpdate) {
      onSnapshotUpdate(snapshot);
    }
  }, [snapshot, onSnapshotUpdate]);

  const getStatusColor = () => {
    switch (status) {
      case "connected":
        return "emerald";
      case "connecting":
        return "yellow";
      case "error":
        return "rose";
      default:
        return "gray";
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case "connected":
        return <Wifi className="h-4 w-4" />;
      case "connecting":
        return <Activity className="h-4 w-4 animate-pulse" />;
      case "error":
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <WifiOff className="h-4 w-4" />;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case "connected":
        return "Live";
      case "connecting":
        return "Connecting...";
      case "error":
        return "Connection Error";
      default:
        return "Disconnected";
    }
  };

  return (
    <div className="flex items-center gap-4">
      {/* Connection Status */}
      <div className="flex items-center gap-2">
        <Badge color={getStatusColor()}>
          <div className="flex items-center gap-1.5">
            {getStatusIcon()}
            <span>{getStatusText()}</span>
          </div>
        </Badge>
      </div>

      {/* Last Update */}
      {snapshot && isConnected && (
        <div className="text-xs text-gray-500">
          Last update:{" "}
          {new Date(snapshot.timestamp).toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })}
        </div>
      )}

      {/* Recent Events */}
      {events.length > 0 && (
        <div className="flex items-center gap-2 max-w-md overflow-hidden">
          <div className="text-xs text-gray-600 font-medium">Events:</div>
          <div className="text-xs text-gray-500 truncate">{events[events.length - 1]}</div>
        </div>
      )}
    </div>
  );
}
