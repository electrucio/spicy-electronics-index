import type preact from 'preact'
import { useState } from 'preact/hooks'

import { AnchorLink, AnchorScope, useAnchor } from './anchor'

/**
 * A `<details>` whose contents are built the first time it is opened.
 *
 * Nothing is cut from a part's page, so the 1N4148's holds 3,574 documents and 9,344 page links.
 * Building all of that as DOM up front costs far more than downloading it. The previous site did the
 * same thing for the same reason.
 */
export function Fold({
  summary, level, open = false, cls, anchor, children,
}: {
  summary: preact.ComponentChildren
  /** 1 the kind of source, 2 the source, 3 the document. Each reads differently or the nesting is invisible. */
  level: 1 | 2 | 3
  open?: boolean
  /** An extra class, for a level whose names must not be restyled — a repository keeps its case. */
  cls?: string
  /** Its name in the page's addresses (anchor.tsx), for a fold worth linking to. */
  anchor?: string
  children: () => preact.ComponentChildren
}) {
  const a = useAnchor<HTMLDetailsElement>(anchor)
  const [shown, setShown] = useState(open || a.open)
  return (
    <details
      ref={a.ref}
      class={`uses lv${level}${cls ? ` ${cls}` : ''}`}
      open={open || a.open}
      data-anchor={a.path || undefined}
      onToggle={(e) => setShown((e.target as HTMLDetailsElement).open)}
    >
      <summary onClick={a.onToggleClick}>{summary}<AnchorLink path={a.path} at={a.ref} /></summary>
      <AnchorScope value={a.scope}>{shown ? children() : null}</AnchorScope>
    </details>
  )
}

/**
 * One of a part's sections: its heading folds it, and it starts closed so the page opens as a list of
 * what there is to read — all but the one a reader comes for (`defaultOpen`). Left uncontrolled, an
 * opened section stays open on the next part.
 */
export function Section({
  title, anchor, defaultOpen = false, children,
}: {
  title: string
  /** Its name in the page's addresses (anchor.tsx): a link that points inside it finds it open. */
  anchor: string
  defaultOpen?: boolean
  children: preact.ComponentChildren
}) {
  const a = useAnchor<HTMLDetailsElement>(anchor)
  return (
    <details ref={a.ref} class="psec" open={a.open || defaultOpen || undefined} data-anchor={a.path}>
      <summary onClick={a.onToggleClick}><h2>{title}</h2><AnchorLink path={a.path} at={a.ref} /></summary>
      <div class="stack-s"><AnchorScope value={a.scope}>{children}</AnchorScope></div>
    </details>
  )
}

/**
 * A part inside one of those sections, under a smaller heading that folds it the same way: closed until
 * asked for, and built the first time it opens, like a `Fold`, because what it holds is fetched then.
 */
export function SubSection({
  title, anchor, defaultOpen = false, children,
}: {
  title: string
  /** Its name inside its section, in the page's addresses. */
  anchor: string
  defaultOpen?: boolean
  children: () => preact.ComponentChildren
}) {
  const a = useAnchor<HTMLDetailsElement>(anchor)
  const [shown, setShown] = useState(a.open || defaultOpen)
  return (
    <details
      ref={a.ref}
      class="psec psub"
      open={a.open || defaultOpen || undefined}
      data-anchor={a.path}
      onToggle={(e) => setShown((e.target as HTMLDetailsElement).open)}
    >
      <summary onClick={a.onToggleClick}><h3>{title}</h3><AnchorLink path={a.path} at={a.ref} /></summary>
      <AnchorScope value={a.scope}>{shown ? children() : null}</AnchorScope>
    </details>
  )
}
