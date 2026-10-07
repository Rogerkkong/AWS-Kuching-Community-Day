# Pekeliling Navigator: architecture (FAST MODE)

Streamlit and plain Python modules. Everything runs in memory from CSV, JSON and Markdown files, so there is no
database, Docker or model download. Offline mode works with no LLM at all. The validity filter, citations, excluded
list, lineage, access control and verification queue all come from the build guide (sections 6 and 7).

## Modules (`mixup/`)

| Module | Owner | Purpose |
|---|---|---|
| `config.py` | Foundation | `Settings` from env/.env (`LLM_PROVIDER`, `MIXUP_TODAY`, paths, thresholds); `settings.current_date()` |
| `models.py` | Foundation | Dataclasses `Document, Page, Chunk, Relation, User, Hit, Citation, AskResponse` + status/relation/jurisdiction constants and BM/EN labels |
| `textutil.py` | Foundation | tokenizer (no Malay stemming), BM+EN stop-words, `detect_language`, glossary expansion, `find_refs` / `normalize_circular_no` |
| `ingest.py` | Foundation | `parse_bytes/parse_file` (.md/.txt sections, .pdf pages, .docx), `chunk_document` (clause-aware, breadcrumbs), `extract_metadata` (regex) |
| `relations.py` | Foundation | `load_relations_csv`, `extract_candidates` (regex + CANCEL/AMEND words), `classify_with_llm` (prompt B4) |
| `status.py` | Foundation | `compute_status`, `recompute_all`: the guide 7.3 rules |
| `access.py` | Foundation | **The only access choke point**: `visible_docs`, `can_see`, `get_doc`, `get_pages`, `get_chunks`, `filter_chunks`, `filter_docs`, `filter_relations`, `hidden_placeholder` |
| `store.py` | Foundation | `Store`: loads everything, `recompute()`, `add_document()`, `add_relations()`, `update_relation()`, runtime JSON helpers, `reset_runtime()` |
| `search.py` | Foundation | BM25 + glossary expansion + exact circular-number boost; status, clearance (always), jurisdiction and cluster filters; `citation_from_hit` |
| `llm.py` | Foundation | `OfflineLLM` (default), `OllamaLLM`, `BedrockLLM`; `make_llm`, `call_json` -> `(data, warning)` |
| `prompts.py` | Foundation | Appendix B prompts ANSWER, QUERY_REWRITE, METADATA, RELATION, CHANGE_SUMMARY + strict JSON schemas, refusal text |
| `ask.py` | A | Hero flow (stub now) |
| `lineage.py`, `changes.py`, `alerts.py` | B | Lineage graph, what-changed diff, subscriptions/notifications (stubs) |
| `admin.py` | C | Upload analyse/commit, verification queue (working regex-only stub) |
| `evaluate.py`, `analytics.py`, `logging.py` | D | Golden-set harness, dashboard data, append-only query log (stubs) |

UI (`ui/`): `common.py` (Foundation: `UIContext`, `LABELS`, badges, `source_card`, `show_source`), `library_tab.py`
(Foundation), and one `*_tab.py` per feature, each exposing `render(ctx)`. `app.py` holds the header, sidebar
(user switcher, BM/EN toggle, model mode, notification bell, Reset demo) and tabs. Each tab is wrapped so a
crash in one tab does not break the others.

## Data files

```
data/metadata.csv        manual metadata (always wins over regex); one row per document
data/relations.csv       verified ground-truth relations (R001..R009)
data/users.json          5 demo users (FED-T0, SWK-T0, FED-T1, OWNER, ADMIN)
data/glossary.json       BM<->EN pairs [{"ms","en"}]
data/golden_set.csv      (Feature D)
data/documents/*.md      synthetic corpus, watermarked SINTETIK - CONTOH SAHAJA
data/upload_demo/SPP-1-2026.md   live-ingestion demo file (not loaded at start)
data/runtime/            gitignored; cleared by Reset demo:
   uploads/<doc_id>/{doc.json, original file}, relations_pending.csv,
   notifications.json, subscriptions.json, query_log.jsonl, feedback.jsonl, change_cache.json, llm_cache/
```

Status flow: load metadata + files, then chunk, then add relations (csv verified + runtime pending), then
`status.recompute_all` (verified relations only), then BM25 index. Any verification calls `store.recompute()`.

## Feature interfaces (exact signatures)

```python
ask.ask(store, user, question, include_historical=False, mode="navigator"|"baseline") -> AskResponse
lineage.get_lineage(store, user, doc_id) -> {"nodes": [...], "edges": [...]};  lineage.to_dot(lineage) -> str
changes.what_changed(store, user, old_id, new_id) -> {"aligned": [...], "summary_ms", "summary_en",
                                                      "effective_date", "who_is_affected", "mode"}
alerts.subscribe(store, user_id, cluster=None, doc_id=None); alerts.notifications(store, user) -> list
alerts.on_new_relations(store, relations); alerts.mark_all_read(store, user)
admin.analyze_upload(store, filename, data) -> {"doc", "candidates", "pages", "warnings", "page_list", ...}
admin.commit_upload(store, analysis) -> doc_id;  admin.pending_relations(store)
admin.verify_relation(store, relation_id, approve, edits=None)
evaluate.run(store, golden_path) -> {"baseline", "navigator", "rows"};  analytics.summary(store, user) -> dict
logging.log_query(store, user, record) -> query_log_id;  logging.read_logs(store);  logging.add_feedback(...)
```

Foundation helpers the features use:

```python
store.search(user, q, k=10, statuses=DEFAULT_STATUSES|None, jurisdictions=None, prefer_jurisdiction=None,
             cluster=None, doc_types=None, doc_ids=None, expand=True, extra_queries=(), max_per_doc=None) -> [Hit]
search.citation_from_hit("S1", hit) -> Citation
llm.call_json(store.llm, system, prompt, schema) -> (dict | None, warning | None)   # None = use offline logic
store.docs / pages / chunks_by_doc / relations / users / glossary / today / llm
store.incoming(doc_id) / outgoing(doc_id) / verified_relations() / pending_relations() / doc_by_circular(no)
store.read_json / write_json / append_jsonl / read_jsonl (runtime files)
```

## Rules for feature code

1. Every path that returns content goes through `access` (or `store.search`, which applies it). Never rely on the
   LLM to hide anything. `tests/test_access.py` is the release blocker.
2. Default answers use only `DEFAULT_STATUSES` (IN_FORCE, AMENDED, UNKNOWN). CANCELLED and ONE_OFF appear only when
   "include historical" is on, and they are always labelled.
3. Document text is untrusted data. Prompts say so, and the code validates every `[S#]` citation.
4. If an LLM call fails, fall back to offline with a warning (`call_json` returns the warning).
5. Status is always shown as text plus colour (`ui.common.status_badge`).
