import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { Layout, ExportActions } from '../src/components/Layout';
import { useBatch } from '../src/lib/queries';
import * as apiModule from '../src/lib/api';

vi.mock('../src/lib/queries', () => ({ useBatch: vi.fn() }));

const batch = {
  batch_id: 'batch-1',
  evaluation_clock: '2026-08-31T18:30:00Z',
  status: 'completed',
  required_sources: ['gateway', 'bank', 'ledger', 'policy'],
  sources: [],
  result_available: true,
  result_batch_id: 'batch-1',
  failure: null,
  created_at: '2026-08-31T18:30:00Z',
  updated_at: '2026-08-31T18:30:00Z',
  lifecycle_sequence: 5,
  links: {},
} as never;
const mockedUseBatch = vi.mocked(useBatch);

function setMobileViewport(matches = false) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    value: vi.fn(() => ({
      matches,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  setMobileViewport(false);
});

describe('shell disclosure and recovery', () => {
  it('makes a closed mobile sidebar inert and returns focus after close', async () => {
    setMobileViewport(false);
    mockedUseBatch.mockReturnValue({
      data: batch,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as never);
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/batches/batch-1/overview']}>
        <Routes>
          <Route path="/batches/:batchId/*" element={<Layout />} />
        </Routes>
      </MemoryRouter>,
    );
    const menu = screen.getByRole('button', { name: 'Toggle navigation' });
    const sidebar = document.getElementById('batch-review-sidebar');
    expect(sidebar).not.toBeNull();
    expect(menu).toHaveAttribute('aria-expanded', 'false');
    expect(sidebar).toHaveAttribute('aria-hidden', 'true');
    expect(sidebar).toHaveAttribute('inert', '');
    await user.click(menu);
    await waitFor(() =>
      expect(screen.getByRole('link', { name: 'Overview' })).toHaveFocus(),
    );
    expect(menu).toHaveAttribute('aria-expanded', 'true');
    await user.click(menu);
    await waitFor(() => expect(menu).toHaveFocus());
    expect(sidebar).toHaveAttribute('aria-hidden', 'true');
  });

  it('keeps the skip-link target present in loading/recovery shell state', () => {
    mockedUseBatch.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('offline'),
      refetch: vi.fn(),
    } as never);
    render(
      <MemoryRouter initialEntries={['/batches/missing/overview']}>
        <Routes>
          <Route path="/batches/:batchId/*" element={<Layout />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: 'Skip to content' })).toHaveAttribute(
      'href',
      '#main-content',
    );
    expect(document.getElementById('main-content')).toBeInTheDocument();
  });
});

describe('export recovery', () => {
  it('shows an inline failure and retries the same export', async () => {
    const download = vi
      .spyOn(apiModule, 'downloadExport')
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce('result.json');
    const user = userEvent.setup();
    render(<ExportActions batchId="batch-1" enabled />);
    await user.click(screen.getByRole('button', { name: 'Result' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Export failed');
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByRole('status')).toHaveTextContent(
      'result.json downloaded',
    );
    expect(download).toHaveBeenCalledTimes(2);
  });
});
