import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { splitSummary } from './licence'

const LICENSE = readFileSync(new URL('../../LICENSE', import.meta.url), 'utf8')

describe('the licence dialog', () => {
  it('shows the summary up to its last line and folds the rest', () => {
    const [shown, folded] = splitSummary(LICENSE)
    expect(shown.trimEnd().endsWith('are what count.')).toBe(true)
    expect(shown).toContain('✓ Use it for free')
    expect(folded).toContain('DISCLAIMER: NO WARRANTY')
    expect(folded).not.toContain('This list is a summary.')
  })

  it('shows everything when the summary line is missing', () => {
    expect(splitSummary('just text\nmore')).toEqual(['just text\nmore', ''])
  })
})
