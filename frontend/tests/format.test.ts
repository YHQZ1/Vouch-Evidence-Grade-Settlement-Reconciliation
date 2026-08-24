import { describe, expect, it } from 'vitest'
import { formatCalculatedValue, formatSubunits } from '../src/lib/format'

describe('integer currency formatting', () => {
  it('formats paise, zero, negatives and Indian grouping exactly', () => {
    expect(formatSubunits(0)).toBe('INR 0.00')
    expect(formatSubunits(1)).toBe('INR 0.01')
    expect(formatSubunits(-125)).toBe('-INR 1.25')
    expect(formatSubunits(123456789)).toBe('INR 12,34,567.89')
    expect(formatSubunits(9007199254740991n)).toBe('INR 9,00,71,99,25,47,409.91')
  })
  it('fails visibly on unsafe numeric values', () => {
    expect(() => formatSubunits(Number.MAX_SAFE_INTEGER + 1)).toThrow(/Unsafe integer/)
  })
  it('formats only monetary calculated values as INR', () => {
    expect(formatCalculatedValue('candidate_score', '246')).toBe('246')
    expect(formatCalculatedValue('ledger_line_count', '2')).toBe('2')
    expect(formatCalculatedValue('signed_net_subunits', '393025')).toBe('INR 3,930.25')
  })
  it('keeps arbitrarily large monetary strings exact with BigInt', () => {
    expect(formatCalculatedValue('signed_net_subunits', '900719925474099312345')).toBe('INR 90,07,19,92,54,74,09,93,123.45')
    expect(() => formatCalculatedValue('signed_net_subunits', '12.5')).toThrow(/Invalid monetary value/)
  })
})
