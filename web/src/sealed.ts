/**
 * The model text the site shows its maintainer, opened in the browser: the other half of
 * `src/spicy_electronics_index/models/seal.py`, checked against the same fixture (`tests/fixtures/sealed/`).
 *
 * Each part with models has a sealed file beside its page, AES-GCM under a key derived from a passphrase
 * only the maintainer holds. Open the site with `#unlock` and the passphrase is asked for once; the key it
 * gives — never the passphrase — is kept in this browser, and every part's models gain their text, ready
 * to paste into an LTspice or QSPICE directive. `#lock` forgets it. Without the key nothing sealed is even
 * fetched: a reader sees the site as it is.
 */
import { DATA, partPath } from './data'

export interface SealManifest {
  v: number
  kdf: { name: 'PBKDF2'; hash: 'SHA-256'; iterations: number; salt: string }
  cipher: 'AES-GCM'
  check: string
}

/** The name a model's text goes by in its part's file: the same expression as seal.py's `model_key`. */
export const modelKey = (m: { hash?: string; source: string; name: string }) => m.hash || `${m.source}:${m.name}`

const STORE = 'sei.sealed.key'
const CHECK = 'spicy-electronics-index sealed models'
const enc = new TextEncoder()

export const fromB64 = (s: string) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0))
const toB64 = (b: ArrayBuffer) => btoa(String.fromCharCode(...new Uint8Array(b)))

/** The passphrase as both halves read it: trimmed, and in one Unicode spelling (NFC). */
export const normal = (phrase: string) => phrase.trim().normalize('NFC')

export async function deriveKey(phrase: string, m: SealManifest): Promise<CryptoKey> {
  const base = await crypto.subtle.importKey('raw', enc.encode(normal(phrase)), 'PBKDF2', false, ['deriveKey'])
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', hash: m.kdf.hash, salt: fromB64(m.kdf.salt), iterations: m.kdf.iterations },
    base, { name: 'AES-GCM', length: 256 }, true, ['decrypt'])
}

/** One sealed blob opened: 12 bytes of IV, then the ciphertext and its tag. Throws on the wrong key. */
export async function unseal(key: CryptoKey, aad: string, blob: Uint8Array): Promise<Uint8Array<ArrayBuffer>> {
  const plain = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: blob.slice(0, 12), additionalData: enc.encode(aad) }, key, blob.slice(12))
  return new Uint8Array(plain)
}

export async function unpack(plain: Uint8Array<ArrayBuffer>): Promise<Record<string, string>> {
  const text = await new Response(new Blob([plain]).stream().pipeThrough(new DecompressionStream('gzip'))).text()
  return (JSON.parse(text) as { v: number; models: Record<string, string> }).models
}

/** Whether a key opens the manifest's check value, so a wrong passphrase is told before it is kept. */
export async function opens(key: CryptoKey, m: SealManifest): Promise<boolean> {
  try {
    return new TextDecoder().decode(await unseal(key, 'check', fromB64(m.check))) === CHECK
  } catch {
    return false
  }
}

// --- the key this browser holds -----------------------------------------------------------------------------
let held: Promise<CryptoKey | null> | null = null
const opened = new Map<string, Promise<Record<string, string> | null>>()
const listeners = new Set<() => void>()

export function heldKey(): Promise<CryptoKey | null> {
  held ??= (async () => {
    if (!globalThis.crypto?.subtle) return null
    try {
      const raw = localStorage.getItem(STORE)
      return raw ? await crypto.subtle.importKey('raw', fromB64(raw), 'AES-GCM', false, ['decrypt']) : null
    } catch {
      return null
    }
  })()
  return held
}

/** Be told when the key is taken or forgotten; returns the way to stop. */
export function onKeyChange(f: () => void): () => void {
  listeners.add(f)
  return () => { listeners.delete(f) }
}

function hold(key: CryptoKey | null) {
  held = Promise.resolve(key)
  opened.clear()
  listeners.forEach((f) => f())
}

async function manifest(): Promise<SealManifest | null> {
  try {
    const r = await fetch(`${DATA}/sealed/manifest.json`, { cache: 'no-cache' })
    return r.ok ? ((await r.json()) as SealManifest) : null
  } catch {
    return null   // no file, or the dev server's page in its place
  }
}

/** Try a passphrase: 'ok' and the key is held, 'wrong', 'none' when this site has nothing sealed, or
 *  'insecure' when the page came over plain http from another machine (the dev server on the network):
 *  browsers give WebCrypto only to https and localhost. */
export async function unlock(phrase: string): Promise<'ok' | 'wrong' | 'none' | 'insecure'> {
  if (!globalThis.crypto?.subtle) return 'insecure'
  const m = await manifest()
  if (!m) return 'none'
  const key = await deriveKey(phrase, m)
  if (!(await opens(key, m))) return 'wrong'
  try {
    localStorage.setItem(STORE, toB64(await crypto.subtle.exportKey('raw', key)))
  } catch { /* a private window: held for this visit only */ }
  hold(key)
  return 'ok'
}

export function lock() {
  try { localStorage.removeItem(STORE) } catch { /* nothing kept to forget */ }
  hold(null)
}

/** One part's model texts by `modelKey`, or null: no key held, no sealed file, or one this key does not open. */
export function partTexts(part: string): Promise<Record<string, string> | null> {
  let p = opened.get(part)
  if (!p) {
    p = (async () => {
      const key = await heldKey()
      if (!key) return null
      try {
        const r = await fetch(`${DATA}/sealed/${partPath(part)}.bin`)
        return r.ok ? await unpack(await unseal(key, part, new Uint8Array(await r.arrayBuffer()))) : null
      } catch {
        return null
      }
    })()
    opened.set(part, p)
  }
  return p
}
