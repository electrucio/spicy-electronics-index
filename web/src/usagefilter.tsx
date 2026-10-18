/**
 * The filter above the parts list: which sources a part's usages are counted from.
 *
 * Folded to one line until asked for, because the list is what the column is for. Open, it is the page's
 * three groups — what somebody built, what a magazine or a book printed (each by decade, folded under its
 * name), and GitHub — each source with a box and how many documents the site shows from it. Its data is
 * fetched the first time it is opened (`usages.json`, 170 KB gzipped).
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

function Source({ s, dropped, setDropped }: { s: SourceEntry; dropped: Set<string>; setDropped: (d: Set<string>) => void }) {
  const keys = s.facets.map((f) => f.key)
  const name = s.source === 'github' ? 'GitHub' : s.source
  const dated = s.facets.length > 1 || !!s.facets[0]?.decade
  const label = <><span class="srcname">{name}</span><span class="count">{n(s.n)}</span></>
  if (!dated) return <Box keys={keys} dropped={dropped} setDropped={setDropped} label={label} />
  const kept = s.facets.filter((f) => !dropped.has(f.key)).length
  return (
    <details class="decades">
      <summary>
        <Box keys={keys} dropped={dropped} setDropped={setDropped} label={label} />
        <span class="count" aria-hidden="true">{kept === s.facets.length ? 'by decade' : `${kept} of ${s.facets.length} decades`}</span>
      </summary>
      <div class="decadelist">
        {s.facets.map((f) => (
          <Box key={f.key} keys={[f.key]} dropped={dropped} setDropped={setDropped}
            label={<><span class="srcname">{f.decade ?? 'undated'}</span><span class="count">{n(f.n)}</span></>} />
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
