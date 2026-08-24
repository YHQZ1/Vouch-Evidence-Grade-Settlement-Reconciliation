import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { InvestigationPanel } from '../src/features/settlements/InvestigationPanel';
import type { EffectiveReview, SettlementResult } from '../src/types/api';

const mocks = vi.hoisted(() => ({
  runs: {
    data: { batch_id: 'batch-1', items: [], total: 0 },
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null as Error | null,
    refetch: vi.fn(),
  },
  eligibility: {
    data: { eligible: true, provider_available: true, explanation: 'eligible' },
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null as Error | null,
    refetch: vi.fn(),
  },
  effective: {
    data: {
      review: {
        accepted_decision: null as EffectiveReview['accepted_decision'],
        base_state: 'needs_review',
        effective_state: 'needs_review',
      },
    },
    isFetching: false,
    isError: false,
    error: null as Error | null,
    refetch: vi.fn(),
  },
  mutation: { isPending: false, isError: false, mutate: vi.fn() },
  download: vi.fn(),
}));

vi.mock('../src/lib/queries', () => ({
  useInvestigations: () => mocks.runs,
  useInvestigationEligibility: () => mocks.eligibility,
  useEffectiveReview: () => mocks.effective,
  useRunInvestigation: () => mocks.mutation,
}));
vi.mock('../src/lib/api', () => ({ downloadExport: mocks.download }));

const settlement = { state: 'needs_review' } as SettlementResult;

afterEach(() => {
  vi.clearAllMocks();
  mocks.eligibility.data = {
    eligible: true,
    provider_available: true,
    explanation: 'eligible',
  };
  mocks.effective.data.review.accepted_decision = null;
  mocks.mutation.isPending = false;
  mocks.mutation.isError = false;
  mocks.runs.data.items = [];
});

describe('bounded investigation panel', () => {
  it('uses server provider availability and blocks disabled invocation', () => {
    mocks.eligibility.data = {
      eligible: true,
      provider_available: false,
      explanation: 'The configured investigation provider is disabled.',
    };
    render(
      <InvestigationPanel
        batchId="batch-1"
        settlementId="set-1"
        settlement={settlement}
      />,
    );
    expect(
      screen.getByRole('button', { name: 'Investigate ambiguous evidence' }),
    ).toBeDisabled();
    expect(
      screen.getByRole('heading', { name: 'Investigate ambiguous evidence' }),
    ).toHaveAttribute('id', 'investigation-title');
    expect(screen.getByText(/AI is disabled or unavailable/)).toBeInTheDocument();
  });

  it('does not expose an action for a non-needs-review settlement or after acceptance', () => {
    const { rerender } = render(
      <InvestigationPanel
        batchId="batch-1"
        settlementId="set-1"
        settlement={{ state: 'critical_exception' } as SettlementResult}
      />,
    );
    expect(
      screen.queryByRole('button', { name: 'Investigate ambiguous evidence' }),
    ).not.toBeInTheDocument();
    mocks.effective.data.review.accepted_decision = {
      decision_id: 'decision-1',
    } as NonNullable<EffectiveReview['accepted_decision']>;
    mocks.eligibility.data = {
      eligible: false,
      provider_available: true,
      explanation: 'Already accepted.',
    };
    rerender(
      <InvestigationPanel
        batchId="batch-1"
        settlementId="set-1"
        settlement={settlement}
      />,
    );
    expect(
      screen.getByRole('button', { name: 'Investigate ambiguous evidence' }),
    ).toBeDisabled();
    expect(screen.getByText('Verifier accepted.')).toBeInTheDocument();
  });

  it('keeps export failure visible and permits a retry', async () => {
    mocks.download
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce('file.json');
    const user = userEvent.setup();
    render(
      <InvestigationPanel
        batchId="batch-1"
        settlementId="set-1"
        settlement={settlement}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'Export investigations' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('offline');
    await user.click(screen.getByRole('button', { name: 'Export investigations' }));
    expect(mocks.download).toHaveBeenCalledTimes(2);
  });

  it('surfaces eligibility failures with a retry action', async () => {
    mocks.eligibility.isError = true;
    mocks.eligibility.error = new Error('eligibility offline');
    const user = userEvent.setup();
    render(
      <InvestigationPanel
        batchId="batch-1"
        settlementId="set-1"
        settlement={settlement}
      />,
    );
    expect(await screen.findByText('eligibility offline')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(mocks.eligibility.refetch).toHaveBeenCalledOnce();
  });

  it('keeps invocation disabled while post-mutation projections refetch', () => {
    mocks.effective.isFetching = true;
    render(
      <InvestigationPanel
        batchId="batch-1"
        settlementId="set-1"
        settlement={settlement}
      />,
    );
    expect(
      screen.getByRole('button', { name: 'Investigate ambiguous evidence' }),
    ).toBeDisabled();
  });
});
