import { describe, expect, it } from 'vitest'

import { place, tickFigures, ticks } from './chart'
import { fmt, si, siValue } from './format'

describe('axes', () => {
  it('place values on linear and log scales', () => {
    expect(place(['x', '', 'lin', 0, 10], 5, 100)).toBe(50)
    expect(place(['x', '', 'log', 1, 100], 10, 100)).toBe(50)
  })
  it('tick 1-2-5 per decade on a log axis and round steps on a linear one', () => {
    expect(ticks(['x', '', 'log', 1, 100]).map((t) => t.v)).toEqual([1, 2, 5, 10, 20, 50, 100])
    expect(ticks(['x', '', 'lin', 0, 30]).map((t) => t.v)).toEqual([0, 10, 20, 30])
  })
  it('always stop, however far the zoom went', () => {
    expect(ticks(['t', 's', 'lin', 3.1e-6, 3.1e-6 + 1e-20]).length).toBeLessThan(41)        // a step the doubles cannot add
    expect(ticks(['t', 's', 'lin', 3.1e-6, 3.1e-6]).length).toBe(0)
    expect(ticks(['ic', 'A', 'log', 1e-3, 1.2e-3]).map((t) => t.v)).toEqual([0.001, 0.00105, 0.0011, 0.00115, 0.0012])   // less than half a decade: linear
  })
  it('label ticks with enough figures to tell them apart', () => {
    expect(tickFigures([3.105e-6, 3.11e-6, 3.115e-6, 3.12e-6, 3.125e-6].map((v) => ({ v })), 3)).toBe(4)   // 3.105 µs, 3.11 µs … not 3.11 µs twice
    expect(tickFigures([0, 2, 4, 6, 8].map((v) => ({ v })), 3)).toBe(3)
    expect(tickFigures([], 2)).toBe(2)
  })
})

describe('numbers as an engineer reads them', () => {
  it('carry a prefix and the unit', () => {
    expect(si(2.0274e-12, 'F')).toBe('2.03 pF')
    expect(si(0.65321, 'V')).toBe('653 mV')
    expect(si(235153809, 'Hz')).toBe('235 MHz')
    expect(si(154.04, '')).toBe('154')
    expect(si(0, 'A')).toBe('0 A')
    expect(si(1.2e-17, 'A')).toBe('1.2e-17 A')
  })
  it('read a condition back', () => {
    expect(siValue('100µA')).toBeCloseTo(1e-4)
    expect(siValue('5V')).toBe(5)
    expect(siValue('1kΩ')).toBe(1000)
  })
  it('keep the old bare format', () => {
    expect(fmt(0.0123456)).toBe('0.01235')
    expect(fmt(1.5e-9)).toBe('1.50e-9')
  })
})
