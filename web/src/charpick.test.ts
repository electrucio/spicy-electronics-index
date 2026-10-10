/** The characterization's pickers: the list of curves and how it is searched. */
import { describe, expect, it } from 'vitest'

import type { Sel } from './charpick'
import { atTokens, choiceToken, chosenOf, curveRows, curveStatus, defaultCurve, filterGroups, findRow, groupModels, matchCurve, matchModel, readSelection, resolveAt, resolveModels, slug, writeSelection } from './charpick'
import type { Curve, Measurement, ModelCharacter, PartModel } from './types'

const cv = (name: string, y: string, x: string, at?: Record<string, number | string>, k?: number) => ({ name, y, x, scale: 'lin', at, k }) as Curve
const ms = [
  { id: 'bjt-tracer', group: 'dc', family: { note: '' }, curves: [cv('IC, step 1, auto', 'ic', 'vce', { 'IB step': 'auto' }, 1), cv('IC, step 2, auto', 'ic', 'vce', { 'IB step': 'auto' }, 2)] },
  { id: 'bjt-runs', group: 'dc' },
  { id: 'bjt-gummel', group: 'dc', family: { note: '' }, curves: [cv('IC', 'ic', 'vbe'), cv('IB', 'ib', 'vbe')] },
  { id: 'bjt-hfe-ic', group: 'dc', curves: [cv('hFE, VCE=1V', 'hfe', 'ic', { VCE: 1 }), cv('hFE, VCE=5V', 'hfe', 'ic', { VCE: 5 }), cv('VBE, VCE=5V', 'vbe', 'ic', { VCE: 5 }), cv('IC(VBE)', 'ic', 'vbe', { VCE: 5 })] },
  { id: 'bjt-hfe-ac', group: 'dc', curves: [cv('hfe, VCE=5V', 'hfe_ac', 'ic', { VCE: 5 })] },
  { id: 'bjt-saturation', group: 'high-current', curves: [cv('VCE(sat), 10', 'vcesat', 'ic', { 'IC/IB': 10 }), cv('VBE(sat), 10', 'vbesat', 'ic', { 'IC/IB': 10 })] },
  { id: 'bjt-on-voltages', group: 'dc', family: { note: '' }, curves: [cv('VBE(sat)', 'von', 'ic'), cv('VCE(sat)', 'von', 'ic')] },
  { id: 'bjt-capacitance', group: 'capacitance', curves: [cv('Cob', 'cob', 'v'), cv('Cib', 'cib', 'v')] },
  { id: 'bjt-ft', group: 'frequency', curves: [cv('fT, 5V', 'ft', 'ic', { VCE: 5 }), cv('|hfe|, 1mA', 'h21', 'f', { IC: 1e-3 })] },
  { id: 'bjt-switching', group: 'switching', curves: [cv('ts, 10V', 'ts', 'ic', { VCC: 10 })] },
  { id: 'bjt-noise', group: 'noise', curves: [cv('en, 1mA', 'en', 'f', { IC: 1e-3 }), cv('in, 1mA', 'in', 'f', { IC: 1e-3 }), cv('NF, 1mA', 'nf', 'rs', { IC: 1e-3 })] },
  { id: 'bjt-temperature', group: 'temperature', curves: [cv('hFE, 25', 'hfe', 'ic', { T: 25 }), cv('VCE(sat), 25', 'vcesat', 'ic', { T: 25 })] },
  { id: 'bjt-breakdown', group: 'breakdown' },
] as unknown as Measurement[]
const present = new Set(ms.map((m) => m.id).filter((id) => id !== 'bjt-capacitance'))
const rows = curveRows(ms, present)
const find = (q: string) => rows.filter((r) => matchCurve(r, q)).map((r) => r.label)

describe('the list of curves', () => {
  it('has one row per quantity, a family as one row, with names an address can carry', () => {
    expect(rows.map((r) => r.id)).toEqual([
      'bjt-tracer', 'bjt-gummel', 'bjt-hfe-ic.hfe.ic', 'bjt-hfe-ic.vbe.ic', 'bjt-hfe-ic.ic.vbe', 'bjt-hfe-ac.hfe_ac.ic', 'bjt-on-voltages',
      'bjt-saturation.vcesat.ic', 'bjt-saturation.vbesat.ic', 'bjt-ft.ft.ic', 'bjt-ft.h21.f', 'bjt-switching.ts.ic',
      'bjt-noise.en.f', 'bjt-noise.in.f', 'bjt-noise.nf.rs', 'bjt-temperature.hfe.ic', 'bjt-temperature.vcesat.ic',
    ])
    for (const r of rows) expect(r.id).toMatch(/^[a-z0-9._-]+$/)
  })
  it('names every row "Y against X", the family by all its quantities', () => {
    for (const r of rows) expect(r.label).toContain(' against ')
    expect(rows[1]!.label).toBe('IC and IB against VBE')
    expect(rows.find((r) => r.mid === 'bjt-on-voltages')!.label).toBe('VBE(sat), VBE(on) and VCE(sat) against IC')
    expect(rows.find((r) => r.id === 'bjt-tracer')!.curves).toHaveLength(2)
  })
  it('heads the rows by their group in the order groups first appear, so a late dc entry stays under DC', () => {
    expect([...new Set(rows.map((r) => r.heading))]).toEqual(['DC', 'High current', 'Frequency', 'Switching', 'Noise', 'Temperature'])
    expect(rows.slice(0, 7).every((r) => r.heading === 'DC')).toBe(true)
  })
  it('tells apart two rows of one name, hFE and hfe alike, and leaves the first plain', () => {
    expect(rows.find((r) => r.id === 'bjt-hfe-ic.hfe.ic')!.label).toBe('hFE against IC')
    expect(rows.find((r) => r.id === 'bjt-hfe-ac.hfe_ac.ic')!.label).toBe('hfe against IC · AC, 1 kHz')
    expect(rows.find((r) => r.id === 'bjt-temperature.hfe.ic')!.label).toBe('hFE against IC · by temperature')
    expect(new Set(rows.map((r) => r.label.toLowerCase())).size).toBe(rows.length)
  })
  it('leaves out what the models have not run and what draws no curve', () => {
    expect(rows.some((r) => ['bjt-capacitance', 'bjt-runs', 'bjt-breakdown'].includes(r.mid))).toBe(false)
  })
})

describe('the search of curves', () => {
  it('matches everything when empty, and nothing for a word no row has', () => {
    expect(find('')).toHaveLength(rows.length)
    expect(find('  ')).toHaveLength(rows.length)
    expect(find('xyz')).toEqual([])
  })
  it('finds a quantity by the other names a reader knows it by', () => {
    expect(find('beta')).toEqual(['hFE against IC', 'hfe against IC · AC, 1 kHz', 'hFE against IC · by temperature'])
    expect(find('noise figure')).toEqual(['NF against RS'])
    expect(find('storage')).toEqual(['ts against IC'])
    expect(find('gbw')).toEqual(['fT against IC'])
    expect(find('curve tracer')).toEqual(['IC against VCE'])
  })
  it('reads VCE(sat) written any way, and "vs" as a joining word', () => {
    const sat = ['VBE(sat), VBE(on) and VCE(sat) against IC', 'VCE(sat) against IC', 'VCE(sat) against IC · by temperature']
    expect(find('vcesat')).toEqual(sat)
    expect(find('vce sat')).toEqual(sat)
    expect(find('VCE(sat)')).toEqual(sat)
    expect(find('hfe vs ic')).toEqual(find('hfe ic'))
    expect(find('hfe vs ic')).not.toContain('|hfe| against f')       // a qualifier not shown is not searched
  })
  it('matches the start of a word, so "in" is not every row "against" something', () => {
    expect(find('in')).toEqual(['in against f'])
    expect(find('noise')).toEqual(['en against f', 'in against f', 'NF against RS'])   // the heading counts
  })
})

describe('the curve shown first', () => {
  it('is the kind\'s usual one when the part has it, else the first row', () => {
    expect(defaultCurve(rows, 'bjt')).toBe('bjt-hfe-ic.hfe.ic')
    expect(defaultCurve(rows.filter((r) => r.mid !== 'bjt-hfe-ic'), 'bjt')).toBe('bjt-tracer')
    expect(defaultCurve(rows, 'jfet')).toBe('bjt-tracer')
    expect(defaultCurve([], 'bjt')).toBe('')
  })
  it('is found from the address by its name, or by its measurement alone', () => {
    expect(findRow(rows, 'bjt-ft.h21.f')!.label).toBe('|hfe| against f')
    expect(findRow(rows, 'bjt-ft')!.id).toBe('bjt-ft.ft.ic')
    expect(findRow(rows, 'nope')).toBeUndefined()
    expect(findRow(rows, null)).toBeUndefined()
  })
})

describe('whether a model drew a row', () => {
  const hfe = rows.find((r) => r.id === 'bjt-hfe-ic.hfe.ic')!
  const rec = (curves: Record<string, Record<string, unknown>>, codes: Record<string, string>) => ({ curves, codes }) as unknown as ModelCharacter
  it('says ok with two points, the record\'s code without, and why there is nothing when no code says', () => {
    expect(curveStatus(rec({ 'bjt-hfe-ic': { 'hFE, VCE=5V': [100, 120, null] } }, { 'bjt-hfe-ic': 'ok' }), hfe)).toBe('ok')
    expect(curveStatus(rec({ 'bjt-hfe-ic': { 'hFE, VCE=5V': [100, null] } }, { 'bjt-hfe-ic': 'failed' }), hfe)).toBe('failed')
    expect(curveStatus(rec({}, { 'bjt-hfe-ic': 'ok' }), hfe)).toBe('no curve')
    expect(curveStatus(undefined, hfe)).toBe('not run')
  })
  it('counts any trace of a family, and [x, y] pairs as points', () => {
    const tracer = rows.find((r) => r.id === 'bjt-tracer')!
    expect(curveStatus(rec({ 'bjt-tracer': { 'IC, step 2, auto': [[0, 0], [1, 1e-3]] } }, {}), tracer)).toBe('ok')
  })
})

describe('the models with identical results', () => {
  const rec = (o: Partial<Record<keyof ModelCharacter, unknown>>) => ({
    hash: 'h', codes: { 'bjt-ft': 'ok' }, derived: { va: 50 }, curves: { 'bjt-ft': { fT: [1, 2] } }, values: { 'bjt-ft': { qspice: { ft: 1e8 } } },
    agree: {}, decks: {}, changes: {}, other_curves: {}, ...o,
  }) as unknown as ModelCharacter
  it('are one row whatever their decks, other engines\' curves and fixes, the lowest number first', () => {
    const groups = groupModels([
      { i: 3, rec: rec({ decks: { a: { pack: 10 } }, other_curves: { ngspice: { x: 1 } }, changes: { a: ['fix'] } }) },
      { i: 0, rec: rec({}) },
      { i: 1, rec: rec({ codes: { 'bjt-ft': 'failed' } }) },
      { i: 2, rec: rec({ curves: { 'bjt-ft': { fT: [1, 3] } } }) },
      { i: 4, rec: rec({ agree: { 'bjt-ft': [0.1, '>5%', [], null] } }) },
    ])
    expect(groups).toEqual([[0, 3, 4], [1], [2]])
  })
  it('are each their own row when there is one model, and nothing when there is none', () => {
    expect(groupModels([{ i: 0, rec: rec({}) }])).toEqual([[0]])
    expect(groupModels([])).toEqual([])
  })
})

describe('the search of models', () => {
  const models = [
    { source: 'bordodynov-qspice', name: 'BD139_C' }, { source: 'cordell', name: 'BD139C' },
    { source: 'bordodynov-qspice', name: 'BD139', copies: [{ source: 'diyaudio', name: 'BD139' }] },
    { source: 'onsemi', name: 'Qbd139' }, { source: 'groupsio-ltspice', name: 'BD139_' },
  ] as PartModel[]
  it('finds a model by its name written any way, its source, a copy elsewhere or its number', () => {
    expect(matchModel(models[0]!, 0, 'bd139c')).toBe('self')
    expect(matchModel(models[1]!, 1, 'BD139_C')).toBe('self')
    expect(matchModel(models[1]!, 1, 'cordell')).toBe('self')
    expect(matchModel(models[2]!, 2, 'diyaudio')).toBe('copy')
    expect(matchModel(models[2]!, 2, '[3]')).toBe('self')
    expect(matchModel(models[1]!, 1, '[3]')).toBeNull()
    expect(matchModel(models[3]!, 3, 'onsemi 139')).toBe('self')
    expect(matchModel(models[3]!, 3, 'onsemi zz')).toBeNull()
  })
  it('keeps the rows any model of which answers, and opens one only to show a model other than its first', () => {
    const groups = [[0, 1], [2], [3, 4]]
    expect(filterGroups(groups, models, '').map((g) => [g.members[0], g.open])).toEqual([[0, false], [2, false], [3, false]])
    expect(filterGroups(groups, models, 'cordell').map((g) => [g.members[0], g.open, [...g.hits.keys()]])).toEqual([[0, true, [1]]])
    expect(filterGroups(groups, models, 'groupsio').map((g) => [g.members[0], g.open])).toEqual([[3, true]])
    expect(filterGroups(groups, models, '139').every((g) => !g.open)).toBe(true)
    expect(filterGroups(groups, models, 'nothing')).toEqual([])
  })
})

describe('the selection in the address', () => {
  const hfe = { id: 'bjt-hfe-ic', select: { VCE: 5 } } as unknown as Measurement
  const vce: Sel = { key: 'VCE', values: [1, 2, 5, 10] }
  const ic: Sel = { key: 'IC', values: [1e-5, 1e-3, 1] }
  const step: Sel = { key: 'IB step', values: ['auto', 1e-5, 2e-5] }
  const span: Sel = { key: 'span', values: ['−55 to 25°C', '25 to 100°C'] }
  const f: Sel = { key: 'f', values: [1e8, 'extrapolated'] }
  it('writes conditions in letters an address keeps', () => {
    expect([1e-3, 1e-5, 5, -55, 1e8, 1.5e-6, 0.0003].map(choiceToken)).toEqual(['1m', '10u', '5', '-55', '100M', '1.5u', '300u'])
    expect(choiceToken('−55 to 25°C')).toBe('-55to25c')
    expect(choiceToken('10 Hz to 15.7 kHz')).toBe('10hzto15.7khz')
    expect(choiceToken('all')).toBe('all')
    expect(slug('IB step')).toBe('ibstep')
    expect(slug('IC/IB')).toBe('icib')
  })
  it('reads them back as the selectors\' own values, and drops what no selector offers', () => {
    expect(resolveAt([['vce', '10'], ['ic', '1m'], ['ibstep', '10u'], ['span', '-55to25c'], ['f', '100M']], [vce, ic, step, span, f]))
      .toEqual({ VCE: 10, IC: 1e-3, 'IB step': 1e-5, span: '−55 to 25°C', f: 1e8 })
    expect(resolveAt([['VCE', '10'], ['ic', '0.001'], ['ic', '1mA']], [vce, ic])).toEqual({ VCE: 10, IC: 1e-3 })
    expect(resolveAt([['vce', '999'], ['t', '25'], ['f', '100m']], [vce, f])).toEqual({})
    expect(resolveAt([['vce', 'all'], ['ic', 'all']], [vce, { key: 'IC', values: [1] }])).toEqual({ VCE: 'all' })
  })
  it('writes only what differs from the measurement\'s default, and falls back to it on a stale value', () => {
    expect(atTokens(hfe, [vce], { VCE: 5 })).toEqual([])
    expect(atTokens(hfe, [vce], { VCE: 10 })).toEqual([['vce', '10']])
    expect(atTokens(hfe, [vce], { VCE: 'all' })).toEqual([['vce', 'all']])
    expect(chosenOf(hfe, [vce], { VCE: 10 })).toEqual({ VCE: 10 })
    expect(chosenOf(hfe, [vce], { VCE: 7 })).toEqual({ VCE: 5 })
    expect(chosenOf(hfe, [vce])).toEqual({ VCE: 5 })
    expect(chosenOf(hfe, [{ key: 'VCE', values: [5] }], { VCE: 'all' })).toEqual({ VCE: 5 })
  })
  it('finds a row by a hash of any of its models', () => {
    const hashes = ['0ca21363aa', '9c1fef0fbb', '59b3cf06cc', '673b8dc1dd', '7040b0cbee']
    const groups = [[0, 1], [2], [3, 4]]
    const hashOf = (i: number) => hashes[i]
    expect(resolveModels(['9c1fef0f'], groups, hashOf)).toEqual([0])
    expect(resolveModels(['7040b0cb', '59b3cf06', '0ca213'], groups, hashOf)).toEqual([0, 2, 3])
    expect(resolveModels(['ffffffff'], groups, hashOf)).toEqual([])
  })
  it('reads the address, keeping only what it understands', () => {
    expect(readSelection('?part=BD139&curve=bjt-hfe-ic.hfe.ic&model=59B3CF06,zz,673b8dc1&at=vce:10,bad,ic:1m'))
      .toEqual({ curve: 'bjt-hfe-ic.hfe.ic', models: ['59b3cf06', '673b8dc1'], at: [['vce', '10'], ['ic', '1m']] })
    expect(readSelection('?part=BD139')).toEqual({ curve: undefined, models: [], at: [] })
  })
  it('writes the selection in place of the last, every other parameter as it was', () => {
    const sel = { curve: 'bjt-hfe-ic.hfe.ic', models: ['59b3cf06', '673b8dc1'], at: [['vce', '10']] as [string, string][] }
    const out = writeSelection('?part=APT1608LSECK%2FJ3-PRV&curve=old&model=1234567&at=x:1', sel)
    expect(out).toBe('?part=APT1608LSECK%2FJ3-PRV&curve=bjt-hfe-ic.hfe.ic&model=59b3cf06,673b8dc1&at=vce:10')
    expect(readSelection(out)).toEqual(sel)
    expect(writeSelection('?part=BD139', { curve: 'bjt-tracer', models: [], at: [] })).toBe('?part=BD139&curve=bjt-tracer')
    expect(writeSelection('', { models: [], at: [] })).toBe('')
    expect(out).toMatch(/^\?[A-Za-z0-9%=&._:,-]+$/)
  })
})
