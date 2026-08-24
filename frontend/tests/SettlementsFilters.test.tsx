import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SettlementsPage } from '../src/features/settlements/SettlementsPage';
import { useSettlements } from '../src/lib/queries';

vi.mock('../src/lib/queries', () => ({ useSettlements: vi.fn() }));
const mockedUseSettlements = vi.mocked(useSettlements);

afterEach(() => vi.restoreAllMocks());

function LocationProbe() {
  return (
    <output aria-label="location">
      <>{useLocation().search}</>
    </output>
  );
}

describe('settlement URL filters', () => {
  it('preserves filters in the URL while the collection is filtered', async () => {
    mockedUseSettlements.mockReturnValue({
      data: { batch_id: 'batch-1', items: [], total: 0 },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as never);
    const user = userEvent.setup();
    render(
      <MemoryRouter
        initialEntries={['/batches/batch-1/settlements?q=set_12&state=needs_review']}
      >
        <Routes>
          <Route
            path="/batches/:batchId/settlements"
            element={
              <>
                <SettlementsPage />
                <LocationProbe />
              </>
            }
          />
        </Routes>
      </MemoryRouter>,
    );
    expect(
      screen.getByPlaceholderText('Search settlement or balance account'),
    ).toHaveValue('set_12');
    expect(screen.getByLabelText('State')).toHaveValue('needs_review');
    await user.selectOptions(screen.getByLabelText('State'), 'critical_exception');
    expect(screen.getByLabelText('location')).toHaveTextContent(
      'q=set_12&state=critical_exception',
    );
  });
});
