/**
 * The filter box above a part's usage lists: which documents answer what a reader types.
 *
 * The 1N4148's "Magazines and books" holds thousands of documents under a dozen sources, and Ctrl+F
 * leaves every one of them on the screen. The box keeps the documents whose title, date or other names
 * hold every word typed, case and accents aside, and the page marks the words where they fall. A word in
 * the name of the source a document is listed under counts for it too, so "elektor 1995" is that
 * magazine's issues of 1995. Nothing here touches the DOM: the page draws what this returns.
 */
import { foldText } from './words'

/** What a document is searched by: its title (its address when it has none), its date, the other titles
 *  it is filed under and the other archives it is at. */
export type Searchable = { t: string; u: string; y: string; aka?: string[]; also?: string[] }

/** The words of a query, folded as `foldText` folds them; none for a blank query. */
export function queryWords(query: string): string[] {
  return foldText(query).split(/\s+/).filter(Boolean)
}

/** Whether a document answers the words: each is somewhere in what it is searched by, or in `context`,
 *  the name of the source or repository it is listed under. No words, every document. */
export function matchDoc(d: Searchable, words: string[], context = ''): boolean {
  if (!words.length) return true
  const text = foldText([d.t || d.u, d.y, ...(d.aka ?? []), ...(d.also ?? []), context].join('\n'))
  return words.every((w) => text.includes(w))
}

const COMBINING = /[̀-ͯ]/

/**
 * Where the words fall in `text`, as `[start, end)` in the text's own characters, merged where they touch,
 * for marking them. Folding changes a character's length — a ligature becomes two letters, an accent
 * written apart from its letter becomes nothing — so each folded character is mapped back to the one it
 * came from, and a mark never ends between a letter and its accent.
 */
export function highlights(text: string, words: string[]): [number, number][] {
  if (!text || !words.length) return []
  let folded = ''
  const from: number[] = []
  const to: number[] = []
  let i = 0
  for (const ch of text) {
    const f = foldText(ch)
    for (let k = 0; k < f.length; k++) {
      from.push(i)
      to.push(i + ch.length)
    }
    folded += f
    i += ch.length
  }
  const found: [number, number][] = []
  for (const w of words) {
    for (let at = folded.indexOf(w); at >= 0; at = folded.indexOf(w, at + 1)) {
      let end = to[at + w.length - 1]!
      while (end < text.length && COMBINING.test(text[end]!)) end++
      found.push([from[at]!, end])
    }
  }
  found.sort((a, b) => a[0] - b[0] || a[1] - b[1])
  const out: [number, number][] = []
  for (const [s, e] of found) {
    const last = out[out.length - 1]
    if (last && s <= last[1]) last[1] = Math.max(last[1], e)
    else out.push([s, e])
  }
  return out
}
