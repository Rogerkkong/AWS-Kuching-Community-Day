> **This is a transcription of a teammate's research PDF.**
> Original file: [`docs/Government Knowledge Search_ Problem-Sp...pdf`](../../Government%20Knowledge%20Search_%20Problem-Sp...pdf) (16 pages; PDF title "Government Knowledge Search_ Problem-Sp...h for a Malaysia and Sarawak Hackathon"; created 7 Oct 2026).
>
> - The wording is kept faithful to the PDF. Only the formatting was cleaned: sentences split across pages were joined, and the `<!-- page N -->` markers were moved to the nearest paragraph boundary.
> - `[source: x]` marks the clickable source chips in the PDF. The links behind them are not reproduced here.
> - **Before you put anything from this file on a slide, check the [fact-check table](README.md#fact-check-results).** Several numbers were corrected. The claim that Malaysia "still lacks" a cross-document layer is out of date, because Sarawak launched ADAM AI in July 2026.

<!-- page 1 -->

# Government Knowledge Search: Problem-Space Research for a Hackathon (Malaysia/Sarawak and Global)

The problem is real, the market is already full of generic "chat with your documents" tools, and the winning gap is **trust in a government setting**: answers that are cited, current (aware of superseded circulars), permission-aware, and bilingual (Bahasa Melayu and English), and that can run inside sovereign or on-premise infrastructure. Malaysia already digitised its records through DDMS 2.0 and gave civil servants general-purpose GenAI through Google Gemini. What it still lacks is a cross-document "what is the current valid rule, and where does it say so" layer that is safe to use with Terhad/Sulit material. That is where your team should aim.

## TL;DR

- **The problem is validated, but the famous statistics are weak.** The popular "1.8 hours a day searching" figure (McKinsey, 2012) and IDC's "2.5 hours a day" are widely repeated but methodologically shaky. Use recent government trial data instead. Australia's 7,600-person Copilot trial reported time savings of up to an hour on summarising and information search. The UK's 20,000-person trial reported 26 minutes saved per day. In Malaysia's own AI at Work pilot, Google Cloud reported that 97% of participants saved 3.25 hours per week.
- **Government precedent favours purpose-built, permission-aware RAG over generic copilots.** Singapore's AIBots (RAG over agency knowledge bases, 20,000+ bots), Pair Search (hybrid search plus reranking over about 58,000 documents) and the UK's Humphrey suite all show this. Australia's evaluation found Copilot surfaced sensitive data that staff had not classified or stored properly.
- **Best hackathon direction:** a bilingual, cited "Pekeliling Navigator". It ingests real public circulars (MyPPSM, Treasury 1PP, Sarawak eCircular), tracks supersession ("is this still in force, and what replaced it?"), enforces classification-aware access, extracts decisions and action items from meeting minutes, and runs on open-weight models (SEA-LION / ILMU-class models plus BGE-M3 embeddings). This fits Malaysian rules that keep Rahsia/Rahsia Besar data off any cloud and keep Sulit/Terhad data off public cloud.

## Key Findings

### 1. Problem validation and scale

#### Headline statistics, and how to use them honestly

- McKinsey (2012): employees spend 1.8 hours a day (9.3 hours a week) searching and gathering information, often framed as "hire five, only four show up". IDC has published figures of about 2.5 hours a day (roughly 30% of the workday), 8.8 hours a week (2011), and 5 hours a week searching for documents (2012). [source: linkedin] [source: m-files] IDC's 2012 survey reportedly found almost half of that search time ends without finding the document. [source: uspto]

<!-- page 2 -->

- **Caveat:** enterprise-search analyst Martin White has documented these numbers as a "myth" chronology. Original sources often do not contain the cited claim, and IDC's own later methodology produced much lower estimates. He argues "time spent searching is a meaningless metric without being attributed to a group of users undertaking similar tasks." [source: linkedin] In a pitch, cite these numbers only as context and lean on the government trial data below. Judges with domain knowledge will respect that.

#### Stronger, government-specific evidence (2024–2026)

- **Australia (DTA, Microsoft 365 Copilot, Jan–Jun 2024, more than 7,600 staff, evaluated by Nous Group):** [source: mlex] [source: microsoft]
  - Participants estimated time savings of up to an hour when summarising information, drafting and *searching for information*. [source: digital]
  - 69% said it improved speed and 61% said it improved quality. 86% wanted to keep using it. [source: digital] [source: nousgroup]
  - Only 1 in 3 used it daily, and up to 7% said it *added* time. [source: digital]
  - Copilot "surfaced sensitive data that staff had not classified or stored appropriately". Inaccuracy limited adoption, and users worried about vendor lock-in. [source: digital +2]
- **UK (GDS Copilot experiment, more than 20,000 civil servants, 12 organisations, 3 months, published June 2025):** [source: www] [source: techradar]
  - Users reported saving 26 minutes a day (about 2 weeks a year). Over 70% reported less time searching for information, and 82% wanted to continue. [source: ground]
  - 17% reported no time saved. All results were self-reported. [source: mlex] [source: computing]
- **Malaysia (AI at Work pilot):**
  - Google Cloud's 5 Feb 2025 press release says the pilot involved 270 public officers from several agencies, including JDN (not JDN alone). "97% of pilot participants experienced time savings of 3.25 hours per individual per week, with 91% indicating that gen AI has helped enhance their quality of work." Digital Minister Gobind Singh Deo repeated these figures in the Dewan Rakyat.
  - The programme then expanded to 445,000 civil servants with Google Workspace, Gemini and NotebookLM ("AI at Work 2.0", launched 5 Feb 2025 by the Ministry of Digital, NAIO and Google Cloud). [source: computerweekly +2]

**What this means:** time savings are real but modest and self-reported, and generic copilots plateau because of accuracy and trust problems. A focused tool that answers *policy questions with verifiable citations* targets exactly where these trials found weakness.

<!-- page 3 -->

#### Government-specific pain points (and the Malaysian evidence)

- **Volume and silos:** documents are spread across shared drives, email, DMS platforms and paper. JDN Director-General Ts Nik Zalbiha binti Nik Mat told GovInsider that DDMS 2.0 has been "rolled out to 395 agencies with over 56,000 users" (Bernama reported in 2024 that it held 12.3 million records, with a target of 500 agencies by 2025). She said uneven digital maturity caused "inconsistent adoption rates", migrating legacy records requires "intensive planning, quality control, and validation", and a uniform file classification across agencies was hard because agency functions differ.
- **Supersession and versioning:** the JPA built MyPPSM (launched 30 Sep 2021, in force 1 Jan 2022) specifically "to review circulars that were outdated or no longer relevant and reduce the number of existing circulars through merging and cancellation". It reorganised HR circulars into 6 clusters and 23 master circulars (Pekeliling Induk), each with an appendix listing cancelled circulars. [source: jpa] This is direct evidence that "which circular is still valid?" is a recognised, expensive problem in Malaysia.
- **Keyword search failure:** Singapore's Pair Search team noted that searching "Covid 19" on a government press-centre site returned zero results unless written "covid-19". [source: hack] Lexical brittleness is a real failure mode. It gets worse with Malay morphology (prefixes and suffixes such as *ber-*, *-kan*, *peng-…-an*) and code-switching.
- **Classification and access:** Malaysian documents carry Arahan Keselamatan levels (Terbuka, Terhad, Sulit, Rahsia, Rahsia Besar). [source: mygovuc] [source: mypolycc] MyPPSM itself does not display circulars classified "Terhad", which shows that even public repositories have a hidden restricted layer. [source: jpa]
- **Institutional memory loss:** one of DDMS 2.0's stated objectives is "Memelihara Memori Institusi Negara" (preserving national institutional memory). [source: mampu] Staff transfers in the civil service (for example, rotation between agencies) make tacit knowledge loss a common complaint, though this research found no quantified Malaysian survey on it.
- **Multilingual content:** federal circulars are mostly in Bahasa Melayu, while technical guidelines and reports are often in English. Sarawak adds English-heavy state documents.

#### Document types differ, so the retrieval and answer strategy should too

<!-- page 4 -->

| Document type | Structure | Typical questions | Technical implication |
|---|---|---|---|
| Policies / Pekeliling Induk | Numbered clauses, definitions, effective dates, cancellation appendices | "What is the current rule on X?" "Since when?" | Clause-level chunking that keeps the section path; effective/cancelled dates as metadata |
| Circulars (PP/SPP/Surat Edaran) | Short, amend or supersede earlier ones, reference numbers (e.g., JPA.600-8/1/8(1)) [source: jpa] | "Which circular superseded Y?" "Is Y still in force?" | Supersession graph; extract reference numbers |
| SOPs | Step lists, roles, forms | "How do I do X? Who approves?" | Keep steps together; extract roles |
| Guidelines | Long, explanatory, sometimes in English | "What does the guideline recommend about Y?" | Hierarchical chunks plus summaries |
| Reports | Long narrative, tables, figures | "Summarise findings", "What was the 2024 figure?" | Table-aware parsing; map-reduce summarisation |
| Meeting minutes | Attendees, agenda items, decisions ("Mesyuarat bersetuju..."), action items ("Tindakan: ...") | "What was decided in meeting Z?" "Who owns action item N?" "What's still open?" | Structured extraction into a decisions/actions table |

### 2. Existing solutions and case studies

#### Singapore (the most relevant model)

- **Pair Chat:** launched in 2023 by Open Government Products. In a written parliamentary reply on 5 Nov 2025, the Ministry of Digital Development and Information (MDDI) said: "About 80% of our 150,000 officers have used Pair Chat... Over 20,000 of such bots have been created." It is cleared for data up to RESTRICTED / SENSITIVE NORMAL, unlike ChatGPT (public data only). [source: tech] It came out of the 2023 Hack for Public Good hackathon, built by a team of five, and is still run by a lean team of seven. [source: undp]
- **Pair Search:** a 2024 Hack for Public Good project. It covers Hansard (1955 to January 2024, over 30,000 reports), Supreme Court judgments and legislation, and Pair's own blog says it indexes about 58,000 documents. It runs on Vespa.ai. Keyword search uses "Vespa's weakAnd operator alongside nativeRank and BM25", combined with semantic search on e5 embeddings and ColBERTv2 reranking, in three phases. It also exposes a retrieval API for RAG. This is effectively the reference architecture for your project.

<!-- page 5 -->

- **Pair's "Beyond RAG" stance:** for Pair Chat, OGP chose long-context processing, reading whole documents, because generic RAG "pulls specific sections … based on mechanical matching" and is more prone to hallucination. The team says it is exploring hybrids. [source: pair] *Lesson:* use RAG to find the right documents, then give the model full sections or whole short circulars rather than tiny fragments.
- **AIBots:** a 2023 hackathon project. It lets officers build RAG chatbots over internal knowledge bases "in under 15 minutes". Usage: 40,300 users, 23,300 active bots and 118 agencies (Aug 2024–Oct 2025). Top bots include HR Q&A, procurement and finance-policy Q&A. One GovTech officer did in 2 days a feedback analysis that previously cost $20k and took weeks with a consultant. [source: medium] [source: go] *Lesson on failure:* AIBots initially could not get approval because every bot was visible to every user. It needed proper user access management, and early on 200+ bots were approved one by one. [source: medium] **Access control is the gating feature for government RAG.**
- Next step: GovTech is building a registry of AI agents for 150,000 officers (2026) that tracks ownership and permissions. [source: thestar] [source: startupfortune]

#### United Kingdom (i.AI "Humphrey" suite, Jan 2025)

- **Consult:** analyses consultation responses, cutting turnaround "from months to hours". [source: verdict]
- **Parlex:** searches decades of parliamentary debate. [source: globalgovernmentfor...]
- **Minute:** secure meeting transcription with summaries in civil-service formats; trialled in councils. [source: globalgovernmentfor...] [source: government-transfor...]
- **Redbox:** summarises policy and drafts briefings. The Department for Business and Trade built its own fork. [source: futurescot] [source: blog]
- **Lex:** legal research. [source: globalgovernmentfor...]
- **Criticism:** TechCrunch noted early-stage maturity, uncertainty about the underlying LLMs, and past failures of cross-department programmes. [source: TechCrunch]

**Australia:** the whole-of-government Copilot trial is described above. Australian Treasury's own evaluation relied on voluntary self-reported data, which shows the evidence base is soft everywhere. [source: treasury]

**Other jurisdictions (lower verification in this research):** Estonia's Bürokratt (an interoperable network of public-service virtual assistants), South Korea, Hong Kong, the UAE/Dubai and India all have government chatbot or AI programmes. However, I could not verify architecture or impact data for them within this research, so treat them as background only.

<!-- page 6 -->

#### Malaysia (federal)

- **DDMS 2.0:** developed by MAMPU (now JDN) with Arkib Negara (ANM) and CGSO. It manages the full record lifecycle (creation, capture, storage, use, disposal), [source: malaysia] complies with MS ISO 16175-1:2012, and rests on the National Archives Act 2003 (Act 629). [source: govinsider] It handles both Rekod Rasmi and Rekod Rahsia Rasmi, and won a 2025 GovInsider Festival of Innovation award. [source: mampu] [source: govinsider] *It is a records-management system, not a semantic Q&A layer.* That makes it a natural data source and integration point for an AI layer, not a competitor.
- **ANM:** issued "Tatacara Pengurusan Rekod Elektronik dalam DDMS di Pejabat Awam" (2022), which governs how e-records are managed. [source: arkib]
- **JDN / NAIO / Ministry of Digital:**
  - NAIO launched in Dec 2024. [source: freemalaysiatoday]
  - The Public Sector AI Adaptation Guidelines (GPAISA) were launched 27 Feb 2025. The document is 158 pages, numbered Bil 1 Tahun 2025, still in force, with an online self-assessment based on 7 ethics principles at gpaisa.jdn.gov.my. [source: jdn +2]
  - JDN runs an in-house GenAI chatbot, "AI@JDN" (July 2024). [source: jdn]
  - MyGOV Malaysia super-app soft launch (Feb 2025). [source: digital]
- **Malaysian and SEA LLMs:**
  - **ILMU** (YTL AI Labs with Universiti Malaya): launched Aug 2025. It understands BM, Manglish and dialects such as Kelantanese, is hosted on local YTL AI Cloud, and claims top Malay MMLU scores (a vendor claim). [source: dagangnews] [source: ilmu] API access is available. [source: malaysianwireless +2]
  - **MaLLaM** (Mesolitica): open-weight, Malay-first models in 1.1B, 3B and 5B sizes. According to Zolkepli et al. (arXiv:2401.14680, Jan 2024), they were trained from scratch "on a substantial 349GB dataset, equivalent to 90 billion tokens... for a single epoch".
  - **SEA-LION v4** (AI Singapore): based on Gemma 3 27B, open for commercial use, 128K context, multimodal (useful for scanned pages), and claimed to run on a 32GB-RAM laptop. Smaller 4B/8B variants and a Nemotron-based v4.8 also exist. [source: sea-lion] [source: sea-lion]

#### Sarawak

- **Sovereign AI Infrastructure Platform:** launched Aug 2026, run by SAINS as technical custodian and hosted entirely in Sarawak data centres. Its stated purpose is "secure, locally hosted AI services for government". The Premier urged ministries and agencies to use it. [source: theborneopost +2]

<!-- page 7 -->

- **Governance:** the State Civil Service Digitalisation Unit (SCSDU) sets policy and the Digital Government Committee is chaired by the State Secretary. More than 200 departments can submit digital proposals. SAINS describes the direction as moving "from digital government to AI government" by 2030. [source: digitalnewsasia] [source: borneotalk]
- **Data and skills:**
  - Sarawak Data Governance Framework (SDGF) 2026, built by SCSDU, SMA, SAIC and SAINS. [source: sarawaktribune]
  - Under the "SCS Digital Literacy 2025" initiative, the Sarawak Tribune reported that "Nearly 17,500 officers, 93 per cent of the workforce, have completed online modules on AI and cybersecurity". A later Sarawak Tribune report put completion at 98% of more than 19,220 officers and staff for the 'AI untuk Rakyat' and 'Defence Against Phishing' modules.
  - Sarawak Pass digital ID (IDECS 2025). [source: sdec]
- **Sarawak AI guideline (V1_2025):** "Garis Panduan Penggunaan Kecerdasan Buatan (AI) dalam Perkhidmatan Awam Sarawak", prepared by SCSDU with UPPSM and SMA. [source: sarawak]
  - It bans uploading personal data, citizens' information, confidential official documents or OSA-protected information into any AI system "dalam apa jua keadaan" (in all circumstances). [source: sarawak]
  - It bans uploading source code into web AI tools. [source: sarawak]
  - It applies its principles to on-premise government AI too. [source: sarawak]
  - Para 5.6 explicitly names **AI-assisted search across government manuals, guidelines, circulars and laws** as a valid use case. [source: sarawak] That is effectively an endorsement of your problem statement.

#### Commercial products, and why governments do not simply buy them

- Microsoft 365 Copilot (with SharePoint), Google Agentspace / Vertex AI Search, Amazon Q Business / Kendra, Glean, Elastic and Coveo all offer connectors, permission-trimmed retrieval and cited answers.
- Limits revealed by public-sector evidence:
  - Per-user licence costs that Australia flagged as a consideration. [source: digital]
  - Vendor lock-in concerns (Australia). [source: digital]
  - Oversharing caused by poor existing permissions (Australia). [source: digital]
  - **Data residency and classification rules.** In Malaysia, a Sep 2025 MyGovUC FAQ states only "Terbuka" information may be handled on public cloud. Terhad, Sulit, Rahsia and Rahsia Besar are "TIDAK DIBENARKAN SAMA SEKALI" on Google Workspace because the data sits outside Malaysia. [source: mygovuc]
  - Uneven BM quality, and little awareness of Malaysian document conventions (bilangan/tahun numbering, cancellation appendices).

<!-- page 8 -->

#### Open-source building blocks (for a hackathon)

- **Full platforms you can stand up in hours:**
  - RAGFlow: strong deep-document parsing and citations.
  - Onyx (formerly Danswer): enterprise connectors and permission sync.
  - Dify: visual workflow and agent builder.
  - AnythingLLM and Open WebUI: chat front ends with document RAG.
  - Kotaemon: a RAG UI with citation highlighting.
  - PrivateGPT: fully local.
- **Libraries if you want custom logic:** LlamaIndex, LangChain/LangGraph, Haystack.
- **Recommendation:** use a library rather than an off-the-shelf platform for the core, because your differentiators (supersession graph, classification filters, minutes extraction) need custom code. You can borrow a UI (Open WebUI) or parsing (Docling) where convenient.
- *Note:* feature claims for these frameworks come from general knowledge of their public repositories and were not individually re-verified in this research.

### 3. Technical approaches and best practices

#### Ingestion and parsing

- Docling (IBM, permissive licence) is strong on tables. IBM reports 97.9% table-cell accuracy on its benchmark. [source: ertas]
- Marker is faster, but its GPL licence has restrictions. [source: link]
- Unstructured covers the widest range of formats. [source: ertas]
- Independent benchmarks conflict. One 2026 test scored Docling only 50.3 on olmOCR-Bench (64.0 on born-digital PDFs), against about 83 for Marker 2 and MinerU on born-digital PDFs. Another found Docling the best free table extractor (0.911 TEDS). [source: dev] [source: builderai] *Takeaway:* benchmark on 20 of your own circulars before you commit.
- For scans, use Tesseract (it has a Malay language pack) or PaddleOCR. A vision-language model such as SEA-LION v4 or Gemma 3 can serve as a fallback for messy pages.

#### Chunking for policy documents

- Split on structural boundaries (Bahagian / Perenggan / clause numbers) rather than fixed token windows.
- Attach a breadcrumb to each chunk: document title > section > clause.
- Store metadata on every chunk: document number, year, issuing agency, effective date, status (in force / cancelled), classification, language and page number.

<!-- page 9 (begins with the third chunking bullet above) -->

#### Embeddings and retrieval

- **BGE-M3** (MIT licence, more than 100 languages, 8,192-token input) produces dense, sparse (lexical) *and* multi-vector (ColBERT-style) representations from one model. Combining all three gives the best results, and that hybrid directly fixes the "Covid 19 vs covid-19" brittleness. [source: deepinfra] [source: zilliz]
- Pair with **bge-reranker-v2-m3** (multilingual cross-encoder). [source: github] multilingual-e5 is the alternative.
- Vector store options: Qdrant, Milvus (native BGE-M3 sparse plus dense support), pgvector, or Vespa / OpenSearch for production hybrid search. [source: milvus]
- Use query rewriting to expand BM↔EN, so a query like "cuti sakit" also matches "sick leave", and to resolve circular numbers.

**RAG vs long context:** research is mixed. Some studies find RAG beats long context beyond about 100K tokens at lower cost. Others (and Singapore's Pair team) prefer whole-document reading for nuance. [source: pair] [source: arxiv] A practical hybrid: retrieve at document or section level, then pass whole sections, kept in original order, to a 128K-context model.

#### Advanced features

- **Temporal validity / supersession:** build a graph of nodes (circulars, clauses) and edges (*supersedes*, *amends*, *cancels*, *references*).
  - Extract the edges with regex on reference patterns (e.g., "Pekeliling Perkhidmatan Bilangan 5 Tahun 2018") plus an LLM pass.
  - Seed them from MyPPSM's official cancellation appendices, which act as free ground truth. [source: jpa]
  - Default retrieval to "in force" documents, and show the lineage on demand.
- **GraphRAG / knowledge graphs:** useful for cross-document "how do these policies relate" questions. For a hackathon, a lightweight property graph (Neo4j or NetworkX) built around supersession is higher-value than full Microsoft-style GraphRAG.
- **Contradiction detection:** run an NLI or LLM judge over pairs of retrieved clauses on the same topic from different in-force documents, and flag "possible conflict, needs review". Present it as an assistive flag, never as an authoritative ruling.
- **Meeting minutes:** extract structured {decision, owner, deadline, status, source page} records into a table. Malaysian minutes use stable markers ("Keputusan", "Tindakan"), which makes extraction reliable. The UK's Minute and Singapore's Pair Noms (with its own evaluation rubric for good minutes) validate this use case. [source: undp] [source: globalgovernmentfor...]

<!-- page 10 -->

- **Agentic RAG:** a router that decides between "lookup current rule", "trace lineage", "compare two documents" and "summarise report". Keep it bounded, because agents add latency and demo risk.

#### Trust and accuracy

- Every claim should link to document, page and clause, with the passage highlighted.
- Refuse when the evidence is missing: "Tiada maklumat dalam dokumen yang dibekalkan" (no information in the supplied documents).
- Show a retrieval-confidence indicator (for example, based on reranker score) and a status badge ("Berkuat kuasa" in force / "Dibatalkan" cancelled, with a link to the replacement).
- **Evaluation:**
  - Build a gold set of 50–100 bilingual Q&A pairs from your corpus.
  - Measure retrieval with Recall@k and MRR.
  - Measure generation with RAGAS-style faithfulness, answer relevance and context precision.
  - Measure refusal accuracy on unanswerable questions.
  - Show judges a live "keyword search vs. your system" comparison on the same questions.

#### Security and governance

- **Access control must be enforced before generation.** Recent research ("Enterprise AI Must Enforce Participant-Aware Access Control", arXiv 2509.14608) argues probabilistic defences such as output filtering are "fundamentally insufficient", and that content must be authorised for every recipient at every stage. [source: arxiv]
  - Practical patterns: metadata filters on classification and role (fine for a demo), separate indexes per classification tier (the clearest isolation, easy to audit), or fine-grained document- or chunk-level ACLs. [source: medium]
  - Documents lose their source permissions when turned into embeddings, so ACLs must be carried into chunk metadata. [source: protecto]
- **Prompt injection:** OWASP ranks it the top LLM risk for 2025. [source: protecto] Treat retrieved text as untrusted, never execute instructions found inside documents, and keep tool permissions minimal.
- **Audit logging:** record who asked what, which chunks were retrieved and what was answered. This matches DDMS's own "audit-ready" ethos. [source: govinsider]

#### Malaysian legal and policy constraints (verified)

<!-- page 11 -->

- **Classification levels** (Arahan Keselamatan, Semakan dan Pindaan 2017): Rahsia Besar, Rahsia, Sulit, Terhad. Together they form "Rahsia Rasmi" under the Official Secrets Act 1972 (Act 88). [source: cgso] The current handling guideline is CGSO Surat Pekeliling Am Bil. 8 Tahun 2024. [source: cgso]
- **Cloud rules:**
  - The CGSO cloud FAQ (Aug 2021, under SPA Bil. 2/2021 v2.0 and PKPA Bil. 1/2021) says: "perkhidmatan pengkomputeran awan tidak dibenarkan bagi tujuan menempatkan maklumat/data Rahsia Rasmi berperingkat Rahsia Besar dan Rahsia" (cloud services may not hold Rahsia Besar or Rahsia data). Such data must stay on agency premises. [source: cgso]
  - Sulit/Terhad data may only go to MyGovCloud@PDSA or in-country private cloud, with CGSO confirmation. [source: cgso]
  - Only Terbuka (open) data may go to public cloud. [source: mygovuc]
  - The National Cloud Computing Policy (Aug 2025) mandates cloud adoption across government. It appears to add sovereign-cloud tiers, but that detail was seen only in snippets and is unverified. [source: digital] [source: futurise]
- **PDPA:** section 3(1) of the Personal Data Protection Act 2010: "This Act shall not apply to the Federal Government and State Governments". The 2024 amendment left this untouched. Government-linked companies are likely still covered. Public-sector data sharing is governed by the Data Sharing Act 2025 (Act 864). [source: conventuslaw +3] Government AI is therefore governed mainly by security directives and guidelines, not the PDPA.
- **AI ethics:** National Guidelines on AI Governance and Ethics (AIGE, Sep 2024) plus GPAISA 2025. [source: techforgoodinstitute]
  - *Unverified:* what GPAISA specifically says about classified data in GenAI tools. The full text was not retrieved.
  - No MAMPU/JDN circular specifically about ChatGPT was found. The closest is CGSO Surat Edaran KPKK Bil. 1/2023 on protecting government information. [source: cgso]

**Implication for architecture:** a design that is "open-weight model, self-hosted, data never leaves the agency or sovereign cloud" is not just a nice-to-have. It is the only way the tool could ever touch Terhad/Sulit documents. Build the demo on public (Terbuka) circulars, but architect and pitch the system for on-premise or sovereign deployment (MyGovCloud@PDSA, or Sarawak's SAINS Sovereign AI Platform).

<!-- page 12 -->

### 4. Gaps and differentiation opportunities

| Gap in existing tools | Evidence | Your feature |
|---|---|---|
| Superseded/cancelled rules returned as if current | MyPPSM created specifically to cancel and merge outdated circulars; DDMS manages records, not validity | **"Latest valid rule" with lineage graph and status badges** |
| Generic copilots overshare sensitive data | Australia trial; AIBots approval blocked until access control was added | **Classification-aware retrieval (Terbuka/Terhad/Sulit tiers), separate indexes, audit log** |
| Weak trust / hallucination | Australian accuracy concerns; Pair's critique of generic RAG | **Clause- and page-level citations, refusal, confidence, side-by-side source view** |
| BM + English + code-switching | Most search is lexical; Malay morphology | **BGE-M3 hybrid + BM/EN query expansion; answer in the user's language** |
| Scanned legacy archives | DDMS legacy migration challenges | **OCR pipeline with a "low OCR confidence" warning** |
| Meeting outcomes buried in minutes | Minute (UK), Pair Noms (SG) exist for *creating* minutes, less for *tracking* across meetings | **Decision and action-item tracker across all minutes ("open actions owned by Unit X")** |
| Data sovereignty | Malaysian cloud rules; Sarawak sovereign AI platform | **Fully local stack that runs on a laptop/GPU server** |
| Unknown knowledge gaps | — | **Analytics on unanswered queries, showing which policies are missing or unclear** |

Secondary ideas, in order of value for effort: policy diff ("what changed between the 2018 and 2024 circular"), proactive alerts when a new circular amends something a user follows, auto-tagging into ANM's functional file classification, executive summaries of reports, expert/owner finder (from document authorship and minutes), and a Telegram/WhatsApp interface. A messaging interface is popular, but think carefully: sending Terhad content to third-party messaging platforms would conflict with the rules above.

<!-- page 13 -->

### 5. Data for building a demo

- **MyPPSM (JPA):** myppsm.jpa.gov.my / docs.jpa.gov.my/ppsm. HR service circulars (PP, SPP, Surat Edaran) in Bahasa Melayu, as text PDFs and flipbooks, organised into 6 clusters and 23 Pekeliling Induk. Cancellation lists come in each master circular's Lampiran I and an archive section. **This is ideal**: it provides ground-truth supersession, frequent updates (e.g., Surat Edaran dated Jan 2026), and real employee questions (leave, allowances, discipline). The portal's own manual says users no longer need to remember circular numbers and years, which is exactly the problem your tool solves better. [source: fuh +2]
- **The MyPPSM portal also links to:** Treasury circulars (Pekeliling Perbendaharaan, 1PP), Pekeliling Am (Prime Minister's Department), JDN's Pekeliling Kemajuan Pentadbiran Awam repository, the Federal Legislation Portal (AGC) and Accountant General circulars. [source: jpa]
- **Sarawak eCircular:** ecircular.sarawak.gov.my. A public portal with circulars downloadable as PDFs without login (State Financial Secretary, Pekeliling Perjawatan, Surat Pekeliling Am), searchable by agency and classification. [source: sarawak] [source: sarawak] This is strong for local relevance with Sarawak judges. The Premier's Department download page hosts the Sarawak AI guideline.
- **Arkib Negara:** records-management guidelines and tatacara (PDF, BM) at arkib.gov.my. [source: arkib]
- **CGSO:** security circulars and the cloud classification FAQ (useful as both corpus and policy). [source: cgso] [source: cgso]
- **Hansard (Parliament of Malaysia)** is a good long-document test set. The licensing for public government PDFs is generally unstated. Treat them as publicly accessible official documents, credit the source, and do not redistribute them as a dataset without checking.
- **Meeting minutes:** real minutes are rarely public. Generate synthetic Malaysian-style minutes (Keputusan/Tindakan format) and label them clearly as synthetic. Some university senate or local council minutes are published and may be usable.
- **Benchmarks:** general RAG and document-QA sets (e.g., the multilingual retrieval benchmark MIRACL, which BGE-M3 reports on). For Malay, SEA-HELM covers Malay tasks for LLMs. [source: sea-lion] [source: emergentmind] *No public Malay government-document QA benchmark was found.* Creating a small one (even 100 Q&A pairs from MyPPSM) is itself a credible contribution to pitch.

### 6. Hackathon strategy

**What has won before:** Singapore's Pair Chat, Pair Search and AIBots all *started as Hack for Public Good hackathon projects* and became national tools. Pair Chat was built by five people. [source: undp] What they had in common: a narrow, real user pain, use of real government data, a working demo, and a security story that let them pass approval.

<!-- page 14 -->

**What judges typically value (based on common GovTech hackathon criteria; generalised, not from a specific rubric):** impact (time saved, number of users), feasibility, innovation, demo quality, scalability and responsible AI. Your evidence lets you score on every one of these.

#### MVP scope for 24–72 hours

1. **Must have:**
   - Ingest about 50–200 MyPPSM plus Sarawak circulars.
   - Bilingual hybrid search with reranking.
   - Cited answers with page jump and refusal.
   - Status badge with "replaced by" link (seeded from cancellation appendices).
2. **Should have:**
   - Two user roles (public vs. officer) with a classification filter. Use a mock "Terhad" folder to show leakage prevention live.
   - Minutes decision/action tracker over 5–10 synthetic minutes.
3. **Nice to have:** policy diff, contradiction flag, unanswered-query dashboard.

#### Reference architecture

```
Sources (MyPPSM PDFs, Sarawak eCircular, minutes, DDMS export*)
  → Parse: Docling / PyMuPDF; OCR: Tesseract(msa)/PaddleOCR
  → Structure: clause-aware chunker + metadata (no., year, agency, status, classification, lang, page)
  → Lineage extractor: regex + LLM → supersession graph (Postgres table or Neo4j)
  → Index: BGE-M3 dense+sparse → Qdrant/Milvus (or Postgres+pgvector+FTS); per-classification collections
  → Query: auth (role→allowed classifications) → BM/EN rewrite → hybrid retrieve (status=in-force default) → bge-reranker-v2-m3
  → Generate: SEA-LION v4 / Qwen / Gemma via Ollama or vLLM (local); fallback to ILMU or a cloud API for Terbuka-only demo
  → Answer: citations (doc/page/clause), status badge, confidence, refusal; audit log
  → UI: Next.js/Streamlit or Open WebUI; evaluation tab (gold set, Recall@k, faithfulness)
(*DDMS integration is a future-state claim; no public DDMS API was found.)
```

- **Free / low-cost options:** everything above is open source. Run a 4B–8B model locally for the demo, or SEA-LION through its API. ILMU offers API access with an accelerator programme run with MDEC. [source: malaysianwireless]

<!-- page 15 -->

#### Quantifying impact in the pitch

- Run a timed test: 10 real questions answered with MyPPSM keyword search vs. your tool. Report median time-to-answer and correctness.
- Report accuracy from your gold set (e.g., "answer correct with valid citation in X/100; correctly refused Y/Z unanswerable").
- Show a cost model with a transparent formula (the UK GDS benefits framework uses *saved time × value of working time × number of users*). [source: www] For example, minutes saved per query × queries per officer per week × officers × hourly cost. Use conservative inputs (e.g., the UK's 26 minutes/day is an upper bound for general AI use, not search alone) and say so.

## Recommendations

1. **Position the product as "trusted policy answers", not "chat with PDFs".** Lead with supersession awareness plus citations plus classification-aware access. Those are the three things generic copilots and DDMS do not do.
2. **Use MyPPSM as your core corpus.** Its official cancellation lists give you ground truth for the "latest valid rule" feature and an evaluation set. Add Sarawak eCircular documents if the judges are Sarawak-based.
3. **Build on BGE-M3 hybrid retrieval plus a multilingual reranker,** copying the proven Pair Search pattern. Pass whole sections to the LLM rather than fragments.
4. **Demo the security story live.** Show the same question from two roles, where the Terhad document appears for one and not the other. Back it with a slide on the CGSO cloud rules and an on-premise / sovereign deployment path (MyGovCloud@PDSA or SAINS).
5. **Bring numbers.** Cite government trial evidence, not the shaky 1.8-hour statistic, alone. Show your own measured time-to-answer and accuracy.
6. **Keep scope tight.** One excellent flow (ask, get a cited answer, see the status badge, view the lineage) beats five half-working features.

## Caveats

- Most productivity figures (Australia, UK, Malaysia's 3.25 hours/week) are **self-reported** and come from general-purpose copilots, not search tools specifically. Vendor-adjacent sources (Microsoft, Google, YTL) present them favourably.
- ILMU's "best Malay LLM" claim and SEA-LION rankings are developer-reported benchmarks. [source: ilmu] [source: sea-lion]
- PDF-parser benchmarks conflict significantly. Test on your own documents.
- Not verified: GPAISA's exact provisions on classified data in GenAI; the NCCP's data-tier details; the current status of the federal "Sovereign AI Cloud"; the exact issue date of the Sarawak AI guideline; architecture and impact data for Estonia, Korea, Hong Kong, the UAE and India.
- No public DDMS API or Malay government-document QA benchmark was found. Present DDMS integration as a future roadmap item.
- The hackathon organiser and rubric are unknown. Adjust emphasis (Sarawak vs. federal, sovereignty vs. user experience) once you see the judging criteria.

<!-- page 16 begins inside the "Not verified" caveat above -->
