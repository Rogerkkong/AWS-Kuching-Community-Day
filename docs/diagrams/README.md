# MixUp pitch diagrams

Six 16:9 slide images for the MixUp pitch at AWS Student Community Day Kuching. Each PNG is the 1920x1080 slide rendered at 2x (3840x2160). The `.html` file next to it is the editable source.

| # | Image | Slide | Speaker note (one sentence) |
|---|-------|-------|-----------------------------|
| 1 | `01-mixup-overview.png` | **The solution**, right after the problem slide | "MixUp reads the circulars, SOPs, guidelines and minutes officers already use, runs them through a validity engine that knows which rules are still in force, and gives every officer the current rule with circular, clause and page as proof, offline on a laptop." |
| 2 | `02-answer-flow.png` | **How it works**, just before the live demo | "Ask the same mileage question to a typical chatbot and it quotes RM0.55/km from SPP 3/2019, which was cancelled; MixUp searches only what you are cleared to see, drops cancelled circulars, and answers RM0.80/km from SPP 2/2025 para 4.2, telling you what it excluded." |
| 3 | `03-keeping-rules-current.png` | **Innovation**: the validity engine | "When the new SPP 1/2026 is uploaded, MixUp finds its PEMBATALAN clause, proposes that it cancels SPP 1/2023 and SPP 2/2025, waits for an admin to verify, then updates the salasilah and alerts officers that the rate is now RM0.85/km and the claim window is 90 days." |
| 4 | `04-architecture.png` | **Technical solution / architecture**, right after the live demo | "One codebase runs in two modes: a central Publisher parses, OCRs and verifies circulars and signs one SQLite knowledge pack per clearance tier, the packs travel by shared folder, intranet or USB, and each officer's Windows PC checks the signature, installs the pack and answers fully offline, with sources first and every citation validated." |
| 5 | `05-three-workflows.png` | **How it works behind the scenes**, or a backup slide for technical Q&A | "Three loops keep MixUp honest: a person approves every relation before a signed pack is published, the officer's app installs a pack only if the checksum, signature and embedding model all pass, and every question is answered offline with sources on screen in under 2 seconds." |
| 6 | `06-aws-deployment.png` | **Feasibility and scale**, the roadmap slide near the end | "To scale past the demo, the Publisher side for public Terbuka circulars moves to AWS in the Malaysia Region, with S3, Textract, Step Functions and Lambda, Bedrock proposing relations, a human review app on Amplify and KMS-signed packs on CloudFront, while Terhad and Sulit packs never touch public cloud and every officer still answers offline." |

## Notes for the presenter

- Show slide 2 before slide 3. Slide 2 is the state before SPP 1/2026 (RM0.80/km is current), and slide 3 is the live upload that changes it to RM0.85/km.
- Slide 2 uses the default **federal** officer profile because the answer cites a federal Treasury circular. The Sarawak switch comes later in the demo: for the childcare-leave example a Sarawak officer sees Pekeliling Am Negeri Bil. 2/2024 (10 days) first, with federal PP 4/2024 (7 days) beside it.
- On slide 3 the lineage arrows point from the newer circular to the older one it cancels (*membatalkan*) or amends (*meminda*). Say it as "newer cancels older".
- All circular numbers and figures are synthetic (marked *Contoh sintetik / synthetic example* on slides 2, 3 and 5). Slides 4 and 6 show no example data, so they carry no synthetic label.
- Slides 4 and 5 show the same system at two zoom levels. In a short pitch show slide 4 only and keep slide 5 as a backup for "how does the update work?" questions. The bell on slide 5 ("SPP 1/2023 kini Dibatalkan") is the same synthetic story as slide 3.
- Slide 6 is a production path, not what the team deployed. Before presenting it, check these points so you can answer judges' follow-up questions:
  - **Region availability.** Confirm that Amazon Textract, Amazon Bedrock (and the Claude model you name) and Amazon QuickSight are offered in the AWS Asia Pacific (Malaysia) Region. If one is not, say which step would run elsewhere or on-premise; "data in-country" only holds if every step stays in the Region.
  - **Malay OCR.** Textract does not list Malay as a supported language. Test it on scanned circulars and keep Tesseract (msa+eng) in a Lambda function as the fallback.
  - **Signing algorithm.** The desktop app verifies Ed25519 signatures. Either confirm that AWS KMS can sign with Ed25519 in the Region, or switch the app to a KMS-supported algorithm such as ECDSA P-256.
  - **Same embedding model.** Keep BGE-M3 in the cloud pipeline. Packs built with any other embedding model are rejected by officers' apps.
  - **Restricted tiers.** Terhad and Sulit packs are never built or stored on public cloud; they reach cleared officers only by intranet or USB.

## Editing

Edit the `.html` file, then re-render it at a 1920x1080 viewport with `device_scale_factor=2` (for example with Playwright's `page.screenshot`). The slides use the locally installed Inter font, so no network access is needed. Slides 4 to 6 place their arrows with a short inline script that reads the box positions, so render them in a real browser; a viewer that does not run scripts shows those slides without arrows.
