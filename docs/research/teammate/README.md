# Teammate Research: Summary, Fact-Check and Options

This page summarises the two research PDFs written by our teammates, shows which of their claims are safe to use, and sets out three solution options for the team to choose from. **We have not chosen a solution yet.** This page is meant to help us choose one.

*Written 7 October 2026 for team MixUp, AWS Student Community Day Kuching. The rules for this event: a 4-hour build, a prototype on localhost, AWS described in the pitch only, and judging on Innovation 30%, Feasibility 25%, Social/Economic Impact 25% and Pitch 20%.*

| File | What it is |
|---|---|
| [`government-knowledge-search.md`](government-knowledge-search.md) | Transcription of PDF 1, "Government Knowledge Search: Problem-Space Research" (16 pages). It covers the evidence that the problem is real, what other governments built, the technical approach and Malaysian rules on classified data. |
| [`pekeliling-navigator.md`](pekeliling-navigator.md) | Transcription of PDF 2, "Pekeliling Navigator: Competitive Analysis" (11 pages). It covers competitors, which features are "table stakes" and which are real differentiators, and a demo plan. |
| The original PDFs | In [`docs/`](../../): `Government Knowledge Search_ Problem-Sp...pdf` and `Pekeliling Navigator_ Competitive Analy...pdf` |

**Words used on this page**

| Word | Meaning |
|---|---|
| Pekeliling | A circular: an official instruction to government staff |
| Supersession | When a new circular cancels or replaces an old one ("*membatalkan*", "*menggantikan*") |
| In force (*berkuat kuasa*) | Still valid today; not cancelled |
| RAG | The AI first finds relevant passages in our documents, then answers using only those passages |
| Terbuka / Terhad / Sulit | Open / Restricted / Confidential. These are Malaysian security labels on documents. |
| Table stakes | A feature every competitor already has, so it does not count as innovation |

---

## In one minute

1. **The problem is real, and Malaysia has already admitted it.** In 2021 JPA built MyPPSM specifically to cancel and merge outdated circulars. JPA's older portal could search circular *titles* only. The Treasury and Sarawak portals record cancellations in titles or inside PDF attachments. Officers really do struggle to know which rule is still valid.
2. **"Chat with your PDFs, with citations" is not innovative any more.** Gemini and NotebookLM are already free for up to 445,000 Malaysian civil servants until 2028. Student projects on GitHub already ship cited answers with page highlighting. The UK even retired its own document-chat tool (Redbox) because Copilot did the same job.
3. **The open gap is validity.** No tool we know of answers "which rule is in force today, what did it replace, and does the federal or the Sarawak rule apply to me?" for administrative circulars. Both PDFs reach this conclusion on their own.
4. **Both PDFs missed ADAM AI.** Sarawak launched ADAM AI on 7 July 2026. It is an on-premise AI assistant for Sarawak civil servants and includes an e-Circular agent. Kuching judges will probably know it. So we must never say "first" or "nobody has a pekeliling chatbot". We position ourselves as the validity layer that ADAM AI and similar tools do not have, as far as public sources show.
5. **Trust and security are the entry ticket, not the headline.** Malaysian rules allow only *Terbuka* (open) information on public cloud. Classified documents need on-premise or approved government hosting. Our demo should use only public or fictional documents and say so. A filter that decides which documents each role may see, applied before the AI reads anything, is a good trust slide, but Copilot, Glean and Singapore's AIBots already do this.
6. **Use government trial numbers, not the famous old statistics.** "1.8 hours a day searching" (McKinsey, 2012) and "2.5 hours a day" (IDC, actually from 2001) are weak. Use Malaysia's AI at Work pilot (97% of 270 officers reported saving 3.25 hours a week) and the UK and Australian trials. All of these figures are self-reported, so say so.
7. **Both PDFs plan for 24 to 72 hours and assume the judging rubric is unknown.** We have 4 hours and a known rubric. Pick one "hero" flow and make it work perfectly on stage.

---

## Fact-check results

An independent check of each PDF was done on 7 October 2026. Many checks relied on search-result snippets, because several government sites block automated access. **Before any number goes on a slide, one of us should open the link and read it.**

How to read the table:

- **Confirmed** or **Corrected**: usable, but use the wording in the "Use in pitch?" column.
- **Unverifiable**: avoid it, or soften it.
- **Refuted**: do not use it.

### Problem and time-saving numbers

| Claim (from the PDFs) | Verdict | Use in pitch? | Source link |
|---|---|---|---|
| "Employees spend 1.8 hours a day (9.3 hours a week) searching" (McKinsey 2012) | Corrected | **Avoid on slides.** If you need it as background, say "about 19% of the workweek (McKinsey Global Institute, 2012, all industries)". The "9.3 hours" figure is not in the report. | [McKinsey report](https://mckinsey.com/~/media/McKinsey/Industries/Technology%20Media%20and%20Telecommunications/High%20Tech/Our%20Insights/The%20social%20economy/MGI_The_social_economy_Full_report.ashx) |
| "2.5 hours a day searching" (IDC) | Corrected | **Avoid.** It comes from a 2001 IDC paper, so it is not current data. | [IDC 2001 paper](https://computhink.com/wp-content/uploads/2015/10/IDC20on20The20High20Cost20Of20Not20Finding20Information.pdf) |
| IDC 2012: 5 hours a week searching for documents, and almost half of that time ends without finding the document | Confirmed, but only through vendor blogs | **Avoid or soften.** The source is weak. | [M-Files blog](https://www.m-files.com/blog/how-long-does-it-actually-take-to-find-a-document/) |
| Malaysia AI at Work pilot: 270 officers; 97% saved 3.25 hours a week; 91% said quality improved | Confirmed | **Yes:** "In Malaysia's AI at Work pilot, 97% of 270 public officers reported saving 3.25 hours a week (self-reported; Google Cloud, Feb 2025)." The 270 officers came from several agencies, not JDN alone. The 91% figure is about work quality, not time saved. | [Google Cloud press release](https://www.googlecloudpresscorner.com/2025-02-05-445,000-Public-Officers-in-Malaysia-to-Benefit-from-Generative-AI-Under-the-AI-at-Work-2-0-Initiative-by-the-Ministry-of-Digital-and-Google-Cloud) |
| AI at Work 2.0: 445,000 civil servants get Gemini and NotebookLM Plus free until 2028 | Confirmed | **Yes:** say "**up to** 445,000 public officers have access". This is not a count of active users. | [Ministry of Digital](https://www.digital.gov.my/en-GB/siaran/Ministry-Of-Digital,-Through-NAIO,-Secures-AI-Training-For-445,000-Civil-Servants-Under-Google-AI-At-Work-2.0-Initiative) |
| UK: 20,000 civil servants saved 26 minutes a day | Confirmed | **Yes:** "a self-reported average of 26 minutes a day (UK Copilot experiment, Sep–Dec 2024)" | [GOV.UK report](https://www.gov.uk/government/publications/microsoft-365-copilot-experiment-cross-government-findings-report) |
| UK: "over 70% spent less time searching; 82% wanted to continue" | Corrected | **Yes, reworded:** "over 70% said it cut time spent searching for information **and on mundane tasks**; 82% would not want to go back" | [GOV.UK report (HTML)](https://www.gov.uk/government/publications/microsoft-365-copilot-experiment-cross-government-findings-report/microsoft-365-copilot-experiment-cross-government-findings-report-html) |
| UK: 17% reported no time saved | Confirmed | **Yes.** This is a good honesty point. | [PublicTechnology](https://www.publictechnology.net/2025/06/03/education-and-skills/major-government-copilot-trial-finds-half-an-hour-average-time-savings-per-day/) |
| Australia: Copilot trial with 7,600+ staff in 60+ agencies (Jan–Jun 2024); about 1 in 3 used it daily; up to about an hour a day saved on summarising and searching | Confirmed (self-reported) | **Yes** | [DTA](https://www.dta.gov.au/blogs/evaluation-whole-government-trial-generative-ai-now-available) |
| Australia: Copilot "surfaced sensitive data that staff had not classified or stored appropriately"; inaccuracy reduced the benefits | Confirmed | **Yes.** This is a strong trust point. The DTA calls it an information-management problem rather than a Copilot bug, so say that if a judge asks. | [DTA findings](https://www.digital.gov.au/initiatives/copilot-trial/summary-evaluation-findings/cts-evaluation-findings) |

### Malaysia and Sarawak

| Claim (from the PDFs) | Verdict | Use in pitch? | Source link |
|---|---|---|---|
| MyPPSM (launched 2021, in force 2022) was built to cancel and merge outdated circulars into 6 clusters and 23 master circulars (Pekeliling Induk) | Confirmed | **Yes.** This is our strongest proof that the problem is real. | [JPA](https://www.jpa.gov.my/perkhidmatan/surat-edaran/pelaksanaan-pekeliling-perkhidmatan-sumber-manusia-myppsm) |
| MyPPSM does not show circulars marked "Terhad" | Confirmed | **Yes** | [JPA MyPPSM FAQ](https://docs.jpa.gov.my/docs/myppsm/Soalan-Lazim-MyPPSM/) |
| JPA's older portal (MyPPSPP) searched titles only, and labelled circulars Kuatkuasa / Dibatalkan / One-off | Confirmed | **Yes.** Call it "JPA's older portal". | [MyPPSPP](https://docs.jpa.gov.my/ppspp/) |
| Treasury circulars are marked "(PEKELILING DIBATALKAN)" | Confirmed | **Yes.** Bonus fact: the number "PS 2.7" now refers to a different, current circular. That kind of number reuse is a good example of why a validity check is needed. | [Treasury PPP archive](https://ppp.treasury.gov.my/arkib/frontend) |
| Sarawak eCircular shows "Status: Active" on a 1982 circular, so its status data is "unreliable" | Confirmed (the screen); the "unreliable" conclusion is not | **Soften.** Say "status fields don't tell you whether an old circular was cancelled". Only say "unreliable" if we find a cancelled circular that still shows Active. | [eCircular 83/1982](https://ecircular.sarawak.gov.my/view_circular.php?id=7485) |
| Sarawak PPNS Bil. 5/2026 lists the circulars it cancels only in an attachment | Confirmed (the attachment number is unclear) | **Yes.** It is a good real example. Check the page by hand before naming the attachment. | [eCircular PPNS 5/2026](https://ecircular.sarawak.gov.my/view_circular.php?id=9573) |
| Sarawak eCircular holds 3,715 circulars | Unverifiable | **Avoid or soften:** say "thousands of circulars", or check the live site first. | [eCircular search](https://ecircular.sarawak.gov.my/advance_search.php) |
| DDMS 2.0 is used by 395 agencies with 56,000+ users | Confirmed (GovInsider, quoting JDN's Director-General) | **Yes**, with the source. Bernama gave different figures (370 agencies, about 60,000 users, 12.3 million records), so name the source for each number. | [GovInsider](https://govinsider.asia/intl-en/article/malaysia-digitalises-public-sector-document-management) |
| "Malaysia still lacks a cross-document 'current valid rule' layer" / "no pekeliling chatbot exists" | **Refuted** | **Do not use.** Sarawak's ADAM AI (launched 7 Jul 2026) answers from approved government documents and circulars. Public sources do not say it tracks which circular is still valid. That narrower gap is ours. | [UKAS Sarawak: ADAM AI](https://ukas.sarawak.gov.my/web/subpage/news_view/44571) |
| JDN's GCBot is "the closest existing match" | Corrected | **Usable only as:** "GCBot is a keyword-based search inside GovChat, linked to JDN's policy repository." ADAM AI is now the closest match. | [GovChat FAQ](https://gcinfo.mampu.gov.my/index.php/soalan-lazim) |
| JDN's AISHAH chatbot launched 22 Jul 2024 | Confirmed | **Yes.** It answers questions about JDN services only, for the public. | [JDN AIaaS blog](https://aiaas.jdn.gov.my/jdn/blog/2025/08/15/ai-chatbot-aishah/) |
| Sarawak Sovereign AI Infrastructure Platform launched 17 Aug 2026, run by SAINS and hosted in Sarawak | Confirmed | **Yes:** "deployable on the SAINS platform". Do not imply that we have a partnership. | [Borneo Post](https://www.theborneopost.com/2026/08/17/new-platform-launched-to-boost-sarawaks-sovereign-ai-capabilities/) |
| Sarawak AI guideline "V1_2025"; its para 5.6 endorses AI search across circulars | Corrected; para 5.6 is unverifiable | Call it by its official name: **Surat Pekeliling ICT Bil. 4 Tahun 2025** (17 Sep 2025). **Do not quote para 5.6** until one of us reads the PDF. | [eCircular ICT 4/2025](https://ecircular.sarawak.gov.my/view_circular.php?id=9506) |
| "Uploading official documents to ChatGPT breaches the OSA" | Corrected (overstated) | **Do not use as written.** Only classified documents (Terhad and above) are restricted. Public Terbuka circulars are not. | [eCircular ICT 4/2025](https://ecircular.sarawak.gov.my/view_circular.php?id=9506) |
| Sarawak civil service: 98% of more than 19,220 officers finished the AI and anti-phishing modules | Confirmed | **Yes.** It shows that officers are ready to use AI tools. | [Sarawak Tribune](https://www.sarawaktribune.com/sarawak-civil-service-urged-to-strengthen-cyber-readiness/) |
| SAINS: "from digital government to AI government"; "200+ departments can submit proposals" | Unverifiable | **Avoid** | [Premier's Dept](https://premierdept.sarawak.gov.my/web/subpage/news_view/8199/SCSDU) |

### Rules on classified data

| Claim (from the PDFs) | Verdict | Use in pitch? | Source link |
|---|---|---|---|
| CGSO cloud rules: Rahsia and Rahsia Besar stay on agency premises; Sulit and Terhad may go only to MyGovCloud@PDSA or an in-country private cloud, after consulting CGSO; public cloud is for Terbuka only | Confirmed | **Yes.** This is the basis for "our demo uses Terbuka documents only" and for the hosting slide. | [CGSO cloud FAQ](https://www.cgso.gov.my/wp-content/uploads/2021/08/Lam1-FAQ-Klasifikasi-Data-CCC_kemaskini30Ogos21_Uploadportal.pdf) |
| MyGovUC: Terhad, Sulit, Rahsia and Rahsia Besar are "TIDAK DIBENARKAN SAMA SEKALI" on Google Workspace | Corrected | **Yes, reworded:** "only Terbuka information may be kept on Google Workspace". Don't quote the all-capitals phrase, because there is a narrow secure-email exception for Terhad and Sulit. | [MyGovUC FAQ](https://www.mygovuc.gov.my/uploads/content-downloads/file_20250922093232.pdf) |
| Classification levels under Arahan Keselamatan: Terhad, Sulit, Rahsia, Rahsia Besar (OSA 1972) | Confirmed | **Yes.** Note that "Terbuka" means open and is not one of the four secret levels. | [CGSO SPA 8/2024](https://www.cgso.gov.my/wp-content/uploads/2024/09/SPA-8-TAHUN-2024-GARIS-PANDUAN-PENGURUSAN-DAN-PENGENDALIAN-RAHSIA-RASMI-DALAM-PERKHIDMATAN-AWAM.pdf) |
| PDPA does not apply to federal and state governments; the Data Sharing Act 2025 covers federal agencies only | Confirmed | **Yes, in Q&A only.** The Data Sharing Act does not cover Sarawak state agencies. | [Conventus Law](https://conventuslaw.com/report/malaysia-overview-on-the-data-sharing-act-2025/) |

### Competitors and overseas tools

| Claim (from the PDFs) | Verdict | Use in pitch? | Source link |
|---|---|---|---|
| Singapore: about 80% of 150,000 officers used Pair Chat; "over 20,000 bots" | Confirmed, but the bots belong to AIBots, not Pair Chat | **Yes**, attributed correctly | [MDDI reply, 5 Nov 2025](https://www.mddi.gov.sg/newsroom/mddi-s-response-to-pq-on-progress-of-adopting-ai-tools-within-public-service/) |
| Singapore's AIBots could not get approval until it added access control | Confirmed | **Yes:** "access control was the gate to adoption" | [AIBots on Medium](https://medium.com/aibots/ctrl-alt-future-feature-how-aibots-have-made-work-work-better-for-the-singapore-government-ff04058556f7) |
| AIBots: 23,300 active bots and 118 agencies | Unverifiable | **Avoid** these two numbers. 40,300 users (Aug 2024–Oct 2025) is confirmed. | [GovTech AIBots deck](https://file.go.gov.sg/aibots-intro-20250515.pdf) |
| Pair Chat is "still run by a lean team of seven"; Pair Search indexes "about 58,000 documents" | Unverifiable | **Avoid.** "Pair began as a five-person hackathon project in January 2023" is confirmed. | [UNDP blog](https://www.undp.org/policy-centre/singapore/blog/pairing-ai-public-sector-impact-singapore) |
| UK retired Redbox (document chat) in Dec 2025, after 6,000+ users, because Copilot offered similar functionality | Confirmed | **Yes:** "generic document chat gets absorbed by big vendors" | [UK DBT blog](https://digitaltrade.blog.gov.uk/2026/02/04/from-redbox-to-assist-building-ai-tools-that-balance-innovation-and-trust/) |
| Singapore's Noms by Pair drafts minutes in government format | Corrected | **Don't present it as live.** It closes on 30 Oct 2026. | [Pair Noms guide](https://pair.guides.gov.sg/pair-noms/pair-noms-guide) |
| Microsoft in-country Copilot processing for Malaysia "announced for 2026" | Corrected | **Do not use.** Microsoft's April 2026 update dropped Malaysia from the schedule, so there is no current public date. | [Microsoft blog](https://www.microsoft.com/en-us/copilot/blog/2025/11/04/microsoft-offers-in-country-data-processing-to-15-countries-to-strengthen-sovereign-controls-for-microsoft-365-copilot/) |
| NotebookLM "answers from static copies" | Corrected | **Reword:** "Even with Google Drive sync, NotebookLM doesn't know which circular cancels another, and uploaded PDFs stay static." | [Android Authority](https://www.androidauthority.com/notebooklm-auto-google-drive-syncing-3671289/) |
| Concentric AI: 16% of business-critical files overshared; 802,000 at-risk files per organisation | Corrected | **Avoid.** If you must use it, say "over 15% (vendor study, 2022 data)". | [Concentric AI](https://concentric.ai/press-release/latest-industry-data-risk-report-from-concentric-ai-shows-60-percent-increase-in-oversharing-of-sensitive-data-over-the-past-year/) |
| "Average sensitivity-label coverage of only 12%" | Corrected (consultancy marketing figure) | **Avoid** | [EPC Group](https://www.epcgroup.net/microsoft-365-tenants-not-ready-copilot-2026) |
| A Malaysian GitHub project (ai-legal-tool) proposes validity checks for Acts | Corrected: it has already shipped repeal badges | **Yes**, as: "others do this for Acts of Parliament; we do it for circulars" | [GitHub issue #60](https://github.com/aishahsofea/ai-legal-tool/issues/60) |
| Amazon Quick: $20 or $40 per user per month, plus $250 per account per month | Confirmed | **Yes.** It is AWS's own answer to "why not just buy X?", so mention it in the AWS section. | [AWS pricing](https://aws.amazon.com/quick/pricing) |
| Docling: IBM reports 97.9% table accuracy | Unverifiable | **Avoid** | [Ertas blog](https://www.ertas.ai/blog/pdf-parsing-accuracy-benchmark-docling-unstructured) |
| Our event is "most likely AI HackerDorm" and the rubric is unknown | **Refuted** | **Do not use.** We are at AWS Student Community Day Kuching and the rubric is known. | [AI HackerDorm](https://aihackerdormsarawak.org/) |

> Note: the PDF 2 fact-check contradicts itself in one place. It says "91% of 270 JDN officers saved 3.25 hours", but the press release says **97%** saved 3.25 hours and 91% reported better work quality. Use the press-release wording.

### Safe statistics and news to quote

Each line below is ready to say. Every one of them should still be read at its link before it goes on a slide.

- **Malaysia's own pilot:** "97% of 270 public officers in the AI at Work pilot reported saving 3.25 hours a week (self-reported)." ([Google Cloud, Feb 2025](https://www.googlecloudpresscorner.com/2025-02-05-445,000-Public-Officers-in-Malaysia-to-Benefit-from-Generative-AI-Under-the-AI-at-Work-2-0-Initiative-by-the-Ministry-of-Digital-and-Google-Cloud))
- **Scale of AI access:** "Up to 445,000 public officers have Gemini and NotebookLM Plus under AI at Work 2.0, free until 2028." ([Ministry of Digital](https://www.digital.gov.my/en-GB/siaran/Ministry-Of-Digital,-Through-NAIO,-Secures-AI-Training-For-445,000-Civil-Servants-Under-Google-AI-At-Work-2.0-Initiative))
- **JPA admits the problem:** "JPA built MyPPSM to cancel and merge outdated circulars into 23 master circulars." ([JPA](https://www.jpa.gov.my/perkhidmatan/surat-edaran/pelaksanaan-pekeliling-perkhidmatan-sumber-manusia-myppsm))
- **Title-only search:** "JPA's older circular portal searched titles only, not the content." ([MyPPSPP](https://docs.jpa.gov.my/ppspp/))
- **Cancellations hidden in attachments:** "Sarawak's PPNS Bil. 5/2026 lists the circulars it cancels in an attachment." ([eCircular](https://ecircular.sarawak.gov.my/view_circular.php?id=9573))
- **Records exist, answers don't:** "DDMS 2.0 serves 395 agencies and 56,000+ users. It stores records; it does not answer questions." ([GovInsider](https://govinsider.asia/intl-en/article/malaysia-digitalises-public-sector-document-management))
- **UK trial:** "20,000 UK civil servants reported saving 26 minutes a day on average; 17% saved nothing." ([GOV.UK](https://www.gov.uk/government/publications/microsoft-365-copilot-experiment-cross-government-findings-report))
- **Trust risk:** "Australia's trial of 7,600+ staff found Copilot surfaced sensitive data that staff had not classified or stored appropriately." ([DTA](https://www.digital.gov.au/initiatives/copilot-trial/summary-evaluation-findings/cts-evaluation-findings))
- **Generic tools get absorbed:** "The UK retired its Redbox document-chat tool in Dec 2025 because Copilot offered similar functionality." ([UK DBT blog](https://digitaltrade.blog.gov.uk/2026/02/04/from-redbox-to-assist-building-ai-tools-that-balance-innovation-and-trust/))
- **Access control gates adoption:** "Singapore's AIBots needed proper access control before it was approved." ([AIBots](https://medium.com/aibots/ctrl-alt-future-feature-how-aibots-have-made-work-work-better-for-the-singapore-government-ff04058556f7))
- **Data rules:** "Only Terbuka information may go on public cloud. Sulit and Terhad need MyGovCloud@PDSA or an in-country private cloud. Rahsia stays on premises." ([CGSO FAQ](https://www.cgso.gov.my/wp-content/uploads/2021/08/Lam1-FAQ-Klasifikasi-Data-CCC_kemaskini30Ogos21_Uploadportal.pdf))
- **Sarawak context:** "ADAM AI, launched 7 Jul 2026, is the Sarawak civil service's AI colleague." ([UKAS](https://ukas.sarawak.gov.my/web/subpage/news_view/44571)) "The SAINS Sovereign AI Infrastructure Platform launched on 17 Aug 2026." ([Borneo Post](https://www.theborneopost.com/2026/08/17/new-platform-launched-to-boost-sarawaks-sovereign-ai-capabilities/))
- **AWS tie-in:** "AWS was the main sponsor of Digital Penang's AI Hackathon for Public Sector 2026, where 14 public-sector teams built AI tools." ([Digital Penang](https://digitalpenang.my/2026/06/30/ai-hackathon-for-public-sector-2026-in-digital-penang/))

---

## Where the two PDFs agree / disagree

### They agree on

- **The gap is "which rule is still valid".** Both make a "latest valid rule" engine with a supersession (lineage) graph the core idea. Both say answers should come from in-force documents by default, with the cancelled chain shown on request.
- **Evidence:** both use MyPPSM, Treasury and Sarawak eCircular as proof, and both suggest these portals as demo data.
- **Basics:** cited answers, refusing when no source supports an answer, BM and English search, BGE-M3 plus a reranker, and checking our own accuracy with a small set of test questions.
- **Security:** demo with Terbuka documents only, show a role switch where a mock Terhad document disappears, and pitch on-premise or sovereign hosting (MyGovCloud@PDSA or SAINS).
- **DDMS 2.0** is a future data source to connect to, not a competitor.
- **Statistics:** use government trial data and be honest that it is self-reported.
- **Minutes tracking** is secondary to the validity idea.

### They disagree or differ

| Topic | PDF 1 (Government Knowledge Search) | PDF 2 (Pekeliling Navigator) | What we should do |
|---|---|---|---|
| What counts as innovative | "Trust" bundle: cited, current, permission-aware and bilingual | Citations, hybrid search and OCR are **table stakes**. Classification is only "partly differentiated". Spend the demo on validity. | Follow PDF 2. Our competitors already have citations. |
| Extra differentiators | Minutes tracker, contradiction flag, unanswered-question analytics | Adds **federal vs Sarawak** disambiguation, **gred/skim** personalisation, **"what changed for you"** alerts and a draft compliance checker | Federal vs Sarawak and "what changed" are cheap and local. Consider them. |
| Minutes tracker | "Should have" | Ranked 10th of 12: "cut it, or show one screen" | One screen at most, unless we pick Option C |
| Closest competitor | Says Malaysia "still lacks" this layer | Says JDN GCBot is closest and "no pekeliling chatbot found" | **Both are out of date:** Sarawak's ADAM AI (July 2026) exists. GCBot is keyword search. |
| Build time and rubric | 24–72 hours; rubric unknown | 24–48 hours; guesses AI HackerDorm | We have **4 hours** and a known rubric. Cut scope hard. |
| AI model | Open-weight models run locally (SEA-LION, ILMU) | Same | Our draft prototype uses Claude on Amazon Bedrock, which fits an AWS event, with an offline fallback. The pitch needs one honest sentence about classified data (see open question 4). |
| Arguments against competitors | — | Some are now outdated: NotebookLM "static copies", Microsoft "Malaysia in-country 2026", "uploading breaches the OSA" | Use the corrected wording from the fact-check table |

### Compared with our other docs

`docs/research/` had no other research files when this page was written, so we compared the PDFs with [`docs/problem-explainer.md`](../../problem-explainer.md) instead.

- **Agree:** the gap ("current valid rule + sources + BM/EN + safe for government data"), the AI at Work pilot numbers, and "DDMS stores files but does not answer questions".
- **Missing from the explainer:** ADAM AI (Sarawak), JDN's GCBot and AISHAH, JPA's title-only search portal, and the exact CGSO cloud rules. These are worth adding.
- **Wording to fix in the explainer:** "445,000 public officers" should be "up to 445,000". The DDMS figure (395 agencies, 56,000 users) is cited to a vendor case study; GovInsider quoting JDN's Director-General is a stronger source for the same number.
- **In the explainer but not in the PDFs (and not checked by these fact-checks):** JPA's 2026 review of rules older than 20 years, the Government Service Efficiency Commitment Act 2025 (Act 867), 1.3 million federal civil servants, and the AWS Malaysia Region investment. These are strong "why now" points, but they still need their own check. The explainer points to `research/06-malaysia-news.md` for that check, and that file does not exist yet.

---

## Solution options for the team to choose

All three options fit the problem statement. They differ in **who the hero of the demo is**: the *document* (A), the *officer* (B) or the *meeting* (C).

### Option A: Pekeliling Navigator (validity first)

**One-line pitch:** "Ask in BM or English and get the rule that is in force today, with the clause, the page and what it replaced. Never cite a cancelled circular again."

**What the demo shows**
- **Wrong answer vs right answer:** the same question asked in "plain search" mode and in Navigator mode. Plain mode quotes the cancelled 2021 travel-claim circular (30 days, RM0.55/km). Navigator mode answers from the 2024 circular (60 days, RM0.70/km) and labels the old one "Dibatalkan, replaced by Bil. 1/2024".
- **Lineage and "what changed":** a map of which circular replaced which, and a card that reads: "30 → 60 days; RM0.55 → RM0.70/km; paper forms → e-Tuntutan; effective 1 March 2024".
- **A new circular arrives:** we upload it, the app spots "*membatalkan ...*", and the map and the answers update live.

**Innovation angle:** validity awareness for *administrative circulars*. Gemini, NotebookLM, Copilot, MyPPSM search and eCircular do not offer it, and neither does ADAM AI according to public sources. Legal tools do this for Acts of Parliament; nobody we found does it for circulars.

**Feasibility in 4 hours on localhost:** **High.** The draft prototype already has document status, "supersedes" links, an in-force filter, a map tab and upload detection. The work left is connecting them in the Ask tab, building one "what changed" card and adding a side-by-side toggle. Fictional sample data is ready.

**Impact story for Malaysia and Sarawak:** JPA built a whole portal to clean up outdated circulars, yet officers still answer the public using rules that were cancelled years ago. Every wrong answer means a rejected claim, rework or a complaint. In Sarawak, cancellations sit inside PDF attachments, and officers follow both federal and state circulars. The Navigator could feed ADAM AI's e-Circular agent and run on the SAINS sovereign platform. For the economic case, use the formula minutes saved × questions per week × officers × hourly cost, with conservative inputs.

**Risks**
- Judges may think "it's just RAG" unless the wrong-vs-right moment is clear.
- A wrong "valid" badge is worse than no badge. Show "verified by the policy owner / not yet verified".
- ADAM AI could add this feature later, so pitch ourselves as a partner layer.
- Fictional data can look like a toy. Adding one real public circular chain would help.

**Score estimate:** Innovation 24/30 · Feasibility 21/25 · Impact 20/25 · Pitch 17/20 = **about 82/100**

### Option B: Role-aware officer assistant (onboarding copilot)

**One-line pitch:** "Tell it who you are (federal or Sarawak service, your grade, your clearance), and it answers only with rules that apply to you and that you are allowed to see. It also gives new officers a 'what changed for you' briefing."

**What the demo shows**
- **Same question, two officers, two answers:** a Sarawak state officer and a federal officer posted in Sarawak see different rules side by side.
- **Clearance filter:** an officer cleared only for Terbuka asks a question, and the mock Terhad document never appears, because it is filtered out *before* the AI reads anything.
- **New-officer briefing:** "the 10 rules you need in your first month as a Gred 41 officer", plus "what changed since your last login", each item with its source.

**Innovation angle:** personalisation by gred/skim and federal-versus-Sarawak disambiguation. PDF 2 rates both 5/5 for uniqueness. The clearance filter maps to Malaysian security levels, but the idea of filtering by permissions is not new (Glean, Copilot and AIBots already do it).

**Feasibility in 4 hours on localhost:** **Medium-low.** The prototype has no profile, clearance, jurisdiction or grade fields. We would need new sample documents whose rules really differ by grade or service, and we would have to make up those rules convincingly. Four hours would be tight.

**Impact story for Malaysia and Sarawak:** officers rotate between agencies, and knowledge leaves with them. "Preserving institutional memory" is one of DDMS 2.0's stated goals. Sarawak runs its own civil service alongside federal departments, so "which rule applies to me?" is a real local question. 98% of Sarawak's 19,000+ officers have already done AI training.

**Risks**
- It overlaps most with ADAM AI, a general assistant for Sarawak civil servants. Judges will ask "how is this different from ADAM?"
- Grade rules are complex, and wrong personalisation is worse than none.
- We have no real grade data.
- Hard to show in a 6-minute pitch that an answer is the right one for that person.

**Score estimate:** Innovation 21/30 · Feasibility 14/25 · Impact 19/25 · Pitch 14/20 = **about 68/100**

### Option C: Minutes-to-Decisions tracker linked to policies

**One-line pitch:** "Turns a pile of meeting minutes into a live list of decisions and actions (who owes what, by when), and warns when a decision rests on a circular that has since been cancelled."

**What the demo shows**
- **Extract:** pick a set of minutes and get a table of *Keputusan* (decisions) and *Tindakan* (actions: owner, due date, status), each with a page citation.
- **Track across meetings:** "open actions for Unit X", overdue items, and "what was decided about hybrid work across all meetings?"
- **Policy-link alert:** "Decision 3.1 of Meeting 4/2025 cites GP-ICT 1/2022, which was replaced by GP-ICT 2/2025."

**Innovation angle:** it mines *historical* minutes across meetings and links them to which circular is still valid. Existing government tools (UK Minute, Singapore's Noms, which closes in Oct 2026) draft minutes from live meetings; they do not track decisions across an archive. PDF 2 rates the uniqueness 3/5.

**Feasibility in 4 hours on localhost:** **Medium.** Malaysian minutes use stable markers ("Keputusan", "Tindakan"), so extraction is reliable. The prototype has 2 synthetic minutes and stub functions. We would need 4 to 6 more synthetic minutes and a new tracker screen.

**Impact story for Malaysia and Sarawak:** committee decisions get lost between meetings, and actions slip. Better follow-through means faster, more consistent decisions, which matches the "make better decisions" part of the problem statement. However, fewer people use it (committee secretariats and managers), and there is no Malaysian data on how much time is lost.

**Risks**
- Real minutes are rarely public, so the whole demo is synthetic.
- It looks like existing meeting tools (Teams recap, Otter, Read.ai).
- It is a weaker fit with "searchable knowledge resource".
- Both PDFs call minutes tracking secondary.

**Score estimate:** Innovation 20/30 · Feasibility 17/25 · Impact 15/25 · Pitch 14/20 = **about 66/100**

### Side by side

| | Innovation (30) | Feasibility (25) | Impact (25) | Pitch (20) | Total |
|---|---|---|---|---|---|
| **A. Pekeliling Navigator** | 24 | 21 | 20 | 17 | **82** |
| B. Role-aware officer assistant | 21 | 14 | 19 | 14 | 68 |
| C. Minutes-to-Decisions tracker | 20 | 17 | 15 | 14 | 66 |

*These scores are our rough guesses to help the discussion. They do not predict what the judges will give.*

### Recommended: Option A

- **Best evidence:** both PDFs chose validity as the #1 differentiator on their own, and the proof is Malaysian, recent and checked (MyPPSM, JPA's title-only portal, Treasury's "DIBATALKAN" tags, Sarawak PPNS 5/2026).
- **Most feasible:** most of the plumbing already exists in the draft prototype, so our 4 hours go into a polished demo rather than new code.
- **Easiest to pitch in 6 minutes:** a "wrong answer vs right answer" moment that judges will remember, and a clear reply to "why not Gemini or ADAM AI?". If time remains, borrow one screen from B (the Terhad role switch, as the trust slide) and one from C ("this decision cites a cancelled circular").

---

## How the draft prototype fits

> **The prototype is changing while you read this.** It is still a draft. At about 04:10 on 7 Oct, a rewrite toward Option A began in the working copy and has not been committed yet. This section describes both versions. The committed draft stays in git history (commit `55ad34c`) if we choose B or C and need it back.

**The committed draft (commit `55ad34c`):** a Streamlit app called "MixUp" in [`prototype/`](../../../prototype/). It has five tabs: Ask, MixUp Map, Smart Upload, Minutes & Conflicts, and Library.

- **AI:** Claude on Amazon Bedrock, with an offline mode that falls back to keyword search. Titan embeddings are optional.
- **Search:** BM25 keyword search with BM↔EN glossary expansion.
- **Data:** 10 **fictional** documents for "Kerajaan Negeri Contoh". They include two supersession chains: travel claims (Bil. 3/2021 → Bil. 1/2024) and cloud guidelines (2022 → 2025). There are also a WFH SOP and a hybrid-work policy that disagree, 2 sets of minutes and 1 report.
- **Unfinished parts:** several features are still stubs. `answer.ask()` only lists the top passages, and `compare.what_changed()`, `minutes.extract_actions()` and `conflicts.check()` return placeholders.

**The rewrite in progress (uncommitted):** the minutes, conflict, upload and map modules and the old sample data have been removed. The new `mixup/models.py` follows Option A and PDF 2 closely:

- **Statuses** with BM labels: Berkuat kuasa, Dipinda, Dibatalkan, Sekali sahaja, Belum disahkan.
- **Relations** (CANCELS, SUPERSEDES, AMENDS, REFERENCES), each with evidence, a confidence score and a "verified" flag. Only verified relations change a document's status.
- **Clause-level chunks** with a breadcrumb (for example "SPP 1/2023 > PEMAKAIAN > 4.1").
- **Jurisdiction** (Federal, Sarawak, or federal adopted by Sarawak) and a document **classification level**.
- **A user** with clearance, jurisdiction and grade.

So the rewrite is **Option A with the cheapest parts of Option B** (the federal vs Sarawak toggle and the clearance filter). It has no minutes tracking.

**Which option it matches:** **Option A**, in both versions. The committed draft has `status` and `supersedes` / `superseded_by` in `data/manifest.csv`, a version graph and supersession detection in `mixup/versions.py`, an `include_superseded` flag in `mixup/search.py`, the map tab and Smart Upload. Only the committed draft has building blocks for C (the minutes tab stub, `discussed_in` links and 2 sets of minutes). Only the rewrite has building blocks for B.

**What would need to change for each option** (file names refer to the committed draft. In the rewrite, the A and B data fields in the table below mostly exist already.)

| | Option A: Navigator | Option B: Role-aware assistant | Option C: Minutes tracker |
|---|---|---|---|
| Core logic | `mixup/answer.py`: make `ask()` search with `include_superseded=False` by default, cite the document and page, and add a notice when a cancelled document matched ("Bil. 3/2021 was cancelled by Bil. 1/2024"). `mixup/compare.py`: implement `what_changed()` for the two existing chains, with an offline fallback. | `mixup/models.py` and `data/manifest.csv`: add `jurisdiction` (federal / sarawak), `classification` (terbuka / terhad), `applies_to_grades` and `scheme`. `mixup/search.py`: filter by the user's clearance, service and grade **before** scoring and before the AI sees any text. | `mixup/minutes.py`: implement `extract_actions()` using the AI for structured output, with an offline fallback that reads "Keputusan" / "Tindakan" / "Decision" / "Action" lines. Use `versions.detect_references()` and `is_superseded()` to flag decisions that cite cancelled documents. |
| Screens | `ui/ask_tab.py`: add a "compare with plain search" toggle that shows both answers side by side, plus a status badge on each source. `ui/map_tab.py`: clicking a document shows its chain (`versions.chain()`). Keep Smart Upload as the "new circular arrives" moment. | `app.py` sidebar: a profile picker with 2 to 3 personas. A new "Briefing" tab: "what changed for you", filtered by profile. | `ui/minutes_tab.py`: a tracker table across all meetings (owner, due date, status, overdue), with filters. Limit Ask to `doc_types=["minutes"]` for "what was decided about X?". |
| Data | Optional: add one real public chain (for example Sarawak PPNS Bil. 5/2026 and a circular it cancels) with `source_url`, or keep it fictional and say so. Optional fields: "amended" status and "verified by policy owner". | 4 to 6 new fictional documents whose rules differ by grade or by federal/Sarawak service, plus 1 mock Terhad document. | 4 to 6 more synthetic minutes from the same committee, with actions carried between meetings and some overdue. |
| Evidence slide | 10 test questions: count how often plain search cites a cancelled circular compared with the Navigator. | Same question asked by 2 personas, with the results compared. | Number of actions extracted correctly out of the total, checked by hand. |
| Drop from the demo | Conflict Check; the minutes tab (or keep one screen) | Map, Smart Upload, Conflict Check, minutes | Conflict Check, "what changed", Smart Upload (unless reused for uploading minutes) |

**Drop or park whichever option we choose**
- **Conflict Check:** both PDFs warn of many false alarms. Show it on one hand-picked pair or hide the tab.
- **Titan embeddings on stage:** they add another AWS call that can fail. Keep keyword search and offline mode as the safe default, and describe embeddings in the AWS architecture slide.
- **OCR, DDMS integration and contradiction detection:** these are roadmap slides only. Do not build them in 4 hours.

---

## Open questions for the team

1. **Which option are we building?** We recommend A, and the prototype draft is already being rebuilt that way. If anyone prefers B or C, say so in the first 15 minutes, so that all three of us build the same thing.
2. **Fictional data only, or add one real public circular chain?** Real data (Sarawak PPNS Bil. 5/2026 or a Treasury item) adds credibility with Kuching judges, but costs about 45 minutes and must be checked by hand.
3. **How do we describe ADAM AI?** Has anyone seen or used it? Agree on one sentence, for example: "ADAM AI answers questions; we add which circular is still valid. It is a layer ADAM's e-Circular agent could use."
4. **What is our hosting story?** AWS (Bedrock) is fine for public Terbuka circulars. What do we say about Terhad and Sulit documents, which CGSO rules keep off public cloud? Are the Bedrock models we use offered in the AWS Malaysia Region? Check before saying "data stays in Malaysia".
5. **Online or offline demo on stage?** Will we have working Bedrock access and Wi-Fi at the venue, or should we rehearse in offline mode (keyword search, no AI-written answers)? Decide before the first rehearsal.
