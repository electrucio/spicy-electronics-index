/**
 * The parts browser: a list on the left, the part on the right.
 *
 * The shape is the previous site's, which is the one worth keeping — a list you can read down while a
 * part stays open beside it, rather than a search box that answers nothing until you type. What is
 * different is what it is built from: 15,558 parts instead of the 1,712 that have a model, because this
 * index also knows where a part is *used*, and that is most of what there is to say about a part.
 *
 * `parts.json` is 61 KB gzipped and holds all of them, so filtering and sorting never ask the server.
 * Opening a part is one request for a file the build already joined and grouped.
 */
import { Fragment } from 'preact'
import { useEffect, useMemo, useRef, useState } from 'preact/hooks'

import { AboutPart, Databooks } from './about'
import { Heading } from './anchor'
import { DATA, loadIndex, partPath, reloadIndex } from './data'
import { Fold, Section, SubSection } from './fold'
import { forViewer } from './links'
import { ModelCharacter } from './character'
import { ModelKey } from './key'
import { Loading } from './loading'
import { modelKey } from './sealed'
import type { DeviceKind, PageUse, PartIndex, PartModel, PartPage, PartRow, UseKind } from './types'
import { CopyButton, usePartTexts } from './unlock'
export { partPath } from './data'
export const n = (v: number) => v.toLocaleString('en-GB')

export type Sort = 'documents' | 'models' | 'sheets' | 'name'
export type Dir = 'asc' | 'desc'

/** The list's columns, each a way of ordering it. A count starts from the most; a name from A. */
const COLUMNS: { key: Sort; label: string; title: string; num: boolean }[] = [
  { key: 'name', label: 'Part', title: 'Part number', num: false },
  { key: 'documents', label: 'Mentions', title: 'Documents that print it', num: true },
  { key: 'models', label: 'SPICE', title: 'SPICE models found for it', num: true },
  { key: 'sheets', label: 'Sheets', title: 'Data sheets and databook pages linked for it', num: true },
]
export const NATURAL: Record<Sort, Dir> = { name: 'asc', documents: 'desc', models: 'desc', sheets: 'desc' }
const PAGE = 300

/**
 * Whether bit `i` of a row's devices is set. Arithmetic, not `&`: JavaScript's bit operators work on 32 bits
 * and the menu has more entries than that; a double holds every integer up to 2^53 exactly.
 */
export function hasBit(bits: number, i: number): boolean {
  return Math.floor(bits / 2 ** i) % 2 === 1
}

/**
 * What kind of part a row is: the entries of the device menu it answers to, the same ones the filter
 * uses — every one it could be, so a D model nothing narrows says "Diodes / Germanium diodes". A finer
 * entry says its device too, so a BC547 is an "NPN silicon BJT" and not also a "Silicon BJT".
 */
export function typeOf(r: PartRow, menu: DeviceKind[]): string {
  const on = menu.filter((_, i) => hasBit(r[4], i))
  const finer = new Set(on.map((d) => d.parent).filter(Boolean))
  return on.filter((d) => !finer.has(d.key)).map((d) => d.label).join(' / ')
}

const COUNT: Record<Exclude<Sort, 'name'>, (r: PartRow) => number> = {
  documents: (r) => r[1],
  models: (r) => r[3],
  sheets: (r) => r[6] ?? 0,
}

/** The order asked for, and inside a tie the most used first, then the most models, then by name. */
export function compare(by: Sort, dir: Dir = NATURAL[by]): (a: PartRow, b: PartRow) => number {
  const sign = dir === 'asc' ? 1 : -1
  return (a, b) => (by === 'name' ? sign * a[0].localeCompare(b[0]) : sign * (COUNT[by](a) - COUNT[by](b)))
    || b[1] - a[1] || b[3] - a[3] || a[0].localeCompare(b[0])
}

/**
 * What a query matches, best first: the part itself, then what starts with it, then what contains it —
 * and inside each of those, whatever order was asked for. The chosen sort used to be dropped as soon as
 * anything was typed, which put parts with no use at all above parts with hundreds of them, because the
 * relevance weight it fell back to counted one SPICE model as twenty-five documents.
 *
 * Last, what the query starts with: somebody who types the order code off a reel — AD817ARZ, TL072CP,
 * LM4562NA — is asking for the type, and the corpus mostly prints the type alone. A key has to be four
 * characters or more to count as the head of a query, so BC does not answer for BC108B.
 */

export function search(rows: PartRow[], q: string, by: Sort = 'documents', dir: Dir = NATURAL[by]): PartRow[] {
  const needle = q.trim().toUpperCase().replace(/[^A-Z0-9]/g, '')
  if (needle.length < 2) return []
  const exact: PartRow[] = []
  const starts: PartRow[] = []
  const has: PartRow[] = []
  const heads: PartRow[] = []
  for (const r of rows) {
    const key = r[0].toUpperCase().replace(/[^A-Z0-9]/g, '')
    if (key === needle) exact.push(r)
    else if (key.startsWith(needle)) starts.push(r)
    else if (key.includes(needle)) has.push(r)
    else if (key.length >= 4 && needle.startsWith(key)) heads.push(r)
  }
  for (const g of [exact, starts, has, heads]) g.sort(compare(by, dir))
  heads.sort((a, b) => b[0].length - a[0].length)     // the longest head is the nearest: BC108B before BC108 for BC108BZ
  return [...exact, ...starts, ...has, ...heads]
}

/** All the parts, in the order asked for. Sorting 15,558 rows is cheap; rendering them is not. */
export function order(rows: PartRow[], by: Sort, dir: Dir = NATURAL[by]): PartRow[] {
  return [...rows].sort(compare(by, dir))
}

/**
 * The rows that answer to the chosen device. An empty choice means all of them.
 *
 * A part carries one bit per device, because it can answer to more than one: a JEDEC number like
 * `2N3904` or `2N5457` could be a transistor, a JFET or a MOSFET and the family pattern cannot tell,
 * so it appears under all three rather than being guessed into one.
 */
export function ofDevice(rows: PartRow[], device: string, menu: DeviceKind[]): PartRow[] {
  const at = menu.findIndex((d) => d.key === device)
  if (at < 0) return rows
  return rows.filter((r) => hasBit(r[4], at))
}

/**
 * How much of its family's physics a model card carries, as a bar: of what the bench checks for the family,
 * how much the card sets to something that has an effect. The models are ranked by it, so the bars fall
 * down the table. Hover for what is missing and what sits at the simulator's default.
 */
/** The kinds the bench never measures: the devices SPICE has no element for, "Passives and hardware" and
 *  the entries under it (`PASSIVE_DEVICES` in src/spicy_electronics_index/web/parts.py). Their rows leave the bench's
 *  columns empty rather than say "not measured", which would promise a measurement. */
export const NOT_BENCHED = new Set(['passive', 'relay', 'transformer', 'magnetic-core', 'inductor', 'speaker', 'pickup',
  'potentiometer', 'switch', 'capacitor', 'thermistor', 'lamp', 'ldr'])

function PhysicsCell({ b }: { b?: PartModel['bench'] }) {
  if (!b?.covers) return <span class="muted small">not measured</span>
  const [has, of] = b.covers
  if (!of) return <span class="muted small" title="the bench checks no physics for a card of this kind">not checked</span>
  const missing = (b.missing ?? []).length ? `missing: ${b.missing!.join(', ')}` : 'every checked parameter is there and does something'
  const defaults = (b.defaults ?? []).length ? `; at the simulator's default: ${b.defaults!.join(', ')}` : ''
  return (
    <div class="small benchcell">
      <span title={`${has} of the ${of} effects the bench checks for its family; ${missing}${defaults}`}>
        <span class="bar"><i class="p" style={{ width: `${(100 * has) / of}%` }} /></span> {has}/{of}
      </span>
      {(b.extensions ?? []).length > 0 && (
        <div>{b.extensions!.map((e) => <span key={e} class="chip" title="physics beyond the family's own, from an extension the card carries">+{e}</span>)}</div>
      )}
    </div>
  )
}

/** The simulators the bench runs, in its order, as their makers write them. */
const SIMS: Record<string, string> = { qspice: 'QSPICE', ngspice: 'ngspice', ltspice: 'LTspice' }

/**
 * Will it work in mine? Each simulator by name: plain where it runs the model, marked where its results
 * stand apart from the other two, struck out where it failed, faint where the model was never run in it.
 * Then a tick when no measurement differs by more than 5 % between those that ran — a spread of a few
 * per cent between simulators is far inside how well any model fits its part — or ≠ when two ran and
 * differ, which two cannot say who is the odd one.
 */
function SimCell({ b }: { b?: PartModel['bench'] }) {
  if (!b?.sims) return null
  const sims = b.sims
  const ran = Object.values(sims).filter((s) => s !== 'failed').length
  const agree = typeof b.agree === 'number' ? Math.round(b.agree * 100) : null
  const odd = b.differs_on ? ` on ${b.differs_on} ${b.differs_on === 1 ? 'measurement' : 'measurements'}` : ''
  const said = (e: string): [string, string] => {
    const s = sims[e]
    if (s === 'ok') return ['', 'runs it']
    if (s === 'differs') return ['differs', `runs it, but its results differ from the other two by more than 5 %${odd}`]
    if (s === 'failed') return ['failed', 'could not run it']
    return ['untried', 'not run in it yet']
  }
  const names = [...Object.keys(SIMS), ...Object.keys(sims).filter((e) => !SIMS[e])]
  return (
    <div class="small benchcell">
      <span class="sims">
        {names.map((e, i) => {
          const [cls, title] = said(e)
          return <Fragment key={e}>{i > 0 && ' · '}<span class={cls} title={`${SIMS[e] ?? e}: ${title}`}>{SIMS[e] ?? e}</span></Fragment>
        })}
        {ran > 1 && !b.differs_on && (
          <span class="ok" title={`they agree within 5 % on every output${agree === null ? '' : `, within 1 % on ${agree} %`}`}> ✓</span>
        )}
        {ran === 2 && !!b.differs_on && <span class="neq" title={`the two differ by more than 5 %${odd}`}> ≠</span>}
      </span>
      {(b.flags ?? []).length > 0 && <div>{b.flags!.map((f) => <span key={f} class="chip k-suspect" title="something no transistor does, or a run that went wrong">{f}</span>)}</div>}
    </div>
  )
}

/** A symbol's drawing, made from its .asy by `sei web symbol-drawings` (never the file itself, CLAUDE.md
 *  rule 1), inline so the page's ink draws it. Nothing when the drawings were not published. */
function SymbolDrawing({ sha }: { sha: string }) {
  const [svg, setSvg] = useState<string | null | undefined>(undefined)
  useEffect(() => {
    let live = true
    fetch(`${DATA}/symbol-drawings/${sha}.svg`).then((r) => (r.ok ? r.text() : null)).catch(() => null)
      .then((t) => { if (live) setSvg(t && t.startsWith('<svg') ? t : null) })
    return () => { live = false }
  }, [sha])
  if (svg === undefined) return <span class="muted small">drawing the symbol…</span>
  if (svg === null) return <span class="muted small">no drawing of this symbol is published; the link beside the model leads to it</span>
  return <div class="asy-view" dangerouslySetInnerHTML={{ __html: svg }} />
}

/** Where one file is had: its download link, the member inside an archive, or the simulator it ships with.
 *  `via` names the source whose published copy the link is, when the model itself only ships with one. */
function Get({ url, member, installed, via, symbol }: { url?: string; member?: string; installed?: string; via?: string; symbol?: PartModel['get']['symbol'] }) {
  return (
    <>
      {url && via && <span class="muted small" title={`ships with ${installed ?? 'a simulator'}; the same model is published by ${via}`}>copy at {via} · </span>}
      {url ? <a href={url}>download</a>
        : installed ? <span class="muted small">ships with {installed}</span>
          : <span class="muted small">origin not recorded</span>}
      {member && <span class="muted small"> · {member}</span>}
      {symbol && (symbol.url === url
        // one archive holds both: the model's file and the symbol's
        ? <span class="muted small" title="the LTspice symbol is in the same archive"> · symbol {symbol.member}</span>
        : <> · <a href={symbol.url} title="the LTspice symbol published with this model">symbol</a>
          {symbol.member && <span class="muted small"> · {symbol.member}</span>}</>)}
    </>
  )
}

function Models({ page }: { page: PartPage }) {
  const m = page.models
  const [open, setOpen] = useState<Set<number>>(new Set())
  // The model text, only in the browser that holds the maintainer's key (unlock.tsx); null everywhere else.
  const texts = usePartTexts(page.part)
  const [reading, setReading] = useState<Set<number>>(new Set())
  // a model's symbol is drawn unless the reader folds it away
  const [undrawn, setUndrawn] = useState<Set<number>>(new Set())
  if (!m) return null
  const flip = (set: typeof setOpen, i: number) => set((s) => { const n = new Set(s); if (n.has(i)) n.delete(i); else n.add(i); return n })
  const toggle = (i: number) => flip(setOpen, i)
  return (
    // the table of models is what a reader comes for: open from the start, the rest folded
    <Section title="SPICE models" anchor="spice-models" defaultOpen>
      <SubSection title="Table of SPICE models" anchor="table" defaultOpen>
        {() => (
          <div class="tablewrap">
            <table>
              <thead>
                <tr>
                  <th aria-label="other places that hold the model" /><th>#</th><th title="how much of the physics the bench checks for its family the card carries">Physics</th><th title="the simulators that run it the same way; hover a name for what it made of the model">Simulators</th><th>Source</th><th>Name</th><th>Kind</th><th>Changed</th><th>Get it</th>
                </tr>
              </thead>
              <tbody>
                {m.models.map((mo, i) => {
                  const copies = mo.copies ?? []
                  const shown = open.has(i)
                  const text = texts?.[modelKey(mo)]
                  return (
                    <Fragment key={i}>
                      <tr>
                        <td class="disc">{copies.length > 0 && <button type="button" class="disc" aria-expanded={shown} title={`${copies.length} other ${copies.length === 1 ? 'place holds' : 'places hold'} this model`} onClick={() => toggle(i)}>{shown ? '−' : '+'}</button>}</td>
                        <td><ModelKey i={i} /></td>
                        <td class="bench">{!NOT_BENCHED.has(m.kind) && <PhysicsCell b={mo.bench} />}</td>
                        <td class="bench sims-td">{!NOT_BENCHED.has(m.kind) && <SimCell b={mo.bench} />}</td>
                        <td>{mo.source}</td>
                        <td>
                          <code>{mo.name}</code>
                          {mo.standin && <> <span class="chip">model of {mo.standin}</span></>}
                          {mo.alias && <> <span class="chip">listed as {mo.alias}</span></>}
                        </td>
                        <td>{mo.type || mo.def}</td>
                        <td>
                          {mo.verbatim
                            ? <span class="muted small">verbatim</span>
                            : <span class="chip">{(mo.changes ?? []).join(' ') || 'changed'}</span>}
                        </td>
                        <td>
                          <Get url={mo.get.url} member={mo.get.member} installed={mo.get.installed_with} via={mo.get.via} symbol={mo.get.symbol} />
                          {mo.get.symbol?.sha256 && <> · <button type="button" class="linkish" aria-expanded={!undrawn.has(i)}
                            title="the symbol drawn" onClick={() => flip(setUndrawn, i)}>{undrawn.has(i) ? 'draw' : 'hide drawing'}</button></>}
                          {text && (
                            // a line of its own: the column is already the table's widest
                            <div class="small"><CopyButton text={text} /> · <button type="button" class="linkish" aria-expanded={reading.has(i)}
                              onClick={() => flip(setReading, i)}>{reading.has(i) ? 'hide' : 'show'}</button></div>
                          )}
                        </td>
                      </tr>
                      {mo.get.symbol?.sha256 && !undrawn.has(i) && (
                        <tr class="copy"><td /><td colSpan={8}><SymbolDrawing sha={mo.get.symbol.sha256} /></td></tr>
                      )}
                      {text && reading.has(i) && (
                        <tr class="copy"><td /><td colSpan={8}><pre class="netlist sealed">{text}</pre></td></tr>
                      )}
                      {shown && copies.map((c, j) => (
                        <tr key={`${i}.${j}`} class="copy">
                          <td /><td /><td /><td />
                          <td><span class="muted">↳</span> {c.source}</td>
                          <td><code>{c.name}</code></td>
                          <td colSpan={2}><span class="muted small">the same model as above</span></td>
                          <td><Get url={c.url} member={c.member} installed={c.installed_with} /></td>
                        </tr>
                      ))}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </SubSection>
      <ModelCharacter page={page} />
    </Section>
  )
}

/**
 * The link to one page, rebuilt from the document's own.
 *
 * The build stores `#page=47&zoom=200,55,523&h=792` rather than the whole address, because that is what
 * it is: all 94,170 page links in the index are a suffix of their document's URL, and writing them out
 * was three quarters of the URL text on a part's page. One that is not a suffix is stored whole and
 * says so by starting with a scheme.
 */
export function pageHref(docUrl: string, suffix: string): string {
  return /^[a-z]+:/i.test(suffix) ? suffix : docUrl + suffix
}

/** The kinds of use worth a word beside the line, because they say "not here, really". */
const KIND_LABEL: Partial<Record<UseKind, string>> = {
  mention: 'mentioned',
  advert: 'advert',
  none: 'not this part',
  reference: 'listed',
}

/**
 * One page: the link, and the line saying what the part does there.
 *
 * The line was read off the page by a language model on the maintainer's machine, one call per page. It
 * is reliable about where the part sits — the stage, the board, the list — and was told not to say what
 * the device is for, which it would guess from the type number. A page not summarised yet shows the
 * designators beside the part instead, which is all the index knew before.
 */
function PageLink({ p, docUrl }: { p: PageUse; docUrl: string }) {
  const line = p[4]
  const kind = p[5]
  const label = kind && KIND_LABEL[kind]
  return (
    <li>
      <a href={forViewer(pageHref(docUrl, p[1]))} target="_blank" rel="noopener">page {p[0]}</a>
      {label && <> <span class={`pill ${kind === 'reference' ? 'na' : 'off'}`}>{label}</span></>}
      {line
        ? <span class="line"> {line}</span>
        : p[2] && <span class="muted small"> beside {p[2]}</span>}
    </li>
  )
}

function Document({ d }: { d: PartPage['docs'][0] }) {
  const summary = (
    <>
      <strong>{d.t || d.u}</strong>
      <span class="count">{n(d.p.length)} {d.p.length === 1 ? 'page' : 'pages'}</span>
      {d.schematic ? <span class="pill acc">schematic</span> : null}
      {d.y ? <span class="small muted">{d.y}</span> : null}
      {d.aka ? <span class="small muted">also filed as {d.aka.join(', ')}</span> : null}
      {d.also ? <span class="small muted">also at {d.also.join(', ')}</span> : null}
    </>
  )
  return (
    <Fold summary={summary} level={3}>
      {() => (
        // No link to the document on its own: every page link opens it, at a more useful place.
        // Pages with a line each take a row; bare page links still fit several to a row.
        <ul class={d.p.some((p) => p[4]) ? 'uselist' : 'uselist cols'}>
          {d.p.map((p, j) => <PageLink key={j} p={p} docUrl={d.u} />)}
        </ul>
      )}
    </Fold>
  )
}

/** A group of documents, folded by source: a part with three thousand hits has to stay readable. */
/**
 * A source's documents by date, oldest first: how a magazine's issues are read. The date is as precise
 * as the index has it — `1985-08` or `1985` — so it sorts as text; a document with none goes last, in
 * the order the build gave.
 */
export function byDate(docs: PartPage['docs']): PartPage['docs'] {
  return docs.map((d, i) => [d, i] as const)
    .sort(([a, i], [b, j]) => (a.y ? (b.y ? a.y.localeCompare(b.y) : -1) : (b.y ? 1 : 0)) || i - j)
    .map(([d]) => d)
}

function Group({
  title, anchor, note, docs, sources, open, dated = false,
}: {
  title: string; anchor: string; note: string; docs: PartPage['docs']; sources: string[]; open: boolean
  /** Each source's documents in date order, instead of the most useful first. */
  dated?: boolean
}) {
  if (docs.length === 0) return null
  const bySource = new Map<string, PartPage['docs']>()
  for (const d of docs) {
    const k = sources[d.s] ?? '?'
    const g = bySource.get(k)
    if (g) g.push(d)
    else bySource.set(k, [d])
  }
  const groups = [...bySource.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))
  const pages = docs.reduce((t, d) => t + d.p.length, 0)
  const summary = (
    <>
      <strong>{title}</strong>
      <span class="count">{n(docs.length)} · {n(pages)} pages</span>
      <span class="small muted">{note}</span>
    </>
  )
  return (
    <Fold summary={summary} open={open} level={1} anchor={anchor}>
      {() => groups.map(([source, ds]) => (
        <Fold
          key={source}
          level={2}
          open={groups.length === 1}
          summary={<><strong>{source}</strong> <span class="count">{n(ds.length)}</span></>}
        >
          {() => (dated ? byDate(ds) : ds).map((d, i) => <Document key={i} d={d} />)}
        </Fold>
      ))}
    </Fold>
  )
}

const REPO_HOST = 'https://github.com/'

/** `owner/repo` of a GitHub address, or null for anything else. */
export function repoOf(url: string): string | null {
  if (!url.startsWith(REPO_HOST)) return null
  const [owner, repo] = url.slice(REPO_HOST.length).split('/')
  return owner && repo ? `${owner}/${repo}` : null
}

/**
 * Boards somebody is making: every GitHub repository that places the part, in one list, once each, the
 * most starred first.
 *
 * They are found two ways — sheets the index read page by page (the open-hardware crawls, a journal, a
 * site that links its boards) and projects the research datasets say place the part — and a reader has
 * no use for that distinction, so it is not shown. A repository whose sheets were read opens onto them,
 * each with its page links; the others link to the repository.
 */
function OpenSource({ page, docs }: { page: PartPage; docs: PartPage['docs'] }) {
  type Repo = { name: string; stars: number; forks: number; watchers: number; sheets: number; docs: PartPage['docs'] }
  const all = new Map<string, Repo>()
  const entry = (name: string) => {
    const k = name.toLowerCase()
    let r = all.get(k)
    if (!r) all.set(k, (r = { name, stars: 0, forks: 0, watchers: 0, sheets: 0, docs: [] }))
    return r
  }
  for (const [name, sheets, stars, forks, watchers] of page.repos ?? []) {
    Object.assign(entry(name), { stars, forks, watchers, sheets })
  }
  for (const d of docs) {
    const name = repoOf(d.u)
    if (name) entry(name).docs.push(d)
  }
  for (const [name, [stars, forks, watchers]] of Object.entries(page.stars ?? {})) {
    const r = all.get(name.toLowerCase())
    if (r && !r.stars) Object.assign(r, { stars, forks, watchers })
  }
  if (!all.size) return null
  const list = [...all.values()].sort((a, b) =>
    b.stars - a.stars || Math.max(b.docs.length, b.sheets) - Math.max(a.docs.length, a.sheets) || a.name.localeCompare(b.name))
  const more = Math.max(0, (page.n.repos ?? 0) - (page.repos?.length ?? 0))
  const summary = (
    <>
      <strong>Open-source projects</strong>
      <span class="count">{n(list.length + more)}</span>
      <span class="small muted">boards on GitHub that place this part, the most starred first</span>
    </>
  )
  const Stars = ({ r }: { r: Repo }) => (r.stars > 0
    ? <span class="muted small" title={`${n(r.stars)} stars, ${n(r.forks)} forks, ${n(r.watchers)} watching`}>★{n(r.stars)}</span>
    : null)
  const Out = ({ r }: { r: Repo }) => (
    <a class="out" href={`${REPO_HOST}${r.name}`} target="_blank" rel="noopener" title="Open the repository on GitHub"
      onClick={(e) => e.stopPropagation()}>↗ GitHub</a>
  )
  return (
    <Fold summary={summary} level={1} open={page.docs.length === docs.length} anchor="open-source">
      {() => (
        <div class="repolist">
          {list.map((r) => {
            const sheets = Math.max(r.docs.length, r.sheets)
            const count = sheets > 1 && <span class="count">{n(sheets)} sheets</span>
            return r.docs.length ? (
              <Fold
                key={r.name} level={2} cls="repo"
                summary={<><strong>{r.name}</strong><Out r={r} /><Stars r={r} />{count}</>}
              >
                {() => r.docs.map((d, i) => <Document key={i} d={{ ...d, t: d.t.replace(`${r.name}: `, '') }} />)}
              </Fold>
            ) : (
              <div class="plain" key={r.name}>
                <strong>{r.name}</strong><Out r={r} /><Stars r={r} />{count}
              </div>
            )
          })}
          {more > 0 && <p class="muted small">and {n(more)} more on GitHub, with fewer stars</p>}
        </div>
      )}
    </Fold>
  )
}

const SITE_KINDS = new Set(['site', 'factory', 'reference'])
const PAPER_KINDS = new Set(['magazine', 'book'])

/**
 * Where the part is used, in three groups: what somebody built, what a magazine or a book printed, and
 * the boards on GitHub. A source of any other kind is not shown; the build already leaves those out.
 */
function Uses({ page, sources, kinds }: { page: PartPage; sources: string[]; kinds: string[] }) {
  const kindOf = (d: PartPage['docs'][0]) => kinds[d.s] ?? ''
  const repos = page.docs.filter((d) => repoOf(d.u))
  const others = page.docs.filter((d) => !repoOf(d.u))
  const built = others.filter((d) => SITE_KINDS.has(kindOf(d)))
  const paper = others.filter((d) => PAPER_KINDS.has(kindOf(d)))
  if (built.length + paper.length + repos.length === 0 && !page.repos?.length && !page.about?.books?.length) return null
  return (
    <Section title="Where it is used" anchor="where-used">
      <Group
        title="Projects and factory schematics" anchor="projects" open
        note="project sites, factory archives and reference works"
        docs={built} sources={sources}
      />
      <Group
        title="Magazines and books" anchor="magazines" open={built.length === 0} dated
        note="the exact page of the PDF; each magazine's issues in date order"
        docs={paper} sources={sources}
      />
      <OpenSource page={page} docs={repos} />
      <Databooks page={page} />
    </Section>
  )
}

/**
 * Who vouches for a part the index has nothing of its own for.
 *
 * Without this a reader who looks up an EFT83 is told nothing at all. "Sold by musikding.de under
 * Transistoren / Germanium Transistoren / Selektiert, PNP, hFE 40–50" is an answer, and it is also this
 * project's own note of what to look for next.
 */
function Listed({ page }: { page: PartPage }) {
  const listed = page.listed
  if (!listed?.length) return null
  return (
    <section class="stack-s">
      <Heading slug="who-lists">Who lists this part</Heading>
      <ul class="uselist">
        {listed.map((l, i) => (
          <li key={i}>
            <strong>{l.source}</strong>
            {l.category && <span class="muted"> · {l.category}</span>}
            {l.note && <span class="muted"> · {l.note}</span>}
          </li>
        ))}
      </ul>
    </section>
  )
}

/** Whether a part page and the index it is read with were built from the same list of sources. A page
 *  without a stamp is from before there were stamps, and is read as it always was. */
export function sameSources(page: { ss?: string } | null, stamp: string | undefined): boolean {
  return !page?.ss || !stamp || page.ss === stamp
}

export function Detail({ part, kind, sources, kinds, stamp, onStale }: {
  /** What kind of part it is, as the list's type column says it. */
  part: string; kind: string; sources: string[]; kinds: string[]; stamp?: string
  /** Fetch the index again, past every cache; settles when the new one is in. */
  onStale?: (stamp: string) => Promise<unknown>
}) {
  const [page, setPage] = useState<PartPage | null>(null)
  const [error, setError] = useState(false)
  // The index is asked for again once per part. If what comes back still has another list of sources, the
  // two files are from different builds — a deploy half done, or a build stopped half way on this
  // machine — and waiting longer will not change that, so the page says so instead of waiting for ever.
  const [reload, setReload] = useState<'idle' | 'asked' | 'done'>('idle')

  useEffect(() => {
    setPage(null)
    setError(false)
    setReload('idle')
    fetch(`${DATA}/part/${partPath(part)}.json`)
      .then((r) => (r.ok ? (r.json() as Promise<PartPage>) : Promise.reject(r.status)))
      .then(setPage)
      .catch(() => setError(true))
  }, [part])
  const fresh = sameSources(page, stamp)
  useEffect(() => {
    if (!page?.ss || fresh || reload !== 'idle') return
    setReload('asked')
    const done = () => setReload('done')
    if (onStale) onStale(page.ss).then(done, done)
    else done()
  }, [page, fresh, reload])

  return (
    <section class="evidence stack">
      <div class="ptitle">
        <h1>{part}</h1>
        {page?.models?.kind && <span class="chip">{page.models.kind}</span>}
      </div>
      {error && <p class="muted">Nothing is published for {part} yet.</p>}
      {!error && !page && <Loading what={`the page of ${part}`} />}
      {page && (
        <>
          <AboutPart page={page} kind={kind} />
          <Listed page={page} />
          <Models page={page} />
          {fresh ? <Uses page={page} sources={sources} kinds={kinds} />
            : reload === 'done' ? (
              <p class="muted">
                Where {part} is used cannot be shown: its page and the parts list come from two different builds
                of the site, so the sources its documents point at would be named wrongly. Reload the page in a
                few minutes.
              </p>
            ) : <Loading what="the list of sources" />}
          {page.docs.length === 0 && !page.models && (
            <p class="muted">
              No SPICE model published and no schematic indexed yet
              {page.listed?.length ? ', which makes it one to look for.' : '.'}
            </p>
          )}
        </>
      )}
    </section>
  )
}

const SIDE = { min: 260, fallback: 480, key: 'sei.side' }

/** The list's width, as the reader last left it. Kept in this browser only, and only as a convenience. */
function savedWidth(): number {
  try { return Number(localStorage.getItem(SIDE.key)) || SIDE.fallback } catch { return SIDE.fallback }
}

/**
 * The bar between the list and the part: drag it, or focus it and use the arrow keys.
 *
 * The width is a CSS variable on the browser, so the grid does the layout and nothing re-renders the
 * fifty thousand rows while it moves.
 */
function Splitter({ host, width, setWidth }: {
  host: { current: HTMLDivElement | null }; width: number; setWidth: (w: number) => void
}) {
  const clamp = (w: number) => Math.round(Math.min(Math.max(w, SIDE.min), innerWidth * 0.7))
  const commit = (w: number) => {
    setWidth(w)
    try { localStorage.setItem(SIDE.key, String(w)) } catch { /* private window: forget it */ }
  }
  const onDown = (e: PointerEvent) => {
    const bar = e.currentTarget as HTMLElement
    const left = host.current?.getBoundingClientRect().left ?? 0
    bar.setPointerCapture(e.pointerId)
    let w = width
    const move = (ev: PointerEvent) => {
      w = clamp(ev.clientX - left)
      host.current?.style.setProperty('--side', `${w}px`)
    }
    const up = () => {
      bar.removeEventListener('pointermove', move)
      bar.removeEventListener('pointerup', up)
      commit(w)
    }
    bar.addEventListener('pointermove', move)
    bar.addEventListener('pointerup', up)
    e.preventDefault()
  }
  const onKey = (e: KeyboardEvent) => {
    const step = e.shiftKey ? 80 : 20
    if (e.key === 'ArrowLeft') commit(clamp(width - step))
    else if (e.key === 'ArrowRight') commit(clamp(width + step))
    else return
    e.preventDefault()
  }
  return (
    <div
      class="splitter" role="separator" aria-orientation="vertical" aria-label="Resize the list"
      aria-valuenow={width} tabIndex={0} onPointerDown={onDown} onKeyDown={onKey}
    />
  )
}

export function Browser({ part, onPick }: { part: string | null; onPick: (p: string | null) => void }) {
  const [index, setIndex] = useState<PartIndex | null>(null)
  const [q, setQ] = useState('')
  const [by, setBy] = useState<Sort>('documents')
  const [dir, setDir] = useState<Dir>(NATURAL.documents)
  const [device, setDevice] = useState('')
  const [shown, setShown] = useState(PAGE)
  const [width, setWidth] = useState(savedWidth)
  const host = useRef<HTMLDivElement>(null)

  useEffect(() => { loadIndex().then(setIndex) }, [])

  const searching = q.trim().length >= 2
  const list = useMemo(() => {
    if (!index) return []
    const kept = ofDevice(index.parts, device, index.deviceKinds)
    return searching ? search(kept, q, by, dir) : order(kept, by, dir)
  }, [index, q, by, dir, device, searching])
  useEffect(() => setShown(PAGE), [q, by, dir, device])
  const kind = useMemo(() => {
    const r = index && part ? index.parts.find((p) => p[0] === part) : undefined
    return r && index ? typeOf(r, index.deviceKinds) : ''
  }, [index, part])

  /** A column's header: the first click orders by it, the next turns the order round. */
  const sortBy = (key: Sort) => {
    if (key === by) setDir(dir === 'asc' ? 'desc' : 'asc')
    else { setBy(key); setDir(NATURAL[key]) }
  }

  return (
    <div
      ref={host}
      class={`browser${part ? ' has-part' : ''}`}
      style={{ '--side': `${width}px` } as Record<string, string>}
    >
      <aside class="side">
        <input
          type="search"
          value={q}
          placeholder="Part number — 12AX7, BC108, TL072…"
          aria-label="Search by part number"
          onInput={(e) => setQ((e.target as HTMLInputElement).value)}
        />
        <select
          aria-label="Kind of device"
          value={device}
          onChange={(e) => setDevice((e.target as HTMLSelectElement).value)}
        >
          <option value="">Every kind of device</option>
          {(index?.deviceKinds ?? []).map((d) => (
            // a finer entry is indented under its device; an em space survives where a space would not
            d.n > 0 ? <option key={d.key} value={d.key}>{d.parent ? '\u2003' : ''}{d.label} ({n(d.n)})</option> : null
          ))}
        </select>
        <p class="count">
          {!index ? <Loading what="the parts list" inline />
            : searching ? `${n(list.length)} match ${q} · closest first`
              : `${n(list.length)} parts · click a heading to sort`}
        </p>
        <div class="plist">
          <table>
            <thead>
              <tr>
                {COLUMNS.map((c) => [c.key === 'documents' && <th key="type" class="type">Type</th>,
                  <th
                    key={c.key}
                    class={c.num ? 'num' : undefined}
                    aria-sort={by === c.key ? (dir === 'asc' ? 'ascending' : 'descending') : undefined}
                  >
                    <button type="button" title={c.title} onClick={() => sortBy(c.key)}>
                      {c.label}
                      <span class="arrow" aria-hidden="true">{by === c.key ? (dir === 'asc' ? '▲' : '▼') : ''}</span>
                    </button>
                  </th>])}
              </tr>
            </thead>
            <tbody>
              {list.slice(0, shown).map((r) => (
                <tr
                  key={r[0]}
                  class={r[0] === part ? 'clickable sel' : 'clickable'}
                  onClick={() => onPick(r[0])}
                >
                  <td>
                    <a
                      class="pn"
                      href={`?part=${encodeURIComponent(r[0])}`}
                      aria-current={r[0] === part ? 'true' : undefined}
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); onPick(r[0]) }}
                    >
                      {r[0]}
                    </a>
                  </td>
                  {(() => {
                    const t = index ? typeOf(r, index.deviceKinds) : ''
                    return <td class="type" title={t}>{t}</td>
                  })()}
                  <td class="num">{r[1] ? n(r[1]) : '—'}</td>
                  <td class="num">{r[3] ? n(r[3]) : '—'}</td>
                  <td class="num">{r[6] ? n(r[6]) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {list.length > shown && (
            <button class="more" onClick={() => setShown((v) => v + PAGE * 2)}>
              {n(list.length - shown)} more
            </button>
          )}
        </div>
      </aside>

      <Splitter host={host} width={width} setWidth={setWidth} />

      {part ? (
        <Detail
          part={part} kind={kind} sources={index?.sources ?? []} kinds={index?.kinds ?? []} stamp={index?.sourcesStamp}
          onStale={(s) => reloadIndex(s).then(setIndex)}
        />
      ) : (
        <section class="evidence stack-s prose">
          <p class="eyebrow">All parts</p>
          <h2>Pick a part from the list</h2>
          <p class="muted">
            Each one shows where it is used in real schematics — with a link that opens the sheet at the
            place the part is, not at the front — which SPICE models exist for it and where each comes
            from, and the data sheets that describe it.
          </p>
        </section>
      )}
      <button class="back" onClick={() => onPick(null)}>← all parts</button>
    </div>
  )
}
