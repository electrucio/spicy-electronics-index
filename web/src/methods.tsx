/**
 * The method page (?bench=): how every transistor model is measured, one entry per measurement of the
 * catalogue — what it tells, the circuit (and its drawing, when made), the conditions, how the number
 * is read, what drives it in the card, what a high or low value means, what it cannot tell, the standard
 * it resembles, and how to repeat it. Written once here; every number on a part page links to its entry.
 */
import type * as preact from 'preact'
import { useEffect, useState } from 'preact/hooks'

import { DATA } from './data'
import { Loading } from './loading'
import type { Measurement, MethodsFile } from './types'

const KIND_NAME: Record<string, string> = { bjt: 'Bipolar transistors', jfet: 'JFETs', mosfet: 'MOSFETs', opamp: 'Op-amps' }
const REPO = 'https://github.com/electrucio/spicy-electronics-index'

/** A condition as the page prints it: numbers in short form, nested blocks as `key: value` lists. */
export function condText(v: unknown): string {
  if (typeof v === 'number') return fmtNum(v)
  if (Array.isArray(v)) return `[${v.map(condText).join(', ')}]`
  if (v && typeof v === 'object') return `{${Object.entries(v as Record<string, unknown>).map(([k, x]) => `${k}: ${condText(x)}`).join(', ')}}`
  return String(v)
}

function fmtNum(x: number): string {
  if (x === 0) return '0'
  const a = Math.abs(x)
  if (a >= 1e-3 && a < 1e6) return String(Number(x.toPrecision(6)))
  return x.toExponential(2).replace('e+', 'e').replace('e-0', 'e-')
}

export function MethodsPage({ id }: { id?: string }) {
  const [file, setFile] = useState<MethodsFile | null | undefined>(undefined)
  const [polarity, setPolarity] = useState('npn')
  useEffect(() => {
    fetch(`${DATA}/bench/methods.json`).then((r) => (r.ok ? r.json() : null)).then(setFile, () => setFile(null))
  }, [])
  useEffect(() => {
    if (file && id && id !== '1') document.getElementById(id)?.scrollIntoView()
  }, [file, id])
  if (file === undefined) return <Loading what="how the models are measured" />
  if (!file) return <p class="muted">The method page is not built. Run <code>make web-data</code>.</p>
  const kinds = [...new Set(file.measurements.map((m) => m.kind))]
  return (
    <section class="stack methods prose-wide">
      <h2>How every transistor model is measured</h2>
      <p>
        Every SPICE transistor model the site lists is run through the same bench: a catalogue of measurements at
        universal conditions — decades of current, a short list of voltages, three temperatures — the same for every
        model of a kind, in three simulators. A part page shows the numbers and the curves; this page says what each
        measurement tells, how the circuit works, how the number is read, which card parameters drive it, what a high or
        low value means, what it cannot tell, and how to repeat it. Nothing here depends on a data sheet: a model is
        characterised the day it is indexed, and comparing it with the real part is a separate step. The specification is{' '}
        <a href={`${REPO}/blob/main/docs/model-characterisation.md`}>docs/model-characterisation.md</a>; catalogue version{' '}
        <code>{file.version}</code>.
      </p>
      <h3>Where a number cannot stand</h3>
      <ul class="small">
        {Object.entries(file.codes).map(([k, v]) => <li key={k}><code>{k}</code> — {v}</li>)}
      </ul>
      <h3>Which measurements matter for which use</h3>
      <table class="uses-table">
        <thead><tr><th>Use</th><th>Groups</th><th>Look at</th></tr></thead>
        <tbody>
          {file.uses.map((u) => (
            <tr key={u.use}><td><b>{u.use}</b></td><td>{u.groups.map((g) => <span key={g} class="chip">{g}</span>)}</td><td>{u.look_at}</td></tr>
          ))}
        </tbody>
      </table>
      <h3>The measurements</h3>
      <p class="small">Circuits and deck lines for{' '}
        {['npn', 'pnp'].map((p) => <label key={p} class="pol"><input type="radio" name="polarity" checked={polarity === p} onChange={() => setPolarity(p)} /> {p.toUpperCase()}</label>)}
        <span class="muted"> — a PNP (and a P-channel FET) runs the same benches with every source reversed; its curves are shown as magnitudes. An op-amp has no polarity.</span></p>
      <ul class="toc small">
        {kinds.map((k) => (
          <li key={k}><b>{KIND_NAME[k] ?? k}:</b>{' '}
            {file.measurements.filter((m) => m.kind === k).map((m, i) => <span key={m.id}>{i ? ' · ' : ''}<a href={`#${m.id}`}>{m.name}</a></span>)}
          </li>
        ))}
      </ul>
      {kinds.map((k) => (
        <div key={k} class="stack">
          <h3 id={`kind-${k}`}>{KIND_NAME[k] ?? k}</h3>
          {file.measurements.filter((m) => m.kind === k).map((m) => <Method key={m.id} m={m} drawings={file.drawings} polarity={polarity} />)}
        </div>
      ))}
      <h3>Repeating any number</h3>
      <ol class="small">
        <li>Get the model from its recipe on the part page (<b>get</b>: URL, file, member, sha256, lines). The project never ships the text.</li>
        <li><code>sei bench deck &lt;measurement&gt; --card your.lib --name &lt;model&gt; --engine ngspice --hash &lt;model hash&gt;</code> writes
          <code> model.lib</code> and the deck(s) and prints each deck's sha256, which must match the digest the part page shows.</li>
        <li><code>docker run --rm -v "$PWD":/w spicy-electronics-index-ngspice simrun /w/&lt;deck&gt;.cir</code>, then
          <code> sei bench read &lt;deck&gt;.raw --measurement &lt;id&gt; --deck &lt;deck&gt;</code> applies the same extraction.</li>
        <li>Build the image yourself with <code>make sim-images</code> (<a href={`${REPO}/tree/main/docker/sim`}>docker/sim</a>): ngspice from a
          pinned tarball, QSPICE and LTspice from the vendor files you download under their licences.</li>
      </ol>
    </section>
  )
}

function Para({ label, text }: { label?: string; text: string }) {
  if (!text?.trim()) return null
  return <p>{label && <b>{label}. </b>}{text.trim()}</p>
}

/** A section a reader may skip: open on the method page, folded in the part page's dialog. */
function Fold({ title, open, children }: { title: string; open: boolean; children: preact.ComponentChildren }) {
  return <details open={open}><summary>{title}</summary>{children}</details>
}

/** The deck's lines as the catalogue quotes them, each beside what it does: a `*` line explains the next. */
export function Directives({ lines }: { lines: string[] }) {
  const rows: { line?: string; says: string[] }[] = []
  let says: string[] = []
  for (const l of lines) {
    if (l.startsWith('*')) says.push(l.replace(/^\*\s*/, ''))
    else { rows.push({ line: l, says }); says = [] }
  }
  if (says.length) rows.push({ says })
  return (
    <table class="deck small">
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td><code>{r.line ?? ''}</code></td>
            <td class="muted">{r.says.join(' ')}</td>
          </tr>))}
      </tbody>
    </table>
  )
}

/**
 * One measurement. On the method page everything is open; in the part page's dialog (`concise`) the
 * circuit, the deck's lines, the conditions, how the number is read and the outputs come first, and the
 * longer prose folds.
 */
export function Method({ m, drawings, polarity = 'npn', concise = false }: { m: Measurement; drawings: string[]; polarity?: string; concise?: boolean }) {
  const open = !concise
  // a PNP shows its own drawing and its own deck lines where they exist
  const pnp = polarity === 'pnp'
  const drawing = pnp && drawings.includes(`${m.id}-pnp`) ? `${m.id}-pnp` : drawings.includes(m.id) ? m.id : null
  const drawn = drawing !== null
  const lines = pnp && m.directives_pnp?.length ? m.directives_pnp : m.directives
  // a view with no circuit of its own (the on voltages) shows the circuits it is drawn from
  const from = !drawn && m.analysis === 'derived' && Array.isArray(m.conditions.from) ? (m.conditions.from as string[]) : []
  const fromDrawings = from.map((id) => (pnp && drawings.includes(`${id}-pnp`) ? `${id}-pnp` : drawings.includes(id) ? id : null))
    .filter((d): d is string => d !== null)
  return (
    <article id={m.id} class="method stack-s">
      <h4>{m.name} <code class="mid">{m.id}</code></h4>
      <p class="small muted">
        group <span class="chip">{m.group}</span> · analysis <code>{m.analysis}</code> · engines {m.engines.join(', ')}
        {m.symbols.length > 0 && <> · symbols {m.symbols.join(', ')}</>}{m.pack && <> · several models share one deck</>}
      </p>
      <Fold title="What it tells" open={open}><Para text={m.what} /></Fold>
      {m.circuit.trim() && (
        <div class="circuit">
          {drawn
            ? <img class="drawing" src={`${DATA}/bench/drawings/${drawing}.svg`} alt={`the ${m.name} circuit${pnp ? ', PNP' : ''}`} />
            : fromDrawings.length
              ? <>{fromDrawings.map((d) => <img key={d} class="drawing" src={`${DATA}/bench/drawings/${d}.svg`} alt={`the ${d} circuit`} />)}</>
              : <p class="small"><b>Set-up.</b> {m.drawing.elements.join(' · ')}.<span class="muted"> Drawing pending.</span></p>}
          {drawn && m.drawing.differs_from_netlist && m.drawing.differs_from_netlist !== 'nothing' && (
            <p class="muted small">The drawing shows the set-up, not the netlist: {m.drawing.differs_from_netlist}.</p>)}
          <Fold title="The circuit in words" open={open}><Para text={m.circuit} /></Fold>
        </div>
      )}
      {lines && lines.length > 0 && (
        <div class="small"><b>The deck (QSPICE{pnp ? ', PNP' : ''}), line by line.</b>
          {pnp && <span class="muted"> Every source carries the opposite sign; the comments give magnitudes.</span>}
          <Directives lines={lines} /></div>)}
      <p class="small"><b>Conditions.</b> <code>{condText(m.conditions)}</code></p>
      <Para label="How the number is read" text={m.extraction} />
      <table class="outputs small">
        <thead><tr><th>Output</th><th>Unit</th><th>What it is</th></tr></thead>
        <tbody>{m.outputs.map((o) => <tr key={o.key}><td><code>{o.key}</code></td><td>{o.unit}</td><td>{o.what}</td></tr>)}</tbody>
      </table>
      {m.curves && m.curves.length > 0 && (
        <p class="small"><b>Curves.</b> {m.curves.map((c) => `${c.name} (${c.y} against ${c.x}, ${c.scale})`).join('; ')}
          {m.grid && <> on {m.grid.values ? `the points ${m.grid.values.map(fmtNum).join(', ')}` : m.grid.per_decade ? `${m.grid.per_decade} points per decade from ${fmtNum(m.grid.from!)} to ${fmtNum(m.grid.to!)}` : `${fmtNum(m.grid.from!)} to ${fmtNum(m.grid.to!)} in steps of ${fmtNum(m.grid.step!)}`} {m.grid.unit ?? ''}</>}.</p>)}
      {m.parameters.length > 0 && <p class="small"><b>Card parameters that drive it.</b> {m.parameters.map((p) => <code key={p} class="param">{p}</code>)}</p>}
      <Fold title="Reading a high or a low value, and what it cannot tell" open={open}>
        <Para label="A high value" text={m.reads_high} />
        <Para label="A low value" text={m.reads_low} />
        <Para label="What it cannot tell" text={m.cannot_tell} />
        <p class="small muted"><b>Standard.</b> {m.standard}</p>
      </Fold>
    </article>
  )
}
