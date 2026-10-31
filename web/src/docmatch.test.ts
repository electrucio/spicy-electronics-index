/** The filter box of a part's usage lists: which documents answer what is typed, and where the words fall. */
import { describe, expect, it } from 'vitest'

import { highlights, matchDoc, queryWords } from './docmatch'

const doc = (t: string, y = '', more: { u?: string; aka?: string[]; also?: string[] } = {}) =>
  ({ t, y, u: more.u ?? 'https://archive.example/file.pdf', aka: more.aka, also: more.also })
const q = queryWords

describe('what a document answers', () => {
  const dac = doc('Elektor 1995-03: Audio DAC', '1995-03')
  const pre = doc('Elektor 1985-08: Preamplifier', '1985-08')

  it('answers a blank query with everything', () => {
    expect(q('')).toEqual([])
    expect(q('  \t ')).toEqual([])
    expect(matchDoc(pre, q(''))).toBe(true)
  })

  it('reads case and accents aside', () => {
    expect(matchDoc(dac, q('audio dac'))).toBe(true)
    expect(matchDoc(dac, q('AUDIO'))).toBe(true)
    expect(matchDoc(doc('Hörbuch-Verstärker'), q('horbuch verstarker'))).toBe(true)
    expect(matchDoc(doc('Horbuch'), q('hörbuch'))).toBe(true)
  })

  it('finds a year in the date as much as in the title', () => {
    expect(matchDoc(doc('Preamplifier', '1995'), q('1995'))).toBe(true)
    expect(matchDoc(dac, q('1995'))).toBe(true)
    expect(matchDoc(pre, q('1995'))).toBe(false)
  })

  it('wants every word, each anywhere', () => {
    expect(matchDoc(dac, q('dac 1995'))).toBe(true)
    expect(matchDoc(dac, q('dac 1985'))).toBe(false)
    expect(matchDoc(dac, q('1995 dac audio'))).toBe(true)
  })

  it("counts the source's own name for every document under it", () => {
    expect(matchDoc(doc('Preamplifier', '1985'), q('elrad'), 'Elrad')).toBe(true)
    expect(matchDoc(doc('Preamplifier', '1985'), q('elrad 1985'), 'Elrad')).toBe(true)
    expect(matchDoc(doc('Preamplifier', '1985'), q('elektor'), 'Elrad')).toBe(false)
    expect(matchDoc(doc('Preamplifier', '1985'), q('elrad 1995'), 'Elrad')).toBe(false)
  })

  it('reads the other names a document is filed under and the other archives it is at', () => {
    const denon = doc('Denon AVR-1803/883 service manual', '', { aka: ['Denon AVR883'], also: ['hifiengine'] })
    expect(matchDoc(denon, q('avr883'))).toBe(true)
    expect(matchDoc(denon, q('hifiengine'))).toBe(true)
    expect(matchDoc(denon, q('marantz'))).toBe(false)
  })

  it('searches the address only when there is no title', () => {
    expect(matchDoc(doc('', '', { u: 'https://a.example/schematics/pre84.pdf' }), q('pre84'))).toBe(true)
    expect(matchDoc(doc('Preamplifier', '', { u: 'https://a.example/schematics/pre84.pdf' }), q('pre84'))).toBe(false)
  })
})

describe('where the words fall', () => {
  it('marks each word where it is, case aside', () => {
    expect(highlights('Elektor 1995-03: Audio DAC', q('elektor 1995'))).toEqual([[0, 7], [8, 12]])
    expect(highlights('Elektor 1995-03: Audio DAC', q('dac'))).toEqual([[23, 26]])
  })

  it('marks every place a word is', () => {
    expect(highlights('Elektor: Elektor', q('elektor'))).toEqual([[0, 7], [9, 16]])
  })

  it('merges words that overlap or touch', () => {
    expect(highlights('abcde', ['abc', 'cde'])).toEqual([[0, 5]])
    expect(highlights('abcde', ['ab', 'cd'])).toEqual([[0, 4]])
    expect(highlights('abcde', ['ab', 'de'])).toEqual([[0, 2], [3, 5]])
  })

  it("maps through accents and ligatures back to the text's own characters", () => {
    expect(highlights('Hörbuch', q('hor'))).toEqual([[0, 3]])
    expect(highlights('ﬁlter', q('fil'))).toEqual([[0, 2]])          // the ligature is one character
    expect(highlights('Verstärker', q('arker'))).toEqual([[5, 10]])
  })

  it('keeps an accent written apart from its letter inside the mark', () => {
    expect(highlights('café au lait', q('cafe'))).toEqual([[0, 5]])
  })

  it('marks nothing for a blank query or an empty text', () => {
    expect(highlights('Elektor', [])).toEqual([])
    expect(highlights('', q('elektor'))).toEqual([])
  })
})
