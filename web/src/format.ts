/**
 * Numbers as an engineer reads them: a prefix instead of an exponent, three significant figures, the
 * unit beside it — 235 MHz, 2.03 pF, 653 mV, 1.2e-11 A only when nothing else fits.
 */
const PREFIXES: [number, string][] = [[1e12, 'T'], [1e9, 'G'], [1e6, 'M'], [1e3, 'k'], [1, ''], [1e-3, 'm'], [1e-6, 'µ'], [1e-9, 'n'], [1e-12, 'p'], [1e-15, 'f']]

/** A value with its unit and the fitting prefix: si(2.03e-12, 'F') → "2.03 pF"; si(0.653, 'V') → "653 mV". */
export function si(x: number, unit = '', figures = 3): string {
  if (!Number.isFinite(x)) return String(x)
  if (x === 0) return `0${unit ? ` ${unit}` : ''}`
  const a = Math.abs(x)
  for (const [scale, p] of PREFIXES) {
    if (a >= scale * 0.9995) {
      const m = x / scale
      const txt = Number(m.toPrecision(figures)).toString()
      return unit || p ? `${txt} ${p}${unit}` : txt
    }
  }
  return `${Number(x.toPrecision(figures)).toExponential()}${unit ? ` ${unit}` : ''}`
}

/** A bare number, at most four significant figures, no exponent in the everyday range. */
export function fmt(x: number): string {
  if (x === 0) return '0'
  const a = Math.abs(x)
  if (a >= 1e-3 && a < 1e5) return String(Number(x.toPrecision(4)))
  return x.toExponential(2).replace('e+', 'e')
}

/** The number an output key's condition spells: "100µA" → 1e-4, "5V" → 5, "1kΩ" → 1000. */
export function siValue(s: string): number {
  const m = /^(-?[0-9.]+)([GMkmµunpf]?)[A-Za-zΩ°]*$/.exec(s)
  if (!m) return Number.NaN
  const p = PREFIXES.find(([, q]) => q === (m[2] ?? ''))
  return Number(m[1] ?? 'x') * (p ? p[0] : (m[2] === 'u' ? 1e-6 : 1))
}
