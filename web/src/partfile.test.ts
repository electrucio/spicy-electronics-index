/**
 * The TypeScript half of the part-file rule, checked against the same fixture as the Python half
 * (src/spicy_electronics_index/core/partfile.py).
 */
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { partFile } from './data'

const fixture = JSON.parse(readFileSync(new URL('../../tests/fixtures/part_files.json', import.meta.url), 'utf8'))

describe('partFile', () => {
  for (const c of fixture.cases) {
    it(`serves ${c.part} from ${c.file}`, () => expect(partFile(c.part)).toBe(c.file))
  }
})
