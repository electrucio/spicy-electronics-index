import { Fragment } from 'preact'
import { useEffect, useRef, useState } from 'preact/hooks'

import { Loading } from './loading'

/**
 * "Non-commercial license & disclaimer": the button beside the build's date, and the dialog that shows the
 * licence in full — the summary with the no-warranty disclaimer, then both legal texts. The summary opens
 * with what the licence allows and what it does not, a tick or a cross on each line, drawn in colour.
 *
 * The texts are the repository's own files, imported raw, so the site cannot say anything the LICENSE
 * file does not. They are a chunk of their own, fetched the first time the dialog opens: a reader who
 * never asks downloads none of it.
 */
type Texts = [title: string, text: string][]

const load = (): Promise<Texts> =>
  Promise.all([
    import('../../LICENSE?raw'),
    import('../../LICENSES/PolyForm-Noncommercial-1.0.0.txt?raw'),
    import('../../LICENSES/CC-BY-NC-SA-4.0.txt?raw'),
  ]).then(([summary, code, rest]) => [
    ['Summary and disclaimer', summary.default],
    ['The code: PolyForm Noncommercial License 1.0.0', code.default],
    ['Everything else: CC BY-NC-SA 4.0', rest.default],
  ])

/**
 * A licence text as written, with its ticks and crosses in the colours of a pass and a fail. A ticked or
 * crossed line is a block of its own, so on a narrow screen it wraps under its words and not under the mark.
 */
function Text({ text }: { text: string }) {
  return (
    <pre class="licence">
      {text.split('\n').map((line, i) => {
        const m = /^\s*([✓✗])\s(.*)$/.exec(line)
        return m
          ? <span key={i} class="mark"><span class={m[1] === '✓' ? 'yes' : 'no'}>{m[1]}</span> {m[2]}</span>
          : <Fragment key={i}>{line}{'\n'}</Fragment>
      })}
    </pre>
  )
}

export const LICENCE_URL = 'https://github.com/electrucio/spicy-electronics-index/blob/main/LICENSE'

function LicenceDialog({ onClose }: { onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const [texts, setTexts] = useState<Texts | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    ref.current?.showModal()
    load().then(setTexts, () => setFailed(true))
  }, [])
  return (
    <dialog ref={ref} class="about" onClose={onClose} onClick={(e) => { if (e.target === ref.current) onClose() }}>
      <div class="about-body stack-s">
        <div class="row" style={{ justifyContent: 'space-between' }}>
          <b>Non-commercial license &amp; disclaimer</b>
          <button type="button" onClick={onClose}>close</button>
        </div>
        {/* A chunk named by its hash is gone after the next deploy: a page left open across one says so. */}
        {failed && <p class="muted">Could not load the licence and disclaimer. <a href={LICENCE_URL}>Read it on GitHub</a>.</p>}
        {!failed && !texts && <Loading what="the licence and disclaimer" />}
        {texts?.map(([title, text]) => (
          <section key={title} class="stack-s">
            <h3>{title}</h3>
            <Text text={text} />
          </section>
        ))}
      </div>
    </dialog>
  )
}

export function Licence() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button type="button" class="licence-btn" onClick={() => setOpen(true)}>Non-commercial license &amp; disclaimer</button>
      {open && <LicenceDialog onClose={() => setOpen(false)} />}
    </>
  )
}
