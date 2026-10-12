import { useEffect, useMemo, useState } from 'preact/hooks'

import { Refs, useCatalogue } from './about'
import { follow } from './data'
import { Fold, Section } from './fold'
import type { Catalogue, PartPage, Seller, SellerGroup, SellersList } from './types'

/**
 * Where parts are bought, worldwide: the sellers list of `data/distributors/sellers.yaml`.
 *
 * A part page shows the sellers whose catalogues cover the part's kind, in tiers: the broad distributors
 * and the maker's own store, the specialists for the kind, then the regional shops and the marketplaces
 * folded away. Within a tier the maintainer's priority orders them, then the name — never the country,
 * and never whether a seller lets a script read its stock: these are links, not findings. A name opens
 * the seller's own search for the part where it publishes one. The sellers page (?sellers=all) is the
 * whole list as one sortable table, each seller with its profile.
 */

const countryNames = typeof Intl !== 'undefined' && 'DisplayNames' in Intl
  ? new Intl.DisplayNames(['en'], { type: 'region' }) : null   // the site is in English whatever the browser's locale

/** A marketplace is based nowhere: the seller you buy from is anywhere. */
export const WORLDWIDE = 'WW'

export function country(code: string): string {
  if (code === WORLDWIDE) return 'Worldwide (depends on the seller)'
  try { return countryNames?.of(code) ?? code } catch { return code }
}

/** The flag of an ISO 3166 code, as the two regional-indicator letters; a globe for a marketplace; nothing else. */
const FLAG_ALIAS: Record<string, string> = { UK: 'GB' }
export function flag(code: string): string {
  if (code === WORLDWIDE) return '🌐'
  const c = FLAG_ALIAS[code] ?? code
  if (!/^[A-Z]{2}$/.test(c)) return ''
  return String.fromCodePoint(...[...c].map((ch) => 0x1f1e6 + ch.charCodeAt(0) - 65))
}

export function searchAt(seller: Seller, part: string): string | undefined {
  return seller.search ? seller.search.replace('{part}', encodeURIComponent(part)) : undefined
}

/** The kinds a part answers to, from its page: the menu's devices, the recipe's kind, the dictionary's id. */
export function partKinds(page: PartPage): Set<string> {
  const out = new Set<string>(page.devices ?? [])
  if (page.models?.kind) out.add(page.models.kind)
  for (const k of (page.kind ?? '').split('/')) if (k) out.add(k)
  return out
}

/** The makers a part is of, from its page: the sheet's maker and its lineage, then the makers the catalogues and the sheets name. */
export function partMakers(page: PartPage): Set<string> {
  const out = new Set<string>()
  const a = page.about
  if (a?.maker) {
    if (a.maker[0]) out.add(a.maker[0])
    for (const m of a.maker[1]) if (m) out.add(m)
  }
  for (const c of a?.catalogue ?? []) if (c[1]) out.add(c[1])
  for (const s of a?.sheets ?? []) if (s[1]) out.add(s[1])
  return out
}

/** The kinds a seller's catalogue covers: its own list when it has one, its group's otherwise. */
export function sellerKinds(s: Seller, groups: Map<string, SellerGroup>): string[] {
  return s.kinds ?? groups.get(s.group)?.kinds ?? []
}

export type Tier = 'aggregators' | 'broad' | 'specialists' | 'regional' | 'marketplaces'

/**
 * The sellers a part page shows, by tier. The broad distributors when their lines cover the kind — all
 * of them when nothing says what the part is — and any seller that is the store of one of the part's
 * makers; the specialists whose kinds cover it, which leaves out every group that lists none (boxes,
 * boards, fabricators); the regional shops, all, for the country filter to choose from; the marketplaces
 * when their kinds cover it. A seller is never left out for refusing scripts: nothing here reads stock.
 */
export function tiers(list: SellersList, kinds: Set<string>, makers: Set<string>): Record<Tier, Seller[]> {
  const groups = new Map(list.groups.map((g) => [g.id, g]))
  const out: Record<Tier, Seller[]> = { aggregators: [], broad: [], specialists: [], regional: [], marketplaces: [] }
  const covers = (s: Seller) => sellerKinds(s, groups).some((k) => kinds.has(k))
  for (const s of list.sellers) {
    if (s.group === 'search') out.aggregators.push(s)
    else if ((s.makers ?? []).some((m) => makers.has(m))) out.broad.push(s)
    else if (s.group === 'broadline') { if (kinds.size === 0 || covers(s)) out.broad.push(s) }
    else if (s.group === 'direct') { /* the maker's store, only on the maker's parts */ }
    else if (s.group === 'regional') out.regional.push(s)
    else if (s.group === 'marketplace_surplus') { if (covers(s)) out.marketplaces.push(s) }
    else if (covers(s)) out.specialists.push(s)
  }
  return out
}

type Found = Record<string, [string, string, string]>
const FOUND_RANK: Record<string, number> = { found: 0, unclear: 1, '': 2, not_found: 3 }
const FOUND_WORDS: Record<string, string> = { found: 'found', unclear: 'unclear', not_found: 'not found' }

/** A tier's order: what a check found first, when one has been made, then the maintainer's priority, then the name. */
export function orderTier(rows: Seller[], found?: Found): Seller[] {
  const key = (s: Seller): [number, number, string] =>
    [FOUND_RANK[found?.[s.id]?.[0] ?? ''] ?? 2, s.priority ?? 2, s.title.toLowerCase()]
  return [...rows].sort((a, b) => {
    const ka = key(a), kb = key(b)
    return ka[0] - kb[0] || ka[1] - kb[1] || ka[2].localeCompare(kb[2])
  })
}

/** The countries a reader has hidden, kept in this browser only, so the choice holds from part to part. */
const HIDE_KEY = 'sei.sellers.hide'
function readHidden(): Set<string> {
  try { return new Set(JSON.parse(localStorage.getItem(HIDE_KEY) || '[]') as string[]) } catch { return new Set() }
}
function writeHidden(h: Set<string>) {
  try { localStorage.setItem(HIDE_KEY, JSON.stringify([...h].sort())) } catch { /* a private window: the choice lasts the page */ }
}
function useHidden(): [Set<string>, (h: Set<string>) => void] {
  const [hidden, setHiddenState] = useState<Set<string>>(readHidden)
  const setHidden = (h: Set<string>) => { setHiddenState(h); writeHidden(h) }
  useEffect(() => {   // another tab's choice, when it changes
    const on = (e: StorageEvent) => { if (e.key === HIDE_KEY) setHiddenState(readHidden()) }
    addEventListener('storage', on)
    return () => removeEventListener('storage', on)
  }, [])
  return [hidden, setHidden]
}
const shown = (s: Seller, hidden: Set<string>) => s.base === WORLDWIDE || !hidden.has(s.base)

/** The country filter, open by default: a box per country, all or none, remembered in this browser. A marketplace is never hidden. */
function CountryFilter({ codes, hidden, setHidden, shown, total }: {
  codes: string[]; hidden: Set<string>; setHidden: (h: Set<string>) => void; shown: number; total: number
}) {
  const toggle = (c: string) => {
    const h = new Set(hidden)
    if (h.has(c)) h.delete(c); else h.add(c)
    setHidden(h)
  }
  return (
    <details class="cfilter" open>
      <summary title="Choose which countries to show; the choice is remembered in this browser, for every part">
        Countries: {hidden.size ? `${codes.length - hidden.size} of ${codes.length} shown, ${total - shown} sellers hidden` : `all ${codes.length}`}
        <span class="muted"> · fold</span>
      </summary>
      <div class="cfilter-box">
        <p class="small">
          <button type="button" onClick={() => setHidden(new Set())}>show all</button>{' '}
          <button type="button" onClick={() => setHidden(new Set(codes))}>hide all</button>
          <span class="muted"> · tick a country to show its sellers</span>
        </p>
        <div class="cfilter-grid">
          {codes.map((c) => (
            <label key={c}><input type="checkbox" checked={!hidden.has(c)} onChange={() => toggle(c)} /> <span class="flag">{flag(c)}</span>{country(c)}</label>
          ))}
        </div>
      </div>
    </details>
  )
}

function FoundChip({ f }: { f: [string, string, string] }) {
  const word = FOUND_WORDS[f[0]] ?? f[0]
  return (
    <span class={`chip ${f[0] === 'found' ? 'ok' : f[0] === 'not_found' ? 'bad' : 'warn'}`} title={`checked ${f[2]}`}>
      {f[1] ? <a href={f[1]} target="_blank" rel="noopener">{word}</a> : word}
    </span>
  )
}

/** The seller's name, as its search for the part where it has one, and the way to its profile. */
function SellerName({ s, part }: { s: Seller; part?: string }) {
  const search = part ? searchAt(s, part) : undefined
  const profile = `?sellers=all#seller-${s.id}`
  return (
    <>
      <strong>
        <a href={search ?? s.url} target="_blank" rel="noopener"
          title={search ? `${s.title}'s own search for ${part}` : `${s.title}'s site; no search address is known`}>{s.title}</a>
      </strong>
      {search && <span class="muted small"> · <a href={s.url} target="_blank" rel="noopener">site</a></span>}
      <span class="muted small"> · <a href={profile} onClick={(e) => follow(e, profile)}
        title="What it says of itself, where it ships, what readers of the forums say">
        {s.opinions?.length ? `profile, ${s.opinions.length} forum thread${s.opinions.length === 1 ? '' : 's'}` : s.about ? 'profile' : 'entry'}
      </a></span>
    </>
  )
}

/** One tier of a part page: the sellers, their country, type and speciality, and what each is for. */
function TierTable({ rows, part, list, groups, found }: {
  rows: Seller[]; part: string; list: SellersList; groups: Map<string, SellerGroup>; found?: Found
}) {
  const withFound = !!found && rows.some((s) => found[s.id])
  return (
    <div class="scroll-x">
      <table class="tier">
        <thead>
          <tr>
            <th>Seller</th>
            {withFound && <th title="What following the search found, when a check has been made">Found</th>}
            <th title="Its base or principal market, not where a parcel ships from">Country</th>
            <th title="What kind of seller it is, which says what still needs checking">Type</th>
            <th>Speciality</th>
            <th>Useful for</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => {
            const g = groups.get(s.group)
            const f = found?.[s.id]
            return (
              <tr key={s.id}>
                <td><SellerName s={s} part={part} /></td>
                {withFound && <td>{f ? <FoundChip f={f} /> : <span class="muted">–</span>}</td>}
                <td class="country"><span class="flag">{flag(s.base)}</span>{country(s.base)}</td>
                <td><span title={list.types[s.type] ?? s.type}>{s.type.replace(/_/g, ' ')}</span></td>
                <td title={g?.note}>{g?.title ?? s.group}</td>
                <td class="useful">{s.useful_for}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

/** The section on a part page: where to buy this kind of part, in tiers. */
export function SellersSection({ page, kind }: { page: PartPage; kind: string }) {
  const cat = useCatalogue()
  const [hidden, setHidden] = useHidden()
  const list = cat?.sellers
  const t = useMemo(() => list ? tiers(list, partKinds(page), partMakers(page)) : null, [list, page])
  if (!cat || !list?.sellers.length || !t) return null
  const groups = new Map(list.groups.map((g) => [g.id, g]))
  const codes = [...new Set(list.sellers.map((s) => s.base).filter((c) => c !== WORLDWIDE))]
    .sort((a, b) => country(a).localeCompare(country(b)))
  const pick = (rows: Seller[]) => orderTier(rows.filter((s) => shown(s, hidden)), page.sellers)
  const broad = pick(t.broad), specialists = pick(t.specialists), regional = pick(t.regional), market = pick(t.marketplaces)
  const listed = t.broad.length + t.specialists.length + t.regional.length + t.marketplaces.length
  const visible = broad.length + specialists.length + regional.length + market.length
  const marketGroup = groups.get('marketplace_surplus')
  const table = (rows: Seller[]) => <TierTable rows={rows} part={page.part} list={list} groups={groups} found={page.sellers} />
  return (
    <Section title="Where to buy" anchor="sellers">
      {t.aggregators.length > 0 && (
        <>
          <h3 class="tier-head">Compare stock and prices across distributors</h3>
          <p class="muted small">
            Each of these asks many distributors at once and shows who lists {page.part}, with stock and prices as
            the distributors report them; the order is placed at the distributor.
          </p>
          {table(orderTier(t.aggregators, page.sellers))}
        </>
      )}
      <p class="muted small">
        Links, not findings: a name opens the seller's own search for {page.part} where it publishes one, its
        site otherwise. Nothing here is read from a seller's stock; the order is the maintainer's priority
        within each tier, then the name.
      </p>
      <CountryFilter codes={codes} hidden={hidden} setHidden={setHidden} shown={visible} total={listed} />
      {hidden.size > 0 && (
        <p class="small">
          Your country filter hides {listed - visible} of the {listed} sellers of this kind of part.{' '}
          <button type="button" class="srow-btn" onClick={() => setHidden(new Set())}>show every country</button>
        </p>
      )}
      {broad.length > 0 && (
        <>
          <h3 class="tier-head">Broad distributors and the maker's store</h3>
          {table(broad)}
        </>
      )}
      {specialists.length > 0 && (
        <>
          <h3 class="tier-head">Specialists for {kind || page.kind || 'this kind of part'}</h3>
          {table(specialists)}
        </>
      )}
      {t.regional.length > 0 && (
        <Fold level={1} anchor="regional" open={hidden.size > 0}
          summary={<strong>Regional shops ({hidden.size ? `${regional.length} of ${t.regional.length}` : t.regional.length})</strong>}>
          {() => regional.length ? table(regional) : <p class="muted small">Every regional shop is in a hidden country.</p>}
        </Fold>
      )}
      {t.marketplaces.length > 0 && (
        <Fold level={1} anchor="marketplaces" summary={<strong>Marketplaces, independent sourcing and surplus ({market.length})</strong>}>
          {() => (
            <>
              <p class="caveat small">
                Open marketplaces carry a counterfeit risk for semiconductors: the seller, not the platform, is who
                you buy from{marketGroup?.caveat && <> <Refs ids={[marketGroup.caveat]} cat={cat} /></>}.
              </p>
              {table(market)}
            </>
          )}
        </Fold>
      )}
      {visible === 0 && hidden.size === 0 && (
        <p class="muted small">No seller of the list names this kind of part; the broad distributors are the place to start.</p>
      )}
      <p class="muted small">
        <a href="?sellers=all">All {list.sellers.length} sellers by speciality</a>, each with its profile: boxes,
        boards, fabricators and the regional shops included.
      </p>
    </Section>
  )
}

/** A seller's profile: what it says of itself, where it ships, what readers of the forums say, and the facts of its entry. */
function Profile({ s, colSpan, target }: { s: Seller; colSpan: number; target: boolean }) {
  return (
    <tr class={`sprofile${target ? ' target' : ''}`}>
      <td colSpan={colSpan}>
        <dl>
          {s.about && (
            <>
              <dt>About itself</dt>
              <dd>{s.about.says} <span class="muted">(<a href={s.about.url} target="_blank" rel="noopener">its page</a>, read {s.about.checked})</span></dd>
            </>
          )}
          {s.ships && (
            <>
              <dt>Ships</dt>
              <dd>
                {s.ships.text}
                {s.ships.url && <span class="muted"> (<a href={s.ships.url} target="_blank" rel="noopener">its page</a>{s.ships.checked ? `, read ${s.ships.checked}` : ''})</span>}
              </dd>
            </>
          )}
          {s.opinions && s.opinions.length > 0 && (
            <>
              <dt>Readers say</dt>
              <dd>
                <ul>
                  {s.opinions.map((o) => (
                    <li key={o.url}>
                      <a href={o.url} target="_blank" rel="noopener">{o.title}</a>
                      <span class="muted"> · {o.forum}, {o.date}</span> — {o.gist}
                    </li>
                  ))}
                </ul>
                <span class="muted">Threads of the forums, linked as opinions; one reader's experience on one day, not a verdict of this index.</span>
              </dd>
            </>
          )}
          <dt>Search</dt>
          <dd>
            {s.search ? <code>{s.search}</code> : <span class="muted">no search address is known</span>}
            {s.search_result && <span class="muted"> · {s.search_result}{s.search_checked ? ` (${s.search_checked})` : ''}</span>}
          </dd>
          {s.robots && (
            <>
              <dt>robots.txt</dt>
              <dd>{s.robots}{s.robots_checked && <span class="muted"> ({s.robots_checked})</span>}</dd>
            </>
          )}
          {s.checked && (
            <>
              <dt>Entry read</dt>
              <dd>{s.checked}</dd>
            </>
          )}
        </dl>
      </td>
    </tr>
  )
}

type Key = 'seller' | 'found' | 'speciality' | 'type' | 'country' | 'priority' | 'useful'
const COLUMNS: { key: Key; label: string; title: string; num?: boolean }[] = [
  { key: 'seller', label: 'Seller', title: 'The seller; on a part page, its search for the part where it publishes one' },
  { key: 'found', label: 'Found', title: 'What following the search found, when a check has been made' },
  { key: 'speciality', label: 'Speciality', title: 'The group of sellers it belongs to' },
  { key: 'type', label: 'Type', title: 'What kind of seller it is, which says what still needs checking' },
  { key: 'country', label: 'Country', title: 'Its base or principal market, not where a parcel ships from' },
  { key: 'priority', label: 'Priority', title: "The maintainer's order of first comparison: 1 first, 3 last resort", num: true },
  { key: 'useful', label: 'Useful for', title: 'What its catalogue covers' },
]

/** The seller a link names, `?sellers=all#seller-<id>`. */
function targeted(): string {
  const h = typeof location !== 'undefined' ? location.hash : ''
  return h.startsWith('#seller-') ? decodeURIComponent(h.slice(8)) : ''
}

/** The whole list as one sortable table: the groups in the registry's order, then priority, then name. */
export function SellersTable({ list, part, found }: { list: SellersList; part?: string; found?: Found }) {
  const [by, setBy] = useState<Key | 'default'>('default')
  const [dir, setDir] = useState<'asc' | 'desc'>('asc')
  const [hidden, setHidden] = useHidden()
  const [open, setOpen] = useState<Set<string>>(() => new Set(targeted() ? [targeted()] : []))
  const [target, setTarget] = useState(targeted)
  useEffect(() => {   // the seller a link names: its profile open, the row in view (`go` scrolled to the top)
    const show = () => {
      const id = targeted()
      setTarget(id)
      if (!id) return
      setOpen((o) => o.has(id) ? o : new Set([...o, id]))
      // Twice: once the row exists, and again after the profile below it and the rest of the page have laid out.
      const into = () => document.getElementById(`seller-${id}`)?.scrollIntoView({ block: 'center' })
      requestAnimationFrame(into)
      setTimeout(into, 400)
    }
    show()
    addEventListener('popstate', show)
    addEventListener('hashchange', show)
    return () => { removeEventListener('popstate', show); removeEventListener('hashchange', show) }
  }, [list])
  const codes = useMemo(() => [...new Set(list.sellers.map((s) => s.base).filter((c) => c !== WORLDWIDE))]
    .sort((a, b) => country(a).localeCompare(country(b))), [list])
  const groups = useMemo(() => new Map(list.groups.map((g) => [g.id, g])), [list])
  const withFound = !!found && list.sellers.some((s) => found[s.id])
  const columns = withFound ? COLUMNS : COLUMNS.filter((c) => c.key !== 'found')
  const rows = useMemo(() => {
    const key = (s: Seller): (string | number)[] => {
      const f = found?.[s.id]?.[0] ?? ''
      switch (by) {
        case 'seller': return [s.title.toLowerCase()]
        case 'found': return [FOUND_RANK[f] ?? 2]
        case 'speciality': return [list.groups.findIndex((g) => g.id === s.group)]
        case 'type': return [s.type]
        case 'country': return [s.base === WORLDWIDE ? '￿' : country(s.base)]
        case 'priority': return [s.priority ?? 2]
        case 'useful': return [s.useful_for.toLowerCase()]
        default: return [list.groups.findIndex((g) => g.id === s.group), FOUND_RANK[f] ?? 2, s.priority ?? 2, s.title.toLowerCase()]
      }
    }
    const out = list.sellers.filter((s) => shown(s, hidden)).sort((a, b) => {
      const ka = key(a), kb = key(b)
      for (let i = 0; i < ka.length; i++) {
        if (ka[i]! < kb[i]!) return -1
        if (ka[i]! > kb[i]!) return 1
      }
      return 0
    })
    return dir === 'desc' ? out.reverse() : out
  }, [list, by, dir, found, hidden])
  const sortBy = (k: Key) => {
    if (k === by) setDir(dir === 'asc' ? 'desc' : 'asc')
    else { setBy(k); setDir('asc') }
  }
  const toggle = (id: string) => setOpen((o) => { const n = new Set(o); if (n.has(id)) n.delete(id); else n.add(id); return n })
  return (
    <div class="stack-s">
      <CountryFilter codes={codes} hidden={hidden} setHidden={setHidden} shown={rows.length} total={list.sellers.length} />
      <div class="scroll-x">
      <table class="sellers">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} class={c.num ? 'num' : undefined} aria-sort={by === c.key ? (dir === 'asc' ? 'ascending' : 'descending') : undefined}>
                <button type="button" title={c.title} onClick={() => sortBy(c.key)}>{c.label}</button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && <tr><td colSpan={columns.length} class="muted">Every country is hidden by the filter.</td></tr>}
          {rows.map((s) => {
            const search = part ? searchAt(s, part) : undefined
            const f = found?.[s.id]
            const g: SellerGroup | undefined = groups.get(s.group)
            const isOpen = open.has(s.id)
            return (
              <>
                <tr key={s.id} id={`seller-${s.id}`} class={target === s.id && !isOpen ? 'target' : undefined}>
                  <td>
                    <strong><a href={search ?? s.url} target="_blank" rel="noopener">{s.title}</a></strong>
                    {search && <span class="muted small"> · <a href={s.url} target="_blank" rel="noopener">site</a></span>}
                    <button type="button" class="srow-btn" aria-expanded={isOpen} onClick={() => toggle(s.id)}
                      title="Its profile: what it says of itself, where it ships, what readers of the forums say">profile</button>
                  </td>
                  {withFound && <td>{f ? <FoundChip f={f} /> : <span class="muted small">{search ? 'not checked' : 'no search'}</span>}</td>}
                  <td title={g?.note}>{g?.title ?? s.group}</td>
                  <td><span title={list.types[s.type] ?? s.type}>{s.type.replace(/_/g, ' ')}</span></td>
                  <td class="country"><span class="flag">{flag(s.base)}</span>{country(s.base)}</td>
                  <td class="num">{s.priority ?? 2}</td>
                  <td class="small">{s.useful_for}</td>
                </tr>
                {isOpen && <Profile s={s} colSpan={columns.length} target={target === s.id} />}
              </>
            )
          })}
        </tbody>
      </table>
      </div>
    </div>
  )
}

/** The standalone page: every seller, with what each kind of seller means. */
export function SellersPage({ cat: given }: { cat?: Catalogue | null }) {
  const loaded = useCatalogue()
  const cat = given ?? loaded
  const list = cat?.sellers
  if (!cat) return <p class="muted">Loading the sellers list.</p>
  if (!list?.sellers.length) return <p class="muted">No sellers list is published yet.</p>
  const profiles = list.sellers.filter((s) => s.about || s.opinions?.length).length
  return (
    <section class="evidence stack">
      <div class="ptitle"><h1>Sellers list</h1></div>
      <p class="lede">
        Where the parts of this index are bought, worldwide: {list.sellers.length} sellers, each with its speciality,
        what its catalogue is for, and a profile — what it says of itself, where it ships, what readers of the
        forums say ({profiles} written so far). A kind of seller says what still needs checking, not how good it is.
        A part's page shows the sellers for its kind of part; this is everyone.
      </p>
      <SellersTable list={list} />
      <dl class="reading">
        {Object.entries(list.types).map(([k, v]) => <><dt>{k.replace(/_/g, ' ')}</dt><dd>{v}</dd></>)}
      </dl>
      <p class="muted small">
        Compiled from a buying guide reviewed on 2026-10-11. Shipping, duty and delivery terms change by
        destination and date and are not recorded here; read them at the seller's checkout. A marketplace is
        based nowhere: the seller you buy from there is anywhere.
      </p>
    </section>
  )
}
