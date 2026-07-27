# Antigravity Expert Skills

A premium suite of **16 custom product-facing agent skills** designed to automate and guide product development workflows inside Google Antigravity and Claude Code workspace environments.

These skills are located under the root `skills/` directory and mapped to the standard customization root at `.agents/skills/` using a symbolic link. This allows the files to be fully visible and browsable on GitHub while remaining auto-discoverable by the local agent CLI.

---

## 🔄 The Product Development Lifecycle (PDLC)

When a new feature or idea is proposed, the **[product-orchestrating](skills/product-orchestrating/SKILL.md)** skill guides you step-by-step through the following development lifecycle:

```mermaid
graph TD
    A0[0. Brainstorming] -->|product-brainstorming| A[1. Prioritization & Feasibility]
    A -->|product-navigating-prioritization| B[2. Competitive Analysis]
    B -->|product-benchmarking-features| C[3. Feature Architecture]
    C -->|product-architecting-features| D[4. Requirements Definition]
    D -->|product-analyzing-requirements| E[5. UX & Flow Optimization]
    E -->|product-optimizing-user-journeys| H[6. Analytics Specifying]
    H -->|product-tracking-analytics| F[7. Documentation & Release]
    F -->|product-documenting-specs| G[Ready for Engineering]
```

---

## 📦 Skills Directory

Here is the complete catalog of skills contained in this repository:

| Skill Directory | Purpose | Key Trigger Keywords |
|---|---|---|
| 🎛️ **[product-orchestrating](skills/product-orchestrating)** | Master coordinator for the end-to-end PDLC and reference routing. | `orchestrate lifecycle`, `features help` |
| 💡 **[product-brainstorming](skills/product-brainstorming)** | Brainstorm concepts, user personas, value proposition mapping, and product hooks. | `brainstorm`, `value proposition`, `hook model` |
| 📊 **[product-navigating-prioritization](skills/product-navigating-prioritization)** | Evaluate features backlog and MVP boundaries using RICE and MoSCoW. | `RICE framework`, `MoSCoW`, `prioritize backlog` |
| 🔍 **[product-benchmarking-features](skills/product-benchmarking-features)** | Benchmark against competitor features to find gaps and define USPs. | `competitor analysis`, `USP`, `market gaps` |
| 🗺️ **[product-architecting-features](skills/product-architecting-features)** | Design modular workflows, user flows, and layout mapping. | `feature modularization`, `WBS`, `user journey` |
| 📝 **[product-analyzing-requirements](skills/product-analyzing-requirements)** | Author user stories, Gherkin-style Acceptance Criteria, and functional specifications. | `user stories`, `acceptance criteria`, `Gherkin` |
| ⚙️ **[product-selecting-development-technology](skills/product-selecting-development-technology)** | Standalone developer/architect utility to select technology stack components, databases, and frameworks by reading files in `docs/`. | `tech stack`, `ADR`, `database selection` |
| 📈 **[product-analyzing-business](skills/product-analyzing-business)** | Map business process logic, stakeholder requirements, and calculate ROI metrics. | `business requirements`, `ROI models`, `KPIs` |
| 🎨 **[product-optimizing-user-journeys](skills/product-optimizing-user-journeys)** | Audit conversion funnels, reduce onboarding friction, and tune UX copy. | `UX audit`, `friction reduction`, `onboarding flow` |
| 🏷️ **[product-tracking-analytics](skills/product-tracking-analytics)** | Design Google Analytics 4 (GA4) custom dimensions and event-tracking schemas. | `GA4`, `event tracking`, `tracking plan` |
| 🗄️ **[product-documenting-specs](skills/product-documenting-specs)** | Publish specifications into folder structures with authority & status badges. | `documentation index`, `specs publishing`, `docs/` |
| 💻 **[product-frontend-clean-architecture-development](skills/product-frontend-clean-architecture-development)** | Write modular, clean, and scalable frontend code adhering to Clean Architecture principles. | `develop frontend screen`, `clean architecture component`, `modular structure` |
| 🔧 **[product-antigravity-skill-activate](skills/product-antigravity-skill-activate)** | Meta-skill to configure, register, and activate custom skills in Antigravity. | `activate skill`, `configure skill`, `register skill` |
| 🖼️ **[product-aso-screenshot-creator](skills/product-aso-screenshot-creator)** | Plan, structure, and generate high-converting, ASO-optimized App Store and Google Play screenshots. | `ASO screenshots`, `store graphics`, `screenshot layout` |
| 💵 **[product-costs-pricing](skills/product-costs-pricing)** | Analyze API execution costs, plan pricing models, and verify profit margins. | `pricing tiers`, `execution costs`, `profit margins` |
| 🔬 **[product-deepsearch](skills/product-deepsearch)** | Conduct high-fidelity, verified deep web research using Chromium and subagents. | `deep research`, `verified research`, `market study` |

---

## 🚀 How to Use

### 1. Auto-Loading in Antigravity
Since this repository includes a symbolic link mapping the unhidden `skills/` directory to `.agents/skills/`, **no manual installation is required**. Simply run your Antigravity agent or Claude Code CLI inside this workspace directory, and the skills will be loaded automatically.

### 2. Triggering the Orchestrator
To begin planning or managing a new feature, prompt the agent:
> *"Orchestrate the development lifecycle for the new feature [Feature Name]."*

### 3. Running Individual Skills
If you want to use a specific skill directly without the full orchestrator:
> *"Run product-benchmarking-features to compare my feature with Competitor A"*
> *"Create a GA4 tracking plan using product-tracking-analytics"*

---

## 🛠️ Verification & Quality Check
The files in this repository have been validated against the CLI skill-development rules (including YAML formatting, trigger descriptions, and the 500-line limit). You can re-run the verification script by executing:
```bash
python3 skills/product-orchestrating/scripts/check_skills.py
```

---

## 🔗 Repository Reference
*   **GitHub Repos main branch:** `https://github.com/alperencinar/antigravity-expert-skills.git`

Skill Kütüphanesi

Bu klasör, Cardiv projesinde kullanılan 3 ana skill'in tam detaylarını, alt skill kırılımlarını ve ilgili research dokümanlarının kopyalarını içerir. Her skill kendi klasöründe kendine yeterli (self-contained) şekilde organize edilmiştir.

## 📁 Klasör Yapısı

```
AlperenSkills/
├── unity-expert/
│   ├── SKILL.md                  # Ana skill tanımı (master)
│   ├── subskills/                # 8 alt skill detay dosyası
│   │   ├── unity-expert-asset.md    # AI 3D Asset Normalization & FBX Pipeline
│   │   ├── unity-expert-arch.md     # FSM State Machine & Solvable Lane Generator
│   │   ├── unity-expert-pool.md     # Zero-GC Object Pooling & Dynamic Hazards
│   │   ├── unity-expert-render.md   # URP CurvedWorld Shader & Lighting Mastery
│   │   ├── unity-expert-juice.md    # Camera Juicing, Dynamic FOV & Screenshake
│   │   ├── unity-expert-audio.md    # Engine Audio Pitch & Haptic Feedback
│   │   ├── unity-expert-ui.md       # Responsive UI, Safe Area & Canvas Splitting
│   │   └── unity-expert-verify.md   # Live Verification, Diagnostics & Capture
│   └── researches/               # 19 research dokümanı kopyası
│
├── 3d-asset-creator/
│   ├── SKILL.md                  # Ana skill tanımı (master)
│   ├── subskills/                # 6 alt skill detay dosyası
│   │   ├── 3d-asset-concept.md      # Reference Image Generation
│   │   ├── 3d-asset-generate.md     # Meshy AI Generation Loop
│   │   ├── 3d-asset-polish.md       # Blender Split, Symmetrize & Scale
│   │   ├── 3d-asset-sync.md         # Unity Textures & PBR Materials
│   │   ├── 3d-asset-auto.md         # Zero-Code Data-Driven Asset Import
│   │   └── 3d-asset-verify.md       # Visual Inspection & Play Mode
│   └── researches/               # 9 research dokümanı kopyası
│
└── game-ui-designer-developer/
    ├── SKILL.md                  # Ana skill tanımı (master)
    ├── subskills/                # 8 alt skill detay dosyası
    │   ├── game-ui-paradigm.md      # AAA UI Paradigms, Color Theory & SDF Typography
    │   ├── game-ui-arch.md          # FSM Layered Canvas & Stack Modal Navigation
    │   ├── game-ui-button.md        # 7-State Button Lifecycle, Spring Juice & Haptics
    │   ├── game-ui-responsive.md    # Safe Area, Aspect Ratio Adapters & Layout Math
    │   ├── game-ui-perf.md          # UGUI vs UI Toolkit & Zero-GC Optimization
    │   ├── game-ui-hud.md           # Dynamic Gameplay HUD & World-Space Damage Text
    │   ├── game-ui-shader.md        # Glassmorphism, Neon Glow & Technical Art Shaders
    │   └── game-ui-a11y.md          # Localization, CJK/RTL & Automated UI Auditors
    └── researches/               # 10 research dokümanı kopyası
```

## 🔗 Kaynak Eşlemesi

| Skill | Orijinal Skill Kaynağı | Research Kaynakları |
|---|---|---|
| `unity-expert` | `.agents/skills/unity-expert/SKILL.md` | `docs/unityexpert/` (11) + `docs/researches/` (8 ilgili) |
| `3d-asset-creator` | `.agents/skills/3d-asset-creator/SKILL.md` | `docs/unityexpert/` (2 ilgili) + `docs/researches/` (7 ilgili) |
| `game-ui-designer-developer` | `.agents/skills/game-ui-designer-developer/SKILL.md` | `docs/gameuidesigner/` (8) + `docs/researches/` (2 ilgili) |

## 📌 Kullanım Notları

- Her alt skill dosyası, kendi klasöründeki `../researches/` altında yer alan doküman kopyalarına göreli linklerle bağlıdır; klasör taşınsa bile linkler çalışır.
- `SKILL.md` dosyaları orijinallerin birebir kopyasıdır; orijinallerdeki mutlak yollar (`docs/...`) hâlâ ana proje dokümanlarına işaret eder. Alt skill dosyaları ise bu klasördeki yerel kopyaları referanslar.
- Research dokümanları kopyadır; ana kaynak (source of truth) `docs/` altındaki orijinallerdir. Orijinaller güncellendiğinde buradaki kopyaların senkronlanması gerekir.
