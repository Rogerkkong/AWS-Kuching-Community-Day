# MixUp Navigator - web UI (`prototype/web/`)

Self-contained demo of the MixUp Navigator for AWS Student Community Day Kuching. A judge opens
`index.html` by double-clicking it (a `file://` URL). No server, no model, no network, no build step.

```
web/
  index.html    shell: <div id="app"> + three <script> tags (data.js -> engine.js -> app.js)
  styles.css    every inline style of design_ref/mockup_*.html, one class per element
  data.js       window.MX_DATA  (exported corpus; owned by the engine agent)
  engine.js     window.MX       (status engine, search, packs, publisher; owned by the engine agent)
  app.js        window.APP      (this UI: labels, renderers, event handling, Ask/install/build flows)
  README-UI.md  this file
```

Screenshots of every screen: `prototype/docs/screenshots/web-*.png` (taken with Playwright from the
`file://` URL at 1520x980, the same preview size as the mockup).

## How the UI is built

* **One render function.** `APP.render()` rebuilds the whole 1440x900 window frame from the current
  state (`S` in app.js + `MX.state`). Every click goes through one delegated listener and a `data-act`
  attribute (`ACT` table), so there are no inline handlers. Scroll positions of panels marked
  `data-scroll` survive re-renders.
* **Design is the teammate's mockup, 1:1.** `styles.css` is the mockup's inline styles turned into
  classes with the same values (colours, paddings, font sizes, radii, shadows). Status colours:
  IN_FORCE `#1E6B41/#E2F0E7`, AMENDED `#7A4F00/#FAEDD0`, CANCELLED `#9A241C/#F7E0DC`,
  UNKNOWN/ONE_OFF `#50565D/#ECECEA`. Fonts fall back to system fonts (`IBM Plex Sans` is used only if
  installed).
* **Bilingual.** The `L` table at the top of app.js holds every UI string as `[ms, en]`; `t(key)` picks
  the current `MX.state.lang`. Keys not in `L` fall through to `MX.t(key)`. The BM/EN switch is in the
  title bar. Answer language follows the question (the engine detects it).
* **Honest status bar.** `Network: offline · Engine: in-browser · ready · Terbuka pack v3 ...`. The UI
  never claims a model or an API.
* **Fallback stub.** If `engine.js` is missing, `makeStub()` at the bottom of app.js installs a small
  placeholder `MX` with six synthetic circulars so the page still renders (the status bar then says
  "engine.js not loaded - placeholder data"). It is for development only.

## Screens

Officer mode: **1 Ask**, **2 Circulars**, **3 Updates**. Publisher mode: **1 Circulars** (upload +
verification queue), **2 Build packs**, **3 Evaluation**, **4 Analytics**.

* **Ask** - headline, TRY cards (hero, trap, jurisdiction, mixed, unanswerable), input, "Include
  historical" and "Compare with a typical chatbot" toggles. After a question: QUESTION, status line,
  red "Excluded from this answer" card, white answer card with `[S#]` chips, confidence chip, real
  timings (`Sources` = engine `timing_ms`, `complete` = wall time to the end of rendering), feedback
  buttons, the "rule differs by jurisdiction" cards, and the baseline card (red WRONG tag when it cites
  a cancelled circular). Right panel: Sources | Page (page text with the cited passage highlighted,
  prev/next page) | Lineage (timeline with evidence quotes and "What changed:" summaries).
* **Circulars** - filter chips (status, jurisdiction) + table; a row opens a Page | Lineage drawer.
  Only documents the user may see are listed.
* **Updates** - the mockup's update-channel card with the 7 install steps that tick as
  `MX.packs.install` resolves (650 ms per step, like the mockup), "Simulate tampered pack" (step 3
  fails, previous version stays), the "What changed v3 -> v4" card and the INSTALLED PACKS cards.
  The amber "Update available" banner shows on the other officer screens while an update is pending.
* **Publisher / Circulars** - upload (`.md`/`.txt`) or "Use demo circular SPP 1/2026" -> analysis card
  (extracted metadata + detected relations with evidence) -> "Add to library" -> verification queue
  (Verify / Reject). Statuses only change after verification.
* **Publisher / Build packs** - tier cards, "Included since vN", version input + "Build packs vN"
  (6 animated steps), then the manifest table (tier, version, file, sha256, signature, documents).
* **Publisher / Evaluation** - headline sentence, Baseline vs MixUp Navigator metrics table, per-type
  table, "Run in browser" (re-asks the golden set through `MX.evaluation({run:true})`).
* **Publisher / Analytics** - stat cards + top questions + cancelled circulars most often excluded.
* **Sidebar** - Officer | Publisher switch, numbered nav with badges, Offline card, the discreet
  "SINTETIK - CONTOH SAHAJA" note with the "Reset demo" link, and the profile card that opens
  "Switch officer (demo)".

## MX functions the UI calls (engine contract)

| Call | Used by |
|---|---|
| `MX.init()`, `MX.reset()` | boot, Reset demo |
| `MX.state` (`lang`, `mode`, `includeHistorical`) | read + written directly by the UI |
| `MX.data.documents / relations / users` | lookups (circular number by doc_id, user list, relation counts) |
| `MX.setUser(id)`, `MX.currentUser()` | profile card, Switch officer |
| `MX.t(key)` | fallback for labels not in app.js |
| `MX.ask(q, {baseline})` | Ask flow (navigator + typical-chatbot comparison) |
| `MX.library({status, jurisdiction})` | Circulars table (the UI also filters client-side) |
| `MX.document(doc_id)` | Page viewer |
| `MX.lineage(doc_id)`, `MX.whatChanged(old, new)` | Lineage tab (summary per pair) |
| `MX.packs.checkUpdates()`, `.installed()`, `.manifest()` | banner, nav badge, Updates, Build, status bar |
| `MX.packs.install(entry, {tamper})` (async) | Install button, Simulate tampered pack |
| `MX.packs.build(version)` (async) | Build packs |
| `MX.publisher.demoUploadText()`, `.analyzeUpload(name, text)`, `.commitUpload(analysis)` | upload area |
| `MX.publisher.pending()`, `.verify(id, approve)` | verification queue, nav badge |
| `MX.notifications()`, `MX.markRead()` | Notifications pill + popover |
| `MX.evaluation()`, `MX.evaluation({run:true})` | Evaluation screen |
| `MX.analytics()` | Analytics screen |

Field names the UI reads defensively (several spellings accepted, see `pick()` / `bi()` in app.js):
pack entries (`tier`, `version`, `file`, `size_bytes`, `sha256`, `signature`, `documents`,
`installed_at`, `previous_version`, `new_documents`, `status_changes`), notifications (`kind`,
`title`/`title_ms`/`title_en`, `body`, `read`), install steps (`label_ms`, `label_en`, `detail`, `ok`),
install diff (`added`, `status_changes[{doc_id, from, to, reason}]`), evaluation (`baseline`,
`navigator` metric objects or a `metrics` row array; `by_type` as array or object).

## Testing

```
/tmp/diagram-venv/bin/python -I <scratch>/shoot.py     # walks every screen via file:// and saves docs/screenshots/web-*.png
```
Open `index.html` directly in Chrome or Safari; nothing is fetched, so `file://` works.
