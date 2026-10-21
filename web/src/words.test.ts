/** The words the Projects tab looks up, cut the same way here and in the build. */
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

import { keysFor, shardOf, unitsOfWord, words } from './words'

const CASES = JSON.parse(readFileSync(new URL('../../tests/fixtures/words_cases.json', import.meta.url), 'utf-8')) as
  { text: string; words: string[] }[]

describe('words', () => {
  it('cuts the shared cases into the same words as the build', () => {
    for (const c of CASES) expect(words(c.text), c.text).toEqual(c.words)
  })
  it('looks a word up in the split of its first two letters, or three where the build split again', () => {
    expect(shardOf('wah')).toBe('wa')
    expect(keysFor('wah', ['wa', 'fe'])).toEqual(['wa'])
    expect(keysFor('wah', ['wa', 'wah', 'wal'])).toEqual(['wah'])
    expect(keysFor('wa', ['wa', 'wah'])).toEqual(['wa'])
    expect(keysFor('wa*', ['wa', 'wah', 'wal', 'fe'])).toEqual(['wa', 'wah', 'wal'])
    expect(keysFor('zzz', ['wa'])).toEqual([])
  })
})

describe('unitsOfWord', () => {
  const shard = { findStamp: 'f', words: { wah: [3, 4], wahwah: [10], wahs: [1], war: [2] } }
  it('finds a word and its plural, and every word a stem with a star starts', () => {
    expect([...unitsOfWord(shard, 'wah')].sort((a, b) => a - b)).toEqual([1, 3, 7])
    expect([...unitsOfWord(shard, 'wah*')].sort((a, b) => a - b)).toEqual([1, 3, 7, 10])
    expect([...unitsOfWord(shard, 'wa')]).toEqual([])
  })
})
