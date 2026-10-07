# MixUp pitch diagrams

Three 16:9 slide images for the MixUp pitch at AWS Student Community Day Kuching. Each PNG is the 1920x1080 slide rendered at 2x (3840x2160). The `.html` file next to it is the editable source.

| # | Image | Slide | Speaker note (one sentence) |
|---|-------|-------|-----------------------------|
| 1 | `01-mixup-overview.png` | **The solution**, right after the problem slide | "MixUp reads the circulars, SOPs, guidelines and minutes officers already use, runs them through a validity engine that knows which rules are still in force, and gives every officer the current rule with circular, clause and page as proof, offline on a laptop." |
| 2 | `02-answer-flow.png` | **How it works**, just before the live demo | "Ask the same mileage question to a typical chatbot and it quotes RM0.55/km from SPP 3/2019, which was cancelled; MixUp searches only what you are cleared to see, drops cancelled circulars, and answers RM0.80/km from SPP 2/2025 para 4.2, telling you what it excluded." |
| 3 | `03-keeping-rules-current.png` | **Innovation**: the validity engine | "When the new SPP 1/2026 is uploaded, MixUp finds its PEMBATALAN clause, proposes that it cancels SPP 1/2023 and SPP 2/2025, waits for an admin to verify, then updates the salasilah and alerts officers that the rate is now RM0.85/km and the claim window is 90 days." |

## Notes for the presenter

- Show slide 2 before slide 3. Slide 2 is the state before SPP 1/2026 (RM0.80/km is current), and slide 3 is the live upload that changes it to RM0.85/km.
- Slide 2 uses the default **federal** officer profile because the answer cites a federal Treasury circular. The Sarawak switch comes later in the demo: for the childcare-leave example a Sarawak officer sees Pekeliling Am Negeri Bil. 2/2024 (10 days) first, with federal PP 4/2024 (7 days) beside it.
- On slide 3 the lineage arrows point from the newer circular to the older one it cancels (*membatalkan*) or amends (*meminda*). Say it as "newer cancels older".
- All circular numbers and figures are synthetic (marked *Contoh sintetik / synthetic example* on slides 2 and 3).

## Editing

Edit the `.html` file, then re-render it at a 1920x1080 viewport with `device_scale_factor=2` (for example with Playwright's `page.screenshot`). The slides use the locally installed Inter font, so no network access is needed.
