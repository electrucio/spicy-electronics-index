/** Which sellers a part page shows, in what order, and the facts said beside them. */
import { describe, expect, it } from 'vitest'

import { country, flag, orderTier, partKinds, partMakers, sellerKinds, tiers } from './sellers'
import type { PartPage, Seller, SellersList } from './types'

function seller(id: string, title: string, group: string, base: string, priority: number, more: Partial<Seller> = {}): Seller {
  return { id, title, url: `https://${id}.example/`, type: 'specialist', base, group, useful_for: 'things', priority, ...more }
}

const LIST: SellersList = {
  types: {},
  groups: [
    { id: 'search', title: 'Search', note: '', kinds: [] },
    { id: 'direct', title: 'Direct', note: '', kinds: [] },
    { id: 'broadline', title: 'Broad', note: '', kinds: ['opamp', 'bjt'] },
    { id: 'pedal_tube_synth', title: 'Pedal', note: '', kinds: ['tube', 'opamp', 'bjt'] },
    { id: 'hifi_transformers', title: 'Hi-fi', note: '', kinds: ['tube'] },
    { id: 'enclosures', title: 'Boxes', note: '', kinds: [] },
    { id: 'regional', title: 'Regional', note: '', kinds: [] },
    { id: 'marketplace_surplus', title: 'Market', note: '', kinds: ['tube', 'bjt'], caveat: 'S97' },
  ],
  sellers: [
    seller('octopart', 'Octopart', 'search', 'US', 1, { type: 'aggregator' }),
    seller('mouser', 'Mouser', 'broadline', 'US', 1, { type: 'authorized_distributor' }),
    seller('tme', 'TME', 'broadline', 'PL', 1, { type: 'authorized_distributor' }),
    seller('ti_direct', 'TI store', 'direct', 'US', 1, { makers: ['texas-instruments', 'national'] }),
    seller('microchipdirect', 'microchipDIRECT', 'direct', 'US', 2, { makers: ['microchip'] }),
    seller('raspberrypi', 'Raspberry Pi resellers', 'direct', 'GB', 2),
    seller('musikding', 'Das Musikding', 'pedal_tube_synth', 'DE', 1),
    seller('tubetown', 'Tube-Town', 'pedal_tube_synth', 'DE', 1, { kinds: ['tube'] }),
    seller('audiophonics', 'Audiophonics', 'hifi_transformers', 'FR', 1, { kinds: ['tube', 'opamp'] }),
    seller('partsexpress', 'Parts Express', 'hifi_transformers', 'US', 1),
    seller('altinkaya', 'Altınkaya', 'enclosures', 'TR', 2),
    seller('diotronic', 'Diotronic', 'regional', 'ES', 2),
    seller('ebay', 'eBay', 'marketplace_surplus', 'WW', 3, { type: 'marketplace' }),
  ],
}
const ids = (rows: Seller[]) => rows.map((s) => s.id).sort()

describe('flags and countries', () => {
  it('turns a code into its flag and a marketplace into a globe', () => {
    expect(flag('US')).toBe('🇺🇸')
    expect(flag('GB')).toBe('🇬🇧')
    expect(flag('UK')).toBe('🇬🇧')   // not ISO, but a reader's hidden set may still carry it
    expect(flag('WW')).toBe('🌐')
    expect(flag('')).toBe('')
    expect(flag('usa')).toBe('')
  })
  it('names a marketplace as based nowhere', () => {
    expect(country('WW')).toBe('Worldwide (depends on the seller)')
    expect(country('DE')).toBe('Germany')
  })
})

describe('what the page says the part is', () => {
  const page = (p: Partial<PartPage>): PartPage => ({ part: 'X', docs: [], n: { documents: 0, shown: 0, copies: 0 }, ...p } as PartPage)
  it('reads the devices first, then the recipe, then the dictionary id in pieces', () => {
    expect([...partKinds(page({ devices: ['bjt', 'jfet'] }))]).toEqual(['bjt', 'jfet'])
    expect([...partKinds(page({ models: { kind: 'opamp', models: [] } }))]).toEqual(['opamp'])
    expect([...partKinds(page({ kind: 'bjt/jfet/mosfet' }))]).toEqual(['bjt', 'jfet', 'mosfet'])
    expect(partKinds(page({})).size).toBe(0)
  })
  it('reads the makers from the sheet and its lineage, then from the catalogues and the sheets', () => {
    expect([...partMakers(page({ about: { maker: ['national', ['texas-instruments']] } }))]).toEqual(['national', 'texas-instruments'])
    const a = { catalogue: [['s', 'toshiba', 'c', 'st', 't', 'r', 'l', 'p', 'd', 'o']],
      sheets: [['l', 'kexin', 'Kexin', 't', 'from', 'note']] } as PartPage['about']
    expect([...partMakers(page({ about: a }))]).toEqual(['toshiba', 'kexin'])
    expect(partMakers(page({})).size).toBe(0)
  })
})

describe('the tiers of a part page', () => {
  it('puts the broad distributors and the maker\'s own store first for an op-amp of TI', () => {
    const t = tiers(LIST, new Set(['opamp']), new Set(['texas-instruments']))
    expect(ids(t.aggregators)).toEqual(['octopart'])
    expect(ids(t.broad)).toEqual(['mouser', 'ti_direct', 'tme'])
    expect(ids(t.specialists)).toEqual(['audiophonics', 'musikding'])   // the override counts; a box maker never
    expect(ids(t.regional)).toEqual(['diotronic'])
    expect(t.marketplaces).toEqual([])   // no op-amp is bought on a marketplace by this list
  })
  it('shows a valve the specialists and the marketplaces, and no broad distributor', () => {
    const t = tiers(LIST, new Set(['tube']), new Set())
    expect(t.broad).toEqual([])
    expect(ids(t.specialists)).toEqual(['audiophonics', 'musikding', 'partsexpress', 'tubetown'])
    expect(ids(t.marketplaces)).toEqual(['ebay'])
  })
  it('shows every broad distributor and no specialist when nothing says what the part is', () => {
    const t = tiers(LIST, new Set(), new Set())
    expect(ids(t.broad)).toEqual(['mouser', 'tme'])
    expect(t.specialists).toEqual([])
  })
  it('lets a seller override its group\'s kinds', () => {
    const groups = new Map(LIST.groups.map((g) => [g.id, g]))
    expect(sellerKinds(LIST.sellers[7]!, groups)).toEqual(['tube'])
    expect(sellerKinds(LIST.sellers[6]!, groups)).toEqual(['tube', 'opamp', 'bjt'])
  })
})

describe('the order within a tier', () => {
  const rows = [seller('arrow', 'Arrow', 'broadline', 'US', 2), seller('tme', 'TME', 'broadline', 'PL', 1), seller('digikey', 'DigiKey', 'broadline', 'US', 1)]
  it('is the maintainer\'s priority, then the name, never the country', () => {
    expect(orderTier(rows).map((s) => s.id)).toEqual(['digikey', 'tme', 'arrow'])
  })
  it('puts what a check found first, when a check has been made', () => {
    expect(orderTier(rows, { arrow: ['found', 'https://arrow.example/x', '2026-10-12'] }).map((s) => s.id)).toEqual(['arrow', 'digikey', 'tme'])
  })
})
