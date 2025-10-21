import { useTranslation } from "react-i18next";

interface MetadataSectionProps {
  owner: string;
  doc: string;
  tags: string;
  onOwnerChange: (value: string) => void;
  onDocChange: (value: string) => void;
  onTagsChange: (value: string) => void;
}

export function MetadataSection({
  owner,
  doc,
  tags,
  onOwnerChange,
  onDocChange,
  onTagsChange,
}: MetadataSectionProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-900">
        Metadata
      </h3>

      {/* Owner */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("topic.owner")} *
        </label>
        <input
          type="text"
          value={owner}
          onChange={(e) => onOwnerChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="team-data"
          required
        />
      </div>

      {/* Documentation */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("topic.doc")} (URL) *
        </label>
        <input
          type="url"
          value={doc}
          onChange={(e) => onDocChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="https://wiki.company.com/topics/orders"
          required
        />
        <p className="text-xs text-gray-500 mt-1">
          Link to Confluence/Wiki documentation
        </p>
      </div>

      {/* Tags */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("topic.tags")}
        </label>
        <input
          type="text"
          value={tags}
          onChange={(e) => onTagsChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="orders, critical, pii"
        />
        <p className="text-xs text-gray-500 mt-1">
          Comma-separated tags
        </p>
      </div>
    </div>
  );
}
