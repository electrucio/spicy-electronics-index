/**
 * The usage filter above the parts list: which sources a part's usages are counted from.
 *
 * The index counts every document the site shows; a reader after what Elektor printed in the 1980s, or
 * what is on GitHub, wants the list counted from those alone. The build writes each part's documents
 * by facet (`usages.json`, `web/parts.py: usage_facets`), and this narrows the rows with it: a part's
 * usages become the sum over the kept facets, and a part with none left leaves the list.
 */
import type { PartIndex, PartRow, UsageFacet, Usages } from './types'

/** A part's usages by facet, as `usages.json` holds them. */
export type Used = [number, number][]

/** Each part's row of the usages file, by part — when the file was built with this index. */
export function usedBy(index: PartIndex, usages: Usages): Map<string, Used> | null {
  if (usages.parts.length !== index.parts.length) return null
  if (index.sourcesStamp && usages.sourcesStamp && index.sourcesStamp !== usages.sourcesStamp) return null
  // one part added and another dropped keeps the length and moves every row between them
  if (index.partsStamp && usages.partsStamp && index.partsStamp !== usages.partsStamp) return null
  return new Map(index.parts.map((r, i) => [r[0], usages.parts[i] ?? []]))
}

/**
 * The rows counted from the kept facets only, in their order: the usages column becomes that count, and
 * a row left with none is dropped. `dropped` names the facets left out, by key, so a choice survives the
 * file being fetched again.
 */
export function narrow(rows: PartRow[], used: Map<string, Used>, facets: UsageFacet[], dropped: Set<string>): PartRow[] {
  if (dropped.size === 0) return rows
  const out: PartRow[] = []
  for (const r of rows) {
    let docs = 0
    for (const [f, n] of used.get(r[0]) ?? []) {
      const key = facets[f]?.key
      if (key !== undefined && !dropped.has(key)) docs += n
    }
    if (docs > 0) out.push([r[0], docs, ...r.slice(2)] as PartRow)
  }
  return out
}

/** One source of the menu: its facets, in order — a magazine's decades, the books' titles, or the one facet a site is. */
export type SourceEntry = { source: string; group: UsageFacet['group']; facets: UsageFacet[]; n: number }

/** The menu by group and source, in the file's order, which is the page's. */
export function menu(facets: UsageFacet[]): Record<UsageFacet['group'], SourceEntry[]> {
  const out: Record<UsageFacet['group'], SourceEntry[]> = { projects: [], paper: [], github: [] }
  for (const f of facets) {
    const list = out[f.group]
    const last = list[list.length - 1]
    if (last && last.source === f.source) { last.facets.push(f); last.n += f.n }
    else list.push({ source: f.source, group: f.group, facets: [f], n: f.n })
  }
  return out
}

/** `dropped` with these facets all left out, or all kept: a source's checkbox, or a group's "all" and "none". */
export function toggled(dropped: Set<string>, keys: string[], keep: boolean): Set<string> {
  const next = new Set(dropped)
  for (const k of keys) {
    if (keep) next.delete(k)
    else next.add(k)
  }
  return next
}
