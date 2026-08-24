import { describe, expect, it } from 'vitest';
import { fetchAllPages, PaginationError } from '../src/lib/pagination';
import type { Page } from '../src/types/api';

type Row = { id: string };
const page = (
  items: Row[],
  offset: number,
  next_offset: number | null,
  total = 3,
): Page<Row> => ({ batch_id: 'batch-1', items, offset, limit: 2, next_offset, total });

describe('bounded complete pagination', () => {
  it('follows server pages with a page size below 100 and preserves order', async () => {
    const calls: number[] = [];
    const result = await fetchAllPages(
      (offset) => {
        calls.push(offset);
        return Promise.resolve(
          offset === 0
            ? page([{ id: 'a' }, { id: 'b' }], 0, 2)
            : page([{ id: 'c' }], 2, null),
        );
      },
      (row) => row.id,
      'settlement',
    );
    expect(calls).toEqual([0, 2]);
    expect(result.items.map((row) => row.id)).toEqual(['a', 'b', 'c']);
    expect(result.total).toBe(3);
  });
  it('surfaces cyclic, duplicate, and safety-bound responses', async () => {
    await expect(
      fetchAllPages(
        () => Promise.resolve(page([{ id: 'a' }], 0, 0, 1)),
        (row) => row.id,
        'exception',
      ),
    ).rejects.toThrow(PaginationError);
    await expect(
      fetchAllPages(
        (offset) =>
          Promise.resolve(
            page(
              [{ id: offset === 0 ? 'a' : 'a' }],
              offset,
              offset === 0 ? 1 : null,
              2,
            ),
          ),
        (row) => row.id,
        'audit',
      ),
    ).rejects.toThrow(/duplicate/);
    await expect(
      fetchAllPages(
        (offset) =>
          Promise.resolve(page([{ id: String(offset) }], offset, offset + 1, 999)),
        (row) => row.id,
        'audit',
        2,
      ),
    ).rejects.toThrow(/safety bound/);
  });
  it('rejects incomplete terminal pages and inconsistent page identity', async () => {
    await expect(
      fetchAllPages(
        () => Promise.resolve(page([{ id: 'a' }], 0, null, 2)),
        (row) => row.id,
        'settlement',
      ),
    ).rejects.toThrow(/declared 2/);
    await expect(
      fetchAllPages(
        (offset) =>
          Promise.resolve(
            offset === 0
              ? page([{ id: 'a' }], 0, 1, 2)
              : { ...page([{ id: 'b' }], 1, null, 2), batch_id: 'other-batch' },
          ),
        (row) => row.id,
        'exception',
      ),
    ).rejects.toThrow(/batch_id/);
    await expect(
      fetchAllPages(
        () => Promise.resolve({ ...page([{ id: 'a' }], 3, null, 1) }),
        (row) => row.id,
        'audit',
      ),
    ).rejects.toThrow(/page offset/);
  });
});
