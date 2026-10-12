import { render } from 'preact'
import { useEffect, useRef, useState } from 'preact/hooks'

import { FamilyPage, MakerPage, SchemePage } from './about'
import { SellersPage } from './sellers'
import { DATA } from './data'
import { Feedback } from './feedback'
import { LICENCE_URL, Licence } from './licence'
import { Loading } from './loading'
import { MethodsPage } from './methods'
import { Browser } from './parts'
import { Unlock } from './unlock'
import logo from './logo.svg'
import './style.css'
import type { Manifest } from './types'

/** A page of the catalogue, when one is open: a family, a naming scheme or an organisation. */
type Topic = { family?: string; scheme?: string; maker?: string; bench?: string; sellers?: string }

/**
 * Which part is open, kept in the URL, or which catalogue page a part linked to.
 *
 * A result has to be linkable — half the point of an index is being able to send somebody a part — and
 * the back button has to mean what it says.
 */
function useRoute(): [string | null, Topic, (p?: string | null) => void] {
  const read = () => {
    const q = new URLSearchParams(location.search)
    const topic: Topic = {
      family: q.get('family') ?? undefined, scheme: q.get('scheme') ?? undefined, maker: q.get('maker') ?? undefined,
      bench: q.get('bench') ?? undefined, sellers: q.get('sellers') ?? undefined,
    }
    return [q.get('part'), topic] as const
  }
  const [[part, topic], set] = useState(read)
  useEffect(() => {
    const onPop = () => set(read())
    addEventListener('popstate', onPop)
    return () => removeEventListener('popstate', onPop)
  }, [])
  const go = (p: string | null = null) => {
    history.pushState({}, '', p ? `?part=${encodeURIComponent(p)}` : location.pathname)
    set([p, {}] as const)
    scrollTo(0, 0)
  }
  return [part, topic, go]
}

function App() {
  const [data, setData] = useState<{ m: Manifest } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [part, topic, go] = useRoute()
  const onTopic = Boolean(topic.family || topic.scheme || topic.maker || topic.bench || topic.sellers)
  // The header's height, for CSS: what stays in view under it (the list, the part's name) starts there.
  const head = useRef<HTMLElement>(null)
  useEffect(() => {
    const el = head.current
    if (!el) return
    const ro = new ResizeObserver(() => document.documentElement.style.setProperty('--header-h', `${el.offsetHeight}px`))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    fetch(`${DATA}/manifest.json`)
      .then((r) => r.json() as Promise<Manifest>)
      .then((m) => setData({ m }))
      .catch(() => setError('Could not load the data. Run `make web-data` to build it.'))
  }, [])

  return (
    <>
      <header class="top" ref={head}>
        <div class="wrap row">
          <a
            class="brand"
            href="?"
            onClick={(e) => { e.preventDefault(); go() }}
          >
            <span class="pepper"><img class="logo" src={logo} alt="" /></span><span class="name">Spicy <span>Electronics Index</span></span>
          </a>
          {/* The build's date, the licence and the way to send feedback, from any page, on one line. */}
          <div class="hright">
            <div class="hline">
              {data && <span class="stamp">built {data.m.built}</span>}
              <Licence />
              <Unlock />
              <Feedback part={onTopic ? undefined : part ?? undefined} />
            </div>
          </div>
        </div>
      </header>

      <main class="wrap">
        {error && <p class="muted">{error}</p>}
        {!error && !data && <Loading what="the index" />}
        {data && topic.family && <FamilyPage id={topic.family} />}
        {data && topic.scheme && <SchemePage id={topic.scheme} />}
        {data && topic.maker && <MakerPage id={topic.maker} />}
        {data && topic.bench && <MethodsPage id={topic.bench} />}
        {data && topic.sellers && <SellersPage />}
        {data && !onTopic && <Browser part={part} onPick={go} />}
      </main>

      <footer class="wrap muted small" style={{ paddingBlock: '24px 48px' }}>
        A non-commercial project, by a hobbyist for hobbyists: free to use and share with credit, never
        commercially, and with no warranty (<a href={LICENCE_URL}>licence and disclaimer</a>).
        Built from the committed dataset. This project stores links, never documents.{' '}
        <a href="https://github.com/electrucio/spicy-electronics-index">Source</a>.
      </footer>
    </>
  )
}

// The page ships a "Loading Spicy Electronics Index…" placeholder for the moment before this script runs. Preact renders beside
// what is already there rather than over it, so the placeholder is cleared first or it stays under the footer.
const root = document.getElementById('app')!
root.textContent = ''
render(<App />, root)
