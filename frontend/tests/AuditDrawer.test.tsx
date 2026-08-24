import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AuditDrawer } from '../src/components/AuditDrawer';
import { api } from '../src/lib/api';
import type { AuditEvent } from '../src/types/api';

const event = {
  audit_id: 'audit-1',
  batch_id: 'batch-1',
  settlement_id: 'set-1',
  decision_type: 'settlement_resolution',
  prior_state: null,
  resulting_state: 'needs_review',
  reason_codes: ['utr_missing'],
  cited_source_record_ids: ['gateway-row-1', 'bank-row-1', 'journal-1'],
  calculated_values: [
    { name: 'candidate_score', value: '246' },
    { name: 'signed_net_subunits', value: '393025' },
  ],
  rule_id: 'rule',
  rule_version: '1',
  policy_version: 'policy',
  schema_version: 'schema',
  evaluation_clock: '2026-08-31T18:30:00Z',
  sequence_number: 1,
  input_fingerprints: ['sha-1'],
  candidate_accepted: null,
  candidate_score: 246,
  candidate_signals: [],
} as AuditEvent;
const complete = { batch_id: 'batch-1', items: [event], total: 1 };

afterEach(() => vi.restoreAllMocks());

describe('audit drawer lifecycle', () => {
  it('enters focus, contains Tab and Shift+Tab, and returns focus on Escape', async () => {
    vi.spyOn(api, 'listAudit').mockResolvedValue(complete);
    const user = userEvent.setup();
    render(<AuditDrawer batchId="batch-1" settlementId="set-1" trigger="Explain" />);
    const trigger = screen.getByRole('button', { name: 'Explain' });
    await user.click(trigger);
    const dialog = await screen.findByRole('dialog');
    expect(screen.queryByText('proposed', { exact: true })).not.toBeInTheDocument();
    await waitFor(() => expect(document.activeElement).toBe(dialog));
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).not.toBe(dialog);
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(document.activeElement).toBe(
      screen.getByRole('button', { name: 'Close audit explanation' }),
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(document.activeElement).toBe(trigger));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('distinguishes API failure from an empty audit trail and retries', async () => {
    const list = vi
      .spyOn(api, 'listAudit')
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce({ batch_id: 'batch-1', items: [], total: 0 });
    const user = userEvent.setup();
    render(<AuditDrawer batchId="batch-1" trigger="Explain" />);
    await user.click(screen.getByRole('button', { name: 'Explain' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('offline');
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(
      await screen.findByText('No audit events cite this settlement.'),
    ).toBeInTheDocument();
    expect(list).toHaveBeenCalledTimes(2);
  });

  it('treats an aborted audit request as cancellation', async () => {
    let signal: AbortSignal | undefined;
    vi.spyOn(api, 'listAudit').mockImplementation((_batchId, requestSignal) => {
      signal = requestSignal;
      return new Promise((_resolve, reject) =>
        requestSignal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        ),
      );
    });
    const user = userEvent.setup();
    render(<AuditDrawer batchId="batch-1" trigger="Explain" />);
    await user.click(screen.getByRole('button', { name: 'Explain' }));
    await waitFor(() => expect(signal).toBeDefined());
    await user.click(screen.getByRole('button', { name: 'Close audit explanation' }));
    expect(signal?.aborted).toBe(true);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
