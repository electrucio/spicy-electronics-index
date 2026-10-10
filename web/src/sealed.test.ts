/**
 * The browser's half of the sealed model text, checked against the fixture the Python half writes
 * (tests/models/test_seal.py). If this fails and that passes, the two have drifted.
 */
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

import { deriveKey, modelKey, normal, opens, type SealManifest, unpack, unseal } from './sealed'

const at = (f: string) => new URL(`../../tests/fixtures/sealed/${f}`, import.meta.url)
const manifest = JSON.parse(readFileSync(at('manifest.json'), 'utf8')) as SealManifest
const fixture = JSON.parse(readFileSync(at('case.json'), 'utf8')) as {
  passphrase: string; part: string; rows: { source: string; name: string; hash?: string }[]; models: Record<string, string>
}
const blob = new Uint8Array(readFileSync(at(`${fixture.part}.bin`)))

describe('the sealed fixture', () => {
  it('opens with the passphrase, read as the Python half reads it', async () => {
    const key = await deriveKey(fixture.passphrase, manifest)
    expect(await opens(key, manifest)).toBe(true)
    expect(await unpack(await unseal(key, fixture.part, blob))).toEqual(fixture.models)
  })

  it('stays closed to another passphrase, and to another part name', async () => {
    const wrong = await deriveKey('another passphrase', manifest)
    expect(await opens(wrong, manifest)).toBe(false)
    const key = await deriveKey(fixture.passphrase, manifest)
    await expect(unseal(key, 'TESTQ2', blob)).rejects.toThrow()
  })

  it('names each model as the Python half does', () => {
    expect(fixture.rows.map(modelKey)).toEqual(Object.keys(fixture.models))
  })

  it('reads a passphrase trimmed and in one spelling', () => {
    expect(normal('  café x \n')).toBe('café x')
  })
})
