/**
 * Something on its way: what it is, said, and a ring that turns while it comes.
 *
 * A bare "Loading…" that stays up tells nobody what is stuck, and a page that waits on four files at once
 * showed four of them. index.html carries the same markup for the moment before the script runs.
 */
export function Loading({ what, small = false, inline = false }: {
  /** What is coming, as it reads after "Loading": "the parts list", "the page of BC547". */
  what: string
  small?: boolean
  /** Inside a sentence rather than a paragraph of its own. */
  inline?: boolean
}) {
  const Tag = inline ? 'span' : 'p'
  return (
    <Tag class={`muted loading${small ? ' small' : ''}`} role="status">
      <span class="spinner" aria-hidden="true" />Loading {what}…
    </Tag>
  )
}
