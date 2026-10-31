/** The arithmetic behind the SVG charts: where a value lands on an axis, and where the ticks go. */

/** An axis: [quantity, unit, lin|log, min, max]. */
export type Axis = [string, string, 'lin' | 'log', number, number]

/** Where a value lands along an axis of `size` pixels. */
export function place(axis: Axis, value: number, size: number): number {
  const [, , scale, lo, hi] = axis
  const f = scale === 'log' ? (Math.log10(value) - Math.log10(lo)) / (Math.log10(hi) - Math.log10(lo)) : (value - lo) / (hi - lo)
  return f * size
}

/** Tick values: 1-2-5 per decade on a log axis, round steps on a linear one; `major` ones are labelled. */
export function ticks(axis: Axis): { v: number; major: boolean }[] {
  const [, , scale, lo, hi] = axis
  const out: { v: number; major: boolean }[] = []
  if (!(hi > lo) || !Number.isFinite(lo) || !Number.isFinite(hi)) return out
  if (scale === 'log' && lo > 0 && Math.log10(hi / lo) >= 0.5) {
    const decades = Math.log10(hi / lo)
    for (let d = Math.floor(Math.log10(lo)); d <= Math.ceil(Math.log10(hi)); d++) {
      for (const m of [1, 2, 5]) {
        const v = m * 10 ** d
        if (v >= lo * 0.999 && v <= hi * 1.001) out.push({ v, major: m === 1 || decades <= 2 })
      }
    }
    return out
  }
  // a linear axis, or a log one zoomed to less than half a decade, where decades mean nothing
  const raw = (hi - lo) / 5
  const p = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 5, 10].map((k) => k * p).find((k) => k >= raw) ?? raw
  if (!(step > 0)) return out
  const first = Math.ceil(lo / step - 1e-9) * step   // a step of 5 * 10 ** -5 makes 1e-3 / step 20.000000000000004
  for (let k = 0; k < 40; k++) {
    const v = first + k * step
    if (v > hi + step * 1e-9) break
    out.push({ v: Number(v.toPrecision(12)), major: true })
  }
  return out
}

/** Significant figures that tell neighbouring ticks apart: three would print 3.11 µs twice when the step is 5 ns. */
export function tickFigures(ts: { v: number }[], atLeast: number): number {
  let step = Infinity
  let big = 0
  for (let i = 0; i < ts.length; i++) {
    const v = ts[i]!.v
    if (Math.abs(v) > big) big = Math.abs(v)
    if (i > 0) {
      const d = Math.abs(v - ts[i - 1]!.v)
      if (d > 0 && d < step) step = d
    }
  }
  if (!Number.isFinite(step) || !(big > 0)) return atLeast
  return Math.max(atLeast, Math.floor(Math.log10(big / step)) + 2)
}
