// The shape of what `sei web build` writes into public/data. Kept by hand for now; once the
// exporters land these are generated from the Python models so the two can never drift.

export interface Manifest {
  schema: number
  built: string
  /** How many parts have a page. */
  parts?: number
  totals: {
    sources: number
    items: number
    indexed: number
    ocr: number
    modelSources: number
    modelFiles: number
    definitions: number
  }
  /** Which exports exist yet. The site renders what is present and says what is not. */
  have: { sources: boolean; index: boolean; parts: boolean; models: boolean; datasheets: boolean }
  sizes: Record<string, number>
}

/** One entry of the device filter: what it is called and how many parts answer to it. A finer entry —
 *  NPN under silicon BJT, N-channel under JFET — names the entry it sits under. */
export interface DeviceKind {
  key: string
  label: string
  n: number
  parent?: string
}

/** One row of the search index: part, documents, uses, model candidates, devices, family, data sheets.
 *  Devices is a bit per entry of `PartIndex.deviceKinds`, because a part can answer to several; family
 *  is a position in `PartIndex.families`, or -1 when nothing says which. */
export type PartRow = [string, number, number, number, number, number?, number?]

export interface PartIndex {
  schema: number
  /** The source names, once. A document names its source by position in this list. */
  sources: string[]
  /** A stamp of `sources` and `kinds`; a part page built against another list carries another stamp. */
  sourcesStamp?: string
  /** What each of those sources is — site, factory, magazine, book — by the same position. */
  kinds: string[]
  /** The device filter's menu, in menu order. A part row carries one bit per entry. */
  deviceKinds: DeviceKind[]
  /** Family ids, in the order a part row names one. */
  families?: string[]
  parts: PartRow[]
}

export interface PartModel {
  source: string
  name: string
  def: string
  /** The model's identity: how its text is found in the part's sealed file (`sealed.ts`). */
  hash?: string
  type?: string
  pins?: string[]
  verbatim?: boolean
  /** Our named fixups, when the text was not used as published. */
  changes?: string[]
  /** `via`: the url is a published copy's, because only a simulator ships the model itself. */
  get: { url?: string; member?: string; installed_with?: string; file?: string; how?: string; via?: string
    /** The LTspice symbol published with the model: in the same archive as `url`, or a file of its own. */
    symbol?: { url: string; member?: string; sha256?: string } }
  /** The same model in other sources, each with its own link. */
  copies?: { source: string; name: string; url?: string; member?: string; installed_with?: string }[]
  /** A model of another part, filed for this one: the part it models. */
  standin?: string
  /** The name the model was found under, when it is not the part's own. */
  alias?: string
  /** What its card and its author's notes say (`src/spicy_electronics_index/web/character.py`). */
  chk?: ModelCheck
  /** What the bench and the card say before any data sheet (`bench_summary`): the order of the list follows it. */
  bench?: { rank: number; sims?: Record<string, 'ok' | 'differs' | 'failed'>; differs_on?: number; covers?: [number, number]; missing?: string[]; defaults?: string[]; extensions?: string[]; artefacts?: string[]; agree?: number; flags?: string[]; cpu_s?: number }
}

/** What a part's characterisation holds, known before its file is fetched: models and measurements. */
export interface CharacterSummary { n: number; m: number }

/** The method page's data (`data/bench/methods.json`): the measurement catalogue as published. */
export interface Grid { x: string; from?: number; to?: number; per_decade?: number; step?: number; values?: number[]; unit?: string }
/** `k`: in a family (the curve tracer's traces), the trace's multiple of the step. */
export interface Curve { name: string; x: string; y: string; scale: 'log' | 'lin'; unit?: string; x_unit?: string; at?: Record<string, number | string>; grid?: Grid; k?: number }
/** What a chart computes for the point under the cursor: [term, op, term] over x, y, the local slope (dx, dy),
 *  the trace's base current (ib) and the curve's conditions (at.<selector>). */
export interface HoverExtra { y: string; label: string; unit: string; of: [string, string, string]; what?: string }

export interface MethodsFile {
  version: string
  codes: Record<string, string>
  /** The parameters a chart's dropdowns offer, with their units. */
  selectors?: Record<string, { unit: string; what?: string }>
  uses: { use: string; groups: string[]; look_at: string }[]
  measurements: Measurement[]
  /** The measurement ids whose circuit drawing exists. */
  drawings: string[]
}

export interface Measurement {
  id: string
  kind: string
  group: string
  name: string
  symbols: string[]
  what: string
  circuit: string
  drawing: { file: string; elements: string[]; differs_from_netlist: string }
  analysis: string
  conditions: Record<string, unknown>
  grid?: Grid
  extraction: string
  /** The lines of the single-model QSPICE deck that set the circuit up and the analysis, verbatim; `*` starts a comment. */
  directives?: string[]
  /** The same lines as the PNP deck writes them (the sources with the opposite sign), from the site build. */
  directives_pnp?: string[]
  /** `plotted`: a curve shows it, so the table does not repeat it. */
  outputs: { key: string; unit: string; what: string; plotted?: boolean }[]
  /** `at`: the selector values the curve was taken at (the chart's dropdowns); `grid`: its own x grid where
   *  that is not the measurement's. */
  curves?: Curve[]
  /** The value each selector shows first, or 'all' to overlay every value. */
  select?: Record<string, number | string>
  hover?: HoverExtra[]
  /** A quantity that can be shown relative to one published value of each model (hFE / hFE at 1 mA, 5 V, 25 °C). */
  normalise?: { y: string; by: { id: string; key: string }; label: string }[]
  /** The curves are one family (a curve tracer's traces), drawn together in the model's colour; `note` says what
   *  tells the traces apart and `key` names the output that gives each model's own step. */
  family?: { note: string; key?: string; because?: { id: string; key: string; label: string } }
  parameters: string[]
  reads_high: string
  reads_low: string
  cannot_tell: string
  standard: string
  pack: boolean
  engines: string[]
}

/** A model's published characterisation (`data/verification/models/<hh>/<hash>.json`), as the part's file carries it. */
export interface ModelCharacter {
  hash: string
  polarity?: string
  runs: Record<string, 'ok' | 'failed'>
  codes: Record<string, string>
  /** measurement id → engine → output key → value; secondary engines hold only what differs from the primary. */
  values: Record<string, Record<string, Record<string, number | string | boolean | null | number[]>>>
  derived: Record<string, number | null>
  /** measurement id → curve name → y on the catalogue's grid, or [x, y] pairs. */
  curves: Record<string, Record<string, (number | null)[] | [number, number][]>>
  /** engine → the same, for the measurements on which that engine differs from the primary by more than 1 %. */
  other_curves?: Record<string, Record<string, Record<string, (number | null)[] | [number, number][]>>>
  /** measurement id → [largest spread, '1%' | '5%' | '>5%', engines compared, odd engine] */
  agree: Record<string, [number, string, string[], string | null]>
  decks: Record<string, { ids: string[]; analysis: string } & Record<string, unknown>>
  changes: Record<string, string[]>
  errors: Record<string, Record<string, string>>
}

/** `data/character/<PART>.json`: the characterised models by their place in the page's list. */
export interface CharacterFile {
  catalogue: string
  primary: string
  engines: Record<string, EngineRun & { cpu_s?: number }>
  models: Record<string, ModelCharacter>
}

export interface ModelCheck {
  family?: string
  absent?: string[]
  why?: Record<string, string>        // a parameter that is there but does nothing, and the value that makes it so
  default?: string[]                  // left at SPICE's own default: nobody fitted it
  extensions?: string[]               // physics beyond the family's own, from an extension the card carries
  geometry?: string                   // "default": a bare level 1–3 MOSFET card, W and L the simulator's
  thermal_pin?: boolean               // an electro-thermal subcircuit
  dialect?: string[]
  /** What the card declares of the part's ratings (LTspice's catalogue fields): vceo, icrating in SI units, mfg. */
  ratings?: Record<string, number | string>
  claims?: { yes?: string[]; no?: string[]; limits?: string[]; simulator?: string; lines?: [number, number][]; scope?: string }
}

export interface EngineRun {
  version: string | { exe: string; sha256: string }
  image: string
  bench: { commit: string; clean: boolean }
  on: string
}

/** What one page's use of the part was read as: a circuit, a technique, a table, an advert, a part
 *  named but not used, or a number that is not a component at all. */
export type UseKind = 'project' | 'technique' | 'reference' | 'advert' | 'mention' | 'none'

export type PageUse = [number, string, string, number] | [number, string, string, number, string, UseKind]

export interface PartPage {
  part: string
  /** The `PartIndex.sourcesStamp` this page's source positions refer to. */
  ss?: string
  docs: {
    /** Index into `PartIndex.sources`. */
    s: number
    t: string
    u: string
    y: string
    schematic: number
    /** page number, link, nearby designators, times on the page — then, once the page has been
     *  summarised, the line saying what the part does there and the kind of use it is. */
    p: PageUse[]
    more?: number
    also?: string[]
    /** Other titles the same file (same sha256) is published under. */
    aka?: string[]
  }[]
  /** Who vouches for this part: a shop that sells it, a databook, an article. */
  listed?: { source: string; category?: string; note?: string }[]
  /** `owner/repo`, sheets that place the part, then stars, forks and watchers. */
  repos?: [string, number, number, number, number][]
  /** Stars, forks and watchers of the repositories whose sheets are among `docs`, by `owner/name`. */
  stars?: Record<string, [number, number, number]>
  n: { documents: number; shown: number; copies: number; repos?: number }
  models?: {
    kind: string
    models: PartModel[]
    char?: CharacterSummary
    datasheet?: { url: string; maker?: string; doc?: string; date?: string }
  }
  /** What the part is, each piece present only when something says so. */
  about?: About
  /** What a search at each seller found, by seller id: result (found, not_found, unclear), the address followed, date. */
  sellers?: Record<string, [string, string, string]>
  /** What the part is, as the dictionary's id (`opamp`, `bjt`, `bjt/jfet/mosfet`), when something says. */
  kind?: string
  /** The devices of the parts menu it answers to, from `kind` or from what a model library says. */
  devices?: string[]
}

/** A part number read under the standard that assigned it: text, what the piece is, what it says. */
export interface NameReading {
  scheme: string
  label: string
  segments: [string, string, string][]
  caveats: string[]
  refs: string[]
  /** What the letters say it was designed for, to follow its kind: "for high frequency". */
  use?: string
}

export interface About {
  name?: NameReading
  /** The family, and what says so: a maker's sheet, the letters of the name, or the part's kind. */
  family?: [string, 'documented' | 'name' | 'kind']
  /** Which way round a transistor is, one row per source that says: polarity (NPN, PNP, N-channel,
   *  P-channel), what says it (the letters of its name, a model library, a maker's catalogue, a page found
   *  for it, the type it is a grade of), who — a scheme id, a census source, a maker id, the page's own
   *  words, the type — and a link to it. */
  polarity?: [string, 'name' | 'model' | 'catalogue' | 'sheet' | 'type', string, string][]
  documented?: { note: string; refs: string[]; status: 'draft' | 'reviewed' }
  /** Who published the sheet the models were measured against, and the organisations it descends from. */
  maker?: [string, string[]]
  /** What a manufacturer's catalogue says: source, maker id, category, status, data sheet title,
   *  revision, data sheet link, catalogue page, date read, and the product's own title where the page
   *  gives one instead of the data sheet's. */
  catalogue?: [string, string, string, string, string, string, string, string, string, string][]
  /** Every data sheet known: link, maker id, maker as the source writes it, title, where it came from
   *  ("models", a register or census source, an archive), a note (language, how the archive filed it). */
  /** link, maker id, maker as written, title, where it came from, a note, and an archived copy when the
   *  maker's own address refuses scripts. */
  sheets?: [string, string, string, string, string, string, string?][]
  /** Pages of databooks and device tables that print the part, in the same shape as `sheets`. */
  books?: [string, string, string, string, string, string, string?][]
  /** Catalogues that list the part today: census source, link. */
  listed?: [string, string][]
  /** The oldest dated document here that prints it: year, title, source position, link. */
  first?: [number, string, number, string]
  /** [relation, other part, "out" read from this part, "in" read from the other, "both" for a shared
   *  sheet; references; what the source says; draft or reviewed] */
  related?: [string, string, 'out' | 'in' | 'both', string[], string, 'draft' | 'reviewed'][]
  /** Sheets of other names that document this one too: the type it is a package, packing, grade or
   *  brand of, or a maker's name for a bare number (7812 -> L7812). [name, why, sheets] */
  kin?: [string, string, [string, string, string, string, string, string, string?][]][]
  /** The type this number is a grade or package of. */
  base?: string
  variants?: string[]
}

export interface Family {
  id: string
  label: string
  broader?: string
  definition: string
  question?: string
  key_params?: string[]
  examples?: string[]
  external?: string[]
  kinds?: string[]
  refs?: string[]
}

/** [year, what happened, the other organisation's id, source] */
export type MakerEvent = [number | null, string, string, string]

export interface Maker {
  name: string
  country?: string
  hq_as_of?: string
  founded?: number
  events?: MakerEvent[]
  source?: string
}

export interface SchemeField {
  label: string
  values?: Record<string, string>
  each?: Record<string, string>
  tokens?: Record<string, string>
  ranges?: [number, number, string][]
  meaning?: string
  first?: Record<string, string>
  optional?: boolean
}

export interface Scheme {
  label: string
  summary: string
  applies_to: string[]
  forms: { example: string; pattern: string }[]
  /** In the order the parts of a number are read. */
  fields: [string, SchemeField][]
  caveats?: string[]
  refs?: string[]
}

export interface Reference {
  title: string
  author: string
  url: string
  consulted: string
  link: string
}

export interface Catalogue {
  /** In the order of the file: broad before narrow, the way the menu reads. */
  families: Family[]
  makers: Record<string, Maker>
  schemes: Record<string, Scheme>
  refs: Record<string, Reference>
  listings: Record<string, { title: string; kind: string; maker: string }>
  sellers?: SellersList
}

/** One seller of parts (`data/distributors/sellers.yaml`): what it is, where it is based, what its
 *  catalogue covers, and, when it has one, the address of a search for a part number (`{part}`). */
export interface Seller {
  id: string
  title: string
  url: string
  type: string
  base: string
  group: string
  useful_for: string
  search?: string
  checked?: string
  /** The maintainer's order of first comparison: 1 first, 2 the usual, 3 last resort. */
  priority?: number
  /** The kinds of part its catalogue covers, when they differ from its group's; `[]` keeps it off part pages. */
  kinds?: string[]
  /** The makers it is the store of (ids of `Catalogue.makers`): shown first on those makers' parts. */
  makers?: string[]
  /** What its robots.txt said when read, and when: the technical permission to read it by script. */
  robots?: string
  robots_checked?: string
  /** What following `search` gave, and when. */
  search_checked?: string
  search_result?: string
  /** The seller's own account of itself, paraphrased, with where it was read and when. */
  about?: { url: string; checked: string; says: string }
  /** Where it ships, as its own pages say. */
  ships?: { text: string; url?: string; checked?: string }
  /** What readers of the forums say about it: links, dated, with the gist in the maintainer's words. */
  opinions?: { forum: string; title: string; url: string; date: string; gist: string }[]
}

/** A group of sellers: `kinds` are the kinds of part whose page lists the group (`[]`: none), and
 *  `caveat` a reference the page cites beside it. */
export interface SellerGroup { id: string; title: string; note: string; kinds: string[]; caveat?: string }

/** The sellers list: the kinds of seller in words, the groups in order, and the sellers. */
export interface SellersList { types: Record<string, string>; groups: SellerGroup[]; sellers: Seller[] }
