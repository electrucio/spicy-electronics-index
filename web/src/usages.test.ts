/** Narrowing the parts list to the sources a reader chose. */
import { describe, expect, it } from 'vitest'

import { menu, narrow, toggled, usedBy } from './usages'
import type { PartIndex, PartRow, UsageFacet, Usages } from './types'

const FACETS: UsageFacet[] = [
  { key: 'esp', group: 'projects', source: 'esp', n: 1300 },
  { key: 'elektor/1980s', group: 'paper', source: 'elektor', label: '1980s', by: 'decade', n: 110 },
  { key: 'elektor/2000s', group: 'paper', source: 'elektor', label: '2000s', by: 'decade', n: 639 },
  { key: 'github', group: 'github', source: 'github', n: 900 },
  { key: 'books/Pease', group: 'paper', source: 'books', label: 'Pease — Troubleshooting Analog Circuits', by: 'title', n: 12 },
]
const rows: PartRow[] = [
  ['TL072', 30, 40, 3, 1],
  ['BC547', 12, 14, 2, 1],
  ['12AX7', 5, 6, 6, 1],
]
const used = new Map<string, [number, number][]>([
  ['TL072', [[0, 10], [1, 5], [2, 10], [3, 5]]],
  ['BC547', [[1, 2], [2, 10]]],
  ['12AX7', [[0, 5]]],
])

describe('narrow', () => {
  it('leaves the rows alone while nothing is dropped', () => {
    expect(narrow(rows, used, FACETS, new Set())).toBe(rows)
  })

  it('recounts the usages from the kept facets and drops a part with none left', () => {
    const out = narrow(rows, used, FACETS, new Set(['esp', 'github']))
    expect(out.map((r) => [r[0], r[1]])).toEqual([['TL072', 15], ['BC547', 12]])
    expect(out[0]?.slice(2)).toEqual([40, 3, 1])     // the rest of the row travels untouched
  })

  it('keeps a part the file says nothing about out of a narrowed list', () => {
    expect(narrow([['NEW', 0, 0, 1, 1]], used, FACETS, new Set(['esp']))).toEqual([])
  })
})

describe('the menu', () => {
  it('groups the facets by source, a magazine with its decades under it and the books with their titles', () => {
    const m = menu(FACETS)
    expect(m.projects.map((s) => s.source)).toEqual(['esp'])
    expect(m.paper).toEqual([
      { source: 'elektor', group: 'paper', n: 749, facets: [FACETS[1], FACETS[2]] },
      { source: 'books', group: 'paper', n: 12, facets: [FACETS[4]] },
    ])
    expect(m.github[0]?.source).toBe('github')
  })

  it('toggles a set of keys in or out without touching the rest', () => {
    const d = toggled(new Set(['esp']), ['elektor/1980s', 'elektor/2000s'], false)
    expect([...d].sort()).toEqual(['elektor/1980s', 'elektor/2000s', 'esp'])
    expect([...toggled(d, ['esp', 'elektor/1980s'], true)]).toEqual(['elektor/2000s'])
  })
})

describe('usedBy', () => {
  const index: PartIndex = { schema: 1, sources: [], kinds: [], deviceKinds: [], sourcesStamp: 'a1', parts: rows }
  it('pairs each part with its row when the two files are from one build', () => {
    const usages: Usages = { schema: 1, sourcesStamp: 'a1', facets: FACETS, parts: [[[0, 1]], [], [[3, 2]]] }
    expect(usedBy(index, usages)?.get('12AX7')).toEqual([[3, 2]])
  })
  it('refuses a file from another build, whose rows would be read against the wrong parts', () => {
    expect(usedBy(index, { schema: 1, sourcesStamp: 'b2', facets: FACETS, parts: [[], [], []] })).toBeNull()
    expect(usedBy(index, { schema: 1, sourcesStamp: 'a1', facets: FACETS, parts: [[]] })).toBeNull()
  })
  it('refuses rows of another list of parts of the same length', () => {
    const stamped: PartIndex = { ...index, partsStamp: 'p1' }
    expect(usedBy(stamped, { schema: 1, sourcesStamp: 'a1', partsStamp: 'p2', facets: FACETS, parts: [[], [], []] })).toBeNull()
    expect(usedBy(stamped, { schema: 1, sourcesStamp: 'a1', partsStamp: 'p1', facets: FACETS, parts: [[], [], []] })).not.toBeNull()
  })
})
