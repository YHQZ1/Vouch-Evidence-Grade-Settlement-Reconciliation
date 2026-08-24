import { describe, expect, it } from 'vitest';
import { reasonLabel } from '../src/lib/labels';

describe('canonical labels', () => {
  it('keeps the reason code alongside its human label', () => {
    expect(reasonLabel('ledger_line_duplicated')).toBe('Ledger line duplicated');
    expect(reasonLabel('future_reason_code')).toBe('future reason code');
  });
});
