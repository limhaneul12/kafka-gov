interface ConfirmDestructiveActionOptions {
  actionLabel?: string;
  itemType: string;
  itemName?: string;
  consequence?: string;
}

export function confirmDestructiveAction({
  actionLabel = "delete",
  itemType,
  itemName,
  consequence,
}: ConfirmDestructiveActionOptions) {
  const subject = itemName ? `${itemType} "${itemName}"` : itemType;
  const message = `Are you sure you want to ${actionLabel} ${subject}?`;

  return window.confirm(consequence ? `${message} ${consequence}` : message);
}
