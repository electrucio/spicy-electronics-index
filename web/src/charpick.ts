/**
 * The vocabulary of the characterization's curves, apart from how they are drawn: the names a quantity is
 * printed with, the quantities a measurement's curves show, and the selectors (VCE, IC, T…) its curves are
 * taken at. Pure functions, so the lists, the search and the address can be tested without a page.
 */
import { si, siValue } from './format'
import type { Curve, Measurement, ModelCharacter, PartModel } from './types'

export const AXIS: Record<string, string> = {
  vce: 'VCE', ic: 'IC', ib: 'IB', vbe: 'VBE', hfe: 'hFE', hfe_ac: 'hfe', h21: '|hfe|', ft: 'fT', f: 'f', t: 't', rs: 'RS',
  v: 'VR', vcesat: 'VCE(sat)', vbesat: 'VBE(sat)', cob: 'Cob', cib: 'Cib', en: 'en', in: 'in', nf: 'NF', vt: 'VT',
  td: 'td', tr: 'tr', ts: 'ts', tf: 'tf', dvbe_dt: 'dVBE/dT', vt_band: 'VT, 10 Hz–15.7 kHz', von: 'V',
  va: 'Va', ia: 'Ia', vg1: 'Vg1', ig: 'Ig', mu: 'µ', gm: 'gm', ra: 'ra', vout: 'Vout (rms)', thd: 'THD', h2: 'H2', h3: 'H3',
}

/** The name a quantity is printed with: VCE, IC, hFE, |hfe|… (the catalogue's keys are lower case). */
export function axisName(key: string): string {
  return AXIS[key] ?? key
}

/** The quantities a measurement's curves show (y against x), each with its curves, in the catalogue's order. */
export function quantities(m: Measurement): { id: string; label: string; curves: Curve[] }[] {
  const out: { id: string; label: string; curves: Curve[] }[] = []
  const xs = new Set((m.curves ?? []).map((c) => c.x))
  for (const c of m.curves ?? []) {
    const id = `${c.y}|${c.x}`
    let q = out.find((o) => o.id === id)
    if (!q) {
      q = { id, label: xs.size > 1 ? `${axisName(c.y)} against ${axisName(c.x)}` : axisName(c.y), curves: [] }
      out.push(q)
    }
    q.curves.push(c)
  }
  return out
}

export type Choice = number | string   // a selector's value, or 'all'

/** Two selector values are the same: numbers within a millionth, texts exactly. */
export function sameValue(a: Choice, b: Choice): boolean {
  return typeof a === 'number' && typeof b === 'number' ? Math.abs(a - b) <= 1e-6 * Math.max(Math.abs(a), Math.abs(b), 1e-300) : a === b
}

/** The selectors of a quantity: each parameter its curves are taken at, with the values in the catalogue's order. */
export function selectorsOf(curves: Curve[]): { key: string; values: Choice[] }[] {
  const out: { key: string; values: Choice[] }[] = []
  for (const c of curves) {
    for (const [k, v] of Object.entries(c.at ?? {})) {
      let s = out.find((o) => o.key === k)
      if (!s) {
        s = { key: k, values: [] }
        out.push(s)
      }
      if (!s.values.some((w) => sameValue(w, v))) s.values.push(v)
    }
  }
  return out
}

/** What a selector shows first: the measurement's `select` (a value, or 'all'), else its first value. */
export function firstChoice(m: Measurement, sel: { key: string; values: Choice[] }): Choice {
  const want = m.select?.[sel.key]
  if (want === 'all') return 'all'
  if (want !== undefined) {
    const hit = sel.values.find((v) => sameValue(v, want))
    if (hit !== undefined) return hit
  }
  return sel.values[0]!
}

export function fmtChoice(v: Choice | undefined, unit = ''): string {
  if (v === undefined) return ''
  return typeof v === 'number' ? si(v, unit) : String(v)
}

/** The curves of a quantity that match the choice, each with the suffix that tells it apart where 'all' overlays
 *  several values of a selector. */
export function pickCurves(curves: Curve[], choice: Record<string, Choice>, units: Record<string, string> = {}): { c: Curve; suffix: string }[] {
  return curves
    .filter((c) => Object.entries(choice).every(([k, v]) => v === 'all' || (c.at?.[k] !== undefined && sameValue(c.at[k]!, v))))
    .map((c) => ({ c, suffix: Object.entries(choice).filter(([, v]) => v === 'all').map(([k]) => `${k} = ${fmtChoice(c.at?.[k], units[k] ?? '')}`).join(', ') }))
}

/* ---------------------------------------------------------------------------------------------------
 * The list of curves: one row per quantity a measurement draws (a family, the curve tracer's traces or the
 * Gummel plot's two lines, is one row), under the measurement's group, found by its printed name and by
 * the other names a reader may know it by. Kind-specific words sit in small tables, so a JFET or MOSFET
 * catalogue only adds rows to them.
 * ------------------------------------------------------------------------------------------------- */

/** The curve shown when the address names none: the one every data sheet of the kind draws. */
export const DEFAULT_CURVE: Record<string, string> = {
  bjt: 'bjt-hfe-ic.hfe.ic', jfet: 'jfet-transfer.id.vgs', mosfet: 'mosfet-transfer.id.vgs', opamp: 'opamp-aol.gain.f',
}

/** The headings of the list: the catalogue's groups, as a reader writes them. */
export const GROUP_LABEL: Record<string, string> = {
  dc: 'DC', 'high-current': 'High current', capacitance: 'Capacitance', frequency: 'Frequency', switching: 'Switching',
  noise: 'Noise', temperature: 'Temperature', breakdown: 'Breakdown', distortion: 'Distortion', leakage: 'Leakage',
  recovery: 'Body diode', slew: 'Large signal', supply: 'Supply', output: 'Output',
}

/** A row whose axis names do not say what it is (the on voltages are three quantities on one "V" axis). */
export const ROW_LABEL: Record<string, string> = { 'bjt-on-voltages': 'VBE(sat), VBE(on) and VCE(sat) against IC' }

/** What tells two rows of the same name apart: added to the later ones only, the first keeps the plain name. */
export const QUALIFIER: Record<string, string> = {
  'bjt-hfe-ac': 'AC, 1 kHz', 'bjt-tracer': 'curve tracer', 'bjt-early': 'Early voltage', 'bjt-temperature': 'by temperature',
  'jfet-tracer': 'curve tracer', 'jfet-temperature': 'by temperature', 'jfet-gm': '1 kHz', 'jfet-ohmic': 'ohmic region',
  'mosfet-tracer': 'curve tracer', 'mosfet-temperature': 'by temperature', 'mosfet-gm': '1 kHz', 'mosfet-rdson': 'on-resistance',
  'triode-anode': 'anode family', 'triode-transfer': 'transfer', 'triode-params': 'against current',
  'opamp-stability': 'stability', 'opamp-aol-swing': 'open loop, DC', 'opamp-zout': 'output impedance', 'opamp-noise-rs': 'against RS',
}

/** Other names of a quantity, by its y axis: what a reader may type instead of the printed name. */
export const SYNONYMS: Record<string, string> = {
  hfe: 'beta gain current gain dc gain h21e bf', hfe_ac: 'beta gain small signal ac h21e', h21: 'gain frequency response h21e',
  ft: 'transition frequency gain bandwidth gbw unity', cob: 'capacitance output ccb cbc cjc miller', cib: 'capacitance input ceb cbe cje',
  en: 'noise voltage', in: 'noise current', nf: 'noise figure', vt: 'noise total', vt_band: 'noise total wideband audio band',
  td: 'delay time', tr: 'rise time', ts: 'storage time', tf: 'fall time',
  vcesat: 'saturation voltage', vbesat: 'saturation voltage', von: 'on voltages saturation', vbe: 'base emitter voltage',
  dvbe_dt: 'temperature coefficient tempco drift',
}

/** Words for every row of a measurement: the name of the instrument or method behind it. */
export const MEASUREMENT_WORDS: Record<string, string> = {
  'bjt-tracer': 'curve tracer output characteristics family', 'bjt-gummel': 'gummel plot', 'bjt-early': 'early voltage output resistance',
  'bjt-switching': 'waveform transient edges', 'bjt-ft': 'transition frequency',
  'jfet-tracer': 'curve tracer output characteristics family', 'jfet-transfer': 'transfer idss pinch-off vgs off square law',
  'jfet-gm': 'transconductance gfs yfs gos', 'jfet-ohmic': 'rds on resistor vcr', 'jfet-gate': 'gate diode leakage igss',
  'mosfet-tracer': 'curve tracer output characteristics family', 'mosfet-transfer': 'transfer threshold vth subthreshold',
  'mosfet-rdson': 'on resistance rds on', 'mosfet-gate-charge': 'gate charge qg qgd plateau miller', 'mosfet-body-diode': 'body diode vsd reverse recovery trr qrr',
  'opamp-aol': 'open loop gain phase gbw margin bode', 'opamp-closed-loop': 'closed loop bandwidth', 'opamp-slew': 'slew rate step',
  'opamp-cmrr-f': 'cmrr common mode rejection', 'opamp-psrr-f': 'psrr supply rejection', 'opamp-noise': 'noise en in density',
}

export type CurveRow = {
  id: string            // the address's name for it: mid.y.x, or the measurement's id for a family
  mid: string
  qid: string           // the quantity in quantities(m): `${y}|${x}`
  label: string         // always "Y against X"
  heading: string
  curves: Curve[]       // what the row draws: the quantity's curves, or every curve of a family
  words: string[]       // what the search looks in
}

/** Lower case, accents and the micro sign undone: µ is u, as a reader types it. */
function fold(s: string): string {
  return s.normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/[µμ]/g, 'u').toLowerCase()
}

/** A text's words, and each of its chunks squeezed together: "VCE(sat)" is vce, sat and vcesat. */
function wordsOf(text: string): string[] {
  const f = fold(text)
  return [...f.split(/[^a-z0-9]+/), ...f.split(/\s+/).map((w) => w.replace(/[^a-z0-9]/g, ''))].filter(Boolean)
}

export function groupLabel(group: string): string {
  return GROUP_LABEL[group] ?? (group.charAt(0).toUpperCase() + group.slice(1)).replace(/-/g, ' ')
}

/** The rows of the measurements a part's models have run (`present`), under their groups in the order the
 *  groups first appear in the catalogue, and inside a group in the catalogue's order. */
export function curveRows(ms: Measurement[], present: Set<string>): CurveRow[] {
  const raw: (CurveRow & { group: string; qualifier: string })[] = []
  for (const m of ms) {
    if (!present.has(m.id) || !m.curves?.length) continue
    const qs = quantities(m)
    const qualifier = QUALIFIER[m.id] ?? (() => {
      const keys = selectorsOf(m.curves).map((s) => s.key).filter((k) => k !== 'IB step')
      return keys.length ? `by ${keys.join(', ')}` : m.id
    })()
    const base = { mid: m.id, heading: groupLabel(m.group), group: m.group, qualifier }
    if (m.family) {
      const ys = [...new Set(m.curves.map((c) => c.y))]
      const label = ROW_LABEL[m.id] ?? `${ys.map(axisName).join(' and ')} against ${axisName(m.curves[0]!.x)}`
      raw.push({ ...base, id: m.id, qid: qs[0]!.id, label, curves: m.curves, words: ys.flatMap((y) => wordsOf(SYNONYMS[y] ?? '')) })
      continue
    }
    for (const q of qs) {
      const c = q.curves[0]!
      raw.push({ ...base, id: `${m.id}.${c.y}.${c.x}`, qid: q.id, label: ROW_LABEL[m.id] ?? `${axisName(c.y)} against ${axisName(c.x)}`, curves: q.curves, words: wordsOf(SYNONYMS[c.y] ?? '') })
    }
  }
  const order = [...new Set(raw.map((r) => r.group))]
  const rows = order.flatMap((g) => raw.filter((r) => r.group === g))
  // the same name twice (hFE and hfe count as the same): the later rows say which measurement they come from
  const taken = new Set<string>()
  for (const r of rows) {
    if (taken.has(r.label.toLowerCase())) r.label = `${r.label} · ${r.qualifier}`
    if (taken.has(r.label.toLowerCase())) r.label = `${r.label} (${r.mid})`
    taken.add(r.label.toLowerCase())
  }
  return rows.map(({ group: _g, qualifier: _q, ...r }) => ({
    ...r,
    // the qualifier's words are in the label when it is shown; one not shown is not searched ("by IC, VCE")
    words: [...new Set([...wordsOf(r.label), ...r.words, ...wordsOf(MEASUREMENT_WORDS[r.mid] ?? ''), ...wordsOf(r.heading)])],
  }))
}

/** A row matches when every word typed is the start of one of its words: "beta" finds hFE, "vce sat" and
 *  "VCE(sat)" find VCE(sat), "in" finds in and Cib (input) but not "against". "vs" is a word of joining. */
export function matchCurve(row: CurveRow, query: string): boolean {
  const has = (w: string) => row.words.some((h) => h.startsWith(w))
  return fold(query).split(/\s+/).filter(Boolean).every((chunk) => {
    const whole = chunk.replace(/[^a-z0-9]/g, '')
    if (!whole || whole === 'vs' || whole === 'versus') return true
    if (has(whole)) return true
    const parts = chunk.split(/[^a-z0-9]+/).filter(Boolean)
    return parts.length > 1 && parts.every((p) => p === 'vs' || has(p))
  })
}

/** The kind's usual curve when the part has it, else the first row. */
export function defaultCurve(rows: CurveRow[], kind: string): string {
  const want = DEFAULT_CURVE[kind]
  return rows.find((r) => r.id === want)?.id ?? rows[0]?.id ?? ''
}

/** The address's name of a curve, a measurement's id alone, or nothing known: the row it stands for. */
export function findRow(rows: CurveRow[], id: string | null | undefined): CurveRow | undefined {
  if (!id) return undefined
  return rows.find((r) => r.id === id) ?? rows.find((r) => r.mid === id)
}

/** Whether a model drew a row: 'ok' when one of its curves has two points or more, else the code its record
 *  gives the measurement (failed, absent, n/a), else 'no curve'; 'not run' when there is no record. */
export function curveStatus(rec: ModelCharacter | undefined, row: CurveRow): string {
  if (!rec) return 'not run'
  const mine = rec.curves?.[row.mid] ?? {}
  const drawn = row.curves.some((c) => {
    const raw = mine[c.name] as unknown[] | undefined
    if (!raw) return false
    const n = raw.filter((p) => (Array.isArray(p) ? Number.isFinite(p[1]) : typeof p === 'number' && Number.isFinite(p))).length
    return n >= 2
  })
  if (drawn) return 'ok'
  const code = rec.codes?.[row.mid]
  return code && code !== 'ok' ? code : 'no curve'
}

/* ---------------------------------------------------------------------------------------------------
 * The list of models: one row per distinct result. Cards that differ only where the bench cannot see it
 * (a rating, a comment, a manufacturer field, a parameter no measurement reaches) give the same curves and
 * numbers; they are one row, the others folded under it, and a search by any of their names finds the row.
 * ------------------------------------------------------------------------------------------------- */

/** The models whose results are identical, as lists of row indices, each ascending, the lowest first: the
 *  representative, the best ranked of them (the page lists models by bench rank, then most original first).
 *  Identical means the same codes, derived values, curves and values; what differs between copies of one
 *  result (the decks' packing, the other engines' curves within their 1 %, the fixes made to the card) is
 *  not compared. The records are written with sorted keys (`build.py`, `character_publish.py`), so their
 *  JSON text is canonical; the cheap fields sort first and the curves are compared only where they tie. */
export function groupModels(recs: { i: number; rec: ModelCharacter }[]): number[][] {
  const text = (v: unknown) => JSON.stringify(v ?? null)
  const buckets = new Map<string, { i: number; rec: ModelCharacter }[]>()
  for (const r of [...recs].sort((a, b) => a.i - b.i)) {
    const k = text([r.rec.codes, r.rec.derived])
    buckets.set(k, [...(buckets.get(k) ?? []), r])
  }
  const out: number[][] = []
  for (const b of buckets.values()) {
    if (b.length === 1) { out.push([b[0]!.i]); continue }
    const split = new Map<string, number[]>()
    for (const r of b) {
      const k = text([r.rec.curves, r.rec.values])
      split.set(k, [...(split.get(k) ?? []), r.i])
    }
    out.push(...split.values())
  }
  return out.sort((a, b) => a[0]! - b[0]!)
}

/** Letters and digits only, lower case: BD139_C, bd139c and "BD139 C" are one name. */
function squeeze(s: string): string {
  return fold(s).replace(/[^a-z0-9]/g, '')
}

/** Whether a model answers a search: by its own name, source, alias or the part it stands in for ('self'),
 *  only through one of its copies elsewhere ('copy'), or not at all. Every word typed must be inside one of
 *  them, so "139" finds BD139; "[3]" is the model's number and nothing else. */
export function matchModel(m: PartModel, i: number, query: string): 'self' | 'copy' | null {
  const words = query.split(/\s+/).filter(Boolean)
  if (!words.length) return 'self'
  const own = [m.name, m.source, m.alias ?? '', m.standin ?? ''].map(squeeze).filter(Boolean)
  const theirs = (m.copies ?? []).flatMap((c) => [c.name, c.source]).map(squeeze).filter(Boolean)
  const hit = (w: string, fields: string[]) => {
    if (/^\[\d+\]$/.test(w)) return w === `[${i + 1}]`
    const s = squeeze(w)
    return !s || fields.some((f) => f.includes(s))
  }
  if (words.every((w) => hit(w, own))) return 'self'
  if (words.every((w) => hit(w, [...own, ...theirs]))) return 'copy'
  return null
}

export type GroupView = { members: number[]; hits: Map<number, 'self' | 'copy'>; open: boolean }

/** The rows a search leaves: a row stays when any of its models answers, and opens when only others than
 *  its representative do, so the reader sees which (a search every model answers, "139", opens nothing).
 *  An empty search leaves every row, closed. */
export function filterGroups(groups: number[][], models: PartModel[], query: string): GroupView[] {
  const out: GroupView[] = []
  for (const members of groups) {
    const hits = new Map<number, 'self' | 'copy'>()
    if (query.trim()) {
      for (const i of members) {
        const h = models[i] ? matchModel(models[i]!, i, query) : null
        if (h) hits.set(i, h)
      }
      if (!hits.size) continue
    }
    out.push({ members, hits, open: hits.size > 0 && !hits.has(members[0]!) })
  }
  return out
}

/* ---------------------------------------------------------------------------------------------------
 * The selection in the address, so a link shows one curve of one model at one condition:
 *
 *     ?part=BD139&curve=bjt-hfe-ic.hfe.ic&model=59b3cf06,673b8dc1&at=vce:10
 *
 * `model` is a model's record hash, eight hex digits of it (a row number changes when the list does, a
 * hash does not), and any model of a row stands for the row. `at` holds only the conditions that differ
 * from the measurement's own default. All three use letters, digits and . - : , alone, so a forum or a
 * mail program keeps the link whole. Whatever is not understood is left out, and the defaults stand.
 * ------------------------------------------------------------------------------------------------- */

const OURS = ['curve', 'model', 'at']

/** A selector's name or text value as the address writes it: 'IB step' → ibstep, '−55 to 25°C' → -55to25c. */
export function slug(s: string): string {
  return fold(s).replace(/[−–]/g, '-').replace(/[^a-z0-9.-]/g, '')
}

/** A selector's value as the address writes it: 1e-3 → 1m, 1e-5 → 10u, 1e8 → 100M, 'all', or a text's slug. */
export function choiceToken(v: Choice): string {
  if (typeof v === 'number') return si(v, '', 6).replace(/\s+/g, '').replace(/[µμ]/g, 'u').replace(/\+/g, '')
  return v === 'all' ? 'all' : slug(v)
}

export type Sel = { key: string; values: Choice[] }

/** The value a stored choice gives a selector when the selector offers it, else the measurement's default. */
export function chosenOf(m: Measurement, sels: Sel[], stored: Record<string, Choice> = {}): Record<string, Choice> {
  return Object.fromEntries(sels.map((s) => {
    const v = stored[s.key]
    const ok = v !== undefined && (v === 'all' ? s.values.length > 1 : s.values.some((w) => sameValue(w, v)))
    return [s.key, ok ? (v === 'all' ? 'all' : s.values.find((w) => sameValue(w, v))!) : firstChoice(m, s)]
  }))
}

/** The conditions worth writing down: those that differ from the measurement's default. */
export function atTokens(m: Measurement, sels: Sel[], chosen: Record<string, Choice>): [string, string][] {
  return sels.filter((s) => chosen[s.key] !== undefined && !sameValue(chosen[s.key]!, firstChoice(m, s)))
    .map((s) => [slug(s.key), choiceToken(chosen[s.key]!)])
}

/** The conditions an address asks for, as the selectors' own values: a token as written (case counts, 100M
 *  is not 100m), or a number written another way (0.001, 1mA). Unknown keys and values are dropped. */
export function resolveAt(tokens: [string, string][], sels: Sel[]): Record<string, Choice> {
  const out: Record<string, Choice> = {}
  for (const [k, v] of tokens) {
    const s = sels.find((x) => slug(x.key) === slug(k))
    if (!s) continue
    if (v === 'all') { if (s.values.length > 1) out[s.key] = 'all'; continue }
    let hit = s.values.find((w) => choiceToken(w) === v)
    if (hit === undefined) {
      const n = /^-?[0-9.]+(e-?[0-9]+)?$/.test(v) ? Number(v) : siValue(v)
      if (Number.isFinite(n)) hit = s.values.find((w) => typeof w === 'number' && sameValue(w, n))
    }
    if (hit !== undefined) out[s.key] = hit
  }
  return out
}

/** The rows an address names, as their representatives in the list's order: a hash prefix of any of a row's
 *  models finds the row. */
export function resolveModels(tokens: string[], groups: number[][], hashOf: (i: number) => string | undefined): number[] {
  const reps = new Set<number>()
  for (const t of tokens) {
    const g = groups.find((ms) => ms.some((i) => hashOf(i)?.startsWith(t)))
    if (g) reps.add(g[0]!)
  }
  return groups.map((g) => g[0]!).filter((r) => reps.has(r))
}

export type Selection = { curve?: string; models: string[]; at: [string, string][] }

/** What the address selects; nothing it does not understand. */
export function readSelection(search: string): Selection {
  const q = new URLSearchParams(search)
  const curve = q.get('curve')?.trim() || undefined
  const models = (q.get('model') ?? '').split(',').map((s) => s.trim().toLowerCase()).filter((s) => /^[0-9a-f]{6,40}$/.test(s))
  const at = (q.get('at') ?? '').split(',').flatMap((s): [string, string][] => {
    const k = s.indexOf(':')
    return k > 0 && k < s.length - 1 ? [[s.slice(0, k).trim(), s.slice(k + 1).trim()]] : []
  })
  return { curve, models, at }
}

/** The address's query with this selection in place of the last one. Every other parameter is kept as it
 *  was written, byte for byte (a part with a slash keeps its %2F). */
export function writeSelection(search: string, sel: Selection): string {
  const key = (seg: string) => {
    const k = seg.split('=')[0] ?? ''
    try { return decodeURIComponent(k.replace(/\+/g, ' ')) } catch { return k }
  }
  const keep = search.replace(/^\?/, '').split('&').filter((seg) => seg && !OURS.includes(key(seg)))
  if (sel.curve) keep.push(`curve=${encodeURIComponent(sel.curve)}`)
  if (sel.models.length) keep.push(`model=${sel.models.map(encodeURIComponent).join(',')}`)
  if (sel.at.length) keep.push(`at=${sel.at.map(([k, v]) => `${encodeURIComponent(k)}:${encodeURIComponent(v)}`).join(',')}`)
  return keep.length ? `?${keep.join('&')}` : ''
}

/** The copies elsewhere that a search found a model through: "copy at diyaudio as BD139". */
export function copyHits(m: PartModel, query: string): { source: string; name: string }[] {
  const words = query.split(/\s+/).map(squeeze).filter(Boolean)
  return (m.copies ?? []).filter((c) => words.some((w) => squeeze(c.name).includes(w) || squeeze(c.source).includes(w)))
}
