import { describe, expect, it } from 'vitest'
import { FIELD, aboutLine, feedbackBody } from './feedback'

describe('feedback', () => {
  it('carries the message, the part and the page, each under its own question', () => {
    const body = feedbackBody('  Wrong pinout on page 3\n', 'BC547', 'https://example.org/?part=BC547')
    expect(body.get(FIELD.message)).toBe('Wrong pinout on page 3')
    expect(body.get(FIELD.part)).toBe('BC547')
    expect(body.get(FIELD.page)).toBe('https://example.org/?part=BC547')
  })

  it('from a page with no part names none', () => {
    expect(feedbackBody('Search is slow', undefined, 'https://example.org/').get(FIELD.part)).toBe('')
  })

  it('names three different questions', () => {
    expect(new Set(Object.values(FIELD)).size).toBe(3)
  })

  it('says first what a report is about, when it is about something', () => {
    const about = { kind: 'document' as const, what: 'Elektor 1995-03', where: 'https://archive.example/elektor-1995-03.pdf' }
    expect(aboutLine(about)).toBe('About this document: Elektor 1995-03 — https://archive.example/elektor-1995-03.pdf')
    expect(feedbackBody('  Dead link ', '1N4148', 'https://example.org/?part=1N4148', about).get(FIELD.message))
      .toBe('About this document: Elektor 1995-03 — https://archive.example/elektor-1995-03.pdf\n\nDead link')
    expect(aboutLine({ kind: 'model', what: 'BC547B from cordell' })).toBe('About this model: BC547B from cordell')
    expect(aboutLine(undefined)).toBe('')
  })
})
