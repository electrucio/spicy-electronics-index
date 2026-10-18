/**
 * The two files every view may need, fetched once and shared. The search index is 61 KB gzipped and the
 * catalogue a few more; asking twice for either would be the only cost of opening a family page from a
 * part page, so neither is asked twice.
 */
import type { Catalogue, PartIndex, Usages } from './types'

export const DATA = `${import.meta.env.BASE_URL}data`

/**
 * Where a part's files are served from: its page, and its sealed models. The builder writes
 * APT1608LSECK/J3-PRV as part/APT1608LSECK/J3-PRV.json, a file inside a directory, so the request has to
 * say the slash as a slash: a static host (GitHub Pages) does not turn %2F into a directory separator,
 * and 267 parts carry one.
 */
export function partPath(part: string): string {
  return partFile(part).split('/').map(encodeURIComponent).join('/')
}

/**
 * The part's file name, without the extension: the part itself, and when it has lower-case letters a
 * suffix saying which, so that `CORE` and `Core` stay two files on a case-insensitive disk. The other half
 * of `src/spicy_electronics_index/core/partfile.py`; `tests/fixtures/part_files.json` checks both.
 */
export function partFile(part: string): string {
  let mask = 0n
  Array.from(part).forEach((ch, i) => {
    if (ch !== ch.toUpperCase()) mask |= 1n << BigInt(i)
  })
  return mask ? `${part}~${mask.toString(16)}` : part
}

let index: Promise<PartIndex> | null = null
let catalogue: Promise<Catalogue> | null = null

export function loadIndex(): Promise<PartIndex> {
  index ??= fetch(`${DATA}/parts.json`)
    .then((r) => (r.ok ? (r.json() as Promise<PartIndex>) : Promise.reject(r.status)))
    .catch(() => ({ schema: 0, sources: [], kinds: [], deviceKinds: [], parts: [] }))
  return index
}

/** The index again, past every cache, because a part page says it was built against a newer one. The
 *  stamp in the query makes it a different URL for the browser and for the CDN in front of Pages. */
export function reloadIndex(stamp: string): Promise<PartIndex> {
  // If asking again fails, the index already held is kept: an empty one would empty the list.
  const before = index
  index = fetch(`${DATA}/parts.json?ss=${encodeURIComponent(stamp)}`, { cache: 'reload' })
    .then((r) => (r.ok ? (r.json() as Promise<PartIndex>) : Promise.reject(r.status)))
    .catch(() => before ?? { schema: 0, sources: [], kinds: [], deviceKinds: [], parts: [] })
  return index
}

let usages: Promise<Usages> | null = null
const NO_USAGES: Usages = { schema: 0, facets: [], parts: [] }

/** The usage filter's data, fetched the first time the filter is opened: half the index's size again, and
 *  only a reader who narrows the list by source needs it. With `stamp`, asked for again past every cache. */
export function loadUsages(stamp?: string): Promise<Usages> {
  if (stamp || !usages) {
    const before = usages
    usages = fetch(stamp ? `${DATA}/usages.json?ss=${encodeURIComponent(stamp)}` : `${DATA}/usages.json`, stamp ? { cache: 'reload' } : undefined)
      .then((r) => (r.ok ? (r.json() as Promise<Usages>) : Promise.reject(r.status)))
      .catch(() => before ?? NO_USAGES)
  }
  return usages
}

export function loadCatalogue(): Promise<Catalogue> {
  catalogue ??= fetch(`${DATA}/catalogue.json`)
    .then((r) => (r.ok ? (r.json() as Promise<Catalogue>) : Promise.reject(r.status)))
    .catch(() => ({ families: [], makers: {}, schemes: {}, refs: {}, listings: {} }))
  return catalogue
}

/**
 * Move to another view of the site without a reload. The router in main.tsx listens for popstate, so a
 * link anywhere — a family named on a part's page, a maker in a family's — needs only its href.
 */
export function go(href: string) {
  history.pushState({}, '', href)
  dispatchEvent(new PopStateEvent('popstate'))
  scrollTo(0, 0)
}

/** An <a> that follows `go` instead of reloading, and still opens in a new tab when asked. */
export function follow(e: MouseEvent, href: string) {
  if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
  e.preventDefault()
  go(href)
}
