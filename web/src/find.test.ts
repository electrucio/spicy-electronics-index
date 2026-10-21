/** The Projects tab's engine: parts together and none of those, families in three answers, what the reader has. */
import { describe, expect, it } from 'vitest'

import {
  AFTER, EMPTY, EXACT, GRADE, IS, MIGHT, NONE, NOT, SAME, SUBST, UNKNOWN, answer, asked, coverage, decode, familyStates, fold,
  holds, pasted, readQuery, resolver, sameBuild, termOf, writeQuery,
  type Context, type Query,
} from './find'
import type { Family, FinderDocs, FinderUnits, PartIndex, PartRow } from './types'
import { words } from './words'

// families: ic > opamp; discrete > transistor > (bjt, fet > jfet)
const FAMILIES: Family[] = [
  { id: 'ic', label: 'Integrated circuits', definition: '' },
  { id: 'opamp', label: 'Operational amplifiers', broader: 'ic', definition: '' },
  { id: 'discrete', label: 'Discrete semiconductors', definition: '' },
  { id: 'transistor', label: 'Transistors', broader: 'discrete', definition: '' },
  { id: 'bjt', label: 'Bipolar transistors', broader: 'transistor', definition: '' },
  { id: 'fet', label: 'Field-effect transistors', broader: 'transistor', definition: '' },
  { id: 'jfet', label: 'JFETs', broader: 'fet', definition: '' },
  { id: 'tube', label: 'Tubes and valves', definition: '' },
]
const FAM = ['ic', 'opamp', 'discrete', 'transistor', 'bjt', 'fet', 'jfet', 'tube']
const at = (f: string) => FAM.indexOf(f)
// rows of parts.json: name, usages, docs, models, devices, family
const ROWS: PartRow[] = [
  ['12AX7', 9, 3, 1, 0, at('tube')],      // 0
  ['2N3904', 9, 3, 1, 0, at('bjt')],      // 1
  ['2N5457', 9, 3, 1, 0, at('jfet')],     // 2
  ['2N5458', 9, 3, 1, 0, at('transistor')], // 3: a JEDEC number nothing settled
  ['4580M', 9, 3, 0, 0, -1],              // 4: nothing says what it is
  ['BC547', 9, 3, 1, 0, at('bjt')],       // 5
  ['BC547B', 9, 3, 1, 0, at('bjt')],      // 6
  ['BC547C', 9, 3, 1, 0, at('bjt')],      // 7
  ['TL072', 9, 3, 1, 0, at('opamp')],     // 8
  ['TL072CP', 9, 3, 0, 0, at('opamp')],   // 9
  ['2SK170', 2, 1, 1, 0, at('jfet')],     // 10
  ['LSK170', 2, 1, 1, 0, at('jfet')],     // 11
  ['TL071', 2, 1, 1, 0, at('opamp')],     // 12
  ['ECC83', 2, 1, 1, 0, at('tube')],      // 13
]
const INDEX: PartIndex = { schema: 1, sources: ['esp', 'mag'], kinds: ['site', 'magazine'], deviceKinds: [],
  families: FAM, parts: ROWS, partsStamp: 'p1', sourcesStamp: 's1' }

/** Units: 0 fuzz (2N3904 BC547C, names 2N5457), 1 preamp (12AX7 TL072), 2 buffer (2N5458), 3 mag p.1 (BC547B),
 *  4 mag p.2 (TL072CP) running on from p.1, 5 mystery (4580M 2N3904), 6 an advert (TL072, only named). */
const UNITS: FinderUnits = {
  schema: 1, findStamp: 'f1', partsStamp: 'p1', sourcesStamp: 's1',
  roles: ['schematic', 'project_page', 'article', 'figure', 'service_manual', 'issue', 'book'],
  kinds: ['project', 'technique', 'reference', 'mention', 'advert'], negative: ['opamp', 'jfet', 'tube'],
  facets: [{ key: 'esp', group: 'projects', source: 'esp', n: 5 }, { key: 'mag/1970s', group: 'paper', source: 'mag', label: '1970s', by: 'decade', n: 2 }],
  moreFacets: {}, eras: ['mixed', 'vintage'],
  units: {
    role: [1, 0, 1, 5, 5, 0, 1], flags: [1, 1, 0, 0, AFTER, 1, 0], kinds: [0b1001, 1, 1, 1, 1, 1, 0b10000],
    year: [0, 1959, 0, 1975, 1975, 0, 0], page: [0, 0, 0, 1, 2, 0, 0], facet: [0, 0, 0, 1, 1, 0, 0],
    used: [2, 2, 1, 1, 1, 2, 0], usedIds: [1, 6, 0, 8, 3, 6, 9, 1, 3], named: [1, 0, 0, 0, 0, 0, 1], namedIds: [2, 8],
  },
  up: { BC547B: ['BC547'], BC547C: ['BC547'], TL072CP: ['TL072'] },
  alias: {}, shards: [], common: [],
  relations: [
    ['LSK170', 'replacement_for', '2SK170', ['S32'], 'Linear Systems: a direct replacement', 'draft'],
    ['ECC83', 'same_product_as', '12AX7', ['S18'], 'JJ sells one valve as ECC83S, 12AX7 and 7025', 'draft'],
    ['TL071', 'same_datasheet', 'TL071', ['S27'], 'one sheet', 'draft'],
    ['TL072', 'same_datasheet', 'TL071', ['S27'], 'one sheet', 'draft'],
  ],
  coverage: { same_product_as: ['both', 'substitute'], replacement_for: ['out', 'substitute'], next_generation_of: ['out', 'substitute'],
    same_datasheet: ['both', 'hint'] },
}
const DOCS: FinderDocs = {
  schema: 1, findStamp: 'f1',
  title: ['Fuzz Face clone', 'Bassman preamp', 'JFET buffer', 'Mag 1975-02', 'Mag 1975-02', 'Mystery box', 'Advert'],
  url: ['u0', 'u1', 'u2', 'u3#page=1', 'u3#page=2', 'u5', 'u6'], source: [0, 0, 0, 1, 1, 0, 0],
  date: ['', '1959', '', '1975-02', '1975-02', '', ''], also: {}, aka: {}, sheets: {},
}

const finder = decode(UNITS, ROWS.length)
const ctx: Context = {
  index: INDEX, finder, row: new Map(ROWS.map((r, i) => [r[0], i])), facetKeys: UNITS.facets.map((f) => f.key),
  roles: UNITS.roles, eras: UNITS.eras, source: DOCS.source, families: FAMILIES, titleWords: DOCS.title.map((t) => new Set(words(t))),
}
const ask = (q: Partial<Query>, summary?: Map<string, Set<number>>) => answer({ ...EMPTY, ...q }, ctx, summary)
const titles = (hs: { u: number }[]) => hs.map((h) => DOCS.title[h.u])

describe('decode', () => {
  it('reads each unit its parts back, and each part its units', () => {
    expect([...finder.used.subarray(finder.usedAt[0]!, finder.usedAt[1]!)]).toEqual([1, 7])
    expect([...finder.named.subarray(finder.namedAt[0]!, finder.namedAt[1]!)]).toEqual([2])
    expect([...finder.units.subarray(finder.unitsAt[1]!, finder.unitsAt[2]!)]).toEqual([0, 5])   // 2N3904
    expect([...finder.units.subarray(finder.unitsAt[8]!, finder.unitsAt[9]!)]).toEqual([1, 6])   // TL072, used and named
  })
  it('knows the files belong together only when every stamp agrees', () => {
    expect(sameBuild(UNITS, DOCS, INDEX)).toBe(true)
    expect(sameBuild(UNITS, DOCS, { ...INDEX, partsStamp: 'p2' })).toBe(false)
    expect(sameBuild(UNITS, { ...DOCS, findStamp: 'f2' }, INDEX)).toBe(false)
  })
})

describe('familyStates', () => {
  it('answers each part three ways, and says when nothing knows', () => {
    const jfet = familyStates(INDEX, FAMILIES, ['jfet'])
    expect([jfet[2], jfet[3], jfet[1], jfet[4]]).toEqual([IS, MIGHT, NOT, UNKNOWN])
    const opamp = familyStates(INDEX, FAMILIES, ['opamp'])
    expect([opamp[8], opamp[0]]).toEqual([IS, NOT])
  })
})

describe('coverage', () => {
  it('counts a grade or package of a type as the type, and the type against a grade as a maybe', () => {
    const { level } = coverage(INDEX, finder, ['BC547B', 'TL072CP'], 'same')
    expect(level[6]).toBe(EXACT)
    expect(level[5]).toBe(SAME)       // BC547B covers a sheet asking for BC547
    expect(level[7]).toBe(NONE)       // BC547B is not BC547C: a sibling grade
    expect(level[8]).toBe(SAME)       // TL072CP covers TL072
    expect(coverage(INDEX, finder, ['BC547'], 'same').level[7]).toBe(GRADE)
    expect(coverage(INDEX, finder, ['BC547B'], 'exact').level[5]).toBe(NONE)
  })
  it('counts a substitute a document names only from that strictness, only the way the relation runs', () => {
    expect(coverage(INDEX, finder, ['LSK170'], 'same').level[10]).toBe(NONE)
    const sub = coverage(INDEX, finder, ['LSK170'], 'substitute')
    expect(sub.level[10]).toBe(SUBST)                                    // LSK170 does for a 2SK170
    expect(sub.by.get(10)?.rel?.[1]).toBe('replacement_for')
    expect(coverage(INDEX, finder, ['2SK170'], 'substitute').level[11]).toBe(NONE)   // and not back
    expect(coverage(INDEX, finder, ['ECC83'], 'substitute').level[0]).toBe(SUBST)    // the same product, either way
    expect(coverage(INDEX, finder, ['12AX7'], 'substitute').level[13]).toBe(SUBST)
  })
  it('says a part in the same data sheet beside the one asked for, and never counts it', () => {
    const c = coverage(INDEX, finder, ['TL072'], 'similar')
    expect(c.level[12]).toBe(NONE)
    expect(c.hints.get(12)).toEqual(['TL072'])
  })
})

describe('answer', () => {
  it('asks nothing until there is something to ask', () => {
    expect(asked(EMPTY)).toBe(false)
    expect(ask({}).hits).toEqual([])
  })
  it('finds the units every part asked for is on', () => {
    expect(titles(ask({ need: ['2N3904'] }).hits)).toEqual(['Fuzz Face clone', 'Mystery box'])
    expect(titles(ask({ need: ['2N3904', '4580M'] }).hits)).toEqual(['Mystery box'])
    expect(ask({ need: ['XYZ123'] }).hits).toEqual([])
  })
  it('ranks by what is missing from what the reader has, and can keep only what is buildable', () => {
    const a = ask({ have: ['2N3904', 'BC547C', '12AX7'] })
    expect(titles(a.hits)).toEqual(['Fuzz Face clone', 'Bassman preamp', 'Mystery box'])
    expect(a.hits.map((h) => h.missing)).toEqual([1, 1, 1])                 // the fuzz names a 2N5457
    expect(titles(ask({ have: ['2N3904', 'BC547C', '12AX7'], discount: true, miss: 0 }).hits)).toEqual(['Fuzz Face clone'])
  })
  it('leaves out a family only where nothing might be one, and sets the doubtful apart with the reason', () => {
    const a = ask({ need: ['2N3904'], nofam: ['jfet'] })
    expect(titles(a.hits)).toEqual([])
    expect(titles(a.maybe)).toEqual(['Fuzz Face clone', 'Mystery box'])    // names a 2N5457; 4580M nobody knows
    expect(a.maybe[0]!.doubt).toEqual([2])
    expect(a.maybe[1]!.doubt).toEqual([4])
    const b = ask({ fam: ['transistor'], nofam: ['opamp'] })
    expect(titles(b.hits)).toEqual(['Fuzz Face clone', 'JFET buffer'])
    expect(titles(b.maybe)).toEqual(['Mystery box', 'Mag 1975-02'])        // 4580M; an op-amp on the next page
  })
  it('reads the page after with a page of an issue, since an article runs on', () => {
    const a = ask({ need: ['BC547B'], nofam: ['opamp'] })
    expect(a.hits).toEqual([])
    expect(a.maybe[0]!.nextDoor).toEqual([9])                               // TL072CP on page 2
  })
  it('finds a word of the title as the index spells it, its plural, or what a stem starts', () => {
    const t = new Set(words('Crybaby Wah-wah pedals, 5F6-A'))
    expect([termOf('Wah'), termOf('5F6-A'), termOf('pedal*')]).toEqual(['wah', '5f6a', 'pedal*'])
    expect([holds(t, 'wah'), holds(t, 'wahwah'), holds(t, 'pedal'), holds(t, '5f6a'), holds(t, 'ped*'), holds(t, 'wa')])
      .toEqual([true, true, true, true, true, false])
    expect(fold('Señal')).toBe('senal')
  })
  it('finds words in titles and summaries, the title first, and either ranks or requires them', () => {
    expect(titles(ask({ words: ['fuzz'] }).hits)).toEqual(['Fuzz Face clone'])
    const said = new Map([['buffer', new Set([2, 5])]])
    expect(titles(ask({ words: ['buffer'] }, said).hits)).toEqual(['JFET buffer', 'Mystery box'])   // the title first
    expect(titles(ask({ words: ['buffer'], summaries: false }, said).hits)).toEqual(['JFET buffer'])
    expect(titles(ask({ have: ['12AX7', '2N3904'], words: ['bassman'] }).hits)[0]).toBe('Bassman preamp')
    expect(titles(ask({ have: ['12AX7', '2N3904'], words: ['bassman'], require: true }).hits)).toEqual(['Bassman preamp'])
  })
  it('keeps to the sources, types of document and eras asked for', () => {
    expect(titles(ask({ fam: ['bjt'], dropped: new Set(['esp']) }).hits)).toEqual(['Mag 1975-02'])
    expect(titles(ask({ fam: ['bjt'], roles: new Set(['issue']) }).hits)).toEqual(['Mag 1975-02'])
    expect(titles(ask({ fam: ['bjt'], eras: new Set(['mixed']) }).hits)).toEqual(['Fuzz Face clone', 'Mystery box'])
  })
  it('passes over a unit that only names or advertises the parts', () => {
    expect(titles(ask({ need: ['TL072'] }).hits)).toEqual(['Bassman preamp'])
  })
  it('leaves out a unit that uses a part left out', () => {
    expect(titles(ask({ need: ['2N3904'], out: ['4580M'] }).hits)).toEqual(['Fuzz Face clone'])
  })
})

describe('parts as typed', () => {
  it('reads a pasted list, quantities and all', () => {
    expect(pasted('2x TL072\nBC547B, 1N4148 ×3\n12AX7 ECC83; 3 pcs')).toEqual(['TL072', 'BC547B', '1N4148', '12AX7', 'ECC83'])
  })
  it('spells a name the way the index does, and says when the index does not hold it', () => {
    const r = resolver(INDEX)
    expect(r('tl072')).toEqual({ name: 'TL072', known: true })
    expect(r('bc-547b')).toEqual({ name: 'BC547B', known: true })
    expect(r('ne5532')).toEqual({ name: 'NE5532', known: false })
  })
})

describe('the address', () => {
  it('writes the question and reads it back, leaving other parameters alone', () => {
    const q: Query = { ...EMPTY, need: ['TL072', 'ADC121C027CIMK/NOPB'], nofam: ['jfet'], words: ['wah', 'fender'], require: true, summaries: false,
      dropped: new Set(['mag/1970s']), roles: new Set(['issue']), eras: new Set(['modern']), tier: 'exact', miss: 1, sort: 'newest',
      have: ['BC547B'] }
    const s = writeQuery('?x=1', q)
    expect(s.startsWith('?x=1&find')).toBe(true)
    expect(s).not.toContain('have=')                                           // what the reader has stays theirs
    const back = readQuery(s)
    expect(back.need).toEqual(['TL072', 'ADC121C027CIMK/NOPB'])
    expect([back.nofam, back.words, back.require, back.summaries, [...back.dropped], [...back.roles!], back.tier, back.miss, back.sort])
      .toEqual([['jfet'], ['wah', 'fender'], true, false, ['mag/1970s'], ['issue'], 'exact', 1, 'newest'])
    expect(readQuery(writeQuery('', q, true)).shared).toEqual(['BC547B'])
    expect(readQuery('?find').miss).toBe(Infinity)
  })
})
