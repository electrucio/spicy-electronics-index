/**
 * The filter above the parts list: which sources a part's usages are counted from.
 *
 * Folded to one line until asked for, because the list is what the column is for. Open, it is the page's
 * three groups — what somebody built, what a magazine or a book printed (a magazine by decade and the
 * books by title, folded under the name), and GitHub — each source with a box and how many times parts
 * are written in it, which is what the Usages column counts. Its data is fetched the first time it is
 * opened (`usages.json`, 170 KB gzipped).
 */
import { useEffect, useRef, useState } from 'preact/hooks'

import { Loading } from './loading'
import { n } from './parts'
import { menu, toggled, type SourceEntry } from './usages'
import type { UsageFacet, Usages } from './types'

const GROUPS: { key: UsageFacet['group']; title: string }[] = [
  { key: 'projects', title: 'Projects and factory schematics' },
  { key: 'paper', title: 'Magazines and books' },
  { key: 'github', title: 'Open-source projects' },
]

/** A box that is checked when every key is kept, blank when none is, and in between when some are. */
function Box({ keys, dropped, setDropped, label, title }: {
  keys: string[]; dropped: Set<string>; setDropped: (d: Set<string>) => void; label: preact.ComponentChildren; title?: string
}) {
  const out = keys.filter((k) => dropped.has(k)).length
  const all = out === 0
  const ref = useRef<HTMLInputElement>(null)
  useEffect(() => { if (ref.current) ref.current.indeterminate = out > 0 && out < keys.length }, [out, keys.length])
  return (
    <label class="srcbox" title={title}>
      <input ref={ref} type="checkbox" checked={all} onChange={() => setDropped(toggled(dropped, keys, !all))} />
      {label}
    </label>
  )
}

/** The count beside an entry: how many times parts are written under it, as the column counts; hover for the documents. */
function Count({ f }: { f: { n: number; docs?: number } }) {
  return <span class="count" title={f.docs === undefined ? undefined : `written ${n(f.n)} times in ${n(f.docs)} ${f.docs === 1 ? 'document' : 'documents'}`}>{n(f.n)}</span>
}

function Source({ s, dropped, setDropped }: { s: SourceEntry; dropped: Set<string>; setDropped: (d: Set<string>) => void }) {
  const keys = s.facets.map((f) => f.key)
  const name = s.source === 'github' ? 'GitHub' : s.source
  // a source in parts: a magazine by decade, the books by title
  const by = s.facets.find((f) => f.by)?.by
  const docs = s.facets.some((f) => f.docs === undefined) ? undefined : s.facets.reduce((t, f) => t + (f.docs ?? 0), 0)
  const label = <><span class="srcname">{name}</span><Count f={{ n: s.n, docs }} /></>
  if (!by) return <Box keys={keys} dropped={dropped} setDropped={setDropped} label={label} />
  const kept = s.facets.filter((f) => !dropped.has(f.key)).length
  const what = by === 'decade' ? 'decades' : 'titles'
  return (
    <details class="decades">
      <summary>
        <Box keys={keys} dropped={dropped} setDropped={setDropped} label={label} />
        <span class="count" aria-hidden="true">{kept === s.facets.length ? `by ${by}` : `${kept} of ${s.facets.length} ${what}`}</span>
      </summary>
      <div class="decadelist">
        {s.facets.map((f) => (
          <Box key={f.key} keys={[f.key]} dropped={dropped} setDropped={setDropped} title={f.label}
            label={<><span class="srcname">{f.label ?? 'undated'}</span><Count f={f} /></>} />
        ))}
      </div>
    </details>
  )
}

export function UsageFilter({ usages, stale, dropped, setDropped, onOpen }: {
  /** The filter's data, once fetched; `stale` when what came is from another build than the index. */
  usages: Usages | null; stale: boolean
  dropped: Set<string>; setDropped: (d: Set<string>) => void
  /** Called the first time the filter is opened, to fetch its data. */
  onOpen: () => void
}) {
  const [open, setOpen] = useState(false)
  const facets = usages?.facets ?? []
  const groups = menu(facets)
  const kept = facets.length - facets.filter((f) => dropped.has(f.key)).length
  const every = facets.map((f) => f.key)
  return (
    <details class="srcfilter" open={open}
      onToggle={(e) => { const o = (e.target as HTMLDetailsElement).open; setOpen(o); if (o) onOpen() }}>
      <summary>
        <span>Usage sources</span>
        <span class="count">
          {dropped.size === 0 ? 'all' : usages ? `${n(kept)} of ${n(facets.length)}` : `${n(dropped.size)} left out`}
        </span>
      </summary>
      <div class="srcbody">
        {!usages && <Loading what="the list of sources" inline />}
        {usages && stale && (
          <p class="muted small">
            The sources cannot be listed: this list and the parts list come from two different builds of the
            site. Reload the page in a few minutes.
          </p>
        )}
        {usages && !stale && facets.length === 0 && <p class="muted small">No usage is published yet.</p>}
        {usages && !stale && facets.length > 0 && (
          <>
            <p class="small muted srchelp">
              Count usages from the ticked sources only; a part with none left leaves the list.
              {' '}<button type="button" class="linkish" onClick={() => setDropped(new Set())}>all</button>
              {' · '}<button type="button" class="linkish" onClick={() => setDropped(new Set(every))}>none</button>
            </p>
            {GROUPS.map((g) => groups[g.key].length > 0 && (
              <div class="srcgroup" key={g.key}>
                <div class="srchead">
                  <Box keys={groups[g.key].flatMap((s) => s.facets.map((f) => f.key))} dropped={dropped} setDropped={setDropped}
                    label={<strong>{g.title}</strong>} title="every source of the group" />
                </div>
                {groups[g.key].map((s) => <Source key={s.source} s={s} dropped={dropped} setDropped={setDropped} />)}
              </div>
            ))}
          </>
        )}
      </div>
    </details>
  )
}
