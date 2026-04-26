export type ApprovalDecisionAction = "approve" | "reject";

export interface ApprovalDecisionPromptResult {
  approver: string;
  decisionReason?: string;
}

export function promptForRequiredGovernanceInput(
  message: string,
  defaultValue?: string,
): string | null {
  const value = window.prompt(message, defaultValue)?.trim();
  return value ? value : null;
}

export function promptForOptionalGovernanceInput(
  message: string,
  defaultValue?: string,
): string | undefined {
  const value = window.prompt(message, defaultValue)?.trim();
  return value || undefined;
}

export function promptApprovalDecision(
  action: ApprovalDecisionAction,
): ApprovalDecisionPromptResult | null {
  const approver = promptForRequiredGovernanceInput("Approver name", "schema-admin");

  if (!approver) {
    return null;
  }

  const decisionReason = promptForOptionalGovernanceInput(
    action === "approve" ? "Approval reason" : "Rejection reason",
    action === "approve" ? "Reviewed and approved" : "Rejected after review",
  );

  return {
    approver,
    decisionReason,
  };
}

export function confirmSchemaGovernanceAction(message: string): boolean {
  return window.confirm(message);
}
