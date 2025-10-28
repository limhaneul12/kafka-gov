import Badge from "../ui/Badge";

interface FairnessGaugeProps {
  gini: number;
  memberCount: number;
  avgPartitions: number;
  maxPartitions: number;
  minPartitions: number;
}

export default function FairnessGauge({
  gini,
  memberCount,
  avgPartitions,
  maxPartitions,
  minPartitions,
}: FairnessGaugeProps) {
  const getColor = () => {
    if (gini < 0.2) return { color: "emerald", label: "Balanced" };
    if (gini < 0.4) return { color: "yellow", label: "Slight Skew" };
    return { color: "rose", label: "Hotspot" };
  };

  const { color, label } = getColor();
  
  // Calculate gauge angle (0-180 degrees, where 0 is left and 180 is right)
  const angle = Math.min(gini * 180, 180);

  return (
    <div className="space-y-4">
      {/* Gauge Visualization */}
      <div className="relative mx-auto w-48 h-24">
        {/* Background Arc */}
        <svg className="w-full h-full" viewBox="0 0 200 100">
          {/* Green Zone */}
          <path
            d="M 10 90 A 80 80 0 0 1 66.7 26.7"
            fill="none"
            stroke="#10b981"
            strokeWidth="12"
            opacity="0.2"
          />
          {/* Yellow Zone */}
          <path
            d="M 66.7 26.7 A 80 80 0 0 1 133.3 26.7"
            fill="none"
            stroke="#eab308"
            strokeWidth="12"
            opacity="0.2"
          />
          {/* Red Zone */}
          <path
            d="M 133.3 26.7 A 80 80 0 0 1 190 90"
            fill="none"
            stroke="#f43f5e"
            strokeWidth="12"
            opacity="0.2"
          />
          
          {/* Needle */}
          <g transform={`rotate(${angle - 90} 100 90)`}>
            <line
              x1="100"
              y1="90"
              x2="100"
              y2="20"
              stroke="#374151"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <circle cx="100" cy="90" r="6" fill="#374151" />
          </g>
        </svg>
        
        {/* Value Display */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-center">
          <p className="text-3xl font-bold text-gray-900">{gini.toFixed(3)}</p>
          <Badge color={color}>{label}</Badge>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-2 gap-4 pt-4 border-t">
        <div>
          <p className="text-xs text-gray-600">Members</p>
          <p className="mt-1 text-lg font-semibold text-gray-900">
            {memberCount}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-600">Avg Partitions</p>
          <p className="mt-1 text-lg font-semibold text-gray-900">
            {avgPartitions.toFixed(1)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-600">Min</p>
          <p className="mt-1 text-lg font-semibold text-gray-900">
            {minPartitions}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-600">Max</p>
          <p className="mt-1 text-lg font-semibold text-gray-900">
            {maxPartitions}
          </p>
        </div>
      </div>

      {/* Info */}
      <div className="bg-blue-50 rounded-lg p-3">
        <p className="text-xs text-blue-900">
          <strong>Gini Coefficient:</strong> Measures partition distribution fairness.
          Lower is better (0 = perfectly balanced, 1 = completely skewed).
        </p>
      </div>
    </div>
  );
}
