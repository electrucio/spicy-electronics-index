/**
 * The Projects tab: documents found by the parts they use together, the parts the reader has, the families
 * left out, the sources and the words of their titles.
 *
 * The question is built on the left a block at a time, each condition a chip that says itself and goes with
 * a click; the answers are on the right, one card per document or magazine page, each part on it marked by
 * what the reader has of it. Everything is computed in the browser from two files fetched when the tab first
 * opens (`find.ts`, `web/finder.py`), and the question lives in the address, so a search can be sent to
 * somebody — all of it but the reader's own parts, which stay in this browser unless they choose to share.
 */
import { useEffect, useMemo, useRef, useState } from 'preact/hooks'

import { relationWords, useCatalogue } from './about'
import { follow, loadFinder, loadIndex, reloadIndex } from './data'
import {
  AFTER, EXACT, GRADE, SAME, SCHEMATIC, SUBST, answer, asked, coverage, decode, fold, holds, lineage, pasted, readQuery,
  resolver, sameBuild, termOf, writeQuery, type Context, type Hit, type Query, type Sort, type Tier,
} from './find'
import { forViewer } from './links'
import { Loading } from './loading'
import { Splitter, n, savedWidth, search } from './parts'
import type { Catalogue, Family, FinderDocs, FinderUnits, PartIndex } from './types'
import { UsageFilter } from './usagefilter'
import { keysFor, loadShard, unitsOfWord, words as wordsOf } from './words'

const PAGE = 40
const HAVE_KEY = 'sei.find.have'
/** The last question asked here, for the tab to come back to it from a part's page. */
export const LAST_KEY = 'sei.find.last'

const ROLE_LABEL: Record<string, string> = {
  schematic: 'Schematics', project_page: 'Project pages', article: 'Articles', figure: 'Figures',
  service_manual: 'Service manuals', issue: 'Magazine pages', book: 'Book pages',
}
const ERA_LABEL: Record<string, string> = { modern: 'Modern', mixed: 'Mixed', vintage: 'Vintage', '': 'Not said' }
const SORT_LABEL: Record<Sort, string> = { best: 'Best match', missing: 'Fewest missing', newest: 'Newest first', oldest: 'Oldest first' }

/** The parts the reader keeps here: a convenience of this browser, never sent anywhere. */
function savedHave(): string[] {
  try {
    const v: unknown = JSON.parse(localStorage.getItem(HAVE_KEY) ?? '[]')
    return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : []
  } catch { return [] }
}
function saveHave(have: string[]) {
  try { localStorage.setItem(HAVE_KEY, JSON.stringify(have)) } catch { /* a private window: forget it */ }
}

const add = (xs: string[], x: string) => (xs.includes(x) ? xs : [...xs, x])
const drop = (xs: string[], x: string) => xs.filter((y) => y !== x)

/** The strictness a reader can choose: the four, the last only when some relation is a comparison of data sheets. */
function tiers(units: FinderUnits): [Tier, string][] {
  const out: [Tier, string][] = [['exact', 'the same number only'], ['same', 'also its grades, packages and makers’ names'],
    ['substitute', 'also a substitute a document names']]
  if (Object.values(units.coverage ?? {}).some(([, from]) => from === 'similar')) out.push(['similar', 'also a part like it by the data sheets'])
  return out
}

/** A condition: what it says, and a button that takes it away. */
function Chip({ label, from, onRemove, warn }: { label: string; from: string; onRemove: () => void; warn?: string }) {
  return (
    <span class={`fchip${warn ? ' warn' : ''}`} title={warn}>
      {label}
      <button type="button" aria-label={`Remove ${label} from ${from}`} onClick={onRemove}>×</button>
    </span>
  )
}

type Pick = { part: string } | { family: string } | { word: string }

/**
 * A box to add to a block: parts as the parts list matches them (exact, starts with, contains), families by
 * their names, and in the words block anything typed. Enter takes the first suggestion, or what was typed.
 */
function Adder({ index, families, placeholder, label, onPick, words = false }: {
  index: PartIndex; families?: Family[]; placeholder: string; label: string; onPick: (p: Pick) => void; words?: boolean
}) {
  const [text, setText] = useState('')
  const resolve = useMemo(() => resolver(index), [index])
  const t = text.trim()
  const options = useMemo((): { pick: Pick; label: string }[] => {
    if (words || t.length < 2) return []
    const fams = (families ?? []).filter((f) => fold(f.label).includes(fold(t)) || f.id === t.toLowerCase())
      .slice(0, 3).map((f) => ({ pick: { family: f.id }, label: `${f.label} — family` }))
    const parts = search(index.parts, t).slice(0, 6).map((r) => ({ pick: { part: r[0] }, label: r[0] }))
    return [...fams, ...parts]
  }, [t, index, families, words])
  const take = (p: Pick) => { onPick(p); setText('') }
  const enter = () => {
    if (!t) return
    if (words) {
      for (const w of t.split(/\s+/)) take({ word: w })
      return
    }
    take(options[0]?.pick ?? { part: resolve(t).name })
  }
  return (
    <div class="fadd">
      <input
        type="search" value={text} placeholder={placeholder} aria-label={label}
        onInput={(e) => setText((e.target as HTMLInputElement).value)}
        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); enter() } }}
      />
      {options.length > 0 && (
        <ul class="fsugg">
          {options.map((o) => (
            <li key={o.label}><button type="button" onClick={() => take(o.pick)}>{o.label}</button></li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** A radio group the browser draws: a choice of one, with arrow keys for free. */
function Radios<T extends string>({ name, legend, value, options, onChange }: {
  name: string; legend: string; value: T; options: [T, string][]; onChange: (v: T) => void
}) {
  return (
    <fieldset class="fradios">
      <legend>{legend}</legend>
      {options.map(([v, label]) => (
        <label key={v}><input type="radio" name={name} checked={value === v} onChange={() => onChange(v)} /> {label}</label>
      ))}
    </fieldset>
  )
}

/** Boxes over a set where everything ticked is written as no filter at all (null). */
function Ticks({ legend, all, kept, label, count, onChange }: {
  legend: string; all: string[]; kept: Set<string> | null; label: (k: string) => string; count?: (k: string) => number
  onChange: (kept: Set<string> | null) => void
}) {
  const on = (k: string) => !kept || kept.has(k)
  const toggle = (k: string) => {
    const next = new Set(kept ?? all)
    if (next.has(k)) next.delete(k)
    else next.add(k)
    onChange(next.size === all.length ? null : next)
  }
  return (
    <fieldset class="fticks">
      <legend>{legend}</legend>
      {all.map((k) => (
        <label key={k} class="srcbox">
          <input type="checkbox" checked={on(k)} onChange={() => toggle(k)} />
          <span class="srcname">{label(k)}</span>
          {count && <span class="count">{n(count(k))}</span>}
        </label>
      ))}
    </fieldset>
  )
}

function Block({ title, summary, open = true, children }: {
  title: string; summary?: string; open?: boolean; children: preact.ComponentChildren
}) {
  return (
    <details class="fblock" open={open}>
      <summary><span>{title}</span>{summary && <span class="count">{summary}</span>}</summary>
      <div class="fbody">{children}</div>
    </details>
  )
}

/** What each part on a result is to the reader: had, had as another grade or name, a maybe, missing, only named. */
type Mark = { cls: string; sign: string; why: string }

function markOf(p: number, named: boolean, cover: ReturnType<typeof coverage> | null, doubt: Set<number>,
  index: PartIndex, cat: Catalogue): Mark {
  const fid = index.families?.[index.parts[p]?.[5] ?? -1]
  const fam = cat.families.find((f) => f.id === fid)?.label
  const said = fam ? `filed as: ${fam}` : 'nothing here says what it is'
  if (doubt.has(p)) return { cls: 'doubt', sign: '!', why: `${said} — the reason this result is set apart` }
  if (cover) {
    const l = cover.level[p] ?? 0
    const by = cover.by.get(p)
    const name = index.parts[p]?.[0] ?? ''
    if (l === EXACT) return { cls: 'have', sign: '✓', why: `you have it · ${said}` }
    if (l === SAME) return { cls: 'have', sign: '✓', why: `you have ${by?.from}, the same part · ${said}` }
    if (l === SUBST && by?.rel) {
      const [part, relation, , refs, note, status] = by.rel
      const words = relationWords(relation, part === by.from ? 'out' : 'in')
      return { cls: 'have subst', sign: '≈', why: `you have ${by.from}, ${words} ${name}: ${note || relation} (${refs.join(' ')}${status === 'draft' ? ', not yet reviewed' : ''}) · ${said}` }
    }
    if (l === GRADE) return { cls: 'grade', sign: '?', why: `you have ${by?.from}; this asks for one grade of it · ${said}` }
    const hint = cover.hints.get(p)
    if (!named) return { cls: 'miss', sign: '✗', why: `you do not have it${hint ? ` — you have ${hint.join(', ')}, documented in one data sheet with it, which is not the same part` : ''} · ${said}` }
  }
  return named ? { cls: 'named', sign: '', why: `only named on this page, not used · ${said}` } : { cls: '', sign: '', why: said }
}

function Card({ h, ctx, docs, cover, cat, terms, said }: {
  h: Hit; ctx: Context; docs: FinderDocs; cover: ReturnType<typeof coverage> | null; cat: Catalogue; terms: string[]
  said: Map<string, Set<number>> | undefined
}) {
  const { finder: f, index } = ctx
  const u = h.u
  const used = [...f.used.subarray(f.usedAt[u]!, f.usedAt[u + 1]!)]
  const named = [...f.named.subarray(f.namedAt[u]!, f.namedAt[u + 1]!)]
  const doubt = new Set(h.doubt ?? [])
  const k = String(u)
  const date = docs.date[u]
  const page = f.page[u]
  const inTitle = terms.filter((t) => holds(ctx.titleWords[u] ?? new Set(), t))
  const inLine = terms.filter((t) => !inTitle.includes(t) && said?.get(t)?.has(u))
  const chip = (p: number, isNamed: boolean) => {
    const name = index.parts[p]?.[0] ?? ''
    const m = markOf(p, isNamed, cover, doubt, index, cat)
    const href = `?part=${encodeURIComponent(name)}`
    return (
      <a key={`${isNamed ? 'n' : 'u'}${p}`} class={`pc ${m.cls}`} href={href} title={m.why}
        onClick={(e) => follow(e as unknown as MouseEvent, href)}>
        {m.sign && <span aria-hidden="true">{m.sign} </span>}{name}
      </a>
    )
  }
  const next = (h.nextDoor ?? []).map((p) => index.parts[p]?.[0]).filter(Boolean)
  return (
    <article class="fcard">
      <div class="fhead">
        <a class="ftitle" href={forViewer(docs.url[u] ?? '')} target="_blank" rel="noopener">{docs.title[u] || docs.url[u]}</a>
        <span class="small muted">
          {index.sources[docs.source[u] ?? -1] ?? ''}{date ? ` · ${date}` : ''}{page ? ` · page ${page}` : ''}
        </span>
        {f.flags[u]! & SCHEMATIC ? <span class="pill acc">schematic</span> : null}
      </div>
      <div class="fparts">
        {used.map((p) => chip(p, false))}
        {named.map((p) => chip(p, true))}
      </div>
      {(inTitle.length + inLine.length > 0 || docs.also[k] || docs.aka[k] || docs.sheets[k] || next.length > 0) && (
        <p class="small muted fnote">
          {inTitle.length > 0 && <span>“{inTitle.join('”, “')}” in the title</span>}
          {inLine.length > 0 && <span>“{inLine.join('”, “')}” in a summary a language model wrote of the page</span>}
          {docs.aka[k] && <span>also filed as {docs.aka[k]!.join(', ')}</span>}
          {docs.also[k] && <span>also at {docs.also[k]!.join(', ')}</span>}
          {docs.sheets[k] && <span>one of {docs.sheets[k]} designs in its folder: another sheet may hold more parts</span>}
          {next.length > 0 && <span>the article may run on: {next.join(', ')} on the page {f.flags[u]! & AFTER ? 'before or ' : ''}after</span>}
        </p>
      )}
    </article>
  )
}

/** Results by how many of their parts the reader lacks, when the reader said what they have. */
function groups(hits: Hit[], owned: boolean): [string, Hit[]][] {
  if (!owned) return [['', hits]]
  const out = new Map<number, Hit[]>()
  for (const h of hits) out.set(h.missing, [...(out.get(h.missing) ?? []), h])
  return [...out.entries()].sort((a, b) => a[0] - b[0])
    .map(([m, hs]) => [m === 0 ? 'Buildable with what you have' : `${m} ${m === 1 ? 'part' : 'parts'} missing`, hs])
}

function Examples({ setQ, have, left }: { setQ: (f: (q: Query) => Query) => void; have: number; left: number }) {
  const go = (e: MouseEvent, f: (q: Query) => Query) => { e.preventDefault(); setQ(f) }
  return (
    <section class="evidence stack-s prose">
      <p class="eyebrow">Projects</p>
      <h2>Find circuits by the parts in them</h2>
      <p class="muted">
        Say which parts a project must use, which parts you have, which families or parts it must not have, which
        sources to look in and which words its title holds. Every document the parts list counts is here: a
        project page, a factory schematic, or one page of a magazine or a book.
      </p>
      {left > 0 && <p class="small muted">What you leave out applies to whatever you look for next.</p>}
      <ul class="uselist">
        <li><a href="?find&need=TL072,2N3904" onClick={(e) => go(e as unknown as MouseEvent, (q) => ({ ...q, need: ['TL072', '2N3904'] }))}>Projects using a TL072 and a 2N3904</a></li>
        <li><a href="?find&q=fuzz&nofam=opamp" onClick={(e) => go(e as unknown as MouseEvent, (q) => ({ ...q, words: ['fuzz'], nofam: ['opamp'] }))}>Fuzz circuits without an op-amp</a></li>
        {have === 0 && (
          <li><a href="?find" onClick={(e) => go(e as unknown as MouseEvent, (q) => ({ ...q, have: ['TL072', 'NE5532', 'BC547', 'BC557', '2N3904', '2N5457', '1N4148', 'LM386', 'J201', '1N4007'] }))}>
            What can I build with these ten parts?</a></li>
        )}
      </ul>
    </section>
  )
}

export function FinderPage() {
  const [index, setIndex] = useState<PartIndex | null>(null)
  const cat = useCatalogue()
  const [files, setFiles] = useState<{ units: FinderUnits; docs: FinderDocs } | null | undefined>(undefined)
  const [retried, setRetried] = useState(false)
  const initial = useMemo(() => readQuery(location.search), [])
  const [fromLink, setFromLink] = useState(initial.shared.length > 0)
  const [q, setQ] = useState<Query>(() => ({ ...initial, have: initial.shared.length ? initial.shared : savedHave() }))
  const [shown, setShown] = useState(PAGE)
  const [pasting, setPasting] = useState(false)
  const [paste, setPaste] = useState('')
  // On a phone the question folds into one line when the address already asks one, so the answers show.
  const [open, setOpen] = useState(() => !(asked(initial) && matchMedia('(max-width: 860px)').matches))
  const [copied, setCopied] = useState(false)
  const [width, setWidth] = useState(savedWidth)
  const host = useRef<HTMLDivElement>(null)

  useEffect(() => { loadIndex().then(setIndex); loadFinder().then(setFiles) }, [])
  // Back and forward between two questions, or a link to another one, while the tab is open.
  useEffect(() => {
    const onPop = () => {
      if (!new URLSearchParams(location.search).has('find')) return
      const r = readQuery(location.search)
      setFromLink(r.shared.length > 0)
      setQ((old) => ({ ...r, have: r.shared.length ? r.shared : old.have }))
    }
    addEventListener('popstate', onPop)
    return () => removeEventListener('popstate', onPop)
  }, [])
  const fresh = !!(index && files && sameBuild(files.units, files.docs, index))
  // The index and the finder are cached apart: one from the last deploy beside one from this one is asked for
  // again, once, past the cache; if they still disagree the page says the site is being updated.
  useEffect(() => {
    if (!index || !files || fresh || retried) return
    setRetried(true)
    Promise.all([reloadIndex(files.units.findStamp), loadFinder(index.partsStamp ?? index.sourcesStamp ?? 'x')])
      .then(([i, f]) => { setIndex(i); setFiles(f) })
  }, [index, files, fresh, retried])

  useEffect(() => {
    const s = writeQuery(location.search, q)
    history.replaceState(history.state, '', s)
    try { sessionStorage.setItem(LAST_KEY, s) } catch { /* nothing to come back to */ }
  }, [q])
  useEffect(() => { if (!fromLink) saveHave(q.have) }, [q.have, fromLink])
  useEffect(() => setShown(PAGE), [q])

  const finder = useMemo(() => (files && index && fresh ? decode(files.units, index.parts.length) : null), [files, index, fresh])
  const ctx = useMemo((): Context | null => (finder && files && index && cat ? {
    index, finder, row: new Map(index.parts.map((r, i) => [r[0], i])), facetKeys: files.units.facets.map((f) => f.key),
    roles: files.units.roles, eras: files.units.eras, source: files.docs.source, families: cat.families,
    titleWords: files.docs.title.map((t, i) => new Set(wordsOf([t, ...(files.docs.aka[String(i)] ?? [])].join(' · ')))),
  } : null), [finder, files, index, cat])
  // The splits of the word index the search's words fall in, fetched once each, read into each word's units.
  const terms = useMemo(() => q.words.map(termOf).filter(Boolean), [q.words])
  const [said, setSaid] = useState<Map<string, Set<number>> | undefined>(undefined)
  useEffect(() => {
    if (!files || !fresh || !q.summaries || !terms.length) { setSaid(undefined); return }
    const stamp = files.units.findStamp
    let alive = true
    Promise.all(terms.map(async (t) => {
      const shards = await Promise.all(keysFor(t, files.units.shards).map((k) => loadShard(k, stamp)))
      const units = new Set<number>()
      for (const sh of shards) if (sh && sh.findStamp === stamp) for (const u of unitsOfWord(sh, t)) units.add(u)
      return [t, units] as const
    })).then((pairs) => { if (alive) setSaid(new Map(pairs)) })
    return () => { alive = false }
  }, [terms.join(' '), files, fresh, q.summaries])
  const byId = useMemo(() => new Map((cat?.families ?? []).map((f) => [f.id, f])), [cat])
  const negative = files?.units.negative ?? []
  const leaveOutOk = (fid: string) => lineage(fid, byId).some((x) => negative.includes(x))
  // A family the finder cannot be trusted to rule out is shown and not used.
  const effective = useMemo(() => ({ ...q, nofam: q.nofam.filter(leaveOutOk) }), [q, byId, negative])
  const result = useMemo(() => (ctx && asked(effective) ? answer(effective, ctx, said) : null), [ctx, effective, said])
  const cover = useMemo(() => (ctx && q.have.length ? coverage(ctx.index, ctx.finder, q.have, q.tier) : null), [ctx, q.have, q.tier])
  const resolve = useMemo(() => (index ? resolver(index) : null), [index])
  const unknown = useMemo(() => new Set(q.have.filter((p) => resolve && !resolve(p).known)), [q.have, resolve])

  const set = (f: (q: Query) => Query) => setQ((old) => f(old))
  const pick = (block: 'have' | 'need' | 'out') => (p: Pick) => set((old) => {
    if ('part' in p) return { ...old, [block]: add(old[block], p.part) }
    if ('family' in p) return block === 'out' ? { ...old, nofam: add(old.nofam, p.family) } : { ...old, fam: add(old.fam, p.family) }
    return old
  })
  const famLabel = (fid: string) => byId.get(fid)?.label ?? fid

  if (files === null) return <p class="muted">Could not load the project index. Run `make web-data` to build it.</p>
  if (!index || !cat || files === undefined) return <Loading what="the project index (about 3 MB, once)" />
  if (!fresh) {
    return retried
      ? <p class="muted">The project index and the parts list come from two different builds of the site. Reload the page in a few minutes.</p>
      : <Loading what="the project index" />
  }

  const common = terms.filter((t) => files.units.common.includes(t.replace(/\*$/, '')))
  const owned = q.have.length > 0
  const hits = result?.hits ?? []
  const buildable = owned ? hits.filter((h) => h.missing === 0).length : 0
  const summary = [q.have.length && `${q.have.length} have`, q.need.length + q.fam.length && `${q.need.length + q.fam.length} must`,
    q.out.length + q.nofam.length && `${q.out.length + q.nofam.length} out`, q.words.length && q.words.join(' ')].filter(Boolean).join(' · ')
  const roleCount = (r: string) => { const i = files.units.roles.indexOf(r); return finder!.role.reduce((t, x) => t + (x === i ? 1 : 0), 0) }
  const eraList = [...new Set(files.units.eras)].sort((a, b) => Object.keys(ERA_LABEL).indexOf(a) - Object.keys(ERA_LABEL).indexOf(b))
  const copyLink = () => {
    const url = `${location.origin}${location.pathname}${writeQuery(location.search, q, true)}`
    navigator.clipboard?.writeText(url).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500) }, () => {})
  }

  return (
    <div ref={host} class="browser finder" style={{ '--side': `${width}px` } as Record<string, string>}>
      <aside class={`side fquery${open ? '' : ' shut'}`}>
        <button type="button" class="fqtoggle" aria-expanded={open} onClick={() => setOpen(!open)}>
          Your question{summary ? `: ${summary}` : ''}
        </button>
        <div class="fqbody">
          <Block title="What I have" summary={q.have.length ? `${q.have.length} parts` : 'stays in this browser'}>
            {fromLink && (
              <p class="small muted">
                These parts came with the link.{' '}
                <button type="button" class="linkish" onClick={() => { setFromLink(false); saveHave(q.have) }}>Keep them as mine</button>
                {' · '}<button type="button" class="linkish" onClick={() => { setFromLink(false); set((o) => ({ ...o, have: savedHave() })) }}>Use mine</button>
              </p>
            )}
            <div class="fchips">
              {q.have.map((p) => (
                <Chip key={p} label={p} from="What I have" onRemove={() => set((o) => ({ ...o, have: drop(o.have, p) }))}
                  warn={unknown.has(p) ? 'not in the index: no document here prints it' : undefined} />
              ))}
            </div>
            <Adder index={index} placeholder="Add a part you have" label="Add a part you have" onPick={pick('have')} />
            <p class="small fline">
              <button type="button" class="linkish" onClick={() => setPasting(!pasting)}>Paste a list</button>
              {q.have.length > 0 && <>{' · '}<button type="button" class="linkish" onClick={() => set((o) => ({ ...o, have: [] }))}>Clear</button></>}
              {q.have.length > 0 && <>{' · '}<button type="button" class="linkish" onClick={copyLink}>{copied ? 'Copied' : 'Copy a link with my parts'}</button></>}
            </p>
            {pasting && (
              <div class="fpaste">
                <textarea value={paste} rows={4} aria-label="A list of parts, one per line or separated by commas"
                  placeholder={'2x TL072\nBC547B, 1N4148'} onInput={(e) => setPaste((e.target as HTMLTextAreaElement).value)} />
                <button type="button" onClick={() => {
                  const names = pasted(paste).map((p) => resolve!(p).name)
                  set((o) => ({ ...o, have: names.reduce(add, o.have) }))
                  setPaste('')
                  setPasting(false)
                }}>Add these</button>
              </div>
            )}
            <Radios name="tier" legend="Count as mine" value={q.tier} onChange={(tier) => set((o) => ({ ...o, tier }))}
              options={tiers(files.units)} />
            <label class="srcbox small">
              <input type="checkbox" checked={q.discount} onChange={() => set((o) => ({ ...o, discount: !o.discount }))} />
              <span>Do not count a part a page only names as missing</span>
            </label>
          </Block>

          <Block title="Must use" summary={q.need.length + q.fam.length ? `${q.need.length + q.fam.length}` : undefined}>
            <div class="fchips">
              {q.need.map((p) => (
                <Chip key={p} label={p} from="Must use" onRemove={() => set((o) => ({ ...o, need: drop(o.need, p) }))}
                  warn={resolve && !resolve(p).known ? 'not in the index: no document here prints it' : undefined} />
              ))}
              {q.fam.map((f) => <Chip key={f} label={`${famLabel(f)} (family)`} from="Must use" onRemove={() => set((o) => ({ ...o, fam: drop(o.fam, f) }))} />)}
            </div>
            <Adder index={index} families={cat.families} placeholder="A part or a family" label="Add a part or a family it must use" onPick={pick('need')} />
          </Block>

          <Block title="Leave out" summary={q.out.length + q.nofam.length ? `${q.out.length + q.nofam.length}` : undefined}>
            <div class="fchips">
              {q.nofam.map((f) => (
                <Chip key={f} label={`${famLabel(f)} (family)`} from="Leave out" onRemove={() => set((o) => ({ ...o, nofam: drop(o.nofam, f) }))}
                  warn={leaveOutOk(f) ? undefined : 'not used: what files parts under this family cannot yet be trusted to say no'} />
              ))}
              {q.out.map((p) => <Chip key={p} label={p} from="Leave out" onRemove={() => set((o) => ({ ...o, out: drop(o.out, p) }))} />)}
            </div>
            <Adder index={index} families={cat.families.filter((f) => leaveOutOk(f.id))} placeholder="A part or a family"
              label="Add a part or a family to leave out" onPick={pick('out')} />
            <p class="small muted">A family is left out only where no part read on the page is or might be one; the others are set apart below the results, each with its reason.</p>
          </Block>

          <Block title="Words" summary={q.words.length ? q.words.join(' ') : undefined}>
            <div class="fchips">
              {q.words.map((w) => <Chip key={w} label={w} from="Words" onRemove={() => set((o) => ({ ...o, words: drop(o.words, w) }))} />)}
            </div>
            <Adder index={index} words placeholder="wah, fender, blameless…" label="Add a word of the title"
              onPick={(p) => { if ('word' in p) set((o) => ({ ...o, words: add(o.words, p.word.toLowerCase()) })) }} />
            <Radios name="req" legend="Words" value={q.require ? 'require' : 'rank'} onChange={(v) => set((o) => ({ ...o, require: v === 'require' }))}
              options={[['rank', 'put those with them first'], ['require', 'only those with them']]} />
            <label class="srcbox small">
              <input type="checkbox" checked={q.summaries} onChange={() => set((o) => ({ ...o, summaries: !o.summaries }))} />
              <span>Also in the summaries: the line a language model wrote of what each part does on a page</span>
            </label>
            <p class="small muted">A word is found as written or in the plural; end it with * for every word it starts (wah* finds wahwah). A title counts for more than a summary.</p>
            {common.length > 0 && q.summaries && (
              <p class="small muted">“{common.join('”, “')}” {common.length === 1 ? 'is' : 'are'} on too many pages to tell them apart, so the summaries are not searched for {common.length === 1 ? 'it' : 'them'}; titles still are.</p>
            )}
          </Block>

          <Block title="Where from" open={false}
            summary={[q.dropped.size && `${files.units.facets.length - q.dropped.size} sources`, q.roles && `${q.roles.size} types`, q.eras && [...q.eras].map((e) => ERA_LABEL[e] ?? e).join(', ')].filter(Boolean).join(' · ') || 'everywhere'}>
            <UsageFilter
              usages={{ schema: 1, facets: files.units.facets, parts: [] }} stale={false} dropped={q.dropped}
              setDropped={(dropped) => set((o) => ({ ...o, dropped }))} onOpen={() => {}}
              title="Sources" help="Look in the documents of the ticked sources only."
            />
            <Ticks legend="Type of document" all={files.units.roles} kept={q.roles} label={(r) => ROLE_LABEL[r] ?? r} count={roleCount}
              onChange={(roles) => set((o) => ({ ...o, roles }))} />
            <Ticks legend="Era of the source" all={eraList} kept={q.eras} label={(e) => ERA_LABEL[e] ?? e}
              onChange={(eras) => set((o) => ({ ...o, eras }))} />
            <p class="small muted">Modern sources print parts still made; the registry says each source’s era.</p>
          </Block>
        </div>
      </aside>

      <Splitter host={host} width={width} setWidth={setWidth} />

      {!result ? <Examples setQ={set} have={q.have.length} left={q.out.length + q.nofam.length} /> : (
        <section class="evidence stack-s fresults">
          <div class="fbar">
            <p class="count" aria-live="polite">
              {n(hits.length)} {hits.length === 1 ? 'result' : 'results'}
              {owned && ` · ${n(buildable)} buildable with what you have`}
              {result.maybe.length > 0 && ` · ${n(result.maybe.length)} set apart`}
            </p>
            <label class="small">Sort{' '}
              <select value={q.sort} onChange={(e) => set((o) => ({ ...o, sort: (e.target as HTMLSelectElement).value as Sort }))}>
                {(Object.keys(SORT_LABEL) as Sort[]).map((s) => <option key={s} value={s}>{SORT_LABEL[s]}</option>)}
              </select>
            </label>
            {owned && (
              <Radios name="miss" legend="Missing at most" value={Number.isFinite(q.miss) ? String(q.miss) : 'any'}
                onChange={(v) => set((o) => ({ ...o, miss: v === 'any' ? Infinity : Number(v) }))}
                options={[['0', '0'], ['1', '1'], ['2', '2'], ['any', 'any']]} />
            )}
          </div>
          {q.nofam.some((f) => !leaveOutOk(f)) && (
            <p class="small muted">Not left out: {q.nofam.filter((f) => !leaveOutOk(f)).map(famLabel).join(', ')}. What files parts under {q.nofam.length > 1 ? 'these families' : 'this family'} cannot yet be trusted to say no.</p>
          )}
          {hits.length === 0 && (
            <p class="muted">
              Nothing answers all of that.{' '}
              {owned && Number.isFinite(q.miss) && <>Allow more missing parts, or count grades and makers’ names as yours. </>}
              {q.require && q.words.length > 0 && <>Let the words rank rather than require. </>}
              {q.need.length + q.fam.length > 1 && <>Ask for fewer parts at once. </>}
            </p>
          )}
          {(() => {
            let left = shown
            return groups(hits, owned && (q.sort === 'best' || q.sort === 'missing')).map(([title, hs]) => {
              if (left <= 0) return null
              const show = hs.slice(0, left)
              left -= show.length
              return (
                <section key={title || 'all'} class="stack-s">
                  {title && <h3 class="fgroup">{title} <span class="count">{n(hs.length)}</span></h3>}
                  {show.map((h) => <Card key={h.u} h={h} ctx={ctx!} docs={files.docs} cover={cover} cat={cat} terms={terms} said={said} />)}
                </section>
              )
            })
          })()}
          {hits.length > shown && <button class="more" onClick={() => setShown((v) => v + PAGE * 2)}>{n(hits.length - shown)} more</button>}
          {result.maybe.length > 0 && (
            <details class="fmaybe">
              <summary>
                Might have {effective.nofam.map((f) => famLabel(f).toLowerCase()).join(' or ')}: {n(result.maybe.length)}
                <span class="small muted"> — a part on the page is or might be one, or nothing here says what it is</span>
              </summary>
              {result.maybe.slice(0, 200).map((h) => <Card key={h.u} h={h} ctx={ctx!} docs={files.docs} cover={cover} cat={cat} terms={terms} said={said} />)}
              {result.maybe.length > 200 && <p class="muted small">and {n(result.maybe.length - 200)} more.</p>}
            </details>
          )}
          <p class="small muted">
            A part marked ✗ is one this index read on the page and you do not have; passives are not read, so a circuit
            needs more than these. The summaries were written by a language model reading each page: they help find a
            page by its words and hide pages that only name or sell a part, and say nothing this index vouches for.
          </p>
        </section>
      )}
    </div>
  )
}
