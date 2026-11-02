import { describe, expect, it } from 'vitest'
import { pageLabel } from './format'

describe('pageLabel', () => {
  it('names a page by the number printed on it when that is known', () => {
    expect(pageLabel(656, '623')).toBe('p. 623')        // The Art of Electronics: 33 leaves of front matter
    expect(pageLabel(96, '1-85')).toBe('p. 1-85')       // a volume-page number, as the book prints it
  })
  it('falls back to the file’s own number', () => {
    expect(pageLabel(656)).toBe('page 656')
    expect(pageLabel(12, '')).toBe('page 12')
  })
})
