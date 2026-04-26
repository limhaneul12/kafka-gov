import {
  promptForOptionalGovernanceInput,
  promptForRequiredGovernanceInput,
} from "./schemaGovernancePrompts";

export interface ApprovalOverridePayload {
  reason: string;
  approver: string;
  expiresAt: string;
}

export function promptApprovalOverride(changeLabel: string): ApprovalOverridePayload | null {
  const reason = promptForRequiredGovernanceInput(
    `High-risk ${changeLabel}. Enter override reason:`,
  );
  if (!reason) {
    return null;
  }

  const approver = promptForRequiredGovernanceInput(`Enter approver for ${changeLabel}:`);
  if (!approver) {
    return null;
  }

  const expiresAtInput = promptForOptionalGovernanceInput(
    "Enter expiration as ISO 8601 (leave blank for 24 hours from now):",
  );

  let expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
  if (expiresAtInput) {
    const parsedDate = new Date(expiresAtInput);
    if (Number.isNaN(parsedDate.getTime())) {
      throw new Error("Invalid approval expiration timestamp");
    }
    expiresAt = parsedDate.toISOString();
  }

  return {
    reason,
    approver,
    expiresAt,
  };
}
