import { toast } from "sonner";

import { registryAPI } from "../services/api";
import type { SchemaRegistry } from "../types";
import { DEFAULT_UNKNOWN_ERROR_MESSAGE, extractErrorMessage } from "./error";

export const NO_ACTIVE_SCHEMA_REGISTRY_MESSAGE = "No active Schema Registry found";
const DEFAULT_GOVERNANCE_ERROR_DESCRIPTION = "No additional error details were returned.";

export async function resolveActiveRegistry(): Promise<SchemaRegistry | null> {
  const registriesRes = await registryAPI.list();
  const registries = registriesRes.data as SchemaRegistry[] | undefined;
  return registries?.find((registry) => registry.is_active) ?? registries?.[0] ?? null;
}

export async function requireActiveRegistry(): Promise<SchemaRegistry | null> {
  const activeRegistry = await resolveActiveRegistry();

  if (!activeRegistry) {
    toast.error(NO_ACTIVE_SCHEMA_REGISTRY_MESSAGE);
    return null;
  }

  return activeRegistry;
}

export function describeGovernanceError(
  error: unknown,
  fallbackDescription: string = DEFAULT_GOVERNANCE_ERROR_DESCRIPTION,
): string {
  const message = extractErrorMessage(error);
  return message === DEFAULT_UNKNOWN_ERROR_MESSAGE ? fallbackDescription : message;
}

export function toastGovernanceError(
  title: string,
  error: unknown,
  fallbackDescription?: string,
) {
  toast.error(title, {
    description: describeGovernanceError(error, fallbackDescription),
  });
}
