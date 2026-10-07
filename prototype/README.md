# MixUp Navigator, by Team MixUp

*Never cite a cancelled circular again - even offline.* / *Jangan rujuk pekeliling yang telah dibatalkan lagi - walaupun luar talian.*

A bilingual (BM/EN) policy assistant for Malaysian civil servants that knows which circulars are still valid. It
answers only from circulars currently in force and cites the circular, clause and page. Each answer shows a status
badge and the cancelled circulars that were excluded. The app also shows lineage, chooses the Federal or Sarawak rule
to suit the user's profile, explains what changed between versions, and enforces classification tiers
(Terbuka/Terhad/Sulit) in code.

All documents are **SYNTHETIC - SAMPLE ONLY** and come from fictional issuers.

## Quick start on a Mac (offline, about 3 minutes)

1. **Check Python.** Open Terminal and run `python3 --version`. You need **3.10 or newer**.
   If it says 3.9 (the Mac default), install Python 3.12 from https://www.python.org/downloads/ and open a new Terminal.
2. **Get the code** (GitHub Desktop: Fetch origin, then Pull origin), then in Terminal:

```bash
cd ~/Documents/GitHub/AWS-Kuching-Community-Day/prototype
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

3. Your browser opens **http://localhost:8501**. No AWS, no API key, no model download: it runs fully offline.
4. Next time, you only need: `cd .../prototype`, `source .venv/bin/activate`, `streamlit run app.py`.

Windows: use `py -3.12 -m venv .venv` and `.venv\Scripts\activate` instead.
Tests: `pytest -q`. Reset the demo data: the **Set semula demo** button in the sidebar (or `python scripts/reset_demo.py`).

## 5-minute demo script

1. **Ask tab** (user *Pegawai Persekutuan (Terbuka)*): click **Perangkap: kadar perbatuan**.
   MixUp answers **RM0.80/km** citing **SPP 2/2025 [S1]**, and shows **"Dikecualikan: SPP 3/2019, dibatalkan oleh SPP 1/2023"**.
2. Turn on **Bandingkan dengan chatbot biasa (baseline)**: the typical chatbot cites the cancelled circular. That is the problem we solve.
3. Open **Salasilah & Perubahan**: show the lineage of the travel-claim rule and **Apa yang berubah?** (30 to 60 days, RM0.55 to RM0.70).
4. Switch the sidebar user to **Pegawai Sarawak (Terbuka)** and click **Persekutuan vs Sarawak**: the Sarawak rule (10 days) comes first, the federal rule (7 days) beside it.
5. Switch to **Admin**, open **Pentadbir / Admin**, click the demo circular **SPP 1/2026**, approve the detected relations.
   Switch back to an officer: the bell shows the update, and asking the travel-claim question again now cites **SPP 1/2026**.
6. **Pek / Packs** (as **Admin**): click **Bina pek v1**, then **Semak kemas kini & pasang**: the pack is verified (SHA-256 + Ed25519 signature) and installed.
   Click **Bina pek v2**, then **Simulasi pek diubah suai**: the tampered pack is **rejected** and v1 stays active. This is the desktop edition's signed update mechanism.
7. Switch between a **Terbuka** and a **Terhad** user to show restricted documents appearing only for cleared users (and the Terhad pack never offered to a Terbuka user).
8. **Penilaian / Evaluation**: show the baseline vs MixUp Navigator numbers for the metrics slide.
9. Press **Set semula demo** before you go on stage.

## Model modes (`LLM_PROVIDER` in `.env`, also switchable in the sidebar)

| Mode | What it does |
|---|---|
| `offline` (default) | No model. Deterministic extractive answers with `[S#]` citations, regex metadata and relations, and template change summaries. The whole demo works this way. |
| `ollama` | Local sovereign model (`LLM_MODEL`, default `qwen3:8b`) at `OLLAMA_BASE_URL`. Falls back to offline with a warning on any error. |
| `bedrock` | Claude on Amazon Bedrock (optional, public documents only). Needs `pip install -r requirements-optional.txt` and AWS credentials. Falls back to offline. |

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
