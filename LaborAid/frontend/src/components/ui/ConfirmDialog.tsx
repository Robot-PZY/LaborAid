interface ConfirmDialogProps {
  open: boolean;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
}

export function ConfirmDialog({
  open,
  message,
  onConfirm,
  onCancel,
  confirmLabel = '确定',
  cancelLabel = '取消',
  destructive = true,
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4"
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-message"
    >
      <div
        className="w-full max-w-sm rounded-xl bg-card p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <p id="confirm-dialog-message" className="mb-4 text-sm font-medium">
          {message}
        </p>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border px-4 py-2 text-sm hover:bg-accent"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={
              destructive
                ? 'rounded-lg bg-destructive px-4 py-2 text-sm text-destructive-foreground hover:bg-destructive/90'
                : 'rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90'
            }
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
