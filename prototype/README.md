# Pekeliling Navigator, by Team MixUp

*Never cite a cancelled circular again.* / *Jangan rujuk pekeliling yang telah dibatalkan lagi.*

A bilingual (BM/EN) policy assistant for Malaysian civil servants that knows which circulars are still valid. It
answers only from circulars currently in force and cites the circular, clause and page. Each answer shows a status
badge and the cancelled circulars that were excluded. The app also shows lineage, chooses the Federal or Sarawak rule
to suit the user's profile, explains what changed between versions, and enforces classification tiers
(Terbuka/Terhad/Sulit) in code.

All documents are **SYNTHETIC - SAMPLE ONLY** and come from fictional issuers.

## Run (offline, no setup beyond pip)

```bash
cd prototype
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py                                     # http://localhost:8501
pytest -q                                                # tests
python scripts/reset_demo.py                             # clear data/runtime (same as the Reset demo button)
```

## Model modes (`LLM_PROVIDER` in `.env`, also switchable in the sidebar)

| Mode | What it does |
|---|---|
| `offline` (default) | No model. Deterministic extractive answers with `[S#]` citations, regex metadata and relations, and template change summaries. The whole demo works this way. |
| `ollama` | Local sovereign model (`LLM_MODEL`, default `qwen3:8b`) at `OLLAMA_BASE_URL`. Falls back to offline with a warning on any error. |
| `bedrock` | Claude on Amazon Bedrock (optional, public documents only). Needs `anthropic[bedrock]` and AWS credentials. Falls back to offline. |

## Demo data (synthetic)

| Item | Documents |
|---|---|
| 3-step chain (travel claims) | SPP 3/2019 (30 days, RM0.55/km) **cancelled by** SPP 1/2023 (60 days, RM0.70/km, e-Tuntutan), which is **amended (para 4.2)** by SPP 2/2025 (RM0.80/km) |
| Federal vs Sarawak (child care leave) | PP 4/2024 (Federal, 7 days) vs PAN 2/2024, Pekeliling Am Negeri Bil. 2/2024 (Sarawak, 10 days) |
| Supersession (annual leave) | PP 2/2018 (carry forward 15 days) superseded by PP 3/2024 (20 days, Federal and adopted by Sarawak) |
| One-off | SE 1/2021, temporary WFH during the emergency |
| Current WFH | GP 1/2025, hybrid work up to 2 days a week |
| Cloud (English) | GP 1/2022 superseded by GP 2/2025 (Cloud-First) |
| Restricted | SOP 1/2025 (TERHAD, audit thresholds) and PKP 1/2025 (SULIT, backup data centre) |
| Minutes | MINIT 3/2025 |
| Live upload | `data/upload_demo/SPP-1-2026.md` cancels SPP 1/2023 and SPP 2/2025 (90 days, RM0.85/km) |

To freeze "today" for rehearsals, set `MIXUP_TODAY=2026-10-07`. See `ARCHITECTURE.md` for the modules and interfaces.
