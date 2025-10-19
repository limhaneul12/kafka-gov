import { useState, useEffect } from "react";
import Button from "../ui/Button";
import { X } from "lucide-react";

interface EditTopicMetadataModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: {
    owner: string | null;
    doc: string | null;
    tags: string[];
    environment: string;
  }) => Promise<void>;
  initialData: {
    name: string;
    owner: string | null;
    doc: string | null;
    tags: string[];
    environment: string;
  };
}

export default function EditTopicMetadataModal({
  isOpen,
  onClose,
  onSubmit,
  initialData,
}: EditTopicMetadataModalProps) {
  const [owner, setOwner] = useState(initialData.owner || "");
  const [doc, setDoc] = useState(initialData.doc || "");
  const [tags, setTags] = useState(initialData.tags.join(", "));
  const [environment, setEnvironment] = useState(initialData.environment);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setOwner(initialData.owner || "");
      setDoc(initialData.doc || "");
      setTags(initialData.tags.join(", "));
      setEnvironment(initialData.environment);
    }
  }, [isOpen, initialData]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const tagArray = tags
        .split(",")
        .map((t) => t.trim())
        .filter((t) => t.length > 0);

      await onSubmit({
        owner: owner.trim() || null,
        doc: doc.trim() || null,
        tags: tagArray,
        environment,
      });
      onClose();
    } catch (error) {
      console.error("Failed to update topic metadata:", error);
      alert("Failed to update topic metadata");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-2xl m-4 rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">
            Edit Topic Metadata: {initialData.name}
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Team/Owner
            </label>
            <input
              type="text"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              placeholder="e.g., data-team, ml-team"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Documentation
            </label>
            <textarea
              value={doc}
              onChange={(e) => setDoc(e.target.value)}
              rows={3}
              placeholder="Describe the purpose and usage of this topic"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tags (comma-separated)
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g., analytics, realtime, critical"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Separate multiple tags with commas
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Environment
            </label>
            <select
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="dev">Development</option>
              <option value="stg">Staging</option>
              <option value="prod">Production</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Updating..." : "Update Metadata"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
