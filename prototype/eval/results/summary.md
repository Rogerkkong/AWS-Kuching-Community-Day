# Evaluation: Baseline (plain RAG) vs MixUp Navigator

Generated 2026-10-07T05:02:21+00:00 | status date (today) 2026-10-07 | model mode: **Offline** | 30 golden questions (15 BM, 9 EN, 6 mixed) | 14 synthetic documents

**Headline:** on trap questions about cancelled or replaced rules, the baseline presented a stale circular as current in 91.7% of cases (11/12); the Navigator in 0.0% (0/12). Correct and current answers: baseline 13/30, Navigator 25/30. Access leaks: baseline 0, Navigator 0.

| Metric | Baseline (plain RAG) | Navigator | Target |
|---|---|---|---|
| Correct & current answers | 43.3% (13/30) | 83.3% (25/30) | - |
| Cancelled-citation rate | 91.7% (11/12) | 0.0% (0/12) | <= 5% |
| Recall@5 | 100.0% | 100.0% | >= 0.80 |
| MRR | 0.758 | 0.977 | >= 0.60 |
| Citation accuracy | 45.5% | 81.8% | >= 0.85 |
| Jurisdiction accuracy | 60.0% | 100.0% | - |
| Refusal accuracy | 87.5% | 87.5% | >= 0.80 |
| False-refusal rate | 9.1% | 13.6% | - |
| Access leaks | 0 | 0 | 0 |
| Latency p50 | 5.2 ms | 7.5 ms | <= 8 s |
| Latency p95 | 7.4 ms | 10.9 ms | <= 15 s |

## By question type (correct and current)

| Type | n | Baseline | Navigator |
|---|---|---|---|
| normal | 5 | 3 | 3 |
| trap_cancelled | 12 | 0 | 10 |
| jurisdiction | 5 | 3 | 5 |
| unanswerable | 5 | 4 | 4 |
| access | 3 | 3 | 3 |

## Navigator misses (reported honestly)

- **G04** (trap_cancelled, FED-T0) Adakah borang kertas JPC-TP1 masih boleh digunakan untuk tuntutan perjalanan? - refused (answer exists)
- **G07** (trap_cancelled, FED-T0) Berapa hari awal perlu apply cuti rehat? - primary citation PP-3-2024 3.3 [IN_FORCE] (expected PP-3-2024 3.2)
- **G20** (unanswerable, FED-T0) Apakah syarat kelayakan cuti tanpa gaji? - answered (should refuse)
- **G29** (normal, FED-T0) Apakah dokumen sokongan yang diperlukan untuk memohon cuti penjagaan anak? - refused (answer exists)
- **G30** (normal, FED-T1) What is the threshold for automatic internal audit of travel claims? - refused (answer exists)

## Where the baseline cited a stale rule as current

- **G01** Berapakah tempoh untuk mengemukakan tuntutan elaun perjalanan? - SPP-3-2019 4.1 [CANCELLED]
- **G02** What is the current mileage rate for using my own car on official duty? - SPP-3-2019 4.2 [CANCELLED]; SPP-1-2023 4.2 [AMENDED]
- **G03** Is the RM0.55 per km mileage rate still valid? - SPP-3-2019 4.2 [CANCELLED]
- **G04** Adakah borang kertas JPC-TP1 masih boleh digunakan untuk tuntutan perjalanan? - SPP-3-2019 4.3 [CANCELLED]
- **G05** Adakah resit digital diterima untuk tuntutan perjalanan? - SPP-3-2019 4.4 [CANCELLED]
- **G06** Berapa hari maksimum cuti rehat yang boleh dibawa ke tahun berikutnya? - PP-2-2018 3.1 [CANCELLED]
- **G08** Can we store Terhad information in a public cloud? - GP-1-2022 3.1 [CANCELLED]; GP-1-2022 3.2 [CANCELLED]
- **G09** Berapa lama Chief Digital Officer ambil masa untuk decide permohonan cloud? - GP-1-2022 3.3 [CANCELLED]
- **G10** Berapa hari seminggu pegawai boleh bekerja dari rumah? - SE-1-2021 3.1 [ONE_OFF]
- **G11** Boleh saya work from home 5 hari seminggu macam masa darurat dulu? - SE-1-2021 3.1 [ONE_OFF]
- **G12** Boleh saya claim mileage guna kereta sendiri untuk outstation? Berapa rate dia? - SPP-3-2019 4.2 [CANCELLED]; SPP-1-2023 4.2 [AMENDED]
- **G16** Saya pegawai negeri Sarawak. Berapa hari cuti rehat boleh carry forward ke tahun depan? - PP-2-2018 3.1 [CANCELLED]

## Method

- **Corpus:** synthetic documents only (watermarked SINTETIK - CONTOH SAHAJA, fictional issuers): a 3-step travel-claim chain (SPP 3/2019 cancelled by SPP 1/2023, amended by SPP 2/2025), Federal vs Sarawak child-care leave, annual leave (PP 2/2018 replaced by PP 3/2024), a one-off emergency WFH instruction, a current hybrid-work guideline, a cloud guideline pair in English, and one TERHAD and one SULIT document.
- **Golden set:** `data/golden_set.csv`, written by Team MixUp from those documents (Appendix C format): 5 normal, 12 trap_cancelled, 5 jurisdiction, 5 unanswerable, 3 access. Each row names the user profile (FED-T0, SWK-T0, FED-T1), the expected document and clause, and the circulars that must not be cited as current.
- **Model mode:** Offline. In offline mode answers are deterministic and extractive (BM25 + bilingual glossary retrieval, no LLM), so the run is repeatable.
- **Baseline:** the same retrieval and answer step (`ask(..., mode="baseline")`) with no status filter, no jurisdiction logic, no amendment handling and no excluded list: what a typical document chatbot does. The clearance filter lives in the search layer, so it applies to both systems; access leaks are checked independently (restricted doc ids, circular numbers, titles and any 5-word phrase found only in restricted documents).
- **Definitions:** Recall@5 and MRR use the rank of the first passage from the expected document. Citation accuracy needs the primary citation [S1] to be the expected document and clause. Cancelled-citation rate counts trap questions where a must_not_cite document (or amended clause) is cited without a historical/amended label. Correct & current = right document and clause, answer keywords present, nothing stale presented as current, no leak; for unanswerable and access questions, a refusal.
- **Isolation:** each run uses a private copy of the base corpus with an empty runtime folder, so live uploads and the demo query log do not affect the numbers, and the run does not appear in Analytics.
- **Self-measured** by Team MixUp on a laptop (latency includes retrieval and answer generation only). The golden set is small, so treat the numbers as indicative, not as a benchmark.
- **Reproduce:** `python scripts/evaluate.py` (writes this file, `results.csv` and `results.json`).
