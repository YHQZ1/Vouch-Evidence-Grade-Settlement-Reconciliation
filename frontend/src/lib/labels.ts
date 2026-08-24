import type { Readiness, ResolutionState } from '../types/api';

export const SOURCE_LABELS = {
  gateway: 'Razorpay reconciliation CSV',
  bank: 'Bank statement CSV',
  ledger: 'General ledger CSV',
  policy: 'Close policy JSON',
} as const;
export const REASON_LABELS: Record<string, string> = {
  exact_evidence_verified: 'Exact evidence verified',
  fee_tax_netted: 'Fees and tax netted',
  ledger_line_duplicated: 'Ledger line duplicated',
  bank_credit_missing_overdue: 'Bank credit missing and overdue',
  bank_amount_mismatch: 'Bank amount mismatch',
  bank_utr_conflict: 'Bank UTR conflict',
  ledger_unbalanced: 'Ledger journal unbalanced',
  malformed_source_record: 'Malformed source record',
  stronger_candidate_selected: 'Stronger candidate selected',
  amount_mismatch: 'Amount mismatch',
  balance_account_conflict: 'Balance account conflict',
  evidence_integrity_failure: 'Evidence integrity failure',
  pending_within_sla: 'Pending within SLA',
};
export const STATE_LABELS: Record<ResolutionState, string> = {
  auto_cleared: 'Auto-cleared',
  cleared_with_explanation: 'Cleared with explanation',
  pending_within_sla: 'Pending within SLA',
  needs_review: 'Needs review',
  critical_exception: 'Critical exception',
  excluded: 'Excluded',
};
export const READINESS_LABELS: Record<Readiness, string> = {
  READY: 'Ready to close',
  READY_WITH_EXCEPTIONS: 'Ready with exceptions',
  BLOCKED: 'Close blocked',
};
export function reasonLabel(code: string): string {
  return REASON_LABELS[code] ?? code.replaceAll('_', ' ');
}
