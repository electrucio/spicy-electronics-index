import type { ComponentChildren } from 'preact'
import { useEffect, useRef, useState } from 'preact/hooks'

/**
 * Feedback, from anywhere on the site: one dialog, opened by many buttons.
 *
 * The header's button is for anything at all; beside what a report would be about — a part's name, each
 * document once unfolded, each model of the table, the foot of a part's page — a button opens the same
 * dialog *about that thing*, which is named in the dialog and travels as the first line of the message,
 * so a reader who spots a misread part or a dead link says so where they see it, and the maintainer
 * knows which of thirty thousand documents is meant. The buttons are deliberately many: a reader who
 * asked for "some sort of feedback system" had not found the one in the header.
 *
 * The text reaches the maintainer through a Google Form. A static site has nobody to post to, so the
 * form's own endpoint takes the message and the answers land in the maintainer's sheet; the dialog and
 * its buttons are this site's, and nothing of Google is shown. The part on screen, if any, and the page's
 * address travel with the message as fields the reader is not shown. Google does not allow the page to
 * read its answer (`no-cors`), so a network failure is seen and a refusal is not: "sent" means the
 * request left. The form must stay published and must not ask anyone to sign in, or every report is
 * silently refused.
 */
export const FORM = 'https://docs.google.com/forms/d/e/1FAIpQLSdqgUQ9-yQNItSrEm8BDsEKQox0ZFR9IxfKDaCmzMDSwmsuqg/formResponse'

/** The form's three questions by the id Google gave each: what the reader wrote, and where they were. */
export const FIELD = { message: 'entry.371536136', part: 'entry.1742682148', page: 'entry.712592962' }

/** What a report is about, beyond the page: named in the dialog, and sent as the message's first line. */
export type About = { kind: 'document' | 'model' | 'part'; what: string; where?: string }

/** The first line of a message about something, '' for one about nothing in particular. */
export function aboutLine(about?: About): string {
  if (!about) return ''
  return `About this ${about.kind}: ${about.what}${about.where ? ` — ${about.where}` : ''}`
}

export function feedbackBody(message: string, part: string | undefined, page: string, about?: About): URLSearchParams {
  const head = aboutLine(about)
  return new URLSearchParams({
    [FIELD.message]: head ? `${head}\n\n${message.trim()}` : message.trim(),
    [FIELD.part]: part ?? '',
    [FIELD.page]: page,
  })
}

/** What the box suggests, by what the report is about. */
const PROMPT: Record<About['kind'] | 'any', string> = {
  any: 'Something wrong or missing, an idea, a question… A page number or a link helps.',
  document: 'What is wrong here? The part misread, the wrong page, a dead link, a better copy elsewhere… A page number helps.',
  model: 'What is wrong with this model? Misattributed, not loading, the wrong source, a better one elsewhere…',
  part: 'Something wrong or missing about this part: a relation, a data sheet, a usage, a model that should be here…',
}

type State = 'writing' | 'sending' | 'sent' | 'failed'
type Request = { part?: string; about?: About }
const EVENT = 'sei:feedback'

/** Open the dialog from anywhere, about something in particular or nothing. */
export function askFeedback(req: Request = {}) {
  dispatchEvent(new CustomEvent<Request>(EVENT, { detail: req }))
}

/** A speech bubble, the usual sign for "tell us". */
function Bubble() {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor"
      stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M2.5 3.5h11v7.5H7l-3 2.5V11H2.5z" />
    </svg>
  )
}

/** A button that opens the dialog: about `about` when given, for the part `part` concerns. */
export function FeedbackButton({ part, about, cls = 'fb', icon = true, title, children }: {
  part?: string; about?: About; cls?: string; icon?: boolean; title?: string; children: ComponentChildren
}) {
  return (
    <button type="button" class={cls} title={title} onClick={() => askFeedback({ part, about })}>
      {icon && <Bubble />}{icon && ' '}{children}
    </button>
  )
}

/** The dialog, mounted once. `part` is the part on screen, if any, for a request that names none. */
export function FeedbackDialog({ part }: { part?: string }) {
  const [state, setState] = useState<State>('writing')
  const [text, setText] = useState('')
  const [req, setReq] = useState<Request>({})
  const dialog = useRef<HTMLDialogElement>(null)
  const box = useRef<HTMLTextAreaElement>(null)
  const downOutside = useRef(false)

  useEffect(() => {
    const on = (e: Event) => {
      setReq((e as CustomEvent<Request>).detail ?? {})
      setState((s) => (s === 'sent' ? 'writing' : s))
      dialog.current?.showModal()
      box.current?.focus()
    }
    addEventListener(EVENT, on)
    return () => removeEventListener(EVENT, on)
  }, [])
  const close = () => dialog.current?.close()
  const about = req.about

  const send = async (e: Event) => {
    e.preventDefault()
    // A field no person sees: whatever fills it is a bot, and it is told it succeeded.
    const trap = (e.currentTarget as HTMLFormElement).elements.namedItem('website') as HTMLInputElement
    if (trap.value) return setState('sent')
    setState('sending')
    try {
      await fetch(FORM, { method: 'POST', mode: 'no-cors', body: feedbackBody(text, req.part ?? part, location.href, about) })
      setText('')
      setState('sent')
    } catch {
      setState('failed')
    }
  }

  return (
    /* The dialog is its own backdrop's target: a click that lands on it and not on the panel inside
       was outside the panel, so it closes — if it also began there, or selecting text in the box and
       letting go outside would throw the dialog away. */
    <dialog
      ref={dialog}
      class="report"
      onMouseDown={(e) => { downOutside.current = e.target === dialog.current }}
      onClick={(e) => downOutside.current && e.target === dialog.current && close()}
    >
      <div class="panel-in">
        <h3>{about ? 'Report a problem' : 'Provide feedback'}</h3>
        {about && state !== 'sent' && (
          <p class="about">
            <span>About this {about.kind}:</span> <b>{about.what}</b>
            {about.where && <span class="faint mono">{about.where}</span>}
            <button type="button" class="linkish" onClick={() => setReq({ part: req.part })}>not about this</button>
          </p>
        )}
        {state === 'sent' ? (
          <>
            <p>Thanks — sent.</p>
            <div class="row"><span /><button type="button" class="send" onClick={close}>Close</button></div>
          </>
        ) : (
          <form onSubmit={send}>
            <textarea
              ref={box}
              aria-label="Your feedback"
              placeholder={PROMPT[about?.kind ?? 'any']}
              value={text}
              onInput={(e) => setText(e.currentTarget.value)}
            />
            <input name="website" class="hp" tabIndex={-1} autocomplete="off" aria-hidden="true" />
            <p class="small faint">
              {state === 'failed'
                ? 'Could not send — check the connection and try again.'
                : 'Add an e-mail if you would like a reply.'}
            </p>
            <div class="row">
              <span />
              <button type="button" class="linkish" onClick={close}>Cancel</button>
              <button class="send" disabled={state === 'sending' || !text.trim()}>
                {state === 'sending' ? 'Sending…' : 'Send'}
              </button>
            </div>
          </form>
        )}
      </div>
    </dialog>
  )
}
