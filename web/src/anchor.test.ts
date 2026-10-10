import { describe, expect, it } from 'vitest'

import { leadsTo, parentOf, sectionHref, target } from './anchor'

const at = (search: string, hash = '') => ({ pathname: '/spicy-electronics-index/', search, hash })

describe('a section address', () => {
  it('is the fragment, decoded', () => {
    expect(target(at('?part=BC547', '#spice-models/characterization'))).toBe('spice-models/characterization')
    expect(target(at('?part=BC547', '#where-used%2Fmagazines'))).toBe('where-used/magazines')
    expect(target(at('?part=BC547'))).toBe('')
  })

  it('still answers to the link handed out before sections had addresses', () => {
    expect(target(at('?part=BC547&open=character'))).toBe('spice-models/characterization')
    expect(target(at('?part=BC547&open=nothing'))).toBe('')
    // a fragment wins over the old key
    expect(target(at('?part=BC547&open=character', '#data-sheets'))).toBe('data-sheets')
  })

  it('opens the characterization for a link to one of its curves, unless a fragment says otherwise', () => {
    expect(target(at('?part=BD139&curve=bjt-ft.ft.ic'))).toBe('spice-models/characterization')
    expect(target(at('?part=BD139&model=0ca21363'))).toBe('spice-models/characterization')
    expect(target(at('?part=BD139&curve=bjt-ft.ft.ic', '#data-sheets'))).toBe('data-sheets')
    expect(target(at('?part=BD139&at=vce:10'))).toBe('')
  })

  it('points nowhere when the fragment is a broken escape', () => {
    expect(target(at('?part=BC547', '#%E0%A4%A'))).toBe('')
  })

  it('opens every section on the way down, and only those', () => {
    const t = 'spice-models/characterization/figures'
    expect(leadsTo(t, 'spice-models')).toBe(true)
    expect(leadsTo(t, 'spice-models/characterization')).toBe(true)
    expect(leadsTo(t, t)).toBe(true)
    expect(leadsTo(t, 'spice-models/table')).toBe(false)
    expect(leadsTo(t, 'spice')).toBe(false)      // a prefix of a name is not its parent
    expect(leadsTo(t, '')).toBe(false)           // a fold with no address of its own
    expect(leadsTo('', 'spice-models')).toBe(false)
  })

  it('goes back one level when a section closes', () => {
    expect(parentOf('spice-models/characterization/figures')).toBe('spice-models/characterization')
    expect(parentOf('spice-models')).toBe('')
  })

  it('keeps the part, drops the old key and carries the section', () => {
    expect(sectionHref('where-used/magazines', at('?part=BC547'))).toBe('/spicy-electronics-index/?part=BC547#where-used/magazines')
    expect(sectionHref('', at('?part=BC547', '#data-sheets'))).toBe('/spicy-electronics-index/?part=BC547')
    expect(sectionHref('spice-models', at('?part=BC547&open=character'))).toBe('/spicy-electronics-index/?part=BC547#spice-models')
    // a part with a slash keeps the escape it was linked with
    expect(sectionHref('data-sheets', at('?part=APT1608LSECK%2FJ3-PRV'))).toBe('/spicy-electronics-index/?part=APT1608LSECK%2FJ3-PRV#data-sheets')
    // and a selection of the characterization goes along with the section
    expect(sectionHref('spice-models/characterization', at('?part=BD139&curve=bjt-hfe-ic.hfe.ic&model=0ca21363,673b8dc1&at=vce:10')))
      .toBe('/spicy-electronics-index/?part=BD139&curve=bjt-hfe-ic.hfe.ic&model=0ca21363,673b8dc1&at=vce:10#spice-models/characterization')
  })
})
