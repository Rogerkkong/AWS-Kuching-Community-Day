# DECISIONS

Choices made while building, where the spec left room or where reality forced a change.

## Environment

* **D1. Repository root = project folder.** The brief's layout shows `pekeliling-navigator/`; this repo
  (`AWS-Kuching-Community-Day`) *is* that folder, so the layout starts at the repo root.
* **D2. `fake` inference backend (in addition to `ollama` and `llamacpp`).** The dev laptop had ~160 MB of
  free disk when work started, so Ollama (installer rolled back: "not enough space") and the models could
  not be installed. `INFERENCE_BACKEND=fake` gives deterministic hash embeddings (1024-dim) and extractive
  "answers" so the whole pipeline, the UI and the test-suite run without any model. It is clearly labelled
  in the UI ("fake-extractive"), packs built with it record the embedding model `fake-hash-1024`, and an
  Ollama-backed Officer app refuses them (rule 8). The real backends are unchanged and selected by env.
* **D3. Tests always use the fake backend** and never need a model or the network.

## Security

* **D4. Static UI files are served without the token**; every `/api/*` and `/health` request requires
  `X-Session-Token`. The HTML/JS bundle contains no data, and the token reaches the page via the window URL
  (`?token=`), is moved into memory and removed from the address bar. A Host-header check (127.0.0.1 /
  localhost only) blocks DNS-rebinding pages. No CORS middleware is installed.
* **D5. Restricted packs.** Clearance decides which installed packs are *opened*; the update checker only
  fetches tiers up to the highest clearance among the device's officer profiles (on a real device: the one
  officer). **In production, restricted packs are delivered only to cleared officers' devices and stored
  encrypted** (stretch goal; see README). Inside each pack every document/chunk query also carries
  `classification_level <= :clearance`.
* **D6. Status reasons never reveal higher-tier documents.** If a TERBUKA document were cancelled by a TERHAD
  one, the TERBUKA pack says "Dibatalkan oleh dokumen bertaraf keselamatan lebih tinggi". Relations and
  change summaries go into a tier's pack only when every document they touch is at or below that tier.
* **D7. Signature = Ed25519 over the ASCII hex SHA-256**, base64 in `manifest.json` and in a `.sig.json`
  sidecar next to each pack (the sidecar makes the USB / file-picker install possible).
* **D8. Private key location**: `workspace/keys/publisher_private.pem` (gitignored, never in the
  PyInstaller bundle). Public key: `app/resources/publisher_public.pem` (committed + bundled). A team that
  regenerates keys must commit the new public key.

## Ingestion and data

* **D9. Chunk = one numbered section** (heading + sub-clauses, e.g. clause_ref `4.1-4.3`). Real circular
  sections are 150-500 words; the synthetic ones are shorter, and merging unrelated sections to reach 150
  words would break clause-level citation, so structure wins over the word target. Sections > 500 words are
  split at sub-clause boundaries. Minutes: one chunk each for PERKARA / KEPUTUSAN / TINDAKAN, prefixed with
  the agenda item title so short decisions stay searchable.
* **D10. Embedding text = title + breadcrumb + chunk text** (stored text is unchanged).
* **D11. Sarawak references**: the brief's reference regex is used verbatim (series captured in a group);
  a second regex adds "Pekeliling Am Sarawak Bilangan n Tahun yyyy" (`PAS n/yyyy`). User questions use a
  looser regex ("PP 3/2018" without "Bil.").
* **D12. Reference number is read from the header block only** (first 10 lines), because bodies cite other
  circulars (e.g. PP 3/2018's PEMBATALAN clause cites SPP 5/2011).
* **D13. Synthetic corpus = 9 PDFs + 1 held back** (brief: 6-8). The extra allowance circular PP 1/2025 and
  the held-back PP 3/2026 give the live "pack v2" demo a real status change (IN_FORCE -> CANCELLED) that
  is independent of the leave chain. Chain: PP 3/2018 -SUPERSEDES-> by PP 2/2024 -AMENDS(6.1)-> by PP 5/2025.
* **D14. Rejected relations are kept with `verified = -1`** so re-ingesting a file does not re-queue them.
* **D15. Change summaries for AMENDS keep only the scoped clauses** (e.g. 6.1), aligned with the clause that
  carries the evidence sentence; SUPERSEDES aligns by clause_ref (if texts are >= 40% similar) then by
  embedding similarity >= 0.80; unmatched clauses are ADDED / REMOVED. `ingest/changes.py` holds this logic
  (not in the brief's layout).
* **D16. PDF only** (FR-01 mentions DOCX). DOCX can be converted to PDF before upload; noted as future work.

## Retrieval and answers

* **D17. Keyword list fetches 100 BM25 hits, then filters, then keeps 30** (the brief says LIMIT 30 then
  filter, which can starve the list when many hits are cancelled or restricted).
* **D18. Query references are expanded to their long form** ("PP 3/2018" -> "Pekeliling Perkhidmatan
  Bilangan 3 Tahun 2018"), because circulars cite each other that way; this is what lets the trap question
  find PP 2/2024's PEMBATALAN clause.
* **D19. Reranker order (RERANKER=auto)**: backend reranker (llama-server `/v1/rerank`), else
  sentence-transformers CrossEncoder if installed *and cached* (`local_files_only`, never downloads at
  runtime), else cosine similarity with the stored pack vectors. sentence-transformers is optional
  (`requirements-rerank.txt`, ~2.3 GB model + torch) because of the disk constraint.
* **D20. Source floor and excluded notice.** Passages below a per-reranker floor are not shown or sent to
  the model (an off-topic question gets an honest refusal with no fake sources). A cancelled document is
  listed as "Dikecualikan" only if it would have ranked in the top 10 *and* its reranker score reaches
  max(medium threshold, 0.6 x best selected score), so unrelated cancelled circulars are not shown.
* **D21. Jurisdiction conflict** requires strong rule passages from both jurisdictions, each within 75% of
  the top score. FEDERAL_SARAWAK documents count as "own" for both profiles. The question's explicit
  jurisdiction hint overrides the profile.
* **D22. Query rewrite runs with a timeout** (`QUERY_REWRITE_TIMEOUT`, default 8 s) in a worker thread and
  falls back to raw query + glossary; `QUERY_REWRITE_MODE=glossary` skips the LLM call entirely (fastest
  time-to-sources on slow CPUs). Regex refs, history words and the glossary are always applied.
* **D23. History detection avoids "lama"** alone (Malay "berapa lama" = "how long"); it needs "peraturan
  lama", "sebelum ini", "dibatalkan", "previous", etc.
* **D24. Refusal without calling the LLM** when no passage passes the floor; the LLM is also skipped when
  no pack is installed. Confidence is LOW for every refusal.

## Packs and updates

* **D25. Every tier gets a new pack per version** (v2 rebuilds TERBUKA and TERHAD), keeping versions aligned.
* **D26. Pack install keeps a copy** `pack-<tier>.prev.sqlite` and swaps with `os.replace` (atomic on the
  same volume); `/api/packs/rollback` restores it. A shared lock serialises installs with pack reads (Windows
  cannot replace an open file).
* **D27. No notifications on the first install** (everything would be "new"); afterwards officers are notified
  for followed clusters/circulars and for circulars they searched in the last 30 days. Demo profiles follow
  the `cuti` and `elaun` clusters.

## UI and packaging

* **D28. Lineage as a vertical timeline** (no @xyflow dependency).
* **D29. Fonts bundled with @fontsource**; a CSP meta tag limits the page to `'self'`.
* **D30. Library/notifications open documents in an inspector panel** (page image, lineage, what-changed)
  rather than separate routes; page images are fetched with the token header and shown as blob URLs.
* **D31. PyInstaller build is windowed** (`console=False`); `--smoke --smoke-out file` verifies a build.
* **D32. `scripts/dev_server.py`** runs the API in `--browser` mode on a fixed port with the fake backend for
  UI work; `--browser` also writes the tokenised URL to `<data dir>/dev-url.txt`.

## Evaluation

* **D33. BASELINE** = the same retrieval and model, but no status filter, no jurisdiction logic, no
  excluded list and status hidden from the prompt headers ("-"), i.e. a typical document chatbot that
  cannot know a circular was cancelled. Access control stays on for both (it is not an LLM property).
* **D34. Amendment injection.** When a selected passage belongs to an AMENDED document and a verified
  AMENDS relation's scope touches that clause (e.g. PP 5/2025 amends 6.1), the amending clause is placed
  right after it in the context, so the model sees the current wording even if the question shares no
  words with the amendment. Lifted citation accuracy on the golden set from 93% to 96% (fake backend).
* **D35. `scripts/reset_demo.py` archives instead of deleting**: Publisher DB, uploads, built packs and
  (with `--officer`) the Officer data folder are moved to `workspace/archive/<time>/`, then v1 is rebuilt.
* **D36. Golden set** has 42 questions (28 BM, 10 EN, 4 mixed): 11 normal (incl. one cleared TERHAD
  question), 10 trap_cancelled, 5 jurisdiction, 5 unanswerable, 3 access, 3 minutes, 5 action. The brief
  asks for ~50% BM / 30% EN / 20% mixed; add more English and mixed questions with the real corpus.
