/**
 * The Projects tab's engine: which documents use these parts together and none of those.
 *
 * `find/units.json.gz` (`web/finder.py`) holds every document the site shows as a unit — one document, or a
 * page of a magazine issue or a book — with the parts read on it as rows of `parts.json`. Everything here
 * is a pure function of that file, the parts index, the catalogue's families and the reader's question,
 * so the page only draws what this computes.
 *
 * A family a reader leaves out is answered three ways for each part — it is one, it might be one, or
 * nothing says — because a JEDEC number could be a transistor or a JFET, and 23 % of the parts have no
 * family at all. Only a unit with no part that is or might be one is listed as without it; the others are
 * set apart with the reason, since a wrong answer here is a circuit the reader cannot build.
 */
import type { Family, FinderDocs, FinderUnits, PartIndex } from './types'
import { foldText, words as wordsOf } from './words'

/** Flags of a unit (`finder.py`). */
export const SCHEMATIC = 1
export const AFTER = 2
/** The kinds of use, as bits of a unit's mask; the bit after them is a use not summarised yet. */
export const NAMED_ONLY_MASK = 0b11000   // mention, advert

export interface Finder {
  n: number
  role: Int8Array
  flags: Uint8Array
  kinds: Uint8Array
  year: Uint16Array
  page: Uint16Array
  facet: Int16Array
  more: Map<number, number[]>
  /** A unit's parts used on it, then those it only names, as rows of `parts.json`: `used[usedAt[u]..usedAt[u+1]]`. */
  usedAt: Int32Array
  used: Int32Array
  namedAt: Int32Array
  named: Int32Array
  /** Each part's units, used or named: `units[unitsAt[p]..unitsAt[p+1]]`, in order. */
  unitsAt: Int32Array
  units: Int32Array
  /** For "what I have": the types a part is a grade or package of, and the makers' names that are it. */
  up: Map<string, string[]>
  alias: Map<string, string[]>
  /** The same two read backwards: the variants of a type, the bare numbers a maker's name answers for. */
  down: Map<string, string[]>
  aliasOf: Map<string, string[]>
  /** What documents say one part is to another, and what each relation is worth (`catalogue.COVERAGE`). */
  relations: Relation[]
  policy: Record<string, [string, string]>
}

/** [part, relation, other, refs, note, status], as `data/parts/relations.csv` has it. */
export type Relation = [string, string, string, string[], string, string]

function runs(lengths: number[], steps: number[]): [Int32Array, Int32Array] {
  const at = new Int32Array(lengths.length + 1)
  const ids = new Int32Array(steps.length)
  let k = 0
  lengths.forEach((len, u) => {
    at[u] = k
    let prev = 0
    for (let j = 0; j < len; j++, k++) {
      prev += steps[k] ?? 0
      ids[k] = prev
    }
  })
  at[lengths.length] = k
  return [at, ids]
}

function backwards(m: Record<string, string[]>): Map<string, string[]> {
  const out = new Map<string, string[]>()
  for (const [k, vs] of Object.entries(m)) for (const v of vs) out.set(v, [...(out.get(v) ?? []), k])
  return out
}

/** The file as arrays a query can run over fast, with each part's units beside each unit's parts. */
export function decode(f: FinderUnits, partCount: number): Finder {
  const u = f.units
  const n = u.role.length
  const [usedAt, used] = runs(u.used, u.usedIds)
  const [namedAt, named] = runs(u.named, u.namedIds)
  const count = new Int32Array(partCount + 1)
  for (const p of used) count[p + 1]!++
  for (const p of named) count[p + 1]!++
  for (let p = 0; p < partCount; p++) count[p + 1]! += count[p]!
  const unitsAt = count.slice()
  const units = new Int32Array(used.length + named.length)
  const fill = count.slice(0, partCount)
  for (let i = 0; i < n; i++) {
    for (let k = usedAt[i]!; k < usedAt[i + 1]!; k++) units[fill[used[k]!]!++] = i
    for (let k = namedAt[i]!; k < namedAt[i + 1]!; k++) units[fill[named[k]!]!++] = i
  }
  return {
    n, role: Int8Array.from(u.role), flags: Uint8Array.from(u.flags), kinds: Uint8Array.from(u.kinds),
    year: Uint16Array.from(u.year), page: Uint16Array.from(u.page), facet: Int16Array.from(u.facet),
    more: new Map(Object.entries(f.moreFacets).map(([k, v]) => [Number(k), v])),
    usedAt, used, namedAt, named, unitsAt, units,
    up: new Map(Object.entries(f.up)), alias: new Map(Object.entries(f.alias)),
    down: backwards(f.up), aliasOf: backwards(f.alias),
    relations: f.relations ?? [], policy: f.coverage ?? {},
  }
}

/** Whether the finder and the index were built together: the same parts, in the same rows. */
export function sameBuild(f: FinderUnits, d: FinderDocs, index: PartIndex): boolean {
  return f.findStamp === d.findStamp && d.title.length === f.units.role.length
    && (!index.partsStamp || index.partsStamp === f.partsStamp)
    && (!index.sourcesStamp || index.sourcesStamp === f.sourcesStamp)
}

/* --- parts as a reader types them --------------------------------------------------------------------- */

export const squash = (s: string) => s.toUpperCase().replace(/[^A-Z0-9]/g, '')

/** A part name as the index spells it, by its exact name and then ignoring case and punctuation; or the name
 *  as typed, upper-cased, when the index does not hold it. */
export function resolver(index: PartIndex): (name: string) => { name: string; known: boolean } {
  const exact = new Set(index.parts.map((r) => r[0]))
  const loose = new Map<string, string>()
  for (const r of [...index.parts].sort((a, b) => b[1] - a[1])) {
    const k = squash(r[0])
    if (!loose.has(k)) loose.set(k, r[0])
  }
  return (raw) => {
    const t = raw.trim()
    if (exact.has(t)) return { name: t, known: true }
    if (exact.has(t.toUpperCase())) return { name: t.toUpperCase(), known: true }
    const hit = loose.get(squash(t))
    return hit ? { name: hit, known: true } : { name: t.toUpperCase(), known: false }
  }
}

/** The part names in a pasted list: one per line, or separated by commas, semicolons, tabs or spaces, with
 *  quantities ("2x TL072", "TL072 ×2", "3 pcs") left out. */
export function pasted(text: string): string[] {
  const out: string[] = []
  for (const line of text.split(/[\n\r,;\t]+/)) {
    const clean = line.replace(/\b\d+\s*(?:x|×|pcs?\.?|pieces?)(?=\s|$)/gi, ' ').replace(/(?:^|\s)[x×]\s*\d+\b/gi, ' ')
    for (const t of clean.split(/\s+/)) {
      if (/^[A-Za-z0-9][A-Za-z0-9/+.-]{1,30}$/.test(t) && /\d/.test(t) && !out.includes(t)) out.push(t)
    }
  }
  return out
}

/* --- families -------------------------------------------------------------------------------------- */

export const NOT = 0, MIGHT = 1, IS = 2, UNKNOWN = 3
export type FamilyState = typeof NOT | typeof MIGHT | typeof IS | typeof UNKNOWN

/** The family and every family above it, nearest first. */
export function lineage(id: string, byId: Map<string, Family>): string[] {
  const out: string[] = []
  let at: string | undefined = id
  while (at && byId.has(at) && !out.includes(at)) {
    out.push(at)
    at = byId.get(at)?.broader
  }
  return out
}

/**
 * Each part's answer to "is it one of these families": IS when its family sits inside one of them, MIGHT
 * when its family is above one of them (a part filed as a transistor might be a JFET), UNKNOWN when nothing
 * gives it a family, NOT otherwise. One byte per row of `parts.json`.
 */
export function familyStates(index: PartIndex, families: Family[], targets: string[]): Uint8Array {
  const byId = new Map(families.map((f) => [f.id, f]))
  const ids = index.families ?? []
  const per = ids.map((fid) => {
    const up = lineage(fid, byId)
    if (targets.some((t) => up.includes(t))) return IS
    if (targets.some((t) => lineage(t, byId).includes(fid))) return MIGHT
    return NOT
  })
  const out = new Uint8Array(index.parts.length)
  index.parts.forEach((r, i) => {
    const f = r.length > 5 ? (r[5] as number) : -1
    out[i] = f < 0 ? UNKNOWN : per[f] ?? UNKNOWN
  })
  return out
}

/* --- what the reader has -------------------------------------------------------------------------- */

/** How a part a document asks for is covered by what the reader has, strongest first. */
export const NONE = 0, GRADE = 1, SUBST = 2, SAME = 3, EXACT = 4
export type Cover = typeof NONE | typeof GRADE | typeof SUBST | typeof SAME | typeof EXACT
/** How much the reader counts as theirs, each taking in the one before: the same number; its grades, packages
 *  and makers' names; a substitute a document names; a part like it by the data sheets. */
export const TIERS = ['exact', 'same', 'substitute', 'similar'] as const
export type Tier = typeof TIERS[number]

/** Why a part counts as had: the part the reader has, and the relation that says so when one does. */
export interface Because { from: string; rel?: Relation }

/**
 * Each row of `parts.json` covered by the parts the reader has, and by which of them. EXACT: the part itself.
 * SAME: a grade, package or packing of it the reader has (BC547B covers a sheet asking for BC547), or a
 * maker's name for it (MC7812 for 7812, and the other way). SUBST: a part a document names as standing for
 * it, the way the relation counts (`catalogue.COVERAGE`): LSK170 for 2SK170 and not back, ECC83 and 12AX7
 * either way. GRADE: the reader has the type, and the sheet asks for one grade of it (BC547 against BC547C):
 * it may do, and the result says so. A sibling grade, or a part in the same data sheet, covers nothing; the
 * second is said as a hint. Nothing is chained: a replacement for a replacement is not one.
 */
export function coverage(index: PartIndex, f: Finder, have: string[], tier: Tier):
  { level: Uint8Array; by: Map<number, Because>; hints: Map<number, string[]> } {
  const row = new Map(index.parts.map((r, i) => [r[0], i]))
  const level = new Uint8Array(index.parts.length)
  const by = new Map<number, Because>()
  const hints = new Map<number, string[]>()
  const mark = (name: string, l: Cover, because: Because) => {
    const i = row.get(name)
    if (i === undefined || level[i]! >= l) return
    level[i] = l
    by.set(i, because)
  }
  const rank = TIERS.indexOf(tier)
  const owned = new Set(have)
  for (const x of have) {
    mark(x, EXACT, { from: x })
    if (rank < 1) continue
    for (const t of f.up.get(x) ?? []) mark(t, SAME, { from: x })
    for (const t of f.alias.get(x) ?? []) mark(t, SAME, { from: x })
    for (const t of f.aliasOf.get(x) ?? []) mark(t, SAME, { from: x })
    for (const t of f.down.get(x) ?? []) mark(t, GRADE, { from: x })
  }
  // A hint names a group: one data sheet for several parts, whose rows all name the sheet's first part with
  // the same reference. Every member the reader has is said beside the others. Linear in the relations,
  // which a comparison of data sheets will make many.
  const groups = new Map<string, Set<string>>()
  for (const rel of f.relations) {
    const [part, relation, other, refs] = rel
    const [way, from] = f.policy[relation] ?? ['', 'hint']
    if (from === 'hint') {
      const key = `${relation}|${other}|${refs.join(' ')}`
      groups.set(key, (groups.get(key) ?? new Set([other])).add(part))
      continue
    }
    if (TIERS.indexOf(from as Tier) < 0 || rank < TIERS.indexOf(from as Tier)) continue
    if (owned.has(part)) mark(other, SUBST, { from: part, rel })
    if (way === 'both' && owned.has(other)) mark(part, SUBST, { from: other, rel })
  }
  for (const members of groups.values()) {
    const mine = [...members].filter((m) => owned.has(m))
    if (!mine.length) continue
    for (const m of members) {
      const i = row.get(m)
      if (i !== undefined && !owned.has(m)) hints.set(i, [...new Set([...(hints.get(i) ?? []), ...mine])])
    }
  }
  return { level, by, hints }
}

/* --- the question ------------------------------------------------------------------------------------ */

export type Sort = 'best' | 'missing' | 'newest' | 'oldest'

export interface Query {
  have: string[]
  need: string[]
  out: string[]
  fam: string[]
  nofam: string[]
  words: string[]
  require: boolean
  /** look for the words in the summaries too, not only in the titles */
  summaries: boolean
  dropped: Set<string>
  roles: Set<string> | null
  eras: Set<string> | null
  tier: Tier
  miss: number
  discount: boolean
  sort: Sort
}

export const EMPTY: Query = {
  have: [], need: [], out: [], fam: [], nofam: [], words: [], require: false, summaries: true, dropped: new Set(),
  roles: null, eras: null, tier: 'same', miss: Infinity, discount: false, sort: 'best',
}

export function asked(q: Query): boolean {
  return q.have.length + q.need.length + q.fam.length + q.words.length > 0
}

/** What one unit came to. */
export interface Hit {
  u: number
  /** parts it asks for that the reader lacks, has, has the type of only; and words found in its title */
  missing: number
  have: number
  grade: number
  /** the words found: twice for each in the title, once for each only in a summary; and how many of them */
  words: number
  found: number
  /** why it is only possibly without a family left out: the parts that are or might be one, or that
   *  nothing classifies; and of those, the ones on the page before or after rather than on this one */
  doubt?: number[]
  nextDoor?: number[]
}

export interface Answer {
  hits: Hit[]
  /** units set apart because a part on them is or might be of a family left out, with the reason */
  maybe: Hit[]
  /** how many units passed every filter before "missing at most" */
  total: number
}

/** The words of a title, folded the way a reader types: lower case, no accents. */
export const fold = foldText

/** A word of the search as the index spells it: 5F6-A as 5f6a; a stem keeps its star (wah*). */
export function termOf(word: string): string {
  const star = word.endsWith('*')
  const w = wordsOf(star ? word.slice(0, -1) : word)[0] ?? ''
  return w && star ? `${w}*` : w
}

/** Whether a set of words holds a term: the word or its plural, or for a stem any word it starts. */
export function holds(set: Set<string>, term: string): boolean {
  if (term.endsWith('*')) {
    const stem = term.slice(0, -1)
    for (const w of set) if (w.startsWith(stem)) return true
    return false
  }
  return set.has(term) || set.has(`${term}s`) || set.has(`${term}es`)
}

function intersect(a: Int32Array | number[], b: Set<number>): number[] {
  const out: number[] = []
  for (const x of a) if (b.has(x)) out.push(x)
  return out
}

function unitsOf(f: Finder, part: number): Int32Array {
  return f.units.subarray(f.unitsAt[part]!, f.unitsAt[part + 1]!)
}

export interface Context {
  index: PartIndex
  finder: Finder
  /** each part's row in `parts.json`, by name */
  row: Map<string, number>
  facetKeys: string[]
  roles: string[]
  /** each source's era, by position in `parts.json` sources, and each unit's source */
  eras: string[]
  source: number[]
  families: Family[]
  /** the words of each unit's title and of its other titles (`words.ts`) */
  titleWords: Set<string>[]
}

/**
 * The answer to a question. Candidates come from what narrows most: the units every part asked for is on and
 * that have a part of every family asked for; else the units that use a part the reader has; else every unit
 * (for words alone). Each candidate then passes the filters — sources, type of document, era, the parts and
 * families left out — and is scored: missing parts (fewest first, with "missing at most"), parts had, words.
 * A part a page only names is not one the reader needs: it counts as missing, unless they discount it, and
 * never as had.
 */
export function answer(q: Query, c: Context, summary?: Map<string, Set<number>>): Answer {
  const { index, finder: f, row } = c
  const words = q.words.map(termOf).filter(Boolean)
  const said = q.summaries ? summary : undefined
  const cover = q.have.length ? coverage(index, f, q.have, q.tier) : null
  const fam = q.fam.length ? familyStates(index, c.families, q.fam) : null
  const nofam = q.nofam.length ? familyStates(index, c.families, q.nofam) : null
  const out = new Set(q.out.flatMap((p) => (row.has(p) ? [row.get(p)!] : [])))

  // candidates
  let cand: number[] | null = null
  const narrow = (list: Iterable<number>) => {
    const s = new Set(list)
    cand = cand === null ? [...s].sort((a, b) => a - b) : intersect(cand, s)
  }
  for (const p of q.need) {
    const i = row.get(p)
    if (i === undefined) return { hits: [], maybe: [], total: 0 }
    narrow(unitsOf(f, i))
  }
  if (fam) {
    const s = new Set<number>()
    fam.forEach((st, p) => { if (st === IS) for (const u of unitsOf(f, p)) s.add(u) })
    narrow(s)
  }
  const fromHave = cand === null && cover !== null
  if (fromHave) {
    const s = new Set<number>()
    cover!.level.forEach((l, p) => { if (l !== NONE) for (const u of unitsOf(f, p)) s.add(u) })
    narrow(s)
  }
  if (cand === null) {
    if (!words.length) return { hits: [], maybe: [], total: 0 }
    cand = Array.from({ length: f.n }, (_, i) => i)
  }
  const byPartsToo = cover !== null || q.need.length > 0 || fam !== null

  const hits: Hit[] = []
  const maybe: Hit[] = []
  let total = 0
  for (const u of cand as number[]) {
    // sources, type of document, era
    if (q.dropped.size && [f.facet[u]!, ...(f.more.get(u) ?? [])].every((i) => q.dropped.has(c.facetKeys[i] ?? ''))) continue
    if (q.roles && !q.roles.has(c.roles[f.role[u]!] ?? '')) continue
    if (q.eras && !q.eras.has(c.eras[c.source[u]!] ?? '')) continue
    if (f.kinds[u]! && (f.kinds[u]! & ~NAMED_ONLY_MASK) === 0) continue          // every use only names or sells it
    const usedParts = f.used.subarray(f.usedAt[u]!, f.usedAt[u + 1]!)
    const namedParts = f.named.subarray(f.namedAt[u]!, f.namedAt[u + 1]!)
    if (out.size && usedParts.some((p) => out.has(p))) continue
    let found = 0
    let score = 0
    for (const w of words) {
      if (holds(c.titleWords[u] ?? new Set(), w)) { found++; score += 2 }
      else if (said?.get(w)?.has(u)) { found++; score += 1 }
    }
    if (words.length && (q.require ? found < words.length : found === 0 && !byPartsToo)) continue
    const hit: Hit = { u, missing: 0, have: 0, grade: 0, words: score, found }
    if (cover) {
      for (const p of usedParts) {
        const l = cover.level[p]!
        if (l === EXACT || l === SAME || l === SUBST) hit.have++
        else if (l === GRADE) hit.grade++
        else hit.missing++
      }
      if (!q.discount) for (const p of namedParts) if (cover.level[p] === NONE) hit.missing++
      if (fromHave && hit.have + hit.grade === 0) continue        // it only names a part the reader has
    }
    if (nofam) {
      // A part that is one rules the unit out; one that might be, or that nothing classifies, or that the
      // page only names, sets it apart — and so does one that is one on the page before or after, since
      // an article runs on.
      if (usedParts.some((p) => nofam[p] === IS)) continue
      const doubt = [...usedParts, ...namedParts].filter((p) => nofam[p] !== NOT)
      const next = neighbours(f, u).flatMap((v) => [...f.used.subarray(f.usedAt[v]!, f.usedAt[v + 1]!)])
        .filter((p) => nofam[p] === IS && !doubt.includes(p))
      if (doubt.length || next.length) {
        hit.doubt = [...new Set([...doubt, ...next])]
        if (next.length) hit.nextDoor = [...new Set(next)]
        total++
        if (hit.missing <= q.miss) maybe.push(hit)
        continue
      }
    }
    total++
    if (hit.missing <= q.miss) hits.push(hit)
  }
  const order = sorter(q, f, cover !== null)
  hits.sort(order)
  maybe.sort(order)
  return { hits, maybe, total }
}

/** The pages before and after a page of an issue, when the index holds them. */
export function neighbours(f: Finder, u: number): number[] {
  const out: number[] = []
  if (f.flags[u]! & AFTER) out.push(u - 1)
  if (u + 1 < f.n && f.flags[u + 1]! & AFTER) out.push(u + 1)
  return out
}

/** The order of the results: the one asked for, then fewest missing, most had, most words, drawings first. */
export function sorter(q: Query, f: Finder, owned: boolean): (a: Hit, b: Hit) => number {
  const base = (a: Hit, b: Hit) => (owned ? a.missing - b.missing || b.have - a.have || a.grade - b.grade : 0)
    || b.words - a.words || (f.flags[b.u]! & SCHEMATIC) - (f.flags[a.u]! & SCHEMATIC) || a.u - b.u
  const year = (h: Hit) => f.year[h.u] || 0
  switch (q.sort) {
    case 'newest': return (a, b) => (year(b) - year(a)) || base(a, b)
    case 'oldest': return (a, b) => ((year(a) || 9999) - (year(b) || 9999)) || base(a, b)
    case 'missing': return base
    default: return (a, b) => b.words - a.words || base(a, b)
  }
}

/* --- the address ---------------------------------------------------------------------------------- */

const OURS = ['find', 'need', 'out', 'fam', 'nofam', 'q', 'req', 'sum', 'nosrc', 'role', 'era', 'tier', 'miss', 'sort', 'have', 'all']

const list = (v: string | null) => (v ?? '').split(',').map((s) => s.trim()).filter(Boolean)

/** The question an address asks; nothing it does not understand. `have` is read only from a shared link. */
export function readQuery(search: string): Query & { shared: string[] } {
  const p = new URLSearchParams(search)
  const miss = Number(p.get('miss'))
  const sort = p.get('sort') as Sort | null
  return {
    ...EMPTY,
    need: list(p.get('need')), out: list(p.get('out')), fam: list(p.get('fam')), nofam: list(p.get('nofam')),
    words: list(p.get('q')).flatMap((w) => w.split(/\s+/)).filter(Boolean), require: p.get('req') === '1',
    summaries: p.get('sum') !== '0',
    dropped: new Set(list(p.get('nosrc'))),
    roles: p.get('role') ? new Set(list(p.get('role'))) : null,
    eras: p.get('era') ? new Set(list(p.get('era'))) : null,
    tier: (TIERS as readonly string[]).includes(p.get('tier') ?? '') ? p.get('tier') as Tier : 'same',
    miss: p.has('miss') && Number.isInteger(miss) && miss >= 0 ? miss : Infinity,
    discount: p.get('all') === '0',
    sort: sort && ['best', 'missing', 'newest', 'oldest'].includes(sort) ? sort : 'best',
    shared: list(p.get('have')),
  }
}

/** The address's query with this question in place of the last one; every other parameter kept as written.
 *  The parts the reader has go into it only when `share` says so. */
export function writeQuery(search: string, q: Query, share = false): string {
  const key = (seg: string) => {
    const k = seg.split('=')[0] ?? ''
    try { return decodeURIComponent(k.replace(/\+/g, ' ')) } catch { return k }
  }
  const keep = search.replace(/^\?/, '').split('&').filter((seg) => seg && !OURS.includes(key(seg)))
  const enc = (xs: Iterable<string>) => [...xs].map(encodeURIComponent).join(',')
  keep.push('find')
  if (q.need.length) keep.push(`need=${enc(q.need)}`)
  if (q.out.length) keep.push(`out=${enc(q.out)}`)
  if (q.fam.length) keep.push(`fam=${enc(q.fam)}`)
  if (q.nofam.length) keep.push(`nofam=${enc(q.nofam)}`)
  if (q.words.length) keep.push(`q=${enc(q.words)}`)
  if (q.require) keep.push('req=1')
  if (!q.summaries) keep.push('sum=0')
  if (q.dropped.size) keep.push(`nosrc=${enc([...q.dropped].sort())}`)
  if (q.roles) keep.push(`role=${enc([...q.roles].sort())}`)
  if (q.eras) keep.push(`era=${enc([...q.eras].sort())}`)
  if (q.tier !== 'same') keep.push(`tier=${q.tier}`)
  if (Number.isFinite(q.miss)) keep.push(`miss=${q.miss}`)
  if (q.discount) keep.push('all=0')
  if (q.sort !== 'best') keep.push(`sort=${q.sort}`)
  if (share && q.have.length) keep.push(`have=${enc(q.have)}`)
  return `?${keep.join('&')}`
}
