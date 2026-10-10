/**
 * Every section of a part's page has an address, so a reader can send somebody straight to it:
 *
 *     ?part=BC547#spice-models/characterization/figures
 *
 * The fragment is a path of short, fixed names, one per level of folding, chosen here rather than taken
 * from the headings: a heading is reworded every other week, and a link already sent must keep working.
 * Opening the link opens every section on the way down and scrolls to the last one.
 *
 * The address bar follows the reader: opening a section puts its address there, closing it goes back to
 * the section around it, and the `#` beside each heading puts it there too and copies it. That replaces
 * the history entry instead of adding one, so the back button still goes to the previous part.
 */
import type preact from 'preact'
import { createContext } from 'preact'
import { useContext, useEffect, useRef, useState } from 'preact/hooks'

/** Links handed out before sections had addresses: `?part=X&open=character`. */
const LEGACY: Record<string, string> = { character: 'spice-models/characterization' }

type Where = { hash: string; search: string; pathname: string }

/** The section a URL points at, or '' for the top of the page. A link to one curve of the characterization
 *  (`?curve=`, `?model=`, charpick.ts) opens the characterization when it has no fragment, as the old key did. */
export function target(at: Where = location): string {
  let h = ''
  try { h = decodeURIComponent(at.hash.replace(/^#/, '')) } catch { /* a malformed escape points nowhere */ }
  if (h) return h
  const q = new URLSearchParams(at.search)
  const old = LEGACY[q.get('open') ?? '']
  if (old) return old
  return q.has('curve') || q.has('model') ? LEGACY.character! : ''
}

/** True when `path` is the section pointed at or one of the sections around it. */
export function leadsTo(t: string, path: string): boolean {
  return Boolean(path) && (t === path || t.startsWith(`${path}/`))
}

/** The section around this one, '' at the top. */
export function parentOf(path: string): string {
  return path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : ''
}

/** The page's own address with `path` as its fragment, and without the old `open=`, which it replaces. */
export function sectionHref(path: string, at: Where = location): string {
  let search = at.search
  const q = new URLSearchParams(search)
  if (q.has('open')) {
    q.delete('open')
    const rest = q.toString()
    search = rest ? `?${rest}` : ''
  }
  return `${at.pathname}${search}${path ? `#${path}` : ''}`
}

/** Put a section's address in the bar, in place of the current one. */
export function point(path: string) {
  history.replaceState(history.state, '', sectionHref(path))
}

/** The section the address points at, again whenever somebody edits the fragment by hand. */
function useTarget(): string {
  const [t, set] = useState(() => target())
  useEffect(() => {
    const on = () => set(target())
    addEventListener('hashchange', on)
    return () => removeEventListener('hashchange', on)
  }, [])
  return t
}

const STOP = ['wheel', 'touchstart', 'keydown', 'pointerdown'] as const

/**
 * Scroll a section into view and keep it there while the page fills in above it.
 *
 * The page arrives in pieces — the part, then the catalogue that adds its data sheets above the models,
 * then the characterisation — and every piece pushes what is below it down. So it scrolls again each
 * time the page changes size, for three seconds, or until the reader scrolls or clicks for themselves.
 */
function settle(el: Element): () => void {
  const go = () => el.scrollIntoView({ block: 'start' })
  const ro = new ResizeObserver(go)
  ro.observe(document.body)
  const stop = () => {
    ro.disconnect()
    clearTimeout(timer)
    for (const e of STOP) removeEventListener(e, stop)
  }
  const timer = setTimeout(stop, 3000)
  for (const e of STOP) addEventListener(e, stop, { passive: true })
  go()
  return stop
}

/** The address of the section a component sits in. */
const Scope = createContext('')
export const AnchorScope = Scope.Provider

/**
 * Give a section an address. `slug` is its name inside the section around it; without one the component
 * has no address of its own and passes its parent's on.
 *
 * `open` is whether it should start open because a link points inside it; after that the address is only
 * read again when the fragment changes by hand, and then it opens the section but never closes one.
 */
export function useAnchor<T extends HTMLElement>(slug?: string) {
  const parent = useContext(Scope)
  const path = slug ? (parent ? `${parent}/${slug}` : slug) : ''
  const t = useTarget()
  const wanted = leadsTo(t, path)
  const [open] = useState(wanted)
  const ref = useRef<T>(null)
  useEffect(() => {
    const el = ref.current
    if (!el || !wanted) return
    if (el instanceof HTMLDetailsElement && !el.open) el.open = true
    return t === path ? settle(el) : undefined
  }, [t, path])

  /** For the summary's click, before the browser folds or unfolds it: the address follows the reader. */
  const onToggleClick = (e: MouseEvent) => {
    const el = ref.current
    if (!path || e.defaultPrevented || !(el instanceof HTMLDetailsElement)) return
    if (!el.open) point(path)
    else if (leadsTo(target(), path)) point(parentOf(path))
  }
  return { path, scope: path || parent, ref, open, onToggleClick }
}

/** Copy text, through the clipboard API where the page is allowed it and the old way where it is not
 *  (a plain-http address on the local network). */
async function copy(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch { /* not a secure context, or refused */ }
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.cssText = 'position:fixed;opacity:0'
    document.body.append(ta)
    ta.select()
    const ok = document.execCommand('copy')
    ta.remove()
    return ok
  } catch {
    return false
  }
}

/**
 * The `#` beside a heading: its section's address. A click opens the section, puts the address in the
 * bar and copies it; a middle or modified click opens it in a new tab like any link. Either way the fold
 * it sits in is not toggled by it.
 */
export function AnchorLink({ path, at }: { path: string; at: { current: HTMLElement | null } }) {
  const [copied, setCopied] = useState(false)
  // the address is taken when it is used, not when the heading was drawn: what the section shows may have
  // put more in the query since (the characterization's curve and models)
  const [href, setHref] = useState(() => sectionHref(path))
  if (!path) return null
  const fresh = () => setHref(sectionHref(path))
  const onClick = (e: MouseEvent) => {
    e.stopPropagation()
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
    e.preventDefault()
    const el = at.current
    if (el instanceof HTMLDetailsElement) el.open = true
    point(path)
    const now = sectionHref(path)
    setHref(now)
    copy(new URL(now, location.href).href).then((ok) => {
      if (!ok) return
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    })
  }
  return (
    <a class={`anchor${copied ? ' done' : ''}`} href={href} onClick={onClick} onPointerEnter={fresh} onFocus={fresh}
      title="Link to this section: click to copy it" aria-label="Link to this section">
      #{copied && <span class="copied" role="status"> link copied</span>}
    </a>
  )
}

/** A heading that is a section of its own without folding: a title, and an address beside it. */
export function Heading({ slug, children }: { slug: string; children: preact.ComponentChildren }) {
  const a = useAnchor<HTMLHeadingElement>(slug)
  return <h3 ref={a.ref} data-anchor={a.path}>{children}<AnchorLink path={a.path} at={a.ref} /></h3>
}
