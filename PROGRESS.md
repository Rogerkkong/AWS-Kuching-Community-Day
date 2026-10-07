# PROGRESS

## Environment note (7 Oct 2026)
The dev laptop's only drive was full (about 160 MB free), so the Ollama installer rolled back and
`qwen3:4b` / `bge-m3` could not be pulled. Everything below was built and verified with the deterministic
`fake` backend (DECISIONS D2). The Ollama and llama.cpp backends are implemented but not yet run against
real models. M1-M7 were developed in one pass and committed together, after the full test-suite passed.

## M1 Skeleton
- FastAPI app factory on 127.0.0.1 (free port) with a session-token ASGI middleware, a Host check and no CORS; `/health` reports the backend, models, warm-up state and installed packs.
- Inference client with `ollama`, `llamacpp` (stretch, implemented) and `fake` backends; background warm-up.
- pywebview launcher (`python -m app.desktop`), `--browser` dev mode and `--smoke` check; React + Tailwind shell with bundled IBM Plex fonts, matching the design prototype.
- PyInstaller one-folder smoke build: `scripts/package_windows.py` -> 107 MB folder; the packaged exe passes `--smoke` (sqlite-vec loads).

## M2 Publisher ingestion
- 9 synthetic watermarked Malay PDFs + 1 held back (`scripts/make_synthetic_docs.py`): leave chain PP 3/2018 -> PP 2/2024 -> PP 5/2025, Federal/Sarawak pair, SOP, two minutes, one TERHAD guideline.
- PyMuPDF parsing with OCR fallback (graceful when Tesseract is missing); regex + LLM + metadata.csv metadata; structure-aware chunker (sections, minutes on PERKARA/KEPUTUSAN/TINDAKAN); embeddings into publisher.db.
- Publisher documents page: upload, ingestion log, metadata editor.

## M3 Packs v1
- Ed25519 keys (`scripts/make_keys.py`), per-tier packs with manifest, FTS5 (unicode61 remove_diacritics 2), trigram docs, vec0 float[1024], PDFs; sha256 + signature + sidecar `.sig.json`; dist_packs/manifest.json.
- Officer install from the update folder or from file, verification (checksum, signature, manifest, embedding model), atomic swap with a rollback copy.

## M4 Retrieval
- Query rewrite (QUERY_REWRITE prompt with timeout + glossary + long-form circular refs), clearance-gated pack opening, vector + BM25 + trigram lists fused with RRF k=60, rerank (backend / CrossEncoder / cosine fallback), source floor.
- Access-control tests: a TERBUKA session never opens the TERHAD pack and never sees its content (search, excluded, documents, lineage, diff, page images).

## M5 Answers
- SSE `/api/ask`: sources event first, then tokens, then final; streaming parser for "ANSWERABLE" + "ACTIONS:"; citation validator; refusal; LLM-failure warning; confidence.
- Ask page with chips, "Apa perlu saya buat?" box, badges, excluded notice, feedback; source viewer rendering the PDF page from the pack with the passage highlighted.

## M6 Validity
- Relation extraction (brief regex + Sarawak extension, trigger words, RELATION prompt, ground truth from relations.csv), verification queue (approve/reject/edit/undo), status engine with every rule incl. RECORD, change summaries (clause alignment + difflib + CHANGE_SUMMARY), lineage timeline.

## M7 Updates and jurisdiction
- Live flow verified in the UI: Publisher uploads PP 3/2026 -> verifies "SUPERSEDES PP 1/2025" -> builds v2 -> Officer checks, verifies and installs it -> 2 notifications -> what-changed clause diff.
- Demo user switcher (Federal TERBUKA, Sarawak TERBUKA, Federal TERHAD); Sarawak profile gets PAS 4/2023 first with the Federal rule "for comparison"; grade and scheme go into the prompt.
- 60 tests pass (`pytest -q`, about 8 s).
