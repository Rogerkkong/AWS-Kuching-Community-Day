> **This is a transcription of a teammate's research PDF.**
> Original file: [`docs/Pekeliling Navigator_ Competitive Analy...pdf`](../../Pekeliling%20Navigator_%20Competitive%20Analy...pdf) (11 pages; PDF title "Pekeliling Navigator_ Competitive Analy... Government Knowledge-Search Prototype"; created 7 Oct 2026).
>
> - The wording is kept faithful to the PDF. Only the formatting was cleaned: tables split across pages were merged, the `<!-- page N -->` markers were moved to the nearest paragraph or table boundary, and the tick, half-circle and cross symbols in the feature matrix were replaced with the words Yes, Partial and No.
> - `[source: x]` marks the clickable source chips in the PDF. The links behind them are not reproduced here.
> - **Before you put anything from this file on a slide, check the [fact-check table](README.md#fact-check-results).** Three points are now wrong. Sarawak's ADAM AI (launched 7 Jul 2026) means "no pekeliling chatbot found" no longer holds. Our event is AWS Student Community Day Kuching, not AI HackerDorm. Microsoft has no current public date for Malaysian in-country Copilot processing.

<!-- page 1 -->

# Pekeliling Navigator: Competitive Analysis and Differentiation Strategy for a Malaysian Government Knowledge-Search Prototype

Your biggest differentiator is not "AI search with citations", which every competitor and most hackathon teams already have. It is a system that knows which rule is still in force, which rule replaced it, and whether a federal or Sarawak rule applies to the person asking. No portal, commercial assistant or open-source tool we found does this for Malaysian circulars.

## TL;DR

- **Cited RAG chat is table stakes. Validity is the gap.** Cited answers with hybrid search and OCR come free in open-source RAGFlow, in NotebookLM and in many student GitHub projects. The missing piece is validity awareness. MyPPSM's predecessor marks circulars as "Dibatalkan" but searches titles only. Sarawak eCircular showed "Status: Active" even on a 1982 circular and lists cancellations inside attachments. NotebookLM answers from static copies of uploaded files. Build around a "latest valid rule" engine with a supersession lineage graph.
- **Pitch the domain layer, not the chatbot.** The UK's i.AI retired its Redbox document-chat tool, which had been used by over 6,000 civil servants, after a DSIT test-and-learn programme found that Copilot "offered similar functionality". Under "AI at Work 2.0", launched on 5 Feb 2025, Malaysia's 445,000 civil servants have free access to Gemini in Google Workspace until 2028, plus NotebookLM Plus. JDN already runs AISHAH and a GCBot linked to its own policy repository. Judges will ask "why not just use X?", and the only strong answer is something these tools don't do: supersession, federal-versus-Sarawak disambiguation, gred/skim-aware answers, and "what changed for you" alerts.
- **Treat sovereignty and access control as credibility, not as the headline.** CGSO rules keep Terhad and Sulit data off public cloud, and Microsoft's planned in-country Copilot processing for Malaysia doesn't change that by itself. Glean, Copilot and Singapore's AIBots already do permission-aware retrieval. Show classification tiers and an open-weight, locally hostable stack (deployable on the SAINS Sovereign AI platform) as proof that the system can be adopted, then spend most of the demo on validity.

## 1. Hackathon identification

We could not find the exact problem statement ("transform organizational knowledge into an intelligent, searchable resource") online. The organiser and rubric are still unknown. Relevant Malaysian events for 2026:

| Event | Organiser | Dates / status | Relevance |
|---|---|---|---|
| AI HackerDorm Sarawak | AI HackerDorm + Swinburne Computer Science Club, Swinburne Sarawak | 10–11 Oct 2026, Kuching; submission 11 Oct 9:00 AM; two tracks, prizes of 1,200 cash + 1,000 assets for 1st in each track [source: aihackerdormsarawak] | **Most likely match** given your location and timing, but unconfirmed. Its FAQ says participants are "expected to build with AI tools" and receive AI tokens, [source: aihackerdormsarawak] so expect many teams to ship polished chatbots quickly |
| AI Hackathon for Public Sector 2026 | Digital Penang | Concluded 30 Jun 2026; 14 public-sector teams using no-code/low-code AI platforms [source: digitalpenang] | Shows Malaysian agencies are building their own AI tools in-house |
| Project 2030: MyAI Future Hackathon | GDG on Campus UTM | Mar–May 2026; tracks include GovTech [source: community] | Past GovTech track, so similar ideas probably exist among Malaysian students |
| KitaHack 2026 | GDG on Campus Malaysia | Annual | Judging includes "technical depth, code quality, architecture, effective use of AI … and robustness" [source: kitahack2026] |
| Singapore–Sarawak Friendship AI Business Design Hackathon 2026 | AZAM Sarawak, ANCHR AI Labs, Ibrandium | Two days, 10 teams, Kimi AI API credits [source: sarawaktribune] | Business-focused; shows Sarawak hackathons stress understanding user needs first [source: sarawaktribune] |

**Implication:** Without a rubric, plan for the common Malaysian criteria: problem fit and impact, innovation, technical depth, demo quality and feasibility. In an AI-tools-encouraged event, your build speed will be no better than other teams'. Your domain insight is what can set you apart.

<!-- page 2 -->

## 2. Competitor inventory

### 2a. Government-built tools (overseas)

| Tool | What it does | Key facts / limitations | Lesson for you |
|---|---|---|---|
| **Singapore Pair Chat / Pair Intern / Noms by Pair** | General LLM assistant for officers; Pair Intern is email-based for devices without connectivity; Noms (beta) drafts meeting minutes "in the precise format and style unique to government agencies" | Over 11,000 users across 100+ agencies within its first two months. GovTech's developer portal (updated Mar 2025) now reports 50,409 users across 148 agencies. Document upload supported | Minutes drafting from live meetings is already being built by governments |
| **Singapore Pair Search** | Hybrid search (BM25/weakAnd + e5 + ColBERTv2 reranking) over Hansard, judgments and legislation | Strong retrieval engineering | Hybrid search plus reranking is the expected baseline |
| **Singapore AIBots** | No-code RAG bot builder for agencies | Accepts content up to RESTRICTED / SENSITIVE NORMAL; "tables and images are not well-processed"; roadmap: bot analytics (v1.2), API and Agency Admin Portal, higher classification levels (v2.0), SharePoint integration (v3.0); high-risk use cases need approval [source: tech] | Access management was the adoption blocker. Analytics are on their roadmap, so gap analytics alone won't be unique |
| **UK i.AI Humphrey** (Consult, Parlex, Minute, Lex, Redbox) | Consultation analysis, Hansard search, secure meeting transcription, legal research, document chat | **Redbox was retired in December 2025** after being used by over 6,000 civil servants. i.AI said a DSIT test-and-learn programme "showed Copilot offered similar functionality", making Redbox "one of several options, and often not the most integrated one". Code stays open source; DBT forked it into "DBT Assist" for Official Sensitive material | **The most important lesson:** generic document chat gets absorbed by Microsoft or Google. Domain tools like Parlex and Lex last longer |
| **Australia M365 Copilot trial** | Whole-of-government Copilot pilot run by the DTA (1 Jan–30 Jun 2024, 7,600+ staff, 60+ agencies) | Per the DTA evaluation, Copilot "surfaced sensitive data that staff had not classified or stored appropriately", its "inaccuracy reduced the scale of productivity benefits", and only 1 in 3 participants used it daily | Over-sharing and accuracy are real pain points to design against |
| **US federal (USAi, NIPRGPT, Ask Sage), Hong Kong, Japan, Korea, India, UAE, Estonia** | Not verified in this research round | — | Treat as general-purpose chat and RAG platforms; none we know of targets circular supersession (unverified) |

<!-- page 3 -->

### 2b. Malaysian and Sarawak tools (your real competitors)

| Tool | Search capability | Validity / status handling | Gap you can exploit |
|---|---|---|---|
| **MyPPSM (myppsm.jpa.gov.my)** | Organised by Kluster and Ceraian, with a search manual and a "Makluman" update list; [source: jpa] no semantic or AI search observed (unverified because the portal blocks automated access) | Cancelled circulars sit in an archive; [source: upm] by our count from prior research, consolidation produced 23 master circulars across 6 clusters | No natural-language Q&A, no answers tailored to grade or service scheme, and no cross-portal search. MyPPSM links out to Treasury, JPM, JDN and AGC portals, which shows how fragmented the sources are [source: jpa] |
| **MyPPSPP (older JPA portal, docs.jpa.gov.my/ppspp)** | Year, keyword and cluster search, but "Ruangan carian hanya membuat carian berdasarkan tajuk … dan BUKAN maklumat yang terkandung didalam pekeliling" (title-only search) [source: jpa] | **Best existing status model:** "Kuatkuasa", "Dibatalkan (pengeluaran PP/SPP yang baharu membatalkan PP yang lama)" and "One-off"; entries noted e.g. "(Dibatalkan oleh PP Bil. 3 Tahun 1994)" [source: jpa] [source: jpa] | Shows that supersession data exists as text. You can extract it into a graph and make it searchable in full text |
| **Sarawak eCircular (ecircular.sarawak.gov.my)** | Keyword search across 3,715 circulars; Advance Search filters by agency, category (Federal-Kuala Lumpur / Federal-Sarawak / State), ~40 classifications and date range [source: sarawak] [source: sarawak] | Each circular has "Status" and "Circular Expiry Date" fields, **but a 1982 circular showed "Status: Active" with expiry "0000/00/00"**; cancellations such as PPNS Bil.5/2026 appear only in an attachment ("LAMPIRAN 2 – SENARAI PEKELILING PERJ. YANG DIBATALKAN") [source: sarawak] [source: sarawak] | The status metadata seems unreliable (our inference). Cancellation information is buried in PDFs. The federal-versus-state category already exists, which makes rule disambiguation feasible |
| **Treasury Pekeliling Perbendaharaan (PPP, formerly 1PP)** | One-stop centre with an archive; [source: moh] search features not verified | Titles explicitly tagged "(PEKELILING DIBATALKAN)"; amendments listed ("PINDAAN PEKELILING PS 2.7…") [source: treasury] | Clean status signals to ingest. No Q&A layer |
| **JDN AISHAH / AI@JDN / AIaaS** | Generative-AI chatbot launched 22 July 2024 for JDN service information; AIaaS platform since Aug 2025; plans for agentic AI [source: jdn] [source: jdn] | Not circular-validity aware (not found) | JDN is an active builder and a likely judge or partner. Pitch as complementary, not competing |
| **JDN GovChat GCBot** | "fungsi AI iaitu GCBot (Chatbot) yang berintegrasi dengan sistem dasar JDN" [source: jdn] | Depth unverified | **The closest existing match.** Covers JDN's own policies only, not cross-agency, not Sarawak, not supersession-aware as far as we can tell |
| **DDMS 2.0** | Records management (395 agencies, 56,000+ users per prior research) | Not a semantic Q&A layer; no public API found | Pitch as a future integration ("plugs into DDMS"), not as a replacement |
| **Federal Legislation Portal (lom.agc.gov.my)** | Acts by Updated, Repealed, Translated and Revised; amendments; P.U.(A)/(B) [source: agc] | Reprints carry "LIST OF AMENDMENTS … In force from" and "This Article has been repealed by…"; a "Status of Legislation" column [source: agc +2] | Status tracking exists for **Acts**, at Act or reprint level, but not for administrative circulars |
| **Gemini + NotebookLM (AI at Work 2.0)** | Free access for 445,000 civil servants until 2028 (Gemini in Google Workspace, plus NotebookLM Plus) | Static copies, per-notebook source caps, Terhad and above not allowed on Workspace | See the judge Q&A below |
| **Existing pekeliling chatbots** | **None found** from JPA, startups, students or Sinar Project (LinkedIn and Sinar not directly searched) | The GitHub project aishahsofea/ai-legal-tool runs RAG over 639 AGC Act reprints and its issue #60 *proposes* "current / amended / repealed / unknown" status checks for Acts [source: github] [source: github] | Others have noticed the validity problem for Acts. Nobody we found has applied it to circulars |
| **SAINS Sovereign AI Infrastructure Platform** | Launched 17 Aug 2026; hosted entirely in Sarawak data centres; compute foundation for agencies, statutory bodies and GLCs [source: theborneopost +2] | Infrastructure, not a finished circular Q&A product (no document Q&A service found) | **A deployment target, not a competitor.** "Runs on SAINS" is a strong adoption line |

<!-- page 4 begins with the "Existing pekeliling chatbots" row of the table above -->

### 2c. Commercial enterprise AI search

| Product | Strengths | Limitations relevant to Malaysian government | Price (USD, 2026) |
|---|---|---|---|
| **Microsoft 365 Copilot** | Grounds on Graph data under existing permissions; Purview labels can block labelled content [source: aguidetocloud] [source: opsinsecurity] | Over-sharing: Concentric AI's 2022 Data Risk Report (a vendor study of 550M+ records) found 16% of business-critical files visible to users who shouldn't have access, and an average of 802,000 at-risk files per organisation. One assessment found average sensitivity-label coverage of only 12% before deployment. In-country processing for **Malaysia was announced for 2026** [source: microsoft] (live status as of Oct 2026 unverified). Anthropic models fall outside in-country commitments [source: aguidetocloud] | $30/user/month enterprise add-on on top of E3 ($39 from 1 July 2026); Copilot Business $21 (≤300 users; $18 promo) [source: gosearch] [source: alphavima] |
| **Gemini Enterprise / NotebookLM Enterprise** | Permission-aware search, agents, CMEK, audit logs | NotebookLM Enterprise: 300 sources per notebook, 500 queries per user per day, answers from a "static copy" of sources; data stored in US or EU multi-region per Google's docs [source: google] [source: google] | Gemini Enterprise Business $21; Standard/Plus from $30/seat [source: trendytechtribe] |
| **Glean** | 275+ connectors, permission checks before retrieval [source: getmacha] | No public pricing; reported 100-seat minimums, paid POCs, opaque contracts [source: gosearch] [source: exploreagentic] | Reported ~$45–50/user/month plus ~$15 Work AI add-on (third-party estimates) [source: sentra] |
| **Amazon Quick (formerly Quick Suite)** | Quick Index across enterprise data, research agents | Runs in the customer's AWS account; usage meters are hard to forecast [source: therundown] [source: cloudfront] | Professional $20, Enterprise $40/user/month, plus $250/account/month [source: amazon] |
| **Guru** | **Verification workflow:** every card has a verifier and expiry date; unverified content is flagged; Knowledge Agents can be limited to "verified only" content [source: getguru] [source: eesel] | Requires manual authoring and upkeep of cards [source: eesel] | Quote-based [source: eesel] |
| **ChatGPT Enterprise, Claude Enterprise, Perplexity, Rovo, Notion AI, Elastic, Coveo, Sinequa, watsonx, Vectara, Cohere North** | Company-knowledge connectors with citations (general knowledge) | Not verified individually in this round; none known to model circular supersession | Not verified |

<!-- page 5 -->

### 2d–2f. Records management, legal/RegTech and meeting tools

- **Records and document management vendors (OpenText Aviator, M-Files, Laserfiche Smart Chat, Hyland, Box AI, SharePoint Premium):** we did not verify them this round. They add AI Q&A to their own repositories but are generally not aware of Malaysian circular lineage (unverified). We found no use by Malaysian or Sarawak agencies.
- **Legal citators and RegTech:** citators such as Shepard's and KeyCite are the established model for showing whether something is still good law. Malaysia's lom.agc.gov.my provides status for Acts. Global RegTech vendors (Regology, CUBE, Corlytics and others) track regulatory change for regulated firms. **None we found applies validity tracking to internal administrative circulars (PP/SPP/SE, Pekeliling Perbendaharaan, PPNS).** That is the gap. Specific vendor features were not verified this round.
- **Meeting tools:** Noms by Pair (Singapore, beta) and UK Minute draft minutes from live meetings. [source: tech] [source: globalgovernmentfor…] Read.ai markets a searchable knowledge graph across meetings. [source: read] Teams Copilot recap, Otter and Fireflies serve live meetings. **What remains rare is mining historical minutes (PDF/DOCX archives) to track decisions and action items across meetings and link them to the circulars they cite.** That is a real niche, but outside your core.

### 2g. Open-source RAG platforms (what any team can download)

- **RAGFlow** (Apache 2.0) offers DeepDoc layout analysis, OCR and table recognition. Its citations highlight the exact source region in the PDF. It has GraphRAG, and since August 2026 "Knowledge Compilation" into Wikis, Graphs and Timelines. v1.0.0-rc1 (29 Sep 2026) is a Go rewrite. [source: github +2]
- **Onyx (formerly Danswer)** publishes cloud pricing of $20/user/month and positions itself against Glean. [source: onyx]
- **Typical student GitHub projects** already ship hybrid BM25 + vector retrieval, cross-encoder reranking, local Ollama models, Streamlit or Gradio front ends, [source: github +2] and even "click-to-source" PDF page highlighting over ~1,000 circulars and guidelines (e.g., Praveen-Rajes/compliance-document-chatbot). [source: github +2] The arXiv "PolicyBot" paper adds multilingual embeddings, RAG-Fusion, HyDE and reranking. [source: arxiv]
- **Conclusion:** citations, OCR, hybrid search, reranking, local LLMs and even knowledge graphs are **all table stakes**. Dify, AnythingLLM, Open WebUI, Kotaemon, PrivateGPT, LightRAG and others were not individually verified, but they belong in the same category.

## 3. Feature comparison matrix

Legend: Yes = documented · Partial = partial/configurable · No = not found · ? = unverified

<!-- page 6 -->

| Capability | NotebookLM / Gemini | M365 Copilot | Glean | Open-source RAG (RAGFlow) | Typical hackathon RAG bot | DDMS 2.0 | MyPPSM / eCircular search | Legal / RegTech | Pekeliling Navigator |
|---|---|---|---|---|---|---|---|---|---|
| Natural-language Q&A | Yes | Yes | Yes | Yes | Yes | No | No | Partial | Yes |
| Hybrid search | ? | Yes | Yes | Yes | Partial | ? | No (keyword/title) | Yes | Yes |
| Page/clause-level citations | Yes | Partial | Partial | Yes (highlighted) | Partial | No | No | Yes | Yes (clause + page) |
| BM + EN code-switching quality | Partial | Partial | ? | Partial (model-dependent) | Partial | No | BM keyword | No (for BM circulars) | Yes (tested and measured) |
| OCR of scanned docs | Partial | Partial | ? | Yes | Partial | ? | No | ? | Yes (via RAGFlow/DeepDoc or similar) |
| Permission/classification-aware | Partial (per-notebook sharing) | Yes (inherited perms + labels) | Yes | Partial | No | Yes (records) | n/a public | ? | Yes (mapped to Terbuka/Terhad/Sulit) |
| On-prem / sovereign / air-gapped | No | Partial (in-country processing planned) | No | Yes | Yes | Yes (gov-hosted) | Yes | No | Yes (SAINS / MyGovCloud) |
| **Validity / supersession awareness** | No (static copies) | No | No | No | No | No | Partial (labels exist, unreliable) | Yes (Acts/case law only) | Yes (**core**) |
| Version diff | No | No | No | No | No | Partial (versions) | No | Yes (laws) | Yes |
| Contradiction detection | No | No | No | No | No | No | No | Partial | Partial (curated demo) |
| Minutes decisions across meetings | No | Partial (live meetings) | Partial | No | No | No | No | No | Partial (stretch goal) |
| Role/grade-personalised answers | No | No | No | No | No | No | No | No | Yes (gred/skim profile) |
| Federal vs Sarawak disambiguation | No | No | No | No | No | No | Partial (category filter) | No | Yes |
| Knowledge-gap analytics | No | Partial | Partial | Partial | No | No | No | No | Yes |
| Change alerts | No | No | Partial | No | No | No | Partial ("Latest Circulars") | Yes | Yes (personalised) |
| Owner verification / freshness | No | No | Partial | No | No | Partial | No | Yes (editorial) | Yes (Guru-style) |
| Audit logging | Yes (Enterprise) | Yes | Yes | Partial | No | Yes | No | Yes | Yes |
| Cost (1,000 users/yr) | Already provided to civil servants | ~$360k add-on | ~$540k–780k reported | Hardware + ops | Free | Sunk | Free | Subscription | Low, self-hosted |

<!-- page 7 begins with the "Cost (1,000 users/yr)" row of the table above -->

## 4. Table stakes vs differentiators

**Table stakes (judges expect these; don't pitch them as innovation):**

- Natural-language Q&A with cited sources, ideally click-to-page highlighting
- Hybrid BM25 + vector search with reranking (BGE-M3 + bge-reranker-v2-m3)
- PDF parsing with OCR for scanned circulars
- Refusing to answer when no source supports the answer ("Maaf, tiada pekeliling berkaitan ditemui")
- A local or open-weight model option
- Basic login and audit log

**Partly differentiated (others have it; your local adaptation is what's new):**

- Classification-aware access mapped to Arahan Keselamatan tiers. Glean, Copilot and AIBots already do permission-aware retrieval; the new part is the Malaysian tier mapping and CGSO-aligned hosting.
- Owner verification. Guru does this already. Your version adds a "Pegawai Pemilik Dasar" sign-off per circular.
- Knowledge-gap analytics. Already on the AIBots roadmap and in Guru. [source: tech] Your version adds "unanswered questions by agency and circular cluster" for policy owners.
- Minutes action tracking. Singapore's Noms and UK Minute cover live meetings. Your angle is the historical minutes archive linked to circulars.

**Genuine differentiators (absent from everything we found for Malaysian administrative documents):**

1. A supersession-aware "latest valid rule" engine with a lineage graph and status badges (Berkuat kuasa / Dibatalkan / Dipinda / One-off)
2. Federal vs Sarawak (and federal-in-Sarawak) rule disambiguation
3. Answers personalised by gred/skim/service scheme
4. Plain-language "what changed for you" diffs and alerts when a new circular amends or cancels a rule
5. Compliance checking of a draft memo or letter against currently valid circulars only

<!-- page 8 -->

## 5. Ranked differentiators (scored 1–5)

| Rank | Differentiator | Uniqueness | User value | Demo impact | Hackathon feasibility | Evidence and notes |
|---|---|---|---|---|---|---|
| 1 | **Latest-valid-rule engine + lineage graph** | 5 | 5 | 5 | 4 | MyPPSPP and Treasury already *write* "Dibatalkan oleh…" and "(PEKELILING DIBATALKAN)". [source: treasury +2] eCircular buries cancellations in LAMPIRAN lists and shows "Active" on a 1982 circular. [source: sarawak] [source: sarawak] Build it by extracting supersession phrases ("membatalkan", "dibatalkan oleh", "menggantikan", "pindaan") with regex plus an LLM into a `supersedes` table, then filtering retrieval to in-force documents by default and showing the cancelled chain on request |
| 2 | **Federal vs Sarawak rule disambiguation** | 5 | 5 | 4 | 4 | Sarawak runs its own civil service and circulars, and eCircular already tags Federal-KL / Federal-Sarawak / State. [source: sarawak] Ask the user's service (Persekutuan / Negeri Sarawak) and show both rules side by side when they diverge |
| 3 | **"What changed for you" diff + alerts** | 4 | 5 | 5 | 4 | Legal tools do this for statutes; nothing does it for circulars. Demo with two real versions of one circular and a generated BM/EN summary: "Mulai 1 Jan 2026, kadar X berubah daripada A kepada B; terpakai kepada gred 41–54" |
| 4 | **Gred/skim-personalised answers** | 5 | 4 | 4 | 3 | HR circular rules depend on grade and scheme. Start with a simple user profile (gred, skim, service) used as a retrieval filter and prompt context. Limit it to 1–2 clusters (e.g., cuti, kemudahan) |
| 5 | **Draft compliance checker** | 4 | 5 | 5 | 3 | Upload a draft memo and flag clauses that conflict with *in-force* circulars, citing them. Copilot and Gemini can review drafts but don't know which circular is valid. Pick one narrow domain with numbers in the corpus (e.g., a Treasury procurement circular) so the check is deterministic |
| 6 | **Bilingual BM/EN and code-switching, measured** | 3 | 5 | 3 | 4 | Every tool claims multilingual support; few *prove* BM quality. Run a 30–50 question golden set mixing BM, EN and rojak queries and show recall@5 and citation accuracy on a slide. The measurement itself sets you apart |
| 7 | **Classification tiers + sovereign deployment** | 2 | 5 | 3 | 4 | Not unique (Glean, Copilot, AIBots), but essential for adoption under CGSO rules and the Sarawak V1_2025 guideline. Show a role switch: a Terhad document disappears for a Terbuka-cleared user. Run the model locally (e.g., Ollama with an open-weight model) and say "deployable on SAINS" |
| 8 | **Knowledge-gap analytics dashboard** | 2 | 4 | 3 | 5 | Cheap to build: log unanswered or low-confidence queries by cluster. Frame it for policy owners at JPA and BPSM |
| 9 | **Owner verification and stale-document nudges** | 2 | 4 | 2 | 4 | Guru already does this well. Add it as a status field only |
| 10 | **Historical minutes decision tracker** | 3 | 4 | 4 | 2 | Real niche, but a second product. Cut it, or show one screen: "Keputusan mesyuarat bil. 3/2025 merujuk pekeliling yang kini dibatalkan" |
| 11 | **Contradiction detection** | 4 | 3 | 4 | 2 | High false-positive risk. Only demo it on a curated pair |
| 12 | **Voice access for field officers** | 2 | 3 | 3 | 3 | Low priority; adds risk |
| — | **OCR** | 1 | 4 | 1 | 5 | Table stakes; use RAGFlow or an equivalent and don't pitch it |

<!-- page 9 begins with rank 12 of the table above -->

**Recommended scope for 24–48 hours:** #1 + #2 + #3 as the hero flow, #6 as the evidence slide, #7 as the trust slide, #8 as a small dashboard. Mention #5 and #10 as roadmap items unless time remains.

## 6. Judge Q&A cheat sheet: "Why not just use X?"

- **NotebookLM / Gemini (free for 445,000 civil servants until 2028 under AI at Work 2.0):** "NotebookLM answers from whatever static copies a user uploads. It doesn't know that SPP 2019 was cancelled by PP 2024 unless someone curates the notebook by hand. Enterprise notebooks cap at 300 sources, while Sarawak eCircular alone holds 3,715 circulars. [source: sarawak] [source: google] Sharing is per notebook, not organisation-wide classification. And MyGovUC guidance says Terhad and above isn't allowed on Google Workspace. We complement Gemini: officers can use it for drafting, and we guarantee the rule they cite is still in force."
- **Microsoft Copilot:** "Copilot inherits permissions, and that is exactly the problem. Concentric AI's vendor Data Risk Report found 16% of business-critical files visible to users who shouldn't have access and 802,000 at-risk files per organisation. Australia's DTA trial of 7,600+ staff found Copilot 'surfaced sensitive data that staff had not classified or stored appropriately'. Malaysian in-country processing is announced for 2026, [source: computerworld] but CGSO still limits public cloud to Terbuka data. And Copilot has no concept of circular supersession. It costs $30 per user per month on top of E3 licences." [source: gosearch]
- **ChatGPT:** "Public ChatGPT uses outdated public web content, doesn't cite clauses, and uploading official documents breaches Sarawak's AI guideline and the OSA. Enterprise pricing wasn't verified for this pitch, but it's per seat and hosted offshore."
- **Glean:** "Strong permission-aware search, but no public pricing; reported at roughly $45–50 plus a $15 add-on per user per month, with 100-seat minimums. [source: gosearch] [source: exploreagentic] It's SaaS-hosted and doesn't model Malaysian circular lineage."
- **DDMS 2.0:** "DDMS is the records system of record. It stores and files documents. We're the question-answering and validity layer that could sit on top of it later via an integration."
- **MyPPSM's own search:** "JPA's previous portal explicitly searched titles only, not content. [source: jpa] MyPPSM organises by cluster and keyword. Neither answers 'Saya gred 44 di Sarawak, berapa hari cuti X?' with the in-force clause. And MyPPSM covers HR circulars only; officers also need Treasury, JDN and Sarawak circulars."
- **SAINS Sovereign AI platform:** "SAINS provides sovereign compute and hosting. [source: sarawakdaily] [source: sarawaktribune] We're an application that runs on it. That's our deployment path, not a competitor."
- **JDN AI@JDN / GCBot:** "GCBot covers JDN's own policy repository. [source: jdn] We cover HR, Treasury and Sarawak circulars across agencies, with supersession tracking. We'd happily expose our engine to JDN's AIaaS."
- **Another team's RAG chatbot:** "Ask them: 'Is this circular still valid? What replaced it? Does it apply in Sarawak? What changed since last year?' A plain RAG bot will confidently cite a cancelled circular, and that's worse than no answer. Our default filter answers only from in-force documents and shows the lineage."

## 7. Positioning statements

1. **"Pekeliling Navigator: never cite a cancelled circular again."** Bilingual answers from only the rules currently in force, with the clause, the page and the full amendment history.
2. **"The 'is this still valid?' layer for Malaysian government knowledge."** Gemini and Copilot help you write; we make sure what you write rests on the current federal or Sarawak rule for your grade.
3. **"Sovereign, validity-aware policy search for every agency, from Putrajaya to district offices."** Runs on SAINS or a single local server, respects Arahan Keselamatan tiers, and tells officers what changed for them.

<!-- page 10 -->

## 8. Pricing comparison: example 1,000-officer agency (USD per year, list or reported)

| Option | Calculation | Approx. annual cost | Notes |
|---|---|---|---|
| M365 Copilot (enterprise) | $30 × 1,000 × 12 [source: gosearch +2] | ~$360,000 add-on (~$828,000 including E3 at $39) | Business SKU capped at 300 users [source: alphavima] |
| Gemini Enterprise Standard | $30 × 1,000 × 12 | ~$360,000 | Gemini in Workspace is already provided via AI at Work 2.0 |
| Glean | ($45–50 + $15) × 1,000 × 12 [source: sentra] | ~$720,000–780,000 (lower with volume discounts) | Third-party estimates; not published [source: sentra] |
| Amazon Quick Professional / Enterprise | $20 or $40 × 12,000 + $3,000 [source: amazon] | ~$243,000 / ~$483,000 | Plus usage meters |
| ChatGPT Enterprise | — | Not verified | Per-seat, sales-quoted |
| **Self-hosted open-source stack** | One GPU server plus part-time ops | **Our estimate: low tens of thousands USD capex plus staff time** | Or SAINS cost-recovery hosting; [source: digitalnewsasia] marginal cost per extra user near zero |

The self-hosted figure is our own rough estimate, not a sourced quote. Present it as "an order of magnitude cheaper per user" rather than as an exact number.

## 9. Recommended prototype build (24–48 hours)

1. **Corpus (hours 0–6):** manually download 50–150 public circulars from 2–3 clusters (e.g., cuti, kemudahan) across MyPPSM/JPA, Treasury PPP and Sarawak eCircular, including at least 3 known supersession chains and 1 federal-vs-Sarawak divergence. MyPPSM blocks automated crawling via robots.txt, so don't scrape it; curate by hand and say so.
2. **Metadata (hours 4–12):** for each document record circular number, issuer, date, effective date, jurisdiction (Persekutuan/Sarawak), cluster, classification tier and status, plus a `supersedes/amends` edge list extracted with regex and an LLM, then checked by hand.
3. **Retrieval (hours 8–20):** BGE-M3 dense plus BM25, bge-reranker-v2-m3, with an "in-force only" filter on by default. Clause-level chunking on Malay headings ("Perenggan", numbered clauses).
4. **Generation:** an open-weight model locally (e.g., SEA-LION or another available open-weight model), with forced citations and refusal when no source supports the answer.
5. **User interface (hours 16–36):** answer card with a status badge, clause citation, "Lihat salasilah" lineage graph, a federal/Sarawak toggle, a profile (gred/skim), a "What changed" diff view, and a role switch that demonstrates tier filtering.
6. **Evidence (hours 30–42):** a golden set of 30–50 BM, EN and mixed questions. Report recall@5, citation accuracy and "cancelled-circular citation rate", comparing plain RAG with the Navigator. The last metric is your killer slide.
7. **Demo script:** ask a question that a plain RAG bot or NotebookLM gets wrong by citing a cancelled circular, then show the Navigator answering from the valid one with the lineage.

## 10. Risks

- **Big-vendor absorption:** Redbox shows that generic features get absorbed by Copilot or Gemini. [source: ukauthority] Supersession graphs for Malaysian circulars are niche enough that big vendors are unlikely to build them soon, but JPA, JDN or SAINS could add them. Position yourself as a partner or module for them.
- **Data quality:** status metadata is inconsistent (eCircular "Active" on old circulars), so automated extraction will make mistakes. Show a human-verification step and confidence levels.
- **Legal liability:** a wrong "valid" badge is worse than none. Show "Disahkan oleh pemilik dasar / Belum disahkan" and always link the source PDF.
- **Scope creep:** minutes tracking, contradiction detection and voice can sink a 48-hour build.
- **Classification compliance:** use only Terbuka public documents in the prototype, and say so explicitly. This follows Sarawak's V1_2025 guideline and CGSO rules.
- **Rubric uncertainty:** if judges weight social impact, frame time saved for officers and faster, consistent decisions for the public.

<!-- page 11 -->

### Caveats

- We didn't identify the hackathon. AI HackerDorm Sarawak (10–11 Oct 2026) fits the timing and location [source: aihackerdormsarawak] but isn't confirmed.
- We couldn't fetch MyPPSM directly. Its features come from search snippets, and the title-only search quote applies to the older MyPPSPP portal.
- Microsoft's Malaysian in-country Copilot processing was announced for 2026. [source: computerworld] [source: techtrp] Whether it is live as of October 2026 is unverified.
- Glean prices are third-party estimates. ChatGPT Enterprise pricing, US, Hong Kong, Japan, Korea, India, UAE and Estonia tools, records-management vendors, RegTech vendors and most open-source platforms other than RAGFlow weren't verified in this research round.
- "No existing pekeliling chatbot found" comes from a limited search (LinkedIn and Sinar Project not checked directly). Absence of evidence isn't proof, so check again before claiming "first ever".
