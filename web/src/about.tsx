/**
 * What a part is, and the pages that explain it: families, naming schemes, organisations.
 *
 * Everything shown here names where it came from. A part's name is read under a standard, and the page
 * links the standard; a family comes from a maker's sheet or from the kind the part is filed as, and the
 * page says which; a date is the oldest dated document in this index that prints the part, and says it
 * is a floor. A piece nothing vouches for is not drawn at all — the absence is the honest answer.
 */
import type preact from 'preact'
import { Fragment } from 'preact'
import { useEffect, useMemo, useState } from 'preact/hooks'

import { Heading } from './anchor'
import { follow, loadCatalogue, loadIndex } from './data'
import { Loading } from './loading'
import { Fold, Section } from './fold'
import type { Catalogue, Family, PartIndex, PartPage, PartRow } from './types'

const nf = (v: number) => v.toLocaleString('en-GB')
export const partHref = (p: string) => `?part=${encodeURIComponent(p)}`

/** The families by id. The catalogue sends them as a list to keep their order. */
const byId = new WeakMap<Catalogue, Record<string, Family>>()
function fams(cat: Catalogue): Record<string, Family> {
  let m = byId.get(cat)
  if (!m) {
    m = Object.fromEntries(cat.families.map((f) => [f.id, f]))
    byId.set(cat, m)
  }
  return m
}

export function useCatalogue(): Catalogue | null {
  const [cat, setCat] = useState<Catalogue | null>(null)
  useEffect(() => { loadCatalogue().then(setCat) }, [])
  return cat
}

function useIndex(): PartIndex | null {
  const [idx, setIdx] = useState<PartIndex | null>(null)
  useEffect(() => { loadIndex().then(setIdx) }, [])
  return idx
}

/** A link inside the site: no reload, and a middle click still opens a tab. */
export function A({ href, children }: { href: string; children: preact.ComponentChildren }) {
  return <a href={href} onClick={(e) => follow(e as unknown as MouseEvent, href)}>{children}</a>
}

/** The references behind a statement, as their ids, each linking to the source with its title on hover. */
export function Refs({ ids, cat }: { ids?: string[]; cat: Catalogue }) {
  const known = (ids ?? []).flatMap((id) => { const r = cat.refs[id]; return r ? [[id, r] as const] : [] })
  if (!known.length) return null
  return (
    <span class="refs">
      {known.map(([id, r], i) => {
        return (
          <span key={id}>
            {i > 0 && ' '}
            <a href={r.url} target="_blank" rel="noopener" title={`${r.title} — ${r.author}`}>{id}</a>
          </span>
        )
      })}
    </span>
  )
}

/** A source that is not in the reference list: a page read for one fact. */
function Source({ src, cat }: { src?: string; cat: Catalogue }) {
  if (!src) return null
  if (cat.refs[src]) return <Refs ids={[src]} cat={cat} />
  let host = src
  try { host = new URL(src).hostname.replace(/^www\./, '') } catch { /* not a URL */ }
  return <a class="refs" href={src} target="_blank" rel="noopener">{host}</a>
}

function MakerName({ id, cat }: { id: string; cat: Catalogue }) {
  const m = cat.makers[id]
  if (!m) return <>{id}</>
  return (
    <>
      <A href={`?maker=${id}`}>{m.name}</A>
      {m.country && <span class="muted"> ({m.country})</span>}
    </>
  )
}

const label = (id: string, cat: Catalogue) => fams(cat)[id]?.label ?? id

/** The families above this one, outermost first. */
function lineage(id: string, cat: Catalogue): string[] {
  const out: string[] = []
  let at: string | undefined = id
  while (at && fams(cat)[at] && !out.includes(at)) {
    out.unshift(at)
    at = fams(cat)[at]?.broader
  }
  return out
}

/**
 * The box under the part's name: what kind of part it is, in the parts list's words and then what its
 * name says it was designed for; what each piece of the name says under the standard that assigned it;
 * and the other grades of the same type. The reading used to sit on the name itself, one hover per
 * piece; written out, it is read without hunting for it.
 */
function PartInfo({ page, kind }: { page: PartPage; kind: string }) {
  const a = page.about
  const line = [kind, a?.name?.use].filter(Boolean).join(' ')
  const pieces = (a?.name?.segments ?? []).filter(([text]) => text)
  const variants = a?.variants ?? []
  if (!line && !pieces.length && !a?.base && !variants.length) return null
  return (
    <div class="pinfo">
      {line && <p class="pkind">{line}</p>}
      {pieces.length > 0 && a?.name && (
        <dl class="reading">
          {pieces.map(([text, field, meaning], i) => (
            <Fragment key={i}><dt>{text}</dt><dd><span class="field">{field}</span> {meaning}</dd></Fragment>
          ))}
          <dd class="muted small">Read under <A href={`?scheme=${a.name.scheme}`}>{a.name.label}</A></dd>
        </dl>
      )}
      {(a?.base || variants.length > 0) && (
        <p class="small">
          <span class="muted">{a?.base ? 'Same type as ' : 'Variants: '}</span>
          {a?.base && <><A href={partHref(a.base)}>{a.base}</A>{variants.length ? ', ' : ''}</>}
          {variants.map((v, i) => <span key={v}>{i > 0 && ', '}<A href={partHref(v)}>{v}</A></span>)}
        </p>
      )}
    </div>
  )
}

/** What each source of a data sheet is, in words. */
const VIA: Record<string, string> = {
  models: 'the model curation',
  ti_products: "TI's product page",
  renesas_products: "Renesas' product page",
  ti_datasheets: "TI's data sheet index",
  frank_pocnet: "Frank Philipse's tube archive",
  onsemi_docs: "onsemi's data sheet list, read",
  nxp_docs: "NXP's data sheet list, read",
  that_datasheets: "THAT's data sheet page, read",
  jj_datasheets: "JJ's download page, read",
  linearsystems_datasheets: "Linear Systems' product pages, read",
  diotec_products: "Diotec's product tables",
  toshiba_parametric: "Toshiba's parametric tables",
  infineon_tables: "Infineon's product tables",
  st_wayback: "ST's addresses in the Internet Archive, read",
  adi_wayback: "Analog Devices' addresses in the Internet Archive, read",
  archive_databooks: "a databook the Internet Archive holds",
  archive_databooks_more: "a databook the Internet Archive holds",
  cq_tables: "CQ Publishing's device tables, in the Internet Archive",
  data_tables: "D.A.T.A. device tables, in the Internet Archive",
  wrh_books: "a data book World Radio History holds",
  archive_manuallib: "a single sheet the Internet Archive holds",
  datasheet_live: "a copy held by datasheet.live (not the maker's file)",
}

function fileName(url: string): string {
  try { return decodeURIComponent(new URL(url).pathname.split('/').pop() || url) } catch { return url }
}

/**
 * Every data sheet known for the part, grouped by the company that printed it.
 *
 * All of them, not the best one: the same valve described by General Electric, Tung-Sol and Philips is
 * three chances to catch a misprint, and the later work of measuring a model against its sheet wants
 * exactly that redundancy. Each link says where it was found.
 */
const KIN: Record<string, string> = {
  grade: 'the type this is a selected grade of',
  packing: 'the same part, packed differently',
  package: 'the same part in another package',
  brand: 'the type this is a brand of',
  envelope: 'the same valve, filed by its envelope or revision',
  "maker's name": "a maker's name for this number",
}

/** Sheets that document the part under another name: its type, or a maker's name for the bare number. */
function KinSheets({ page }: { page: PartPage }) {
  const kin = page.about?.kin
  if (!kin?.length) return null
  return (
    <section class="stack-s">
      <Heading slug="other-names">Sheets under another name</Heading>
      <ul class="uselist">
        {kin.map(([name, why, rows]) => (
          <li key={name}>
            <strong><a href={`?part=${encodeURIComponent(name)}`}>{name}</a></strong>
            <span class="muted small"> · {KIN[why] ?? why}</span>
            <ul class="sheetlist">
              {rows.map(([url, maker, text, title, via, , copy], i) => (
                <li key={i}>
                  <a href={url} target="_blank" rel="noopener">{title || fileName(url)}</a>
                  <span class="muted small"> · {maker || text || 'maker not stated'} · via {VIA[via] ?? via}
                    {copy && <> · <a href={copy} target="_blank" rel="noopener">archived copy</a></>}</span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  )
}

function Datasheets({ page, cat }: { page: PartPage; cat: Catalogue }) {
  const sheets = page.about?.sheets ?? []
  if (!sheets.length && !page.about?.kin?.length) return null
  const groups = new Map<string, typeof sheets>()
  for (const s of sheets) {
    const key = s[1] || s[2] || 'unknown'
    const g = groups.get(key)
    if (g) g.push(s)
    else groups.set(key, [s])
  }
  const ordered = [...groups.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))
  return (
    <Section title="Data sheets" anchor="data-sheets">
      {sheets.length > 0 && <ul class="uselist">
        {ordered.map(([key, rows]) => (
          <li key={key}>
            <strong>{cat.makers[key] ? <MakerName id={key} cat={cat} /> : (rows[0]?.[2] || 'Maker not stated')}</strong>
            <ul class="sheetlist">
              {rows.map(([url, , , title, via, note, copy], i) => (
                <li key={i}>
                  <a href={url} target="_blank" rel="noopener">{title || fileName(url)}</a>
                  <span class="muted small"> · via {VIA[via] ?? via}{note && <> · {note}</>}
                    {copy && <> · <a href={copy} target="_blank" rel="noopener">archived copy</a></>}</span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>}
      <KinSheets page={page} />
      <p class="muted small">
        Links only: each sheet stays where its publisher or archive keeps it.{' '}
        <a href={`https://www.alldatasheet.com/view.jsp?Searchword=${encodeURIComponent(page.part)}`} target="_blank" rel="noopener">Search alldatasheet</a>
        {' '}or{' '}
        <a href={`https://www.datasheetarchive.com/?q=${encodeURIComponent(page.part.toLowerCase())}`} target="_blank" rel="noopener">Datasheet Archive</a>
        {' '}for more — searches, not checked links.
      </p>
    </Section>
  )
}

/**
 * The pages of old databooks and device tables that print the part, folded shut at the foot of the page.
 *
 * They are sheets too, but a TL072 is on forty of them, bound together decades ago, and listed among the
 * makers' own sheets they buried the one a reader wants first. Folded by the archive that holds them.
 */
export function Databooks({ page }: { page: PartPage }) {
  const books = page.about?.books
  if (!books?.length) return null
  const byVia = new Map<string, typeof books>()
  for (const b of books) {
    const k = VIA[b[4]] ?? b[4]
    const g = byVia.get(k)
    if (g) g.push(b)
    else byVia.set(k, [b])
  }
  const groups = [...byVia.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))
  const summary = (
    <>
      <strong>Databooks</strong>
      <span class="count">{nf(books.length)} {books.length === 1 ? 'page' : 'pages'}</span>
      <span class="small muted">pages of old databooks and device tables that print it</span>
    </>
  )
  return (
    <section class="stack-s">
      <Fold summary={summary} level={1} anchor="databooks">
        {() => groups.map(([via, rows]) => (
          <Fold
            key={via} level={2} open={groups.length === 1}
            summary={<><strong>{via}</strong> <span class="count">{nf(rows.length)}</span></>}
          >
            {() => (
              <ul class="uselist">
                {rows.map(([url, , maker, title, , note, copy], i) => (
                  <li key={i}>
                    <a href={url} target="_blank" rel="noopener">{title || fileName(url)}</a>
                    <span class="muted small">{maker && <> · {maker}</>}{note && <> · {note}</>}
                      {copy && <> · <a href={copy} target="_blank" rel="noopener">archived copy</a></>}</span>
                  </li>
                ))}
              </ul>
            )}
          </Fold>
        ))}
      </Fold>
    </section>
  )
}

/** The top of a part's page, under its name: what it is, then its data sheets. `kind` is the parts list's. */
/** How a relation reads from this part's side ("out") and from the other's ("in" or "both"). */
export const RELATED: Record<string, [string, string]> = {
  replacement_for: ['a replacement for', 'replaced by'],
  next_generation_of: ['the next generation of', 'succeeded by'],
  same_product_as: ['the same product as', 'the same product as'],
  same_datasheet: ['documented in one data sheet with', 'documented in one data sheet with'],
}

export function relationWords(relation: string, direction: 'out' | 'in' | 'both'): string {
  const pair = RELATED[relation]
  if (!pair) return `${relation.replace(/_/g, ' ')} ${direction === 'out' ? '→' : '←'}`
  return direction === 'out' ? pair[0] : pair[1]
}

/**
 * The other parts a document relates this one to — a declared replacement, the next generation, the
 * same product under another name, one data sheet for several — each with the document that says so.
 * `data/parts/relations.csv`; a row without a reference is refused there, so every line here has one.
 */
function Related({ page, cat }: { page: PartPage; cat: Catalogue }) {
  const rel = page.about?.related
  if (!rel?.length) return null
  return (
    <section class="stack-s">
      <Heading slug="related">Related parts</Heading>
      <ul class="uselist">
        {rel.map(([relation, other, direction, refs, note, status], i) => (
          <li key={i}>
            {relationWords(relation, direction)} <strong><A href={partHref(other)}>{other}</A></strong>
            {note && <span class="muted small"> · {note}</span>}
            {' '}<Refs ids={refs} cat={cat} />
            {status === 'draft' && <> <span class="chip" title="recorded with its source, not yet reviewed">draft</span></>}
          </li>
        ))}
      </ul>
    </section>
  )
}

export function AboutPart({ page, kind }: { page: PartPage; kind: string }) {
  const cat = useCatalogue()
  return (
    <>
      <PartInfo page={page} kind={kind} />
      {cat && <Related page={page} cat={cat} />}
      {cat && page.about && <Datasheets page={page} cat={cat} />}
    </>
  )
}

// --- the pages the part page links to -------------------------------------------------------------

function children(id: string, cat: Catalogue): string[] {
  return cat.families.map((f) => f.id).filter((k) => fams(cat)[k]?.broader === id)
}

function below(id: string, cat: Catalogue): Set<string> {
  const out = new Set([id])
  for (const c of children(id, cat)) for (const d of below(c, cat)) out.add(d)
  return out
}

function members(id: string, cat: Catalogue, idx: PartIndex): PartRow[] {
  const ids = below(id, cat)
  const at = new Set((idx.families ?? []).flatMap((f, i) => (ids.has(f) ? [i] : [])))
  return idx.parts.filter((r) => r.length > 5 && at.has(r[5] as number)).sort((a, b) => b[1] - a[1])
}

function PartList({ rows, limit = 120 }: { rows: PartRow[]; limit?: number }) {
  if (!rows.length) return <p class="muted">No part in this index is filed here yet.</p>
  return (
    <>
      <ul class="uselist cols">
        {rows.slice(0, limit).map((r) => (
          <li key={r[0]}>
            <A href={partHref(r[0])}>{r[0]}</A>
            <span class="muted small"> · {nf(r[1])} doc{r[1] === 1 ? '' : 's'}{r[3] ? ` · ${r[3]}m` : ''}</span>
          </li>
        ))}
      </ul>
      {rows.length > limit && <p class="muted small">and {nf(rows.length - limit)} more, most used first.</p>}
    </>
  )
}

function RefList({ ids, cat }: { ids?: string[]; cat: Catalogue }) {
  const known = (ids ?? []).flatMap((id) => { const r = cat.refs[id]; return r ? [[id, r] as const] : [] })
  if (!known.length) return null
  return (
    <section class="stack-s">
      <h3>Sources</h3>
      <ul class="uselist">
        {known.map(([id, r]) => {
          return (
            <li key={id}>
              <span class="chip">{id}</span> <a href={r.url} target="_blank" rel="noopener">{r.title}</a>
              <span class="muted"> — {r.author}</span>
              <div class="muted small">{r.consulted}{r.link !== 'ok' && <> · link: {r.link}</>}</div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function Examples({ label, parts, idx, note }: { label: string; parts?: string[]; idx: PartIndex | null; note?: string }) {
  if (!parts?.length) return null
  const have = new Set(idx?.parts.map((r) => r[0]) ?? [])
  return (
    <p>
      <b>{label}</b>{' '}
      {parts.map((p, i) => (
        <span key={p}>{i > 0 && ', '}{have.has(p) ? <A href={partHref(p)}>{p}</A> : p}</span>
      ))}
      {note && <span class="muted small"> — {note}</span>}
    </p>
  )
}

export function FamilyPage({ id }: { id: string }) {
  const cat = useCatalogue()
  const idx = useIndex()
  const list = useMemo(() => (cat && idx ? members(id, cat, idx) : []), [cat, idx, id])
  if (!cat) return <Loading what="the catalogue of families" />
  const f: Family | undefined = fams(cat)[id]
  if (!f) return <p class="muted">No family called {id}.</p>
  const chain = lineage(id, cat)
  const kids = children(id, cat)
  return (
    <div class="stack prose-wide">
      <div class="stack-s">
        <p class="eyebrow">
          Family
          {chain.slice(0, -1).map((c) => <span key={c}> › <A href={`?family=${c}`}>{label(c, cat)}</A></span>)}
        </p>
        <h2>{f.label}</h2>
        <p class="lede">{f.definition}</p>
        {f.question && <p class="why">{f.question}</p>}
      </div>
      {f.key_params?.length ? (
        <section class="stack-s">
          <h3>What to compare</h3>
          <p>{f.key_params.map((k) => <span key={k} class="chip">{k}</span>).reduce<preact.ComponentChildren[]>((a, c, i) => (i ? [...a, ' ', c] : [c]), [])}</p>
        </section>
      ) : null}
      <Examples label="Examples:" parts={f.examples} idx={idx} />
      <Examples label="Outside this index:" parts={f.external} idx={null} note="worth knowing, not yet in any document indexed here" />
      {kids.length > 0 && (
        <section class="stack-s">
          <h3>Inside this family</h3>
          <ul class="uselist cols">
            {kids.map((k) => (
              <li key={k}><A href={`?family=${k}`}>{label(k, cat)}</A>
                <div class="muted small">{fams(cat)[k]?.definition}</div></li>
            ))}
          </ul>
        </section>
      )}
      <section class="stack-s">
        <h3>Parts filed here</h3>
        {idx
          ? <p class="muted small">{nf(list.length)} parts, by the family their maker's sheet gives or, failing that, the kind they are filed as.</p>
          : <Loading what="the parts list" small />}
        {idx && <PartList rows={list} />}
      </section>
      <RefList ids={f.refs} cat={cat} />
    </div>
  )
}

export function SchemePage({ id }: { id: string }) {
  const cat = useCatalogue()
  if (!cat) return <Loading what="the catalogue of naming schemes" />
  const s = cat.schemes[id]
  if (!s) return <p class="muted">No naming scheme called {id}.</p>
  const others = Object.keys(cat.schemes).filter((k) => k !== id)
  return (
    <div class="stack prose-wide">
      <div class="stack-s">
        <p class="eyebrow">How part numbers are made</p>
        <h2>{s.label}</h2>
        <p class="lede">{s.summary}</p>
        <p class="muted small">
          For example {s.forms.map((f, i) => <span key={f.example}>{i > 0 && ', '}<A href={partHref(f.example)}>{f.example}</A></span>)}.
        </p>
      </div>
      {s.fields.map(([key, f]) => {
        const table = f.values ?? f.each ?? f.tokens
        return (
          <section class="stack-s" key={key}>
            <h3>{f.label}</h3>
            {f.meaning && <p>{f.meaning}{f.optional && <span class="muted small"> (not always there)</span>}</p>}
            {f.each && <p class="muted small">One letter for each part of the device, in alphabetical order.</p>}
            {table && (
              <div class="tablewrap">
                <table>
                  <tbody>
                    {Object.entries(table).map(([k, v]) => (
                      <tr key={k}><td><code>{k === '' ? '(none)' : k}</code></td><td>{v}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {f.ranges && (
              <div class="tablewrap">
                <table>
                  <tbody>
                    {f.ranges.map(([lo, hi, m]) => (
                      <tr key={lo}><td><code>{lo === hi ? lo : `${lo}–${hi}`}</code></td><td>{m}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )
      })}
      {s.caveats?.length ? (
        <section class="stack-s">
          <h3>What the code does not say</h3>
          <ul>{s.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
        </section>
      ) : null}
      <RefList ids={s.refs} cat={cat} />
      <p class="muted small">
        Other schemes: {others.map((k, i) => <span key={k}>{i > 0 && ' · '}<A href={`?scheme=${k}`}>{cat.schemes[k]?.label ?? k}</A></span>)}
      </p>
    </div>
  )
}

export function MakerPage({ id }: { id: string }) {
  const cat = useCatalogue()
  if (!cat) return <Loading what="the catalogue of organisations" />
  const m = cat.makers[id]
  if (!m) return <p class="muted">No organisation called {id}.</p>
  const named = new Set((m.events ?? []).map((e) => e[2]))
  const mentioned = Object.entries(cat.makers)
    .filter(([k, o]) => k !== id && !named.has(k) && (o.events ?? []).some((e) => e[2] === id))
  return (
    <div class="stack prose-wide">
      <div class="stack-s">
        <p class="eyebrow">Organisation</p>
        <h2>{m.name}</h2>
        <dl class="kv">
          {m.country && <><dt>Headquarters</dt><dd>{m.country}{m.hq_as_of && <span class="muted small"> · read {m.hq_as_of}</span>}</dd></>}
          {m.founded && <><dt>Founded</dt><dd>{m.founded}</dd></>}
          {m.source && <><dt>Source</dt><dd><Source src={m.source} cat={cat} /></dd></>}
        </dl>
        {!m.country && !m.founded && <p class="muted">Nothing is recorded about it yet beyond its name.</p>}
        <p class="muted small">Where an organisation is headquartered is not where a given part was made.</p>
      </div>
      {m.events?.length ? (
        <section class="stack-s">
          <h3>What happened to it</h3>
          <ul class="uselist">
            {m.events.map(([year, what, other, src], i) => (
              <li key={i}>
                <b>{year ?? 'undated'}</b> {what}{other && <> <MakerName id={other} cat={cat} /></>}
                {' '}<Source src={src} cat={cat} />
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {mentioned.length > 0 && (
        <p class="muted small">
          Also in the history of {mentioned.map(([k], i) => <span key={k}>{i > 0 && ', '}<MakerName id={k} cat={cat} /></span>)}.
        </p>
      )}
    </div>
  )
}
