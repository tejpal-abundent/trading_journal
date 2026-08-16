import { useState } from "react";
import { Button } from "./Button";
import { TextareaField } from "./TextField";
import "../design/components.css";

const MIN_REASON_LENGTH = 30;

/**
 * Shown when POST /api/policy/limits/{type} returns 409
 * amendment_blocked_during_drawdown. Requires ticking "override and log it"
 * plus a reason of at least 30 characters before the caller can retry the
 * request with override_during_drawdown=true (Brief §4.7).
 */
export function DrawdownAmendmentModal({
  open,
  hint,
  submitting,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  hint: string;
  submitting?: boolean;
  onCancel: () => void;
  onConfirm: (reason: string) => void;
}) {
  const [checked, setChecked] = useState(false);
  const [reason, setReason] = useState("");

  if (!open) return null;

  const reasonOk = reason.trim().length >= MIN_REASON_LENGTH;
  const canSubmit = checked && reasonOk && !submitting;

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="dd-modal-title">
      <div className="modal modal--caution">
        <div id="dd-modal-title" className="modal__title">
          Amendment blocked during drawdown
        </div>
        <p className="modal__body">{hint}</p>
        <label className="modal__checkbox">
          <input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} />
          override and log it
        </label>
        <TextareaField
          label="Reason for overriding"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          helperText={`${reason.trim().length}/${MIN_REASON_LENGTH} characters minimum`}
          rows={4}
        />
        <div className="modal__actions">
          <Button variant="secondary" onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="primary" disabled={!canSubmit} onClick={() => onConfirm(reason.trim())}>
            {submitting ? "Submitting…" : "Override and log it"}
          </Button>
        </div>
      </div>
    </div>
  );
}
