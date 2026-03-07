export interface ApprovalOverridePayload {
  reason: string;
  approver: string;
  expiresAt: string;
}

export function promptApprovalOverride(changeLabel: string): ApprovalOverridePayload | null {
  const reason = window.prompt(`High-risk ${changeLabel}. Enter override reason:`)?.trim();
  if (!reason) {
    return null;
  }

  const approver = window.prompt(`Enter approver for ${changeLabel}:`)?.trim();
  if (!approver) {
    return null;
  }

  const expiresAtInput = window.prompt(
    "Enter expiration as ISO 8601 (leave blank for 24 hours from now):"
  )?.trim();

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
