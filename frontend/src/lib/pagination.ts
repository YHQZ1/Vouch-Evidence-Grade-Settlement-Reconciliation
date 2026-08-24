import type { Page } from '../types/api';

export class PaginationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'PaginationError';
  }
}

export async function fetchAllPages<T>(
  fetchPage: (offset: number) => Promise<Page<T>>,
  keyOf: (item: T) => string,
  label: string,
  maxPages = 1_000,
): Promise<{ batch_id: string; items: T[]; total: number }> {
  const items: T[] = [];
  const seenKeys = new Set<string>();
  const seenOffsets = new Set<number>();
  let offset = 0;
  let expectedTotal: number | undefined;
  let expectedBatchId: string | undefined;

  for (let pageNumber = 0; pageNumber < maxPages; pageNumber += 1) {
    if (seenOffsets.has(offset)) {
      throw new PaginationError(`${label} pagination repeated offset ${offset}.`);
    }
    seenOffsets.add(offset);
    const page = await fetchPage(offset);
    if (page.offset !== offset) {
      throw new PaginationError(
        `${label} returned page offset ${page.offset}; expected ${offset}.`,
      );
    }
    expectedBatchId ??= page.batch_id;
    if (page.batch_id !== expectedBatchId) {
      throw new PaginationError(`${label} batch_id changed during pagination.`);
    }
    expectedTotal ??= page.total;
    if (page.total !== expectedTotal) {
      throw new PaginationError(`${label} total changed during pagination.`);
    }
    for (const item of page.items) {
      const key = keyOf(item);
      if (seenKeys.has(key)) {
        throw new PaginationError(`${label} returned duplicate record ${key}.`);
      }
      seenKeys.add(key);
      items.push(item);
    }
    if (page.next_offset == null) {
      if (items.length !== expectedTotal) {
        throw new PaginationError(
          `${label} ended with ${items.length} records; API declared ${expectedTotal}.`,
        );
      }
      return { batch_id: page.batch_id, items, total: items.length };
    }
    if (!Number.isInteger(page.next_offset) || page.next_offset <= offset) {
      throw new PaginationError(
        `${label} returned invalid next_offset ${page.next_offset}.`,
      );
    }
    offset = page.next_offset;
  }

  throw new PaginationError(
    `${label} pagination exceeded the ${maxPages}-page safety bound.`,
  );
}
