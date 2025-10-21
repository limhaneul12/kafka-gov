import { useTranslation } from "react-i18next";
import { Search, X } from "lucide-react";
import MultiSelect from "../../components/ui/MultiSelect";

interface TopicFiltersProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  envFilter: string[];
  onEnvFilterChange: (values: string[]) => void;
  ownerFilter: string[];
  onOwnerFilterChange: (values: string[]) => void;
  tagFilter: string[];
  onTagFilterChange: (values: string[]) => void;
  allOwners: string[];
  allTags: string[];
  onReset: () => void;
}

export function TopicFilters({
  searchQuery,
  onSearchChange,
  envFilter,
  onEnvFilterChange,
  ownerFilter,
  onOwnerFilterChange,
  tagFilter,
  onTagFilterChange,
  allOwners,
  allTags,
  onReset,
}: TopicFiltersProps) {
  const { t } = useTranslation();

  const hasFilters =
    searchQuery || envFilter.length > 0 || ownerFilter.length > 0 || tagFilter.length > 0;

  return (
    <div className="bg-white rounded-lg border p-4 space-y-4">
      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={t("common.search")}
          className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Filter Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Environment Filter */}
        <MultiSelect
          label={t("topic.environment")}
          options={["dev", "stg", "prod"]}
          selectedValues={envFilter}
          onChange={onEnvFilterChange}
          placeholder={t("topic.selectEnvironment")}
        />

        {/* Owner Filter */}
        <MultiSelect
          label={t("topic.owner")}
          options={allOwners}
          selectedValues={ownerFilter}
          onChange={onOwnerFilterChange}
          placeholder={t("topic.filterByOwner")}
        />

        {/* Tags Filter */}
        <MultiSelect
          label={t("topic.tags")}
          options={allTags}
          selectedValues={tagFilter}
          onChange={onTagFilterChange}
          placeholder={t("topic.filterByTags")}
        />
      </div>

      {/* Reset Button */}
      {hasFilters && (
        <div className="flex justify-end">
          <button
            onClick={onReset}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="h-4 w-4" />
            {t("common.reset")}
          </button>
        </div>
      )}
    </div>
  );
}
