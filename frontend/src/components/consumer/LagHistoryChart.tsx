import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

interface LagDataPoint {
  timestamp: string;
  totalLag: number;
  p95Lag: number;
}

interface LagHistoryChartProps {
  data: LagDataPoint[];
}

export default function LagHistoryChart({ data }: LagHistoryChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        Waiting for data...
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="timestamp"
          stroke="#6b7280"
          tick={{ fontSize: 12 }}
          tickFormatter={(value: string) => {
            const date = new Date(value);
            return date.toLocaleTimeString("en-US", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            });
          }}
        />
        <YAxis
          stroke="#6b7280"
          tick={{ fontSize: 12 }}
          tickFormatter={(value: number) => value.toLocaleString()}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "white",
            border: "1px solid #e5e7eb",
            borderRadius: "8px",
            padding: "8px 12px",
          }}
          labelFormatter={(value: string) => {
            const date = new Date(value);
            return date.toLocaleTimeString("en-US", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            });
          }}
          formatter={(value: number, name: string) => [
            value.toLocaleString(),
            name === "totalLag" ? "Total Lag" : "P95 Lag",
          ]}
        />
        <Line
          type="monotone"
          dataKey="totalLag"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          name="totalLag"
        />
        <Line
          type="monotone"
          dataKey="p95Lag"
          stroke="#f59e0b"
          strokeWidth={2}
          dot={false}
          name="p95Lag"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
