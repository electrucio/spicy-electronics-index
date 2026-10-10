/** The character pane's arithmetic: names a reader can tell apart, keys in the catalogue's order, cells that say why there is no number. */
import { describe, expect, it } from 'vitest'

import { between, beyondRatings, cellOf, chartTitle, ease, fitList, fitRange, jsonMaybeGzip, gridX, hoverExtras, memberFacts, nearestLine, orderKeys, panned, ratingOn, readAt, traceConditions, zoomed } from './character'
import { axisName, firstChoice, fmtChoice, pickCurves, quantities, sameValue, selectorsOf } from './charpick'
import { colourOf, dashOf, modelLabels } from './key'
import type { Curve, HoverExtra, Measurement, ModelCharacter, PartModel } from './types'

const m = {
  id: 'bjt-hfe-ic', outputs: [{ key: 'hfe@{ic},{vce}', unit: '', what: '', plotted: true }, { key: 'vbe@{ic},{vce}', unit: 'V', what: '' }, { key: 'hfe_peak', unit: '', what: '' }],
} as unknown as Measurement

describe('model labels', () => {
  it('number every model, then give its name and its source', () => {
    const models = [
      { source: 'onsemi', name: 'Q2n3904' }, { source: 'cordell', name: '2N3904C' }, { source: 'ltwiki', name: '2N3904' },
      { source: 'ltwiki', name: '2N3904T' }, { source: 'kicad', name: '2N3904' }, { source: 'kicad', name: '2N3904' },
    ] as PartModel[]
    expect(modelLabels(models)).toEqual(['[1] Q2n3904 · onsemi', '[2] 2N3904C · cordell', '[3] 2N3904 · ltwiki', '[4] 2N3904T · ltwiki', '[5] 2N3904 · kicad', '[6] 2N3904 · kicad'])
  })
})

describe('output keys', () => {
  it('sort by the catalogue, then by the conditions, never by the alphabet', () => {
    const keys = ['vbe@1mA,5V', 'hfe_peak', 'hfe@100mA,5V', 'hfe@1mA,5V', 'hfe@10mA,1V', 'hfe@1mA,1V']
    expect(orderKeys(keys, m)).toEqual(['hfe@1mA,1V', 'hfe@1mA,5V', 'hfe@10mA,1V', 'hfe@100mA,5V', 'vbe@1mA,5V', 'hfe_peak'])
  })
})

describe('a cell', () => {
  const mo = {
    hash: 'h', runs: { qspice: 'ok' }, codes: { 'bjt-hfe-ic': 'ok', 'bjt-capacitance': 'absent' },
    values: { 'bjt-hfe-ic': { qspice: { 'hfe@1mA,5V': 150, 'vbe@1mA,5V': 0.65321 }, ngspice: { 'hfe@1mA,5V': 180 } } },
    derived: {}, curves: {}, agree: {}, decks: {}, changes: {}, errors: {},
  } as unknown as ModelCharacter
  it('shows the primary engine with its unit, the other where it differs, and the code where there is no number', () => {
    expect(cellOf(mo, 'bjt-hfe-ic', 'hfe@1mA,5V', 'qspice', 'qspice').text).toBe('150')
    expect(cellOf(mo, 'bjt-hfe-ic', 'vbe@1mA,5V', 'qspice', 'qspice', 'V').text).toBe('653 mV')
    expect(cellOf(mo, 'bjt-hfe-ic', 'hfe@1mA,5V', 'ngspice', 'qspice').text).toBe('180')
    expect(cellOf(mo, 'bjt-hfe-ic', 'vbe@1mA,5V', 'ngspice', 'qspice', 'V').title).toContain('within 1 %')
    expect(cellOf(mo, 'bjt-capacitance', 'cob@10V', 'qspice', 'qspice')).toMatchObject({ text: 'absent', cls: 'k-absent' })
    expect(cellOf(undefined, 'bjt-hfe-ic', 'x', 'qspice', 'qspice').cls).toBe('c-none')
  })
})

describe('colours', () => {
  it('follow the model, in the validated order, and dash past the eighth instead of inventing a hue', () => {
    expect(colourOf(0)).toBe('#2a78d6')
    expect(colourOf(8)).toBe(colourOf(0))
    expect(dashOf(0)).toBe('')
    expect(dashOf(8)).not.toBe('')
  })
})

describe('a grid', () => {
  it('gives its x values from a list, a step or points per decade', () => {
    expect(gridX({ x: 'v', values: [1, 2] })).toEqual([1, 2])
    expect(gridX({ x: 'vce', from: 1, to: 3, step: 1 })).toEqual([1, 2, 3])
    expect(gridX({ x: 'ic', from: 1e-3, to: 1e-1, per_decade: 1 }).map((v) => Number(v.toPrecision(6)))).toEqual([1e-3, 1e-2, 1e-1])
  })
})

describe('zoom and pan', () => {
  it('zoom around the cursor and pan by a step, in the axis\'s own space', () => {
    expect(zoomed([0, 8e-6], 3e-6, 0.5, false)).toEqual([1.5e-6, 5.5e-6])
    expect(zoomed([1e-6, 1e-2], 1e-4, 0.5, true).map((v) => Number(v.toPrecision(6)))).toEqual([1e-5, 1e-3])
    expect(panned([2, 6], 1, false)).toEqual([1, 5])
    expect(panned([10, 1000], 1, true).map((v) => Number(v.toPrecision(6)))).toEqual([1, 100])
    expect(zoomed([0, 8e-6], 1e-3, 0.5, false)).toEqual([4e-6, 8e-6])          // a cursor outside the view clamps to its edge
    expect(zoomed([3.1e-6, 3.1e-6 + 1e-13], 3.1e-6, 0.5, false)).toEqual([3.1e-6, 3.1e-6 + 1e-13])   // no closer than the numbers allow
    expect(zoomed([1e-3, 1.001e-3], 1e-3, 0.5, true)).toEqual([1e-3, 1.001e-3])
  })
})

describe('the chart dropdowns', () => {
  const units = { VCE: 'V', T: '°C', IC: 'A' }
  const mm = {
    id: 'bjt-hfe-ic', grid: { x: 'ic', from: 1e-6, to: 10, per_decade: 5, unit: 'A' }, select: { VCE: 5 },
    curves: [
      { name: 'hFE, VCE=1V', x: 'ic', y: 'hfe', scale: 'log', at: { VCE: 1 } },
      { name: 'hFE, VCE=5V', x: 'ic', y: 'hfe', scale: 'log', at: { VCE: 5 } },
      { name: 'VBE, VCE=1V', x: 'ic', y: 'vbe', scale: 'lin', unit: 'V', at: { VCE: 1 } },
      { name: 'VBE, VCE=5V', x: 'ic', y: 'vbe', scale: 'lin', unit: 'V', at: { VCE: 5 } },
      { name: '|hfe|, 1mA', x: 'f', y: 'hfe', scale: 'log', at: { IC: 1e-3 }, grid: { x: 'f', from: 1e3, to: 1e11, per_decade: 5, unit: 'Hz' } },
    ],
  } as unknown as Measurement
  it('offer one quantity per y against x, and one selector per parameter the curves are taken at', () => {
    const qs = quantities(mm)
    expect(qs.map((q) => q.label)).toEqual(['hFE against IC', 'VBE against IC', 'hFE against f'])
    expect(selectorsOf(qs[0]!.curves)).toEqual([{ key: 'VCE', values: [1, 5] }])
    expect(selectorsOf(qs[2]!.curves)).toEqual([{ key: 'IC', values: [1e-3] }])
  })
  it('show the catalogue\'s default first, or the first value, and overlay on "all" with a suffix that tells the lines apart', () => {
    const q = quantities(mm)[0]!
    const sel = selectorsOf(q.curves)[0]!
    expect(firstChoice(mm, sel)).toBe(5)
    expect(firstChoice({ ...mm, select: undefined } as Measurement, sel)).toBe(1)
    expect(firstChoice({ ...mm, select: { VCE: 'all' } } as Measurement, sel)).toBe('all')
    expect(pickCurves(q.curves, { VCE: 5 }, units).map((p) => p.c.name)).toEqual(['hFE, VCE=5V'])
    expect(pickCurves(q.curves, { VCE: 'all' }, units).map((p) => p.suffix)).toEqual(['VCE = 1 V', 'VCE = 5 V'])
    expect(fmtChoice(-55, '°C')).toBe('-55 °C')
    expect(fmtChoice('25 to 125°C')).toBe('25 to 125°C')
    expect(sameValue(1e-3, 0.001) && !sameValue(1e-3, 1.1e-3)).toBe(true)
  })
})

describe('the point under the cursor', () => {
  const trace = { name: 'IC, step 3, IB step=2µA', x: 'vce', y: 'ic', scale: 'lin', unit: 'A', at: { 'IB step': 2e-6 }, k: 3 } as Curve
  const auto = { ...trace, name: 'IC, step 3, auto', at: { 'IB step': 'auto' } } as Curve
  const hfe = { name: 'hFE, VCE=5V', x: 'ic', y: 'hfe', scale: 'log', at: { VCE: 5 } } as Curve
  it('says what a trace was taken at: its base current as k × step, its conditions', () => {
    expect(traceConditions(trace, { 'IB step': 'A' })).toEqual(['IB = 3 × 2 µA = 6 µA'])
    expect(traceConditions(auto, {}, 1.5e-6)).toEqual(['IB = 3 × 1.5 µA (auto step) = 4.5 µA'])
    expect(traceConditions(hfe, { VCE: 'V' })).toEqual(['VCE = 5 V'])
    expect(traceConditions({ ...hfe, at: { span: '25 to 125°C' } } as Curve)).toEqual(['25 to 125°C'])
    expect(axisName('vcesat')).toBe('VCE(sat)')
    expect(axisName('h21')).toBe('|hfe|')
  })
  it('computes the catalogue\'s quantities for the point: power, gain, the local slope, a condition', () => {
    const extras: HoverExtra[] = [
      { y: 'ic', label: 'P', unit: 'W', of: ['x', '*', 'y'] },
      { y: 'ic', label: 'hFE', unit: '', of: ['y', '/', 'ib'] },
      { y: 'ic', label: 'ro', unit: 'Ω', of: ['dx', '/', 'dy'] },
      { y: 'hfe', label: 'P', unit: 'W', of: ['x', '*', 'at.VCE'] },
    ]
    const pts: [number, number][] = [[1, 1e-3], [2, 1.1e-3], [3, 1.2e-3]]
    const at = readAt(pts, 2.5)!
    expect(at.x).toBe(2.5)
    expect(at.y).toBeCloseTo(1.15e-3, 12)                                // read at the cursor, between the published points
    const got = hoverExtras(extras, trace, at, 6e-6)
    expect(got.map((e) => e.label)).toEqual(['P', 'hFE', 'ro'])
    expect(got[0]!.value).toBeCloseTo(2.5 * 1.15e-3, 9)
    expect(got[1]!.value).toBeCloseTo(1.15e-3 / 6e-6, 6)
    expect(got[2]!.value).toBeCloseTo(1 / 1e-4, 6)                      // the slope of the segment
    expect(hoverExtras(extras, trace, at).map((e) => e.label)).toEqual(['P', 'ro'])   // no base current, no gain
    expect(hoverExtras(extras, trace, readAt([[1, 1e-3], [2, 1e-3], [3, 1e-3]], 1.5), 6e-6).map((e) => e.value)[2]).toBe(Infinity)   // a flat trace: ro is infinite, said so
    expect(hoverExtras(extras, hfe, readAt([[1e-3, 200]], 1e-3), 0)[0]!.value).toBeCloseTo(5e-3, 9)
    expect(readAt([[1e-3, 100], [1e-1, 10000]], 1e-2, true, true)!.y).toBeCloseTo(1000, 6)   // a log-log curve reads as a straight line
    expect(readAt(pts, 9)!.x).toBe(3)                                     // past the end: the end
  })
})

describe('the line under the cursor', () => {
  const box: [number, number, number, number] = [0, 0, 600, 240]
  it('is found along a segment, far from any sample', () => {
    const lines: [number, number][][] = [[[0, 100], [300, 100]], [[0, 200], [300, 150]]]
    const hit = nearestLine(lines, 150, 104, 10, box)!
    expect(hit.n).toBe(0)
    expect(hit.X).toBeCloseTo(150, 9)
    expect(hit.Y).toBeCloseTo(100, 9)
    expect(nearestLine(lines, 150, 130, 10, box)).toBeNull()          // between the two, out of reach of both
  })
  it('is found when a zoom leaves no sample in view, and not where the segment is outside the plot', () => {
    const zoomed: [number, number][][] = [[[-900, 50], [1500, 170]]]   // both samples far outside the plot
    expect(nearestLine(zoomed, 300, 112, 10, box)!.n).toBe(0)
    expect(nearestLine([[[-50, 120], [-10, 120]]], 0, 120, 10, box)).toBeNull()
  })
  it('follows a steep knee to the point nearest the cursor', () => {
    const knee: [number, number][][] = [[[10, 230], [12, 20], [600, 18]]]
    const hit = nearestLine(knee, 16, 120, 10, box)!
    expect(hit.X).toBeGreaterThan(10)
    expect(hit.X).toBeLessThan(12)
  })
})

describe('the ratings a card declares', () => {
  const r = { vceo: 40, icrating: 0.2, mfg: 'PHILIPS' }
  it('are limits on the axis they rate', () => {
    expect(ratingOn('vce', r)).toEqual({ value: 40, label: 'VCEO 40 V' })
    expect(ratingOn('ic', r)!.label).toBe('IC rating 200 mA')
    expect(ratingOn('vbe', r)).toBeNull()
    expect(ratingOn('vce', {})).toBeNull()
  })
  it('warn when a point is beyond them', () => {
    const c = { name: 'IC, step 5, auto', x: 'vce', y: 'ic', scale: 'lin' } as Curve
    expect(beyondRatings(c, { x: 45, y: 0.1 }, r)).toEqual(["⚠ beyond the card's VCEO 40 V"])
    expect(beyondRatings(c, { x: 5, y: 0.3 }, r)).toEqual(["⚠ beyond the card's IC rating 200 mA"])
    expect(beyondRatings(c, { x: 5, y: 0.1 }, r)).toEqual([])
  })
})

describe('a gzipped file', () => {
  it('is read from its bytes, compressed or already undone by the server', async () => {
    const text = JSON.stringify({ hash: 'h', codes: { 'bjt-ft': 'ok' } })
    const gz = await new Response(new Blob([text]).stream().pipeThrough(new CompressionStream('gzip'))).arrayBuffer()
    expect(await jsonMaybeGzip(gz)).toEqual({ hash: 'h', codes: { 'bjt-ft': 'ok' } })
    expect(await jsonMaybeGzip(new TextEncoder().encode(text).buffer as ArrayBuffer)).toEqual({ hash: 'h', codes: { 'bjt-ft': 'ok' } })
  })
})

describe('what the cards of one row say', () => {
  it('is said once when they agree, and by model number where they differ', () => {
    const ms = [{ i: 0, r: '' }, { i: 2, r: 'VCEO 80 V' }, { i: 5, r: 'VCEO 80 V' }, { i: 1, r: '' }]
    expect(memberFacts(ms, (m) => m.r)).toEqual([{ tags: ['[1]', '[2]'], text: '' }, { tags: ['[3]', '[6]'], text: 'VCEO 80 V' }])
    expect(memberFacts([{ i: 0 }, { i: 3 }], () => 'gummel-poon')).toEqual([{ tags: ['[1]', '[4]'], text: 'gummel-poon' }])
  })
})

describe('the chart\'s own title', () => {
  it('says the part, the curve, its conditions, the models and the simulator', () => {
    expect(chartTitle('BD139', 'hFE against IC', ['VCE = 5 V'], ['[1] BD139_C · bordodynov-qspice (+5 identical)'], 'qspice'))
      .toEqual(['BD139 — hFE against IC, VCE = 5 V', '[1] BD139_C · bordodynov-qspice (+5 identical) — simulated in qspice'])
    expect(chartTitle('BD139', 'Cob against VR', [], ['[2] x · y'], 'ngspice', true)[0]).toBe('BD139 — Cob against VR (normalised)')
  })
  it('counts the models that do not fit rather than run off the chart', () => {
    expect(fitList(['aaaa', 'bbbb', 'cccc'], 100)).toBe('aaaa, bbbb, cccc')
    expect(fitList(['aaaa', 'bbbb', 'cccc', 'dddd'], 21)).toBe('aaaa, bbbb and 2 more')
    expect(fitList(['aaaa', 'bbbb', 'cccc', 'dddd'], 20)).toBe('aaaa and 3 more')
    expect(fitList(['a very long first item'], 5)).toBe('a very long first item')
    expect(fitList([], 10)).toBe('')
  })
})

describe('the chart\'s view', () => {
  it('opens on the whole curve, with a margin', () => {
    expect(fitRange([0, 10], false)).toEqual([-0.5, 10.5])
    expect(fitRange([1, 100], true)).toEqual([1 / 1.2, 120])
    expect(fitRange([5, 5], false)).toEqual([5, 5])           // a flat curve: the chart widens it, as before
  })

  it('glides in the axis\'s own space: decades on a log axis', () => {
    expect(between([0, 10], [10, 20], 0.5, false)).toEqual([5, 15])
    expect(between([1, 100], [10, 1000], 0.5, true).map((v) => Number(v.toPrecision(6)))).toEqual([Number((10 ** 0.5).toPrecision(6)), Number((10 ** 2.5).toPrecision(6))])
    expect(between([1, 2], [3, 4], 1, false)).toEqual([3, 4])
  })

  it('eases from rest to rest', () => {
    expect(ease(0)).toBe(0)
    expect(ease(1)).toBe(1)
    expect(ease(0.5)).toBeCloseTo(0.5)
    expect(ease(0.1)).toBeLessThan(0.1)
  })
})
