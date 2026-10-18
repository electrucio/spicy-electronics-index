/**
 * What each model does, measured at the same conditions as every other model of its kind: the "SPICE models
 * characterization" fold of a part page.
 *
 * Laid out as a waveform viewer is: a list of the curves the bench draws, under their groups, and a list
 * of the models, each with a box to find one by name, beside one chart. A model's name shows it alone and
 * its box adds it to the chart; models whose results are identical share a row. The models are named as a
 * reader looks for them, by the name their card gives them, then their source. The chart has a cursor
 * that reads each curve, and a "how is this measured" button that opens the method page's entry in a
 * dialog. The table under it holds what a curve does not show: the single numbers (a peak, a slope, a
 * time, a ratio) and what the card itself says.
 *
 * Numbers, not judgements: a value is a number with its unit, or the code that stands where there is
 * none. The lists, their search and the rows of identical results are pure functions in charpick.ts.
 */
import type preact from 'preact'
import { Fragment } from 'preact'
import { useEffect, useMemo, useRef, useState } from 'preact/hooks'

import { leadsTo, parentOf, target, useAnchor } from './anchor'
import type { Axis } from './chart'
import { place, tickFigures, ticks } from './chart'
import { DATA, follow, partPath } from './data'
import type { Choice, CurveRow, Selection } from './charpick'
import { atTokens, axisName, chosenOf, copyHits, curveRows, curveStatus, defaultCurve, filterGroups, findRow, fmtChoice, groupModels, matchCurve, pickCurves, quantities, readSelection, resolveAt, resolveModels, sameValue, selectorsOf, writeSelection } from './charpick'
import { Fold, SubSection } from './fold'
import { si, siValue } from './format'
import { Swatch, colourOf, dashOf, modelLabels, tag } from './key'
import { Loading } from './loading'
import { Method } from './methods'
import type { CharacterFile, Curve, Grid, HoverExtra, Measurement, MethodsFile, ModelCharacter, PartModel, PartPage } from './types'


/** Output keys in the catalogue's order: by their base in the entry's output list, then by the numbers
 *  of their conditions (1mA before 10mA before 100mA, whatever the alphabet says). */
export function orderKeys(keys: string[], m: Measurement | undefined): string[] {
  const bases = (m?.outputs ?? []).map((o) => o.key.split('@')[0] ?? o.key)
  const rank = (k: string) => { const i = bases.indexOf(k.split('@')[0] ?? k); return i < 0 ? bases.length : i }
  const conds = (k: string) => (k.split('@')[1] ?? '').split(',').map(siValue)
  return [...keys].sort((a, b) => {
    const r = rank(a) - rank(b)
    if (r) return r
    const ca = conds(a)
    const cb = conds(b)
    for (let i = 0; i < Math.max(ca.length, cb.length); i++) {
      const d = (ca[i] ?? 0) - (cb[i] ?? 0)
      if (d) return d
    }
    return a < b ? -1 : a > b ? 1 : 0
  })
}

/** What a cell shows: the number with its unit, or why there is none. */
export function cellOf(mo: ModelCharacter | undefined, mid: string, key: string, engine: string, primary: string, unit = ''): { text: string; cls: string; title: string } {
  if (!mo) return { text: '', cls: 'c-none', title: 'no record for this model' }
  const code = mo.codes[mid]
  const vals = mo.values[mid] ?? {}
  const prim = vals[primary]?.[key]
  const mine = vals[engine]?.[key]
  const v = engine === primary ? prim : (mine ?? prim)
  if (v === undefined || v === null) {
    if (code && code !== 'ok') return { text: code, cls: `k-${code.replace('/', '')}`, title: codeTitle(code) }
    return { text: '·', cls: 'c-none', title: 'not produced for this model' }
  }
  const others = Object.entries(vals).filter(([e]) => e !== engine && vals[e]?.[key] !== undefined).map(([e, d]) => `${e}: ${show(d[key], unit)}`)
  const title = [others.length ? others.join(' · ') : '', engine !== primary && mine === undefined ? `${engine} within 1 % of ${primary}` : ''].filter(Boolean).join(' — ')
  return { text: show(v, unit), cls: 'cc', title }
}

function show(v: unknown, unit = ''): string {
  if (typeof v === 'number') return si(v, unit)
  if (typeof v === 'boolean') return v ? 'yes' : 'no'
  if (Array.isArray(v)) return v.map((x) => (typeof x === 'number' ? si(x, unit) : String(x))).join(' – ')
  return String(v ?? '')
}

function codeTitle(code: string): string {
  return ({
    absent: 'the card has no parameter for this physics: the number would be the simulator\'s default, not the model\'s',
    'n/a': 'the model never reached this step (not saturated, not conducting, not switched)',
    failed: 'the simulator did not return a waveform for this deck',
    suspect: 'a value no transistor has: the behavioural base drive settled on a wrong point in this engine',
  } as Record<string, string>)[code] ?? code
}

export function ModelCharacter({ page }: { page: PartPage }) {
  const m = page.models
  const s = m?.char
  if (!m || !s) return null
  // A link straight to a part's characterisation is ?part=X#spice-models/characterization (anchor.tsx).
  return (
    <section class="stack-s character">
      <SubSection title="SPICE models characterization" anchor="characterization">
        {() => <Panel part={page.part} models={m.models} />}
      </SubSection>
    </section>
  )
}

/** A JSON file that may be gzipped: the bytes are looked at, not the headers, because a static server may or
 *  may not have undone the compression already. */
export async function jsonMaybeGzip(buf: ArrayBuffer): Promise<unknown> {
  const b = new Uint8Array(buf)
  if (b.length > 2 && b[0] === 0x1f && b[1] === 0x8b) {
    const text = await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).text()
    return JSON.parse(text)
  }
  return JSON.parse(new TextDecoder().decode(b))
}

/** The part's index, then each model's record (one gzipped file per model, shared by every part that lists it). */
export async function loadCharacter(part: string): Promise<CharacterFile | null> {
  const r = await fetch(`${DATA}/character/${partPath(part)}.json`)
  if (!r.ok) return null
  const index = (await r.json()) as CharacterFile & { models: Record<string, { hash: string } & Partial<ModelCharacter>> }
  const entries = await Promise.all(Object.entries(index.models).map(async ([k, mo]) => {
    if (mo.codes) return [k, mo as ModelCharacter] as const          // an older file, with the records inside
    const m = await fetch(`${DATA}/character/m/${mo.hash}.json.gz`)
    return m.ok ? ([k, (await jsonMaybeGzip(await m.arrayBuffer())) as ModelCharacter] as const) : null
  }))
  return { ...index, models: Object.fromEntries(entries.filter((e): e is readonly [string, ModelCharacter] => e !== null)) }
}

function Panel({ part, models }: { part: string; models: PartModel[] }) {
  const [file, setFile] = useState<CharacterFile | null | undefined>(undefined)
  const [methods, setMethods] = useState<MethodsFile | null | undefined>(undefined)
  useEffect(() => {
    // another part: its own records, never the last part's beside the new part's list of models
    let current = true
    setFile(undefined)
    loadCharacter(part).then((f) => { if (current) setFile(f) }, () => { if (current) setFile(null) })
    fetch(`${DATA}/bench/methods.json`).then((r) => (r.ok ? r.json() : null)).then(setMethods, () => setMethods(null))
    return () => { current = false }
  }, [part])
  if (file === undefined || methods === undefined) return <Loading what={`the characterization of ${part}'s models`} small />
  if (!file) return <p class="muted small">No characterisation published for this part's models.</p>
  return <Pane key={part} part={part} models={models} file={file} methods={methods} />
}

/** A model as the panel shows it: its place in the part's list, its label and its record. */
type Member = { mo: PartModel; i: number; label: string; rec: ModelCharacter }
/** A row of the model list: the representative of a result, and every model that gives it, itself first. */
type Col = Member & { members: Member[] }

function Pane({ part, models, file, methods }: { part: string; models: PartModel[]; file: CharacterFile; methods: MethodsFile | null }) {
  const labels = useMemo(() => modelLabels(models), [models])
  const cols: Col[] = useMemo(() => {
    const members = models.map((mo, i) => ({ mo, i, label: labels[i]!, rec: file.models[String(i)]! })).filter((c) => file.models[String(c.i)])
    const byI = new Map(members.map((c) => [c.i, c]))
    return groupModels(members).map((g) => ({ ...byI.get(g[0]!)!, members: g.map((i) => byI.get(i)!) }))
  }, [models, labels, file])
  const byId = useMemo(() => new Map((methods?.measurements ?? []).map((m) => [m.id, m])), [methods])
  const seen = new Set<string>()
  for (const c of cols) for (const mid of Object.keys(c.rec.codes)) seen.add(mid)
  // the kind: that of the first measurement the records name that the catalogue knows (an older record may
  // name its agreement after the job's group, "amplifier", where the catalogue says "opamp")
  const kind = [...seen].map((id) => byId.get(id)?.kind).find((k) => k) ?? [...seen][0]?.split('-')[0] ?? ''
  const order = (methods?.measurements ?? []).filter((m) => m.kind === kind).map((m) => m.id)
  const mids = [...order.filter((id) => seen.has(id)), ...[...seen].filter((id) => !order.includes(id))]
  const rows = useMemo(() => curveRows((methods?.measurements ?? []).filter((m) => m.kind === kind), seen), [methods, cols])
  // what the address selects (charpick.ts), when it is this part's; the defaults for what it does not say
  const [asked] = useState(() => (new URLSearchParams(location.search).get('part') === part ? readSelection(location.search) : { models: [], at: [] } as Selection))
  const [curve, setCurve] = useState(() => findRow(rows, asked.curve)?.id ?? defaultCurve(rows, kind))
  // else the first model that drew the curve shown first: a model whose run failed is not what a reader should meet
  const [chosen, setChosen] = useState<number[]>(() => {
    const named = resolveModels(asked.models, cols.map((c) => c.members.map((x) => x.i)), (i) => file.models[String(i)]?.hash)
    if (named.length) return named
    const row = findRow(rows, curve)
    const first = cols.find((c) => !row || curveStatus(c.rec, row) === 'ok') ?? cols[0]
    return first ? [first.i] : []
  })
  const [choice, setChoice] = useState<Record<string, Record<string, Choice>>>(() => {
    const row = findRow(rows, curve)
    return row && asked.at.length ? { [row.mid]: resolveAt(asked.at, selectorsOf(row.curves)) } : {}
  })
  const [engine, setEngine] = useState(file.primary)
  const [cq, setCq] = useState('')
  const [mq, setMq] = useState('')
  const [about, setAbout] = useState<string | null>(null)
  const a = useAnchor<HTMLDivElement>('figures')      // links to the old Figures fold still land on the chart
  const row = findRow(rows, curve)
  const m = row ? byId.get(row.mid) : undefined
  const shown = cols.filter((c) => chosen.includes(c.i))
  const engines = Object.keys(file.engines)
  const eng = file.engines[file.primary]
  const units: Record<string, string> = Object.fromEntries(Object.entries(methods?.selectors ?? {}).map(([k, v]) => [k, v.unit]))
  // the reader's choice goes into the address bar, so the address is a link to what is on the screen. Only
  // from what the reader does, never when the panel is drawn: opening a part leaves its address clean, and
  // a panel still drawn for the last part cannot write over the next one's address
  const write = (cv: string, ch: number[], cc: Record<string, Record<string, Choice>>) => {
    if (new URLSearchParams(location.search).get('part') !== part) return
    const r = findRow(rows, cv)
    const mm = r && byId.get(r.mid)
    const sels = r ? selectorsOf(r.curves) : []
    const at = r && mm ? atTokens(mm, sels, chosenOf(mm, sels, cc[r.mid])) : []
    const hashes = ch.map((i) => file.models[String(i)]?.hash?.slice(0, 8)).filter((h): h is string => Boolean(h))
    const home = parentOf(a.path)
    const hash = leadsTo(target(), home) ? location.hash : `#${home}`
    history.replaceState(history.state, '', `${location.pathname}${writeSelection(location.search, { curve: cv, models: hashes, at })}${hash}`)
  }
  const pick = (id: string) => { setCurve(id); write(id, chosen, choice) }
  const solo = (i: number) => { setChosen([i]); write(curve, [i], choice) }
  const toggle = (i: number) => {
    const next = chosen.includes(i) ? (chosen.length > 1 ? chosen.filter((x) => x !== i) : chosen) : [...chosen, i].sort((x, y) => x - y)
    setChosen(next)
    write(curve, next, choice)
  }
  const onChoice = (key: string, v: Choice) => {
    if (!row) return
    const next = { ...choice, [row.mid]: { ...choice[row.mid], [key]: v } }
    setChoice(next)
    write(curve, chosen, next)
  }
  const total = cols.reduce((n, c) => n + c.members.length, 0)     // the models characterised
  return (
    <div class="stack-s">
      <div class="charpane" ref={a.ref} data-anchor={a.path}>
        {/* the models across the top, in a low box; under them the curves beside the chart, and the curve's
            numbers under both, so a laptop's screen holds the choice and what it draws at once */}
        <ModelList cols={cols} models={models} chosen={chosen} row={row} primary={file.primary} query={mq} onQuery={setMq} onSolo={solo} onToggle={toggle} />
        <div class="lower">
          <CurveList rows={rows} current={row?.id} names={byId} shown={shown} query={cq} onQuery={setCq} onPick={pick} />
          <div class="plot stack-s">
            {row && m
              ? <Chart key={row.id} part={part} m={m} row={row} shown={shown} engine={engine} engines={engines} onEngine={setEngine} primary={file.primary} units={units}
                  choice={choice[row.mid] ?? {}} onChoice={onChoice} onAbout={() => setAbout(row.mid)} />
              : <p class="muted small">No curve published for this part's models.</p>}
          </div>
        </div>
        {/* the curve's own numbers, under the curve, as wide as the panel */}
        {row && (() => {
          const t = rowsOf(row.mid, m, shown)
          return (
            <div class="charwrap curvenums">
              <table class="chk char">
                <ModelColumns shown={shown} />
                <tbody>
                  <MeasurementRows mid={row.mid} m={m} rows={t.rows} shown={shown} engine={engine} primary={file.primary} units={t.units} whats={t.whats} onAbout={() => setAbout(row.mid)} />
                </tbody>
              </table>
            </div>)
        })()}
        <p class="muted small codes">
          <span class="k-absent">absent</span>: the card has no parameter for it · <span class="k-na">n/a</span>: the model never reached the step ·{' '}
          <span class="k-failed">failed</span>: no waveform · <span class="k-suspect">suspect</span>: a wrong operating point in this engine · ·: not produced.
          Hover a value for the other engines'. An agreement chip is the largest spread between engines over the measurement's outputs.
        </p>
        {/* where the numbers come from: under them, so the choice and the curve come first on the screen */}
        <p class="muted small codes">
          Every model of this part at the catalogue's conditions, catalogue <code>{file.catalogue}</code>; values from <b>{file.primary}</b>
          {engines.length > 1 && <> (the others where they differ by more than 1 %)</>}
          {eng && <>, image <code>{eng.image.slice(7, 19)}</code>, bench <code>{eng.bench.commit.slice(0, 7)}</code>, {eng.on}</>}.
          {cols.length < total && <> Models whose results are identical share a row.</>}{' '}
          <a href="?bench=1" onClick={(e) => follow(e, '?bench=1')}>The method page</a> explains every measurement.
        </p>
      </div>
      {/* every number, the measurements without a curve too, and what each card says: for the models chosen */}
      <Fold level={1} anchor="measured-values" summary={<strong>All measured values</strong>}>
        {() => (
          <div class="charwrap">
            <table class="chk char">
              <ModelColumns shown={shown} />
              <tbody>
                <CardRows shown={shown} />
                {mids.map((mid) => {
                  const mm = byId.get(mid)
                  const t = rowsOf(mid, mm, shown)
                  return <MeasurementRows key={mid} mid={mid} m={mm} rows={t.rows} shown={shown} engine={engine} primary={file.primary} units={t.units} whats={t.whats} onAbout={() => setAbout(mid)} />
                })}
              </tbody>
            </table>
          </div>
        )}
      </Fold>
      {about && <About m={byId.get(about)} mid={about} drawings={methods?.drawings ?? []} shown={shown} file={file} part={part} onClose={() => setAbout(null)} />}
    </div>
  )
}

/** The list of curves, under their groups: the one shown is marked, a click shows another. A row none of the
 *  chosen models drew is faint with the reason; one only some drew says how many. */
function CurveList({ rows, current, names, shown, query, onQuery, onPick }: {
  rows: CurveRow[]; current?: string; names: Map<string, Measurement>; shown: Col[]; query: string; onQuery: (q: string) => void; onPick: (id: string) => void
}) {
  const list = useRef<HTMLUListElement>(null)
  const visible = rows.filter((r) => matchCurve(r, query))
  const headings = [...new Set(visible.map((r) => r.heading))]
  // the curve an address chose may be far down the list: bring it into the list's view, not the page's
  useEffect(() => {
    const ul = list.current
    const on = ul?.querySelector<HTMLElement>('label.on')
    if (ul && on) ul.scrollTop = Math.max(0, on.offsetTop - ul.clientHeight / 3)
  }, [])
  return (
    <div class="pick">
      <div class="pickhead">
        <b>Curves</b>
        <input type="search" value={query} placeholder="hfe, beta, cob, noise…" aria-label="Find a curve"
          onInput={(e) => onQuery((e.target as HTMLInputElement).value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && visible[0]) onPick(visible[0].id)
            if (e.key === 'Escape') onQuery('')
          }} />
      </div>
      <ul class="picklist curves" ref={list} aria-label="Curves">
        {headings.map((h) => (
          <Fragment key={h}>
            <li class="pickgroup">{h}</li>
            {visible.filter((r) => r.heading === h).map((r) => {
              const st = shown.map((c) => curveStatus(c.rec, r))
              const have = st.filter((s) => s === 'ok').length
              const why = [...new Set(st.filter((s) => s !== 'ok'))].join(', ')
              return (
                <li key={r.id}>
                  <label class={`crow${r.id === current ? ' on' : ''}${shown.length && !have ? ' faint' : ''}`} title={names.get(r.mid)?.name ?? r.mid}>
                    <input type="radio" class="vh" name="charcurve" checked={r.id === current} onChange={() => onPick(r.id)} />
                    <span class="lb">{r.label}</span>
                    {shown.length > 0 && !have && <span class="pcode">{why}</span>}
                    {have > 0 && have < shown.length && <span class="pcode" title={`drawn by ${have} of the ${shown.length} models shown`}>{have}/{shown.length}</span>}
                  </label>
                </li>)
            })}
          </Fragment>))}
        {!visible.length && <li class="muted small none">No curve matches.</li>}
      </ul>
    </div>
  )
}

/** The model's file, where the models table gets it: a download link, or why there is none. */
function GetLink({ mo }: { mo: PartModel }) {
  const g = mo.get
  if (g.url) {
    const what = `download ${mo.name} from ${g.via ? `${g.via}, which publishes the same model` : mo.source}${g.member ? ` (${g.member} in the archive)` : ''}`
    return <a class="dl" href={g.url} title={what} aria-label={what}>download</a>
  }
  return <span class="dl off" title={g.installed_with ? `ships with ${g.installed_with}` : 'origin not recorded'}>{g.installed_with ? 'built in' : 'no link'}</span>
}

/** The list of models, one row per distinct result: the name shows that model alone, the box adds it to the
 *  chart or takes it off, and "+N identical" shows the models that give the same result. The part's models
 *  the bench has no record of come last, faint, so a search for one still finds it and says why. */
function ModelList({ cols, models, chosen, row, primary, query, onQuery, onSolo, onToggle }: {
  cols: Col[]; models: PartModel[]; chosen: number[]; row?: CurveRow; primary: string; query: string
  onQuery: (q: string) => void; onSolo: (i: number) => void; onToggle: (i: number) => void
}) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const views = filterGroups(cols.map((c) => c.members.map((x) => x.i)), models, query)
  const run = new Set(cols.flatMap((c) => c.members.map((x) => x.i)))
  const unrun = models.map((_, i) => i).filter((i) => !run.has(i))
  const left = filterGroups(unrun.map((i) => [i]), models, query)
  const flip = (i: number) => setExpanded((s) => { const n = new Set(s); n.has(i) ? n.delete(i) : n.add(i); return n })
  const copyNote = (mo: PartModel) => {
    const hits = copyHits(mo, query)
    return hits.length ? <span class="muted"> (copy at {hits.map((h) => `${h.source} as ${h.name}`).join(', ')})</span> : null
  }
  return (
    <div class="pick">
      <div class="pickhead">
        <b>Models</b>
        <span class="muted small">{models.length}{cols.length < run.size && <> · {cols.length} distinct</>}{unrun.length > 0 && <> · {unrun.length} not run</>}</span>
        {models.length > 1 && <input type="search" value={query} placeholder="name, source…" aria-label="Find a model"
          onInput={(e) => onQuery((e.target as HTMLInputElement).value)} onKeyDown={(e) => { if (e.key === 'Escape') onQuery('') }} />}
      </div>
      <ul class="picklist models" aria-label="Models">
        {views.map((v) => {
          const c = cols.find((x) => x.i === v.members[0])!
          const on = chosen.includes(c.i)
          const st = row ? curveStatus(c.rec, row) : 'ok'
          const open = v.open || expanded.has(c.i)
          const last = on && chosen.length === 1
          return (
            <li key={c.i} class={`mrow${on ? ' on' : ''}${st !== 'ok' ? ' faint' : ''}`}>
              <div class="mline">
                <input type="checkbox" checked={on} disabled={last} onChange={() => onToggle(c.i)}
                  aria-label={`${on ? 'take off the chart' : 'add to the chart'}: ${c.label}`} title={last ? 'the chart always shows a model' : on ? 'take off the chart' : 'add to the chart'} />
                <Swatch i={c.i} />
                <button type="button" class="mname" onClick={() => onSolo(c.i)} title={`show ${c.label} alone`}>
                  <span class="tg">{tag(c.i)}</span> <b>{c.mo.name}</b><span class="src">{c.mo.source}{v.hits.get(c.i) === 'copy' && copyNote(c.mo)}</span>
                </button>
                {st !== 'ok' && <span class={`pcode k-${st.replace('/', '')}`}>{st}</span>}
                {c.members.length > 1 && (
                  <button type="button" class="more" aria-expanded={open} onClick={() => flip(c.i)} title={`these models give the same curves and values in ${primary}`}>
                    +{c.members.length - 1} identical
                  </button>)}
                <GetLink mo={c.mo} />
              </div>
              {open && c.members.length > 1 && (
                <ul class="same">
                  {c.members.slice(1).map((x) => (
                    <li key={x.i} class={v.hits.has(x.i) ? 'hit' : ''}><span>{tag(x.i)} {x.mo.name} <span class="muted">· {x.mo.source}</span>{v.hits.get(x.i) === 'copy' && copyNote(x.mo)}</span><GetLink mo={x.mo} /></li>))}
                </ul>)}
            </li>)
        })}
        {left.map((v) => {
          const mo = models[v.members[0]!]!
          return (
            <li key={`u${v.members[0]}`} class="mrow faint" title="the bench has published no characterisation of this model">
              <div class="mline">
                <span class="nobox" />
                <span class="mname"><span class="tg">{tag(v.members[0]!)}</span> <b>{mo.name}</b><span class="src">{mo.source}{v.hits.get(v.members[0]!) === 'copy' && copyNote(mo)}</span></span>
                <span class="pcode">not run</span>
                <GetLink mo={mo} />
              </div>
            </li>)
        })}
        {!views.length && !left.length && <li class="muted small none">No model matches.</li>}
      </ul>
    </div>
  )
}

/** What the cards of one row say about one thing: one entry when they agree, else one per distinct text,
 *  with the numbers of the models that say it, in the row's order. */
export function memberFacts<T extends { i: number }>(members: T[], text: (m: T) => string): { tags: string[]; text: string }[] {
  const out: { tags: string[]; text: string }[] = []
  for (const m of members) {
    const t = text(m)
    const hit = out.find((x) => x.text === t)
    if (hit) hit.tags.push(tag(m.i))
    else out.push({ tags: [tag(m.i)], text: t })
  }
  return out
}

/** What each card says, before any simulation: rows at the top of the table. */
function CardRows({ shown }: { shown: Col[] }) {
  // a row of identical results may hold cards that say different things: each says its own, by number
  const row = (label: string, text: (c: Member) => string) => {
    const cells = shown.map((c) => memberFacts(c.members, text))
    if (cells.every((f) => f.every((x) => !x.text))) return null
    return (
      <tr>
        <td class="stick qty"><span class="muted small">{label}</span></td>
        {shown.map((c, k) => {
          const f = cells[k]!
          return <td key={c.i} class="small">{f.length === 1 ? f[0]!.text : f.map((x) => <div key={x.tags.join()}>{x.tags.join(' ')}: {x.text || '—'}</div>)}</td>
        })}
      </tr>
    )
  }
  return (
    <>
      <tr class="mhead"><th class="stick">The card itself <span class="chip">card</span></th>{shown.map((c) => <td key={c.i} />)}</tr>
      {shown.some((c) => c.members.length > 1) && (
        <tr>
          <td class="stick qty"><span class="muted small">the same results</span></td>
          {shown.map((c) => <td key={c.i} class="small">{c.members.slice(1).map((x) => x.label).join(', ')}</td>)}
        </tr>)}
      {row('family', (c) => c.mo.chk?.family ?? '')}
      {row('not in card', (c) => (c.mo.chk?.absent ?? []).map((p) => c.mo.chk?.why?.[p] ? `${p} (${c.mo.chk.why[p]})` : p).join(', '))}
      {row('left at default', (c) => (c.mo.chk?.default ?? []).join(', '))}
      {row('extensions', (c) => [...(c.mo.chk?.extensions ?? []), ...(c.mo.chk?.thermal_pin ? ['thermal pin'] : []), ...(c.mo.chk?.geometry ? [`geometry ${c.mo.chk.geometry}`] : [])].join(', '))}
      {row('dialect', (c) => (c.mo.chk?.dialect ?? []).join(', '))}
      {row('ratings it declares', (c) => Object.entries(c.mo.chk?.ratings ?? {}).map(([k, v]) => `${k} ${typeof v === 'number' ? si(v, k.startsWith('v') ? 'V' : k.startsWith('i') ? 'A' : '') : v}`).join(', '))}
      {row('author: modelled', (c) => (c.mo.chk?.claims?.yes ?? []).join(', '))}
      {row('author: not modelled', (c) => (c.mo.chk?.claims?.no ?? []).join(', '))}
      {row('written for', (c) => c.mo.chk?.claims?.simulator ?? '')}
    </>
  )
}

/** The single numbers a measurement gives the models shown, in the catalogue's order: its outputs that no
 *  chart draws, with their units and what each is. */
function rowsOf(mid: string, m: Measurement | undefined, shown: Col[]) {
  const plotted = new Set((m?.outputs ?? []).filter((o) => o.plotted).map((o) => o.key.split('@')[0] ?? o.key))
  const keys = new Set<string>()
  for (const c of shown) for (const d of Object.values(c.rec.values[mid] ?? {})) for (const k of Object.keys(d)) if (!plotted.has(k.split('@')[0] ?? k)) keys.add(k)
  return {
    rows: orderKeys([...keys], m),
    units: new Map((m?.outputs ?? []).map((o) => [o.key.split('@')[0] ?? o.key, o.unit])),
    whats: new Map((m?.outputs ?? []).map((o) => [o.key.split('@')[0] ?? o.key, o.what])),
  }
}

/** The head of a table of models: one column per row of the model list, its other models counted. */
function ModelColumns({ shown }: { shown: Col[] }) {
  return (
    <thead>
      <tr>
        <th class="stick corner">Quantity</th>
        {shown.map((c) => <th key={c.i} class="mcol" title={c.members.map((x) => x.label).join('\n')}><Swatch i={c.i} /> {c.label}{c.members.length > 1 && <span class="muted"> +{c.members.length - 1}</span>}</th>)}
      </tr>
    </thead>
  )
}

function MeasurementRows({ mid, m, rows, shown, engine, primary, units, whats, onAbout }: {
  mid: string; m?: Measurement; rows: string[]; shown: Col[]; engine: string; primary: string
  units: Map<string, string>; whats: Map<string, string>; onAbout: () => void
}) {
  return (
    <>
      <tr class="mhead">
        <th class="stick">
          {m?.name ?? mid} {m && <span class="chip">{m.group}</span>}{' '}
          <button type="button" class="linkish small" onClick={onAbout}>how is this measured</button>
        </th>
        {shown.map((c) => {
          const code = c.rec.codes[mid]
          const a = c.rec.agree?.[mid]
          return (
            <td key={c.i} class="small">
              {code && code !== 'ok' && <span class={`k-${code.replace('/', '')}`} title={codeTitle(code)}>{code}</span>}
              {a && <span class={`chip agree a-${a[1].replace('>', 'gt').replace('%', '')}`} title={`spread ${si(a[0] * 100)} % over ${a[2].join(', ')}${a[3] ? `; odd one out: ${a[3]}` : ''}`}>{a[1]}</span>}
            </td>)
        })}
      </tr>
      {rows.map((k) => {
        const base = k.split('@')[0] ?? k
        return (
          <tr key={k}>
            <td class="stick qty" title={whats.get(base) ?? ''}><code>{k}</code></td>
            {shown.map((c) => {
              const cell = cellOf(c.rec, mid, k, engine, primary, units.get(base) ?? '')
              return <td key={c.i} class={`num ${cell.cls}`} title={cell.title}>{cell.text}</td>
            })}
          </tr>)
      })}
    </>
  )
}

/** The method page's entry for one measurement, and the decks behind it, in a dialog of its own. */
function About({ m, mid, drawings, shown, file, part, onClose }: { m?: Measurement; mid: string; drawings: string[]; shown: Col[]; file: CharacterFile; part: string; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => { ref.current?.showModal() }, [])
  const first = shown[0]
  const decks = first ? Object.entries(first.rec.decks).filter(([, d]) => d.ids.includes(mid)) : []
  return (
    <dialog ref={ref} class="about" onClose={onClose} onClick={(e) => { if (e.target === ref.current) onClose() }}>
      <div class="about-body stack-s">
        <div class="row" style={{ justifyContent: 'space-between' }}>
          <b>How is this measured</b>
          <button type="button" onClick={onClose}>close</button>
        </div>
        {/* the circuit and the deck for this part's polarity: a PNP part shows the PNP drawing and deck lines */}
        {m ? <Method m={m} drawings={drawings} polarity={first?.rec.polarity ?? Object.values(file.models)[0]?.polarity} concise /> : <p class="muted">No entry for {mid} on the method page.</p>}
        {first && (
          <div class="how stack-s small">
            <b>Repeat it</b> for {first.label} (hash <code>{first.rec.hash.slice(0, 12)}…</code>, part {part}):
            <ol>
              <li>Get the card from its link in the models table and save it as <code>model.lib</code>.</li>
              <li><code>sei bench deck {mid} --card model.lib --name {first.mo.name} --engine {file.primary} --hash {first.rec.hash}</code> writes the deck(s) below and prints their sha256.</li>
              <li><code>docker run --rm -v "$PWD":/w spicy-electronics-index-{file.primary} simrun /w/&lt;deck&gt;.cir</code>, then <code>sei bench read &lt;deck&gt;.raw --measurement {mid} --deck &lt;deck&gt;</code>.</li>
            </ol>
            <table class="small">
              <thead><tr><th>deck</th><th>analysis</th>{Object.keys(file.engines).map((e) => <th key={e}>{e}: sha256 prefix · models per deck</th>)}</tr></thead>
              <tbody>{decks.map(([name, d]) => (
                <tr key={name}><td><code>{name}</code></td><td>{d.analysis}</td>
                  {Object.keys(file.engines).map((e) => { const x = d[e] as { digest: string; pack: number } | undefined; return <td key={e}>{x ? <><code>{x.digest}</code> · {x.pack}</> : '—'}</td> })}
                </tr>))}</tbody>
            </table>
            {Object.values(first.rec.changes ?? {}).flat().length > 0 && <div class="muted">Changes made to the card before it ran: {[...new Set(Object.values(first.rec.changes).flat())].join(', ')}.</div>}
          </div>
        )}
      </div>
    </dialog>
  )
}

/** The x values of a catalogue grid. */
export function gridX(g: Grid | undefined): number[] {
  if (!g) return []
  if (g.values) return g.values
  const lo = g.from!
  const hi = g.to!
  if (g.per_decade) {
    const k = g.per_decade
    const a = Math.round(Math.log10(lo) * k)
    const b = Math.round(Math.log10(hi) * k)
    return Array.from({ length: b - a + 1 }, (_, i) => 10 ** ((a + i) / k))
  }
  const n = Math.round((hi - lo) / g.step!) + 1
  return Array.from({ length: n }, (_, i) => lo + i * g.step!)
}

/** What a trace was taken at, in words: its conditions, and in a family its base current as k × step. */
export function traceConditions(c: Curve, units: Record<string, string> = {}, autoStep?: number): string[] {
  const out: string[] = []
  for (const [k, v] of Object.entries(c.at ?? {})) {
    if (k === 'IB step') continue
    out.push(k === 'span' ? String(v) : `${k} = ${fmtChoice(v, units[k] ?? '')}`)
  }
  const step = traceStep(c, autoStep)
  if (c.k && step !== undefined) {
    const auto = typeof c.at?.['IB step'] !== 'number'
    out.unshift(`IB = ${c.k} × ${si(step, 'A')}${auto ? ' (auto step)' : ''} = ${si(c.k * step, 'A')}`)
  }
  return out
}

/** A family trace's step: the universal one it was taken at, or the model's own auto step. */
export function traceStep(c: Curve, autoStep?: number): number | undefined {
  const s = c.at?.['IB step']
  return typeof s === 'number' ? s : autoStep
}

/** A curve read at x: the value between the two published points around it (interpolated along the axes'
 *  own scales, so a log curve is read as straight lines in log space) and the slope of that segment. Outside
 *  the curve, its nearest end. */
export type Reading = { x: number; y: number; dx: number; dy: number }
export function readAt(pts: [number, number][], xv: number, logX = false, logY = false): Reading | null {
  if (!pts.length) return null
  if (pts.length === 1) return { x: pts[0]![0], y: pts[0]![1], dx: 0, dy: 0 }
  const f = (v: number) => (logX && v > 0 ? Math.log10(v) : v)
  let k = pts.findIndex((p, n) => n < pts.length - 1 && p[0] <= xv && xv <= pts[n + 1]![0])
  let x = xv
  if (k < 0) {
    k = xv < pts[0]![0] ? 0 : pts.length - 2
    x = xv < pts[0]![0] ? pts[0]![0] : pts[pts.length - 1]![0]
  }
  const a = pts[k]!
  const b = pts[k + 1]!
  const span = f(b[0]) - f(a[0])
  const w = span ? (f(x) - f(a[0])) / span : 0
  const y = logY && a[1] > 0 && b[1] > 0 ? 10 ** (Math.log10(a[1]) + w * (Math.log10(b[1]) - Math.log10(a[1]))) : a[1] + w * (b[1] - a[1])
  return { x, y, dx: b[0] - a[0], dy: b[1] - a[1] }
}

/** The catalogue's hover quantities for a reading of a curve: each [term, op, term] over x, y, the local slope,
 *  the trace's base current and the curve's conditions. A term that cannot be had (no base current, a flat
 *  slope) drops the quantity. */
export function hoverExtras(extras: HoverExtra[] | undefined, c: Curve, p: Reading | null, ib?: number): { label: string; unit: string; value: number }[] {
  if (!p) return []
  const term = (t: string): number | undefined => {
    if (t === 'x') return p.x
    if (t === 'y') return p.y
    if (t === 'dx') return p.dx
    if (t === 'dy') return p.dy
    if (t === 'ib') return ib
    if (t.startsWith('at.')) { const v = c.at?.[t.slice(3)]; return typeof v === 'number' ? v : undefined }
    return undefined
  }
  const out: { label: string; unit: string; value: number }[] = []
  for (const h of extras ?? []) {
    if (h.y !== c.y) continue
    const [l, op, r] = h.of
    const u = term(l)
    const v = term(r)
    if (u === undefined || v === undefined) continue
    // a slope that is flat at the published figures gives an infinite ratio: said as such (no Early effect)
    const value = op === '*' ? u * v : v !== 0 ? u / v : u !== 0 ? Infinity : NaN
    if (Number.isFinite(value) || value === Infinity) out.push({ label: h.label, unit: h.unit, value })
  }
  return out
}

/** The line nearest the cursor, measured to its drawn segments in the chart's pixels — not only to its samples,
 *  which a zoom spreads apart until none is in view — and only where a segment is inside the plot `box`.
 *  Returns the line's index, the point of it nearest the cursor, and the distance; null beyond `reach`. */
export function nearestLine(lines: [number, number][][], fx: number, fy: number, reach: number, box: [number, number, number, number]): { n: number; X: number; Y: number; d: number } | null {
  let best: { n: number; X: number; Y: number; d: number } | null = null
  const inside = (X: number, Y: number) => X >= box[0] - 0.5 && X <= box[2] + 0.5 && Y >= box[1] - 0.5 && Y <= box[3] + 0.5
  const consider = (n: number, X: number, Y: number) => {
    if (!inside(X, Y)) return
    const d = Math.hypot(X - fx, Y - fy)
    if (d <= reach && (!best || d < best.d)) best = { n, X, Y, d }
  }
  lines.forEach((pts, n) => {
    if (pts.length === 1) consider(n, pts[0]![0], pts[0]![1])
    for (let j = 1; j < pts.length; j++) {
      const [ax, ay] = pts[j - 1]!
      const [bx, by] = pts[j]!
      const ux = bx - ax
      const uy = by - ay
      const len = ux * ux + uy * uy
      const t = len ? Math.min(1, Math.max(0, ((fx - ax) * ux + (fy - ay) * uy) / len)) : 0
      consider(n, ax + t * ux, ay + t * uy)
    }
  })
  return best
}

/** A rating a card declares, as a limit on one axis of a chart: VCEO on a VCE axis, the IC rating on an IC
 *  axis. LTspice's catalogue fields are the only structured ratings the site has for now. */
export function ratingOn(axis: string, ratings?: Record<string, number | string>): { value: number; label: string } | null {
  const r = ratings ?? {}
  if (axis === 'vce' && typeof r.vceo === 'number') return { value: r.vceo, label: `VCEO ${si(r.vceo, 'V')}` }
  if (axis === 'ic' && typeof r.icrating === 'number') return { value: r.icrating, label: `IC rating ${si(r.icrating, 'A')}` }
  return null
}

/** What a point is beyond, of the ratings its model's card declares: one line each. */
export function beyondRatings(c: Curve, p: { x: number; y: number }, ratings?: Record<string, number | string>): string[] {
  const out: string[] = []
  for (const [axis, v] of [[c.x, p.x], [c.y, p.y]] as [string, number][]) {
    const lim = ratingOn(axis, ratings)
    if (lim && Math.abs(v) > lim.value) out.push(`⚠ beyond the card's ${lim.label}`)
  }
  return out
}

const W = 600
const H = 264
const M = { l: 54, r: 12, t: 34, b: 36 }   // the top holds the chart's own title: two lines

/** Items joined by ", " within `max` characters, the rest counted: "a, b and 3 more". */
export function fitList(items: string[], max: number): string {
  let out = ''
  for (let k = 0; k < items.length; k++) {
    const next = out ? `${out}, ${items[k]}` : items[k]!
    const rest = items.length - k - 1
    if (next.length + (rest ? ` and ${rest} more`.length : 0) > max && out) return `${out} and ${items.length - k} more`
    out = next
  }
  return out
}

/** The chart's own title, so a picture of it says what it is: the part, the curve and the conditions it is
 *  taken at; then the models drawn and the simulator. */
export function chartTitle(part: string, label: string, conds: string[], models: string[], engine: string, normalised = false): [string, string] {
  const what = `${part} — ${label}${conds.length ? `, ${conds.join(', ')}` : ''}${normalised ? ' (normalised)' : ''}`
  const tail = ` — simulated in ${engine}`
  return [what, `${fitList(models, 112 - tail.length)}${tail}`]
}

/** A magnifier, for the zoom buttons. */
function Lens() {
  return <svg class="lens" viewBox="0 0 16 16" aria-hidden="true"><circle cx="6.5" cy="6.5" r="4.5" /><line x1="10" y1="10" x2="15" y2="15" /></svg>
}

type Series = { i: number; k: number; label: string; name: string; colour: string; dash: string; pts: [number, number][]; own: boolean; c: Curve; ib?: number; cond: string[] }
/** A line under the cursor or pinned: the series (i, k; k = -1 for every trace of a model), where it is drawn,
 *  which of its points is nearest (j), and the x at which it is read (the cursor's). */
type Spot = { i: number; k: number; x: number; y: number; j: number; xv: number }

function nearest(pts: [number, number][], v: number, scale: 'log' | 'lin'): [number, number] {
  const dist = (p: [number, number]) => (scale === 'log' && p[0] > 0 && v > 0 ? Math.abs(Math.log(p[0] / v)) : Math.abs(p[0] - v))
  return pts.reduce((a, p) => (dist(p) < dist(a) ? p : a), pts[0]!)
}

/** The x range shown after a zoom or a pan, kept in the axis's own space (log10 on a log axis). */
export function zoomed(view: [number, number], at: number, factor: number, log: boolean): [number, number] {
  const f = (v: number) => (log ? Math.log10(v) : v)
  const g = (t: number) => (log ? 10 ** t : t)
  const [a, b] = [f(view[0]), f(view[1])]
  const c = Math.min(Math.max(f(at), a), b)
  const out: [number, number] = [g(c - (c - a) * factor), g(c + (b - c) * factor)]
  // no closer than the numbers can tell apart: a span below a millionth of the values (a thousandth of a
  // decade on a log axis) would leave the ticks unable to step and the curve a single point
  const span = log ? Math.log10(out[1] / out[0]) : out[1] - out[0]
  const floor = log ? 1e-3 : 1e-6 * Math.max(Math.abs(out[0]), Math.abs(out[1]), Number.MIN_VALUE)
  if (factor < 1 && !(span > floor)) return view
  return out
}

export function panned(view: [number, number], by: number, log: boolean): [number, number] {
  const f = (v: number) => (log ? Math.log10(v) : v)
  const g = (t: number) => (log ? 10 ** t : t)
  return [g(f(view[0]) - by), g(f(view[1]) - by)]
}

/** The y range that holds every point of the curve with a margin: what the chart opens at and resets to. */
export function fitRange(ys: number[], log: boolean): [number, number] {
  const lo = ys.length ? Math.min(...ys) : 0
  const hi = ys.length ? Math.max(...ys) : 1
  return log ? [lo / 1.2, hi * 1.2] : [lo - (hi - lo) * 0.05, hi + (hi - lo) * 0.05 || hi + 1]
}

/** A range part of the way, `t` from 0 to 1, from one range to another, in the axis's own space (decades on a
 *  log axis), so a zoom or a pan on a log axis moves at an even pace. */
export function between(a: [number, number], b: [number, number], t: number, log: boolean): [number, number] {
  const f = (v: number) => (log ? Math.log10(v) : v)
  const g = (u: number) => (log ? 10 ** u : u)
  return [g(f(a[0]) + (f(b[0]) - f(a[0])) * t), g(f(a[1]) + (f(b[1]) - f(a[1])) * t)]
}

/** Slow out, slow in: a quarter of a second that reads as a movement, not a jump. */
export const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2)
const GLIDE_MS = 250

/** The cursor's position on one axis: a small label with a halo, inside the plot. */
function AxisTag({ x, y, anchor, text }: { x: number; y: number; anchor: 'start' | 'middle'; text: string }) {
  return <text x={x} y={y} class="axtag" text-anchor={anchor}>{text}</text>
}

/** What the line under the cursor is: lines of text beside the point, on a pale box, kept inside the plot. */
function Tag({ x, y, lines, box }: { x: number; y: number; lines: string[]; box: [number, number, number, number] }) {
  const lh = 11
  const w = Math.max(...lines.map((l) => l.length)) * 5.3 + 8
  const h = lines.length * lh + 5
  const left = x + 10 + w > box[2]
  const above = y - 8 - h > box[1]
  const bx = left ? Math.max(box[0], x - 10 - w) : x + 10
  const by = above ? y - 8 - h : Math.min(y + 8, box[3] - h)
  return (
    <g class="tagbox">
      <rect x={bx} y={by} width={w} height={h} rx={3} />
      <text x={bx + 4} y={by + lh} class="tag">
        {lines.map((l, n) => <tspan key={n} x={bx + 4} dy={n ? lh : 0} class={!n ? 'th' : l.startsWith('⚠') ? 'tl tw' : 'tl'}>{l}</tspan>)}
      </text>
    </g>
  )
}

/** One curve of the list, for the models chosen, overlaid. It opens with the whole curve in view, and the axes
 *  then stay as the reader set them: a pan moves along the curve at the same scale, a zoom changes only its own
 *  axis, and only reset (or a double click) fits the whole curve again. The buttons glide to their new view;
 *  a drag follows the pointer. The conditions it is taken at (VCE, IC, T…) are the panel's, so they stay when
 *  another model is chosen and go into the address. */
function Chart({ part, m, row, shown, engine, engines, onEngine, primary, units, choice, onChoice, onAbout }: {
  part: string; m: Measurement; row: CurveRow; shown: Col[]; engine: string; engines: string[]; onEngine: (e: string) => void; primary: string
  units: Record<string, string>; choice: Record<string, Choice>; onChoice: (key: string, v: Choice) => void; onAbout: () => void
}) {
  const [hover, setHover] = useState<number | null>(null)
  const [hoverY, setHoverY] = useState<number | null>(null)   // the cursor's height, in the y axis's units
  const [near, setNear] = useState<Spot | null>(null)         // the line under the cursor
  const [pinned, setPinned] = useState<Spot | null>(null)     // the line a click selected
  const [view, setView] = useState<[number, number] | null>(null)
  const [yview, setYview] = useState<[number, number] | null>(null)
  const [normed, setNormed] = useState(false)
  const drag = useRef<{ x: number; y: number; view: [number, number]; yview: [number, number] | null; moved: boolean } | null>(null)
  // a glide in progress: its frame, and where it is going, so a second click continues from there
  const glide = useRef<{ frame: number; x: [number, number] | null; y: [number, number] | null } | null>(null)
  // what is on screen now, and the ranges a null view stands for: written on every draw, read by a glide
  const drawnNow = useRef<{ x: [number, number]; y: [number, number]; full: [number, number]; fit: [number, number]; logX: boolean; logY: boolean } | null>(null)
  const stop = () => { if (glide.current) cancelAnimationFrame(glide.current.frame); glide.current = null }
  useEffect(() => stop, [])
  /** Move the view to the ranges given (null: the whole curve) over a quarter of a second. */
  const goTo = (toX: [number, number] | null, toY: [number, number] | null) => {
    const now = drawnNow.current
    stop()
    if (!now) { setView(toX); setYview(toY); return }
    const from = { x: now.x, y: now.y }
    const end = { x: toX ?? now.full, y: toY ?? now.fit }
    const t0 = performance.now()
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / GLIDE_MS)
      if (k >= 1) { glide.current = null; setView(toX); setYview(toY); return }
      setView(between(from.x, end.x, ease(k), now.logX))
      setYview(between(from.y, end.y, ease(k), now.logY))
      glide.current = { frame: requestAnimationFrame(step), x: toX, y: toY }
    }
    glide.current = { frame: requestAnimationFrame(step), x: toX, y: toY }
  }
  const reset = () => goTo(null, null)
  // the quantity (y against x) shown, and the value of each selector its curves are taken at: a family
  // (the curve tracer's traces, the Gummel plot's two lines) is drawn whole for the value chosen
  const q = quantities(m).find((o) => o.id === row.qid) ?? quantities(m)[0]!
  const sels = selectorsOf(row.curves)
  const chosen = chosenOf(m, sels, choice)
  const drawn: { c: Curve; suffix: string }[] = m.family
    ? pickCurves(m.curves!, chosen, units).map(({ c }) => ({ c, suffix: c.name }))
    : pickCurves(q.curves, chosen, units)
  // the key's note on each model's own step applies to the auto family alone, not to a universal step
  const showStep = Boolean(m.family?.key) && !sels.some((s) => typeof chosen[s.key] === 'number')
  const curve = drawn[0]?.c ?? q.curves[0]!
  const grid = curve.grid ?? m.grid
  // a quantity some makers print relative to one value of each model (hFE / hFE at 1 mA, 5 V, 25 °C)
  const norm = (m.normalise ?? []).find((n) => n.y === curve.y)
  const relative = Boolean(norm && normed)
  // another model, another value, another engine: the y axis follows the data again (another curve is
  // another chart altogether: the panel draws one per curve)
  useEffect(() => { stop(); setYview(null); setPinned(null) }, [shown.map((c) => c.i).join(','), JSON.stringify(chosen), relative, engine])
  const gx = gridX(grid)
  // a transient keeps [t, y] pairs of its own; everything else sits on the catalogue's grid
  // the selected engine's own curve where it was published (it differs from the primary's by more than 1 %), else the primary's
  const series: Series[] = shown.flatMap((c) => drawn.flatMap(({ c: cv, suffix }, k) => {
    const own = engine !== primary ? c.rec.other_curves?.[engine]?.[m.id]?.[cv.name] : undefined
    const raw = own ?? c.rec.curves?.[m.id]?.[cv.name]
    if (!raw) return []
    let pts: [number, number][] = Array.isArray(raw[0])
      ? (raw as [number, number][])
      : (raw as (number | null)[]).map((y, k) => [gx[k], y] as [number, number | null]).filter((p): p is [number, number] => p[1] !== null && Number.isFinite(p[1]))
    if (relative && norm) {
      const ref = c.rec.values[norm.by.id]?.[primary]?.[norm.by.key]
      if (typeof ref !== 'number' || !ref) return []
      pts = pts.map(([x0, y0]) => [x0, y0 / ref])
    }
    // a family trace's base current, from its step (the universal one, or this model's auto step)
    const auto = c.rec.values[m.id]?.[primary]?.[m.family?.key ?? '']
    const step = traceStep(cv, typeof auto === 'number' ? auto : undefined)
    const ib = cv.k && step !== undefined ? cv.k * step : (typeof cv.at?.IB === 'number' ? cv.at.IB : undefined)
    return pts.length > 1 ? [{ i: c.i, k, label: c.label, name: suffix, colour: colourOf(c.i), dash: dashOf(c.i), pts, own: engine === primary || Boolean(own),
      c: cv, ib, cond: (() => { const t = traceConditions(cv, units, typeof auto === 'number' ? auto : undefined); return t.length || !m.family ? t : [cv.name] })() }] : []
  }))
  const xUnit = curve.x_unit ?? grid?.unit ?? ''
  const yUnit = relative ? '' : (curve.unit ?? '')
  const gv = grid?.values
  const logX = xUnit !== 's' && Boolean(grid?.per_decade || (gv && (gv[0] ?? 0) > 0 && (gv[gv.length - 1] ?? 0) / (gv[0] ?? 1) > 20))
  // the base drive's edges, for the switching fixture: what td and ts are measured from, for the pulse chosen
  const cnd = m.conditions as Record<string, number>
  const tOn = typeof chosen.pulse === 'number' ? chosen.pulse : cnd.t_on_s
  const marks: { t: number; label: string }[] = typeof tOn === 'number' && typeof cnd.t_start_s === 'number' && xUnit === 's'
    ? [{ t: cnd.t_start_s + (cnd.edge_s ?? 0), label: 'drive on' }, { t: cnd.t_start_s + (cnd.edge_s ?? 0) + tOn, label: 'drive off' }]
    : []
  let body: preact.ComponentChildren = (
    <p class="muted small nocurve">No chosen model has this curve: {shown.map((c) => `${tag(c.i)} ${curveStatus(c.rec, row)}`).join(', ')}.</p>)
  let controls: preact.ComponentChildren = null
  let anchor: (i: number) => Spot | null = () => null
  if (series.length) {
    const xs = series.flatMap((s) => s.pts.map((p) => p[0]))
    const full: [number, number] = [Math.min(...xs), Math.max(...xs)]
    const [vx0, vx1] = view ?? full
    // the y axis holds the whole curve until the reader zooms or pans it: a pan along x keeps the scale
    const logY = curve.scale === 'log'
    const fit = fitRange(series.flatMap((s) => s.pts.map((p) => p[1])).filter((y) => !logY || y > 0), logY)
    const x: Axis = [curve.x, xUnit, logX ? 'log' : 'lin', vx0, vx1]
    const y: Axis = [curve.y, yUnit, curve.scale, ...(yview ?? fit)]
    if (x[3] === x[4]) x[4] = x[3] + 1
    if (y[3] === y[4]) y[4] = y[3] * 2 || 1
    drawnNow.current = { x: [x[3], x[4]], y: [y[3], y[4]], full, fit, logX, logY }
    const pw = W - M.l - M.r
    const ph = H - M.t - M.b
    const px = (v: number) => M.l + place(x, v, pw)
    const py = (v: number) => M.t + ph - place(y, v, ph)
    anchor = (i) => {
      const mine = series.filter((t) => t.i === i)
      const top = mine[mine.length - 1]
      if (!top) return null
      let j = top.pts.length - 1
      for (let n = top.pts.length - 1; n >= 0; n--) {
        const [x0, y0] = top.pts[n]!
        if (x0 >= vx0 && x0 <= vx1 && (!logY || y0 > 0)) { j = n; break }
      }
      const last = top.pts[j]!
      return { i, k: -1, x: px(last[0]), y: py(last[1]), j, xv: last[0] }     // k = -1: every trace of the model
    }
    const ok = (p: [number, number]) => (x[2] !== 'log' || p[0] > 0) && (y[2] !== 'log' || p[1] > 0) && Number.isFinite(p[1])
    const path = (pts: [number, number][]) => pts.filter(ok).map((p, k) => `${k ? 'L' : 'M'}${px(p[0]).toFixed(1)},${py(p[1]).toFixed(1)}`).join('')
    // the published samples, one dot each: zero-length strokes with round caps, one path per series
    const dots = (pts: [number, number][]) => pts.filter(ok).filter((p) => p[0] >= vx0 && p[0] <= vx1).map((p) => `M${px(p[0]).toFixed(1)},${py(p[1]).toFixed(1)}h0`).join('')
    const xAt = (e: MouseEvent) => {
      const svg = e.currentTarget as SVGSVGElement
      const r = svg.getBoundingClientRect()
      const fx = ((e.clientX - r.left) / r.width * W - M.l) / pw
      return logX ? 10 ** (Math.log10(vx0) + fx * (Math.log10(vx1) - Math.log10(vx0))) : vx0 + fx * (vx1 - vx0)
    }
    const yspan = logY ? Math.log10(y[4]) - Math.log10(y[3]) : y[4] - y[3]
    const onMove = (e: MouseEvent) => {
      const d = drag.current
      if (d && (e.buttons & 1)) {
        const svg = e.currentTarget as SVGSVGElement
        const r = svg.getBoundingClientRect()
        const dspan = logX ? Math.log10(d.view[1]) - Math.log10(d.view[0]) : d.view[1] - d.view[0]
        if (Math.abs(e.clientX - d.x) > 2 || Math.abs(e.clientY - d.y) > 2) {
          d.moved = true
          setView(panned(d.view, (e.clientX - d.x) / r.width * (W / pw) * dspan, logX))
          if (d.yview) setYview(panned(d.yview, -(e.clientY - d.y) / r.height * (H / ph) * yspan, logY))
        }
        return
      }
      setHover(xAt(e))
      // the line nearest the cursor, in the chart's own pixels, lights up and says which model it is
      const svg = e.currentTarget as SVGSVGElement
      const r = svg.getBoundingClientRect()
      const fx = (e.clientX - r.left) / r.width * W
      const fy = (e.clientY - r.top) / r.height * H
      const fyv = (M.t + ph - fy) / ph
      setHoverY(logY ? 10 ** (Math.log10(y[3]) + fyv * (Math.log10(y[4]) - Math.log10(y[3]))) : y[3] + fyv * (y[4] - y[3]))
      // the nearest drawn segment within 10 screen pixels, whatever the zoom: the chart is drawn smaller than its
      // 600 units, so the reach is converted from the screen
      const reach = 10 * (W / r.width)
      const hit = nearestLine(series.map((sr) => sr.pts.filter(ok).map((p) => [px(p[0]), py(p[1])] as [number, number])), fx, fy, reach, [M.l, M.t, M.l + pw, M.t + ph])
      const sr = hit ? series[hit.n]! : null
      // the curve is read at the x of the point of the line nearest the cursor (on a steep knee, not the cursor's own x)
      const xv = hit ? (logX ? 10 ** (Math.log10(vx0) + (hit.X - M.l) / pw * (Math.log10(vx1) - Math.log10(vx0))) : vx0 + (hit.X - M.l) / pw * (vx1 - vx0)) : 0
      setNear(hit && sr ? { i: sr.i, k: sr.k, x: hit.X, y: hit.Y, j: 0, xv } : null)
    }
    // a button acts on where the view is going, so quick clicks add up instead of starting over mid-glide
    const goal = glide.current
    const goalX: [number, number] = goal ? goal.x ?? full : [vx0, vx1]
    const goalY: [number, number] = goal ? goal.y ?? fit : [y[3], y[4]]
    const keepX = goal ? goal.x : view
    const keepY = goal ? goal.y : yview
    const mid = (r: [number, number], log: boolean) => (log ? 10 ** ((Math.log10(r[0]) + Math.log10(r[1])) / 2) : (r[0] + r[1]) / 2)
    const spanOf = (r: [number, number], log: boolean) => (log ? Math.log10(r[1]) - Math.log10(r[0]) : r[1] - r[0])
    controls = (
      <span class="zoomctl">
        <button type="button" title="zoom in, x axis" onClick={() => goTo(zoomed(goalX, mid(goalX, logX), 0.5, logX), keepY)}><Lens />+x</button>
        <button type="button" title="zoom out, x axis" onClick={() => goTo(zoomed(goalX, mid(goalX, logX), 2, logX), keepY)}><Lens />−x</button>
        <button type="button" title="zoom in, y axis" onClick={() => goTo(keepX, zoomed(goalY, mid(goalY, logY), 0.5, logY))}><Lens />+y</button>
        <button type="button" title="zoom out, y axis" onClick={() => goTo(keepX, zoomed(goalY, mid(goalY, logY), 2, logY))}><Lens />−y</button>
        <button type="button" title="pan left" onClick={() => goTo(panned(goalX, spanOf(goalX, logX) * 0.25, logX), keepY)}>◀</button>
        <button type="button" title="pan right" onClick={() => goTo(panned(goalX, -spanOf(goalX, logX) * 0.25, logX), keepY)}>▶</button>
        <button type="button" title="pan up" onClick={() => goTo(keepX, panned(goalY, -spanOf(goalY, logY) * 0.25, logY))}>▲</button>
        <button type="button" title="pan down" onClick={() => goTo(keepX, panned(goalY, spanOf(goalY, logY) * 0.25, logY))}>▼</button>
        <button type="button" title="back to the whole curve" disabled={!view && !yview && !goal} onClick={reset}>reset</button>
      </span>
    )
    const conds = sels.map((s) => (chosen[s.key] === 'all' ? `every ${s.key}` : s.key === 'span' ? String(chosen[s.key]) : `${s.key} = ${fmtChoice(chosen[s.key], units[s.key] ?? '')}`))
    const title = chartTitle(part, row.label, conds, shown.map((c) => `${tag(c.i)} ${c.mo.name} · ${c.mo.source}${c.members.length > 1 ? ` (+${c.members.length - 1} identical)` : ''}`), engine, relative)
    const xf = tickFigures(ticks(x), 3)   // enough digits to tell neighbouring ticks apart, however deep the zoom
    const yf = tickFigures(ticks(y), 2)
    const clip = `clip-${m.id}`
    body = (
      <svg class={`fig${view ? ' zoomed' : ''}`} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title.join('. ')}
        onMouseMove={onMove} onMouseLeave={() => { setHover(null); setHoverY(null); setNear(null); drag.current = null }}
        onMouseDown={(e) => { if (e.button === 0) { e.preventDefault(); stop(); drag.current = { x: e.clientX, y: e.clientY, view: [vx0, vx1], yview: [y[3], y[4]], moved: false } } }}
        onMouseUp={() => {
          // a click (a press that did not drag) selects the line under the cursor, or clears the selection
          const d = drag.current
          drag.current = null
          if (d && !d.moved) setPinned(near && !(pinned && pinned.i === near.i && pinned.k === near.k) ? near : null)
        }} onDblClick={reset}>
        <text x={M.l} y={13} class="ctitle">{title[0]}</text>
        <text x={M.l} y={26} class="csub">{title[1]}</text>
        <defs><clipPath id={clip}><rect x={M.l} y={M.t} width={pw} height={ph} /></clipPath></defs>
        <rect x={M.l} y={M.t} width={pw} height={ph} class="frame" />
        {ticks(x).map((t) => <line key={`x${t.v}`} x1={px(t.v)} x2={px(t.v)} y1={M.t} y2={M.t + ph} class={t.major ? 'grid major' : 'grid'} />)}
        {ticks(y).map((t) => <line key={`y${t.v}`} y1={py(t.v)} y2={py(t.v)} x1={M.l} x2={M.l + pw} class={t.major ? 'grid major' : 'grid'} />)}
        {ticks(x).filter((t) => t.major).map((t) => <text key={`xl${t.v}`} x={px(t.v)} y={M.t + ph + 12} class="tick" text-anchor="middle">{si(t.v, xUnit, xf)}</text>)}
        {ticks(y).filter((t) => t.major).map((t) => <text key={`yl${t.v}`} x={M.l - 4} y={py(t.v) + 3} class="tick" text-anchor="end">{si(t.v, yUnit, yf)}</text>)}
        <text x={M.l + pw / 2} y={H - 4} class="axis" text-anchor="middle">{axisName(curve.x)}</text>
        <text x={11} y={M.t + ph / 2} class="axis" text-anchor="middle" transform={`rotate(-90 11 ${M.t + ph / 2})`}>{relative && norm ? norm.label : axisName(curve.y)}</text>
        <g clip-path={`url(#${clip})`}>
          {/* the ratings the shown models' cards declare: one dashed line per distinct value, in the model's
              colour when one model declares it, grey when several do */}
          {(['x', 'y'] as const).flatMap((ax) => {
            // every card of a row: models with identical results may still declare different ratings
            const groups = new Map<number, { row: number; m: Member }[]>()
            for (const c of shown) {
              for (const x of c.members) {
                const lim = ratingOn(ax === 'x' ? curve.x : curve.y, x.mo.chk?.ratings)
                if (lim && !(ax === 'y' && relative)) groups.set(lim.value, [...(groups.get(lim.value) ?? []), { row: c.i, m: x }])
              }
            }
            return [...groups.entries()].sort((a, b) => a[0] - b[0]).map(([v, cs], n) => {
              const lim = ratingOn(ax === 'x' ? curve.x : curve.y, cs[0]!.m.mo.chk?.ratings)!
              const rowsOf = new Set(cs.map((x) => x.row))
              const colour = rowsOf.size === 1 ? colourOf(cs[0]!.row) : '#888'
              const who = cs.map((x) => tag(x.m.i)).join(' ')
              if (ax === 'x') {
                if (v < vx0 || v > vx1) return null
                return <g key={`lx${v}`} class="limit"><line x1={px(v)} x2={px(v)} y1={M.t} y2={M.t + ph} stroke={colour} />
                  <text x={px(v) - 3} y={M.t + 10 + 10 * n} text-anchor="end" fill={colour}>{lim.label} · card {who}</text></g>
              }
              if (v < Math.min(y[3], y[4]) || v > Math.max(y[3], y[4])) return null
              return <g key={`ly${v}`} class="limit"><line x1={M.l} x2={M.l + pw} y1={py(v)} y2={py(v)} stroke={colour} />
                <text x={M.l + pw - 3 - 150 * n} y={py(v) - 3} text-anchor="end" fill={colour}>{lim.label} · card {who}</text></g>
            })
          })}
          {marks.filter((k) => k.t >= vx0 && k.t <= vx1).map((k) => (
            <g key={k.label}><line x1={px(k.t)} x2={px(k.t)} y1={M.t} y2={M.t + ph} class="mark" /><text x={px(k.t) + 3} y={M.t + 10} class="tick">{k.label}</text></g>))}
          {series.map((s) => {
            const hot = (near && near.i === s.i && (near.k === s.k || near.k < 0)) || (pinned && pinned.i === s.i && (pinned.k === s.k || pinned.k < 0))
            const cls = hot ? ' hot' : (near || pinned ? ' dim' : '')
            return (
              <g key={`${s.i}.${s.k}`}>
                <path d={path(s.pts)} class={`mine${cls}`} stroke={s.colour} stroke-dasharray={s.dash || undefined} />
                <path d={dots(s.pts)} class={`dots${cls}`} stroke={s.colour} />
              </g>)
          })}
          {hover !== null && hover >= vx0 && hover <= vx1 && <line x1={px(hover)} x2={px(hover)} y1={M.t} y2={M.t + ph} class="cursor" />}
          {hoverY !== null && hover !== null && <line x1={M.l} x2={M.l + pw} y1={py(hoverY)} y2={py(hoverY)} class="cursor" />}
          {/* where the cursor is, on each axis */}
          {hover !== null && hover >= vx0 && hover <= vx1 && <AxisTag x={px(hover)} y={M.t + ph - 4} anchor="middle" text={si(hover, xUnit, 4)} />}
          {hoverY !== null && hover !== null && <AxisTag x={M.l + 3} y={py(hoverY) + 3} anchor="start" text={si(hoverY, yUnit, 4)} />}
          {[pinned, near].filter((t): t is Spot => Boolean(t)).filter((t, j, all) => j === 0 || !(all[0] && t.i === all[0].i && t.k === all[0].k)).map((t) => {
            const mine = series.filter((u) => u.i === t.i)
            const sr = t.k < 0 ? mine[mine.length - 1] : mine.find((u) => u.k === t.k)
            if (!sr) return null
            // the curve read at the cursor's x, between the published points around it
            const p = readAt(sr.pts, t.xv, logX, logY)
            if (!p) return null
            const extras = relative ? [] : hoverExtras(m.hover, sr.c, p, sr.ib)
            const members = shown.find((c) => c.i === sr.i)?.members ?? []
            const beyond = [...new Set(members.flatMap((x) => beyondRatings(sr.c, p, x.mo.chk?.ratings)))]
            const lines = [
              sr.label + (members.length > 1 ? ` +${members.length - 1}` : ''),
              ...(sr.cond.length ? [sr.cond.join(', ')] : []),
              `${axisName(sr.c.x)} = ${si(p.x, xUnit, 4)}, ${relative && norm ? norm.label : axisName(sr.c.y)} = ${si(p.y, yUnit, 4)}`,
              ...(extras.length ? [extras.map((e) => `${e.label} = ${e.value === Infinity ? '∞' : si(e.value, e.unit, 3)}`).join(' · ')] : []),
              ...(relative ? [] : beyond),
            ]
            return (
              <g key={`${t.i}.${t.k}`}>
                <circle cx={px(p.x)} cy={py(p.y)} r={3} class="spot" stroke={sr.colour} />
                <Tag x={px(p.x)} y={py(p.y)} lines={lines} box={[M.l, M.t, M.l + pw, M.t + ph]} />
              </g>)
          })}
        </g>
        {m.family && <text x={M.l + 6} y={M.t + 12} class="tick note">{m.family.note}</text>}
      </svg>
    )
  }
  return (
    <div class="figcard one">
      <h4><span class="qty">{row.label}</span>
        {sels.map((s) => (
          <label key={s.key} class="sel" title={`${s.key}: the curves are taken at these values; "all" overlays them`}>{s.key}{' '}
            <select value={chosen[s.key] === 'all' ? 'all' : String(s.values.findIndex((v) => sameValue(v, chosen[s.key]!)))}
              onChange={(e) => { const v = (e.target as HTMLSelectElement).value; onChoice(s.key, v === 'all' ? 'all' : s.values[Number(v)]!) }}>
              {s.values.map((v, i) => <option key={String(v)} value={String(i)}>{fmtChoice(v, units[s.key] ?? '')}</option>)}
              {s.values.length > 1 && <option value="all">all</option>}
            </select>
          </label>))}
        {norm && <label class="sel" title={norm.label}><input type="checkbox" checked={normed} onChange={() => setNormed((v) => !v)} /> normalised</label>}
        {engines.length > 1
          ? <label class="sel" title={engine === primary ? `the primary simulator's run` : `${engine}'s own curve where it differs from ${primary}'s by more than 1 %; elsewhere ${primary}'s, marked = ${primary}`}>simulated in{' '}
              <select value={engine} onChange={(e) => onEngine((e.target as HTMLSelectElement).value)}>{engines.map((e) => <option key={e} value={e}>{e}</option>)}</select></label>
          : <span class="eng muted small">simulated in {engine}</span>}
        {' '}<button type="button" class="linkish small" onClick={onAbout}>how is this measured</button></h4>
      <p class="muted small mname">{m.name}</p>
      {body}
      {/* the key under the chart: which line is whose, and each model's value under the cursor; the models
          themselves are chosen in the list beside it */}
      <ul class="figkey small" title="the buttons zoom and pan; dragging the chart pans it; a click on a line keeps it lit, a click elsewhere lets go; double-click resets">
        {shown.map((c) => {
          const ss = series.filter((x) => x.i === c.i)
          const s = ss[ss.length - 1]                       // a family: the top trace is the one read out
          const p = s && hover !== null ? nearest(s.pts, hover, logX ? 'log' : 'lin') : null
          const all = ss.length > 1 && hover !== null ? ss.map((t) => `${t.name ? t.name + ': ' : ''}${si(nearest(t.pts, hover, logX ? 'log' : 'lin')[1], yUnit)}`).join(' · ') : ''
          const stepKey = showStep ? m.family?.key : undefined
          const stepRaw = stepKey ? c.rec.values[m.id]?.[primary]?.[stepKey] : undefined
          const step = typeof stepRaw === 'number' ? si(stepRaw, m.outputs.find((o) => o.key === stepKey)?.unit ?? '') : ''
          const why = m.family?.because
          const whyRaw = why ? c.rec.values[why.id]?.[primary]?.[why.key] : undefined
          const because = why && typeof whyRaw === 'number' ? why.label.replace('{value}', si(whyRaw, '')) : ''
          const same = c.members.length > 1 ? `\nthe same result: ${c.members.slice(1).map((x) => x.label).join(', ')}` : ''
          return (
            <li key={c.i} class={`${s ? '' : 'faint'}${near?.i === c.i || pinned?.i === c.i ? ' hot' : ''}`} title={(all || (s && !s.own ? `${primary}'s curve: ${engine} agrees within 1 %` : c.label)) + same}
              onMouseEnter={() => setNear(anchor(c.i))} onMouseLeave={() => setNear(null)}
              onClick={() => setPinned(pinned && pinned.i === c.i ? null : anchor(c.i))}>
              <Swatch i={c.i} /><span class="lb">{c.label}{c.members.length > 1 && <span class="muted"> +{c.members.length - 1}</span>}</span>{step && <span class="muted step" title={because ? `the step is set by the model's gain: ${because}` : undefined}>step {step}{because && <>, as {because}</>}</span>}{s && !s.own && <span class="muted">=</span>}<span class="rv">{p ? si(p[1], yUnit) : s ? '' : curveStatus(c.rec, row)}</span>
            </li>)
        })}
      </ul>
      <div class="small muted row wrap chartbar">
        {controls}
        <span class="readout">{hover !== null && series.length > 0
          ? <>{axisName(curve.x)} = {si(hover, xUnit, 5)}{hoverY !== null && <>, {axisName(curve.y)} = {si(hoverY, yUnit, 4)}</>}</>
          : ''}</span>
      </div>
    </div>
  )
}
