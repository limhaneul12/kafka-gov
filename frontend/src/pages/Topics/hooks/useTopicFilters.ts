import { useState, useMemo } from "react";
import type { Topic } from "../Topics.types";

export function useTopicFilters(topics: Topic[]) {
  const [searchQuery, setSearchQuery] = useState("");
  const [envFilter, setEnvFilter] = useState<string[]>([]);
  const [ownerFilter, setOwnerFilter] = useState<string[]>([]);
  const [tagFilter, setTagFilter] = useState<string[]>([]);

  // Extract unique values for filter options
  const allOwners = useMemo(
    () => Array.from(new Set(topics.flatMap((t) => t.owners))),
    [topics]
  );

  const allTags = useMemo(
    () => Array.from(new Set(topics.flatMap((t) => t.tags))),
    [topics]
  );

  // Apply filters
  const filteredTopics = useMemo(() => {
    return topics.filter((topic) => {
      // Search filter
      if (
        searchQuery &&
        !topic.name.toLowerCase().includes(searchQuery.toLowerCase())
      ) {
        return false;
      }

      // Environment filter
      if (envFilter.length > 0 && !envFilter.includes(topic.environment)) {
        return false;
      }

      // Owner filter
      if (
        ownerFilter.length > 0 &&
        !topic.owners.some((owner) => ownerFilter.includes(owner))
      ) {
        return false;
      }

      // Tag filter
      if (
        tagFilter.length > 0 &&
        !topic.tags.some((tag) => tagFilter.includes(tag))
      ) {
        return false;
      }

      return true;
    });
  }, [topics, searchQuery, envFilter, ownerFilter, tagFilter]);

  const resetFilters = () => {
    setSearchQuery("");
    setEnvFilter([]);
    setOwnerFilter([]);
    setTagFilter([]);
  };

  return {
    searchQuery,
    setSearchQuery,
    envFilter,
    setEnvFilter,
    ownerFilter,
    setOwnerFilter,
    tagFilter,
    setTagFilter,
    allOwners,
    allTags,
    filteredTopics,
    resetFilters,
  };
}
