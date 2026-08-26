import { describe, expect, it } from 'vitest'
import { bandFor, delta, index, money, moneyCompact, percent } from './format'

/**
 * The banding tests are the important ones here.
 *
 * The colour scale encodes the single most important judgement call in the
 * product: **performance is banded by peer index, never by raw WPUPD.** If
 * someone "simplifies" this to rank on WPUPD, the UI silently starts sorting
 * by denomination and every penny machine looks like a removal candidate.
 */
describe('bandFor', () => {
  it('bands a standout as strong', () => {
    expect(bandFor(1.2).band).toBe('strong')
  })

  it('treats exactly average as healthy', () => {
    expect(bandFor(1.0).band).toBe('healthy')
  })

  it('bands a mild shortfall as watch, not critical', () => {
    // 0.85-0.95 is inside normal variance for a slot machine. Calling it
    // critical would train people to ignore the critical band.
    expect(bandFor(0.9).band).toBe('watch')
  })

  it('bands a real shortfall as critical', () => {
    expect(bandFor(0.7).band).toBe('critical')
  })

  it.each([
    [1.15, 'strong'],
    [1.149, 'healthy'],
    [0.95, 'healthy'],
    [0.949, 'watch'],
    [0.85, 'watch'],
    [0.849, 'critical'],
  ])('boundary %f -> %s', (value, expected) => {
    expect(bandFor(value).band).toBe(expected)
  })

  it('untrusted data overrides every performance band', () => {
    // A machine with a suspect meter has no meaningful performance band, and
    // showing one would invite acting on a number we do not believe.
    expect(bandFor(2.5, true).band).toBe('untrusted')
    expect(bandFor(0.2, true).band).toBe('untrusted')
  })

  it('pairs every band with a non-colour glyph', () => {
    // Colour alone is invisible to roughly one man in twelve.
    for (const v of [1.3, 1.0, 0.9, 0.6]) {
      expect(bandFor(v).icon.length).toBeGreaterThan(0)
      expect(bandFor(v).label.length).toBeGreaterThan(0)
    }
    expect(bandFor(1.0, true).icon.length).toBeGreaterThan(0)
  })
})

describe('formatters', () => {
  it('formats money without cents by default', () => {
    expect(money(1234.56)).toBe('$1,235')
  })

  it('formats money with cents on request', () => {
    expect(money(1234.56, true)).toBe('$1,234.56')
  })

  it('compacts large money for tiles', () => {
    expect(moneyCompact(6_412_236)).toBe('$6.4M')
    expect(moneyCompact(340_000)).toBe('$340K')
  })

  it('renders peer index to two decimals', () => {
    expect(index(1.0)).toBe('1.00')
    expect(index(0.6754)).toBe('0.68')
  })

  it('renders a fraction as a percentage', () => {
    expect(percent(0.0636)).toBe('6.36%')
  })

  it('signs deltas explicitly', () => {
    expect(delta(4.1)).toBe('+4.1%')
    expect(delta(-4.1)).toBe('-4.1%')
    expect(delta(0)).toBe('+0.0%')
  })
})
