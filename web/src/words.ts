/**
 * The words of a text as the Projects tab looks them up: the other half of
 * `src/spicy_electronics_index/core/words.py`, held to the same cases by `tests/fixtures/words_cases.json`.
 *
 * The build keeps, for each word of the summaries, which units it is on, split by the word's first two
 * letters (`find/w/<xx>.json.gz`); a search fetches the splits its words fall in, once each.
 */
import { DATA, jsonMaybeGzip } from './data'

const STOP = new Set(`
a an and are as at be been but by for from has have in into is it its near next not of on or so than that the
their then there these this those to two used uses using was were where which while with within without also
one three part parts page pages shown labelled labeled listed list located positioned beside appears appearing
`.split(/\s+/).filter(Boolean))
const DESIGNATOR = /^(?:r|c|q|d|l|t|u|v|j|k|p|s|f|x|ic|tr|vr|rv|sw|led|zd|tp|cn|fb|jp|rl)\d{1,4}[a-z]?$/
const VALUE = /^\d+(?:[kmrunp]\d*|uf|nf|pf|v|w|ma|mv|hz|khz|mhz|db|ohms?)$/
const HYPHENED = /[a-z0-9]+(?:-[a-z0-9]+)+/g

/** Lower case, accents off: what a reader types. */
export function foldText(text: string): string {
  return text.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

function kept(w: string): boolean {
  if (w.length < 2 || STOP.has(w)) return false
  if (/^\d+$/.test(w)) return w.length >= 4
  return !DESIGNATOR.test(w) && !VALUE.test(w)
}

/** The words of `text` the index keeps, each once, in the order they come. */
export function words(text: string): string[] {
  const t = foldText(text)
  const out: string[] = []
  for (const m of t.matchAll(HYPHENED)) {
    const joined = m[0].replace(/-/g, '')
    if (kept(joined) && !out.includes(joined)) out.push(joined)
  }
  for (const w of t.split(/[^a-z0-9]+/)) if (kept(w) && !out.includes(w)) out.push(w)
  return out
}

/** Which split of the index a word is in. */
export const shardOf = (word: string) => word.slice(0, 2)

/**
 * The splits a term needs, of those the build wrote (`FinderUnits.shards`): its first two letters, or three
 * where two made a split too big; for a stem with a star, every split a word it starts can be in.
 */
export function keysFor(term: string, keys: string[]): string[] {
  if (term.endsWith('*')) {
    const stem = term.slice(0, -1)
    return stem.length < 2 ? [] : keys.filter((k) => k.startsWith(stem) || stem.startsWith(k))
  }
  const three = term.slice(0, 3)
  const key = three.length === 3 && keys.includes(three) ? three : term.slice(0, 2)
  return keys.includes(key) ? [key] : []
}

/** One split: each word's units as the first and then the steps between them, built with one finder. */
export interface WordShard { findStamp: string; words: Record<string, number[]> }

const shards = new Map<string, Promise<WordShard | null>>()

/** A split of the index, fetched once; null when there is none or it cannot be had. */
export function loadShard(key: string, stamp: string): Promise<WordShard | null> {
  const id = `${stamp}/${key}`
  let p = shards.get(id)
  if (!p) {
    p = fetch(`${DATA}/find/w/${encodeURIComponent(key)}.json.gz?ss=${encodeURIComponent(stamp)}`)
      .then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(r.status)))
      .then((b) => jsonMaybeGzip(b) as Promise<WordShard>)
      .catch(() => null)
    shards.set(id, p)
  }
  return p
}

/**
 * The units a word of the search is on, from its split: the word itself and its plural, or every word it
 * starts when it ends in `*` (wah* finds wah and wahwah).
 */
export function unitsOfWord(shard: WordShard, word: string): Set<number> {
  const stem = word.endsWith('*') ? word.slice(0, -1) : null
  const out = new Set<number>()
  for (const [w, steps] of Object.entries(shard.words)) {
    if (stem !== null ? w.startsWith(stem) : w === word || w === `${word}s` || w === `${word}es`) {
      let at = 0
      for (const s of steps) { at += s; out.add(at) }
    }
  }
  return out
}
