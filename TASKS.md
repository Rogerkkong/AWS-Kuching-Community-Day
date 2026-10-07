# TASKS

Work top to bottom. Tick a box only when its "done when" check passes. After each milestone: run the
app, commit ("M<n>: <name>"), add 3-5 lines to PROGRESS.md.

## M1 Skeleton
- [x] Repo hygiene: .gitignore, .env.example, requirements.txt, SPEC/TASKS/CLAUDE/DECISIONS/PROGRESS. *Done when* files exist and `git status` shows no venv/node_modules.
- [x] `app/config.py` (env + platformdirs paths, thresholds, PN_TODAY override). *Done when* `python -c "import app.config"` prints paths.
- [x] `app/security.py`: token middleware (X-Session-Token on /api/* and /health), Host check, no CORS. *Done when* `tests/test_security.py` passes (no token -> 401, wrong host -> 400, good token -> 200).
- [x] Inference client with `ollama`, `fake` and `llamacpp` (stub) backends; `/health` reports backend reachable + model status. *Done when* `tests/test_inference_fake.py` passes and /health JSON shows backend status.
- [x] `app/main.py` app factory serving `ui/dist` statics + API. *Done when* TestClient GET / returns the shell HTML.
- [x] React shell (Vite + TS + Tailwind, bundled IBM Plex fonts, sidebar, header with offline indicator, token kept in memory). *Done when* `npm run build` writes ui/dist and the shell renders.
- [x] `app/desktop.py`: --mode, free port, token, Uvicorn thread on 127.0.0.1, wait for /health, pywebview window, background warm-up. *Done when* `python -m app.desktop --smoke` starts, health OK, exits 0.
- [x] README run steps. *Done when* a fresh reader can install and launch.
- [x] Smoke PyInstaller one-folder build. *Done when* `dist/PekelilingNavigator/PekelilingNavigator.exe --smoke` exits 0.

## M2 Publisher ingestion
- [x] `scripts/make_synthetic_docs.py`: 9 watermarked Malay PDFs in data/raw + 1 held-back circular in data/incoming (3-step chain, Federal/Sarawak pair, SOP, 2 minutes, 1 TERHAD). *Done when* PDFs open and every page shows "SINTETIK - CONTOH SAHAJA".
- [x] data/metadata.csv, data/relations.csv, data/glossary.json. *Done when* loaders parse them in tests.
- [x] `app/db.py`: publisher.db schema + app.db schema + pack schema helpers, sqlite-vec loader, version check (>= 3.34). *Done when* schema creation test passes.
- [x] `ingest/parse.py` (PyMuPDF per page, OCR fallback < 30 chars) + `ocr.py` (Tesseract msa+eng, graceful if missing). *Done when* parse test returns page-numbered text.
- [x] `ingest/metadata.py`: regex (numbers, Malay dates, headings) -> METADATA prompt -> metadata.csv override. *Done when* test extracts circular_no / dates from synthetic text.
- [x] `ingest/chunker.py`: numbered paragraphs, headings, minutes PERKARA/KEPUTUSAN/TINDAKAN, breadcrumb, pages, 150-500 words. *Done when* chunker tests pass.
- [x] `ingest/embed.py`: batch embeddings -> chunk_vectors. *Done when* vectors stored with dim 1024.
- [x] `scripts/ingest_folder.py` + Publisher document list endpoint/UI. *Done when* ingesting data/raw fills publisher.db and the Publisher UI lists documents.

## M3 Packs v1
- [x] `scripts/make_keys.py` (Ed25519; private key in workspace/keys, public key in app/resources). *Done when* keys exist and private key is gitignored.
- [x] `packs/build.py` + `packs/sign.py`: per-tier pack with manifest, FTS5, trigram, vec0, files; VACUUM; sha256 + signature; dist_packs/manifest.json; sidecar .sig.json. *Done when* `scripts/build_pack.py --version 1` writes both tiers and manifest.
- [x] `packs/verify.py` + `packs/install.py`: verify sha256, signature, embedding model; atomic install with rollback copy. *Done when* tamper/bad-signature/model-mismatch tests pass and old version stays active.
- [x] Officer packs endpoints (GET /api/packs, POST check/install/install-file) + Packs page. *Done when* Officer installs v1 from dist_packs in the UI.

## M4 Retrieval
- [x] `retrieval/rewrite.py` (QUERY_REWRITE + glossary, fallback). *Done when* test with fake backend returns ms/en queries and refs.
- [x] `retrieval/filters.py` (clearance -> packs, statuses). *Done when* unit test covers TERBUKA/TERHAD and historical.
- [x] `retrieval/hybrid.py` (vector, keyword, trigram, RRF k=60, excluded list, jurisdiction). *Done when* hero question returns PP 2/2024 in top 5.
- [x] `retrieval/rerank.py` (CrossEncoder if available, else embedding cosine fallback; top 5; 250-word trim). *Done when* rerank test passes.
- [x] Access-control test: TERBUKA never opens TERHAD pack, never gets TERHAD content from search/excluded/lineage/diff/page images. *Done when* test passes.

## M5 Answers
- [x] prompts.py with the five prompts verbatim. *Done when* file matches brief.
- [x] `generation/stream.py` splitter (ANSWERABLE line, ACTIONS marker across tokens). *Done when* splitter tests pass.
- [x] `generation/citations.py` validator + ACTIONS parsing. *Done when* citation/actions tests pass.
- [x] `generation/answer.py` + POST /api/ask SSE (sources -> token -> final, refusal, LLM failure warning, confidence). *Done when* SSE test shows event order and refusal path.
- [x] Ask page: sources first, streamed answer with chips, decision box, badges, confidence, excluded notice, historical toggle, feedback. *Done when* hero question works in the window.
- [x] Source viewer: page PNG with highlight + metadata panel. *Done when* clicking [S1] shows highlighted page.

## M6 Validity
- [x] `ingest/relations.py` regex + keyword filter + RELATION prompt + target resolution + relations.csv. *Done when* regex tests pass and candidates stored unverified.
- [x] `validity/status.py` every branch incl. RECORD, with reasons. *Done when* status tests pass.
- [x] Change summaries (clause align + difflib + CHANGE_SUMMARY). *Done when* chain pairs have summaries.
- [x] Publisher verification queue (approve/reject/edit) + metadata editor. *Done when* approving a relation recomputes status.
- [x] `validity/lineage.py` + lineage endpoint + timeline view; excluded notice in Ask. *Done when* lineage of PP 2/2024 shows PP 3/2018 -> PP 2/2024 -> PP 5/2025.
- [x] Rebuild packs. *Done when* officer pack shows correct statuses.

## M7 Updates and jurisdiction
- [x] Publisher upload of held-back circular -> verify -> Build packs v2. *Done when* manifest lists v2.
- [x] Check updates (folder or http URL), verify, install, rollback copy. *Done when* officer installs v2 via UI.
- [x] `packs/diff.py` -> notifications (subscriptions + recent searches) + banner + bell. *Done when* diff test yields expected notifications.
- [x] What-changed view (/api/diff, clause diff + BM/EN summaries). *Done when* view renders for the v2 pair.
- [x] User switcher, Federal/Sarawak comparison panel, grade + scheme in the prompt. *Done when* Sarawak profile sees PAS rule first with comparison panel.

## M8 Analytics and evaluation
- [ ] Query logging + feedback. *Done when* each ask writes a query_logs row.
- [ ] Anonymised export + Publisher import + dashboard. *Done when* imported report shows on the dashboard; export test checks no names, hour-rounded timestamps.
- [ ] data/golden_set.csv (30+ questions) + `scripts/evaluate.py` (baseline vs navigator). *Done when* summary.md and results.csv are written with access leaks = 0.

## M9 Packaging and polish
- [ ] Offline end-to-end ask test with pytest-socket (only 127.0.0.1). *Done when* test passes.
- [ ] BM/EN strings, loading and error states, setup screen. *Done when* every label exists in both languages.
- [ ] PyInstaller one-folder build (`scripts/package_windows.py`). *Done when* built exe runs from its folder with network off.
- [ ] README demo script. *Done when* the hero flow can be run from the README.

## Stretch
- [ ] llamacpp backend with bundled llama-server.
- [ ] Inno Setup installer (packaging/installer.iss).
- [ ] Encrypted restricted packs.
