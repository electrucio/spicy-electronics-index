/**
 * One key per model of a part, the same everywhere it appears: its number in the recipe's order — [1],
 * [2], … — and its colour. The provenance table, the character pane's charts and its table all use it,
 * so "download [3]" and "the green curve" name the same model.
 *
 * The colours are the validated categorical palette in its fixed order (dataviz reference instance,
 * light surface: the charts are drawn on white). A ninth model does not get a new hue: it gets the
 * first hue dashed, and the seventeenth dotted.
 */
import type { PartModel } from './types'

export const HUES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
const DASHES = ['', '6 3', '2 3', '8 3 2 3']

export function colourOf(i: number): string { return HUES[i % HUES.length]! }
export function dashOf(i: number): string { return DASHES[Math.floor(i / HUES.length) % DASHES.length]! }
export function tag(i: number): string { return `[${i + 1}]` }

/** Model labels as a reader looks for them: the number, the name the card gives the model, and its source. */
export function modelLabels(models: PartModel[]): string[] {
  return models.map((m, i) => `${tag(i)} ${m.name} · ${m.source}`)
}

/** The model's colour as a short line, dashed where its colour is a repeat. */
export function Swatch({ i }: { i: number }) {
  return <span class="swatch" style={{ borderTop: `3px ${dashOf(i) ? 'dashed' : 'solid'} ${colourOf(i)}` }} />
}

/** The number and the colour together, as the provenance table shows them. */
export function ModelKey({ i }: { i: number }) {
  return <span class="mkey"><Swatch i={i} />{tag(i)}</span>
}
