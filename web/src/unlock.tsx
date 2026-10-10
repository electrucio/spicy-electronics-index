import { useEffect, useRef, useState } from 'preact/hooks'

import { heldKey, lock, onKeyChange, partTexts, unlock } from './sealed'

/**
 * The maintainer's way in to the sealed model text (sealed.ts): no button anyone else sees. Opening the
 * site with `#unlock` in the address asks for the passphrase; `#lock`, or the "lock" beside the build's
 * date while the text is open, forgets the key. The fragment is taken out of the address afterwards, so a
 * link copied from the bar does not carry it.
 */
export function Unlock() {
  const dialog = useRef<HTMLDialogElement>(null)
  const box = useRef<HTMLInputElement>(null)
  const [state, setState] = useState<'asking' | 'working' | 'wrong' | 'none' | 'insecure'>('asking')
  const open = useHeld()

  useEffect(() => {
    const read = () => {
      if (location.hash === '#unlock') {
        setState('asking')
        dialog.current?.showModal()
        box.current?.focus()
      } else if (location.hash === '#lock') {
        lock()
        clearHash()
      }
    }
    read()
    addEventListener('hashchange', read)
    return () => removeEventListener('hashchange', read)
  }, [])

  const close = () => { dialog.current?.close(); clearHash() }
  const submit = async (e: Event) => {
    e.preventDefault()
    setState('working')
    const r = await unlock(box.current?.value ?? '')
    if (r === 'ok') {
      if (box.current) box.current.value = ''
      close()
    } else setState(r)
  }

  return (
    <>
      {open && <button type="button" class="licence-btn" title="forget the key to the model text in this browser" onClick={lock}>lock</button>}
      <dialog ref={dialog} class="report" onClose={clearHash}>
        <form class="panel-in" onSubmit={submit}>
          <h3>Model text</h3>
          <input ref={box} type="password" class="phrase" aria-label="Passphrase" autocomplete="current-password" />
          {state === 'wrong' && <p class="small">That is not the passphrase.</p>}
          {state === 'none' && <p class="small">This site has no sealed model text.</p>}
          {state === 'insecure' && <p class="small">This browser opens it only over https or from localhost.</p>}
          <div class="row">
            <span />
            <button type="button" class="linkish" onClick={close}>Cancel</button>
            <button class="send" disabled={state === 'working'}>{state === 'working' ? 'Opening…' : 'Open'}</button>
          </div>
        </form>
      </dialog>
    </>
  )
}

function clearHash() {
  if (location.hash === '#unlock' || location.hash === '#lock') history.replaceState(history.state, '', location.pathname + location.search)
}

/** Whether this browser holds the key, kept current. */
function useHeld(): boolean {
  const [held, set] = useState(false)
  useEffect(() => {
    const read = () => { heldKey().then((k) => set(Boolean(k))) }
    read()
    return onKeyChange(read)
  }, [])
  return held
}

/** The texts of one part's models, once the key is held; null otherwise. */
export function usePartTexts(part: string): Record<string, string> | null {
  const [texts, set] = useState<Record<string, string> | null>(null)
  useEffect(() => {
    let live = true
    const read = () => { partTexts(part).then((t) => { if (live) set(t) }) }
    read()
    const stop = onKeyChange(read)
    return () => { live = false; stop() }
  }, [part])
  return texts
}

/** Put text on the clipboard. Served over plain http on the network (the dev server) the page is not a
 *  secure context and has no clipboard API, so the old way is the fallback. */
async function copy(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    const t = document.createElement('textarea')
    t.value = text
    t.style.cssText = 'position:fixed;opacity:0'
    document.body.appendChild(t)
    t.select()
    const ok = document.execCommand('copy')
    t.remove()
    return ok
  }
}

/** The button that copies a model's text, saying for a moment that it did. */
export function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState<boolean | null>(null)
  const click = async () => {
    setDone(await copy(text))
    setTimeout(() => setDone(null), 1500)
  }
  return (
    <button type="button" class="linkish" title="copy the definition, ready to paste into a directive" onClick={click}>
      {done === null ? 'copy' : done ? 'copied' : 'select it below'}
    </button>
  )
}
