import { useTranslation } from "react-i18next";
import type { PolicyVersion } from "../../../Policies.types";

interface PolicyContentViewProps {
  policy: PolicyVersion;
}

export function PolicyContentView({ policy }: PolicyContentViewProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium text-gray-700">Policy ID</label>
          <p className="text-sm text-gray-900 font-mono mt-1">{policy.policy_id}</p>
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700">Type</label>
          <p className="text-sm text-gray-900 mt-1 capitalize">{policy.policy_type}</p>
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700">Environment</label>
          <p className="text-sm text-gray-900 mt-1 uppercase">{policy.target_environment}</p>
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700">Created By</label>
          <p className="text-sm text-gray-900 mt-1">{policy.created_by}</p>
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700">Created At</label>
          <p className="text-sm text-gray-900 mt-1">
            {new Date(policy.created_at).toLocaleString()}
          </p>
        </div>
        {policy.activated_at && (
          <div>
            <label className="text-sm font-medium text-gray-700">Activated At</label>
            <p className="text-sm text-gray-900 mt-1">
              {new Date(policy.activated_at).toLocaleString()}
            </p>
          </div>
        )}
      </div>

      {/* Policy Content (JSON) */}
      <div>
        <label className="text-sm font-medium text-gray-700 mb-2 block">
          Policy Content
        </label>
        <div className="bg-gray-50 rounded-lg p-4 border overflow-x-auto">
          <pre className="text-xs font-mono text-gray-800">
            {JSON.stringify(policy.content, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
