# Problem Explainer: Government Knowledge Search

A plain-English guide to our problem statement, what Malaysia already has, and recent news we can use in the pitch.

> Collected on 7 October 2026 from web searches of credible outlets (NST, FMT, Berita Harian, RTM, Borneo Post, ISEAS, official press releases). Items are being double-checked by our news-verification step before they go on slides; see `research/06-malaysia-news.md` when it is ready.

## 1. The problem in plain words

Government officers must follow thousands of written rules. Finding the right one, **and knowing it is still valid**, is hard.

**Types of documents**

| Type | Malay term | Example |
|---|---|---|
| Circular | *Pekeliling* | "Claims must be submitted within 60 days" |
| SOP | *Prosedur Operasi Standard* | Step-by-step for approving leave |
| Guideline | *Garis panduan* | How to share data between agencies |
| Policy | *Dasar* | Cloud-first, hybrid work |
| Meeting minutes | *Minit mesyuarat* | "Decision: adopt X. Action: Unit Y by 30 June" |
| Reports | *Laporan* | Annual reports, audit findings |

**Why it is hard**

1. **Volume.** Thousands of documents spread across portals, shared drives and email.
2. **Rules change.** A new circular cancels or amends an old one ("*Pekeliling ini membatalkan Pekeliling Bil. 3/2021*"), but the old file stays in folders, so people follow outdated rules.
3. **Two languages.** Documents are in Bahasa Malaysia, English or a mix. A keyword search in one language misses the other.
4. **Jargon and numbering.** Titles like "SPP Bil. 2 Tahun 2024" mean little to new staff.
5. **Scanned PDFs.** Many older documents are images, so their text cannot be searched.
6. **Sensitive data.** Some documents are classified (*Terhad*, *Sulit*), so they cannot simply be uploaded to a public AI tool.
7. **Knowledge loss.** When experienced officers transfer or retire, "where is that rule?" goes with them.

**Result:** slower decisions, wrong answers given to the public, and duplicated work, which is exactly what the problem statement describes.

## 2. What Malaysia already has, and the gap

| Already exists | What it does | What is missing |
|---|---|---|
| **DDMS 2.0** (MAMPU with the National Archives) | Digital storage and records management for government files | It **stores** files; it does not **answer** "what is the current rule?" |
| **MyPPSM / ePekeliling** (JPA) | Portal listing service circulars | Users still search and read manually; relationships between rules are not clear |
| **AI at Work 2.0** (Gemini and NotebookLM for civil servants) | General AI for drafting and summarising | General-purpose: does not know which circular is in force; not suitable for classified documents |

**The gap:** nothing tells an officer "this is the current valid rule, here is exactly where it says so, and here is what it replaced." Our teammates' research PDFs reached the same conclusion.

## 3. Recent news

### AI in the Malaysian civil service

- **Feb 2025:** the government gave **445,000 public officers** access to Google's Gemini AI under *AI at Work 2.0*.
  [FMT](https://fmtv5.freemalaysiatoday.com/category/nation/2025/02/05/malaysia-rolls-out-generative-ai-tool-to-445000-civil-servants) ·
  [Google Cloud press release](https://www.googlecloudpresscorner.com/2025-02-05-445,000-Public-Officers-in-Malaysia-to-Benefit-from-Generative-AI-Under-the-AI-at-Work-2-0-Initiative-by-the-Ministry-of-Digital-and-Google-Cloud)
- **Pilot result:** 270 officers took part, and **97% reported saving about 3.25 hours per week**.
  [NST](https://www.nst.com.my/amp/news/nation/2025/02/1181313/ai-work-20-saves-civil-servants-325-hours-week)
- **Dec 2024:** the **National AI Office (NAIO)** was launched under the Ministry of Digital.
  [The Sun](https://thesun.my/malaysia-news/naio-marks-first-100-days-in-driving-malaysia-s-ai-transformation-HJ13837257) ·
  [NAIO](https://www.ai.gov.my/media/news-details/220325-naio-marks-100-days-revised.pdf)

### Circulars are being reviewed and replaced right now (our strongest "why now")

- **2026:** JPA is reviewing **circulars, regulations and guidelines older than 20 years** as part of bureaucracy reform.
  [RTM](https://berita.rtm.gov.my/nasional/senarai-berita-nasional/senarai-artikel/jpa-teliti-peraturan-sedia-ada-kurangkan-birokrasi/) ·
  [Berita Harian](https://www.bharian.com.my/amp/berita/nasional/2026/02/1508682/bhplus)
- The **Government Service Efficiency Commitment Act 2025 (Act 867)** requires these reviews **every 3 years**. Reports say it took effect on 1 December, which would be 1 December 2025 (to be confirmed by our news check).
- **What it means:** rules will change more often, so "which version is valid?" becomes a bigger problem every year.

### Sarawak

- **Mar 2026:** the **Sarawak Data Governance Framework (SDGF)** was launched at BCCK, Kuching, to standardise how state agencies manage and share data.
  [Borneo Post](https://www.theborneopost.com/2026/03/18/data-governance-framework-to-boost-sarawaks-policy-planning/)
- **Jul 2026:** Sarawak is treating data governance and AI as strategic assets for the Sarawak Civil Service; the Kuching AI Data Campus and a state AI Centre (SAIC) are planned.
  [Borneo Post](https://www.theborneopost.com/2026/07/08/sarawak-strengthens-digital-agenda-with-data-governance-ai-push/) ·
  [MIDA](https://www.mida.gov.my/mida-news/sarawak-ai-centre-to-boost-digital-innovation/)

### Scale and infrastructure

- **Federal civil service:** about **1.3 million people**.
  [ISEAS, 2026](https://www.iseas.edu.sg/articles-commentaries/iseas-perspective/2026-44-understanding-malaysias-federal-civil-service-whos-who-and-how-it-works-by-chan-xin-ying/)
- **DDMS 2.0:** used by **395 agencies with over 56,000 users**. This figure comes from the vendor's case study, so quote it carefully.
  [Crest Solution](https://crestsolution.com/resources/success-stories/malaysia-digital-records-management-mampu-alfresco/)
- **AWS in Malaysia:** in March 2023 AWS announced a Malaysia region with **US$6 billion (about RM25.5 billion) of investment by 2037**, so government data can stay in the country.
  [Amazon press release](https://press.aboutamazon.com/2023/3/aws-to-launch-an-infrastructure-region-in-malaysia)

## 4. What this means for our team

- **The problem is real and timely:** 1.3 million civil servants, rules being reviewed under Act 867, and the government already pushing AI adoption.
- **Plain search and AI already exist** (DDMS, AI at Work), so judges will ask "why not just use Gemini?"
- **Our winning angle:** the **current valid rule** + **proof (sources)** + **works in BM and English** + **safe for government data**.

## Glossary

| Term | Meaning |
|---|---|
| Pekeliling (Perkhidmatan) | (Service) circular: an official instruction issued to government staff |
| SPP (Surat Pekeliling Perkhidmatan) | Service circular letter |
| Membatalkan / menggantikan | Cancels / replaces (how a new circular supersedes an old one) |
| Terhad / Sulit | Restricted / Confidential security classifications |
| JPA | Jabatan Perkhidmatan Awam (Public Service Department) |
| MAMPU | Malaysian Administrative Modernisation and Management Planning Unit |
| DDMS | Digital Document Management System used by government agencies |
| RAG | Retrieval-augmented generation: the AI first finds relevant passages, then answers using only those passages |
