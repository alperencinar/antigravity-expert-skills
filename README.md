# Antigravity Expert Skills

A premium suite of **11 custom product-facing agent skills** designed to automate and guide product development workflows inside Google Antigravity and Claude Code workspace environments.

These skills are located under the root `skills/` directory and mapped to the standard customization root at `.agents/skills/` using a symbolic link. This allows the files to be fully visible and browsable on GitHub while remaining auto-discoverable by the local agent CLI.

---

## 🔄 The Product Development Lifecycle (PDLC)

When a new feature or idea is proposed, the **[product-orchestrating](skills/product-orchestrating/SKILL.md)** skill guides you step-by-step through the following development lifecycle:

```mermaid
graph TD
    A0[0. Brainstorming] -->|product-brainstorming| A[1. Prioritization & Feasibility]
    A -->|navigating-product-prioritization| B[2. Competitive Analysis]
    B -->|benchmarking-product-features| C[3. Feature Architecture]
    C -->|architecting-product-features| D[4. Requirements Definition]
    D -->|analyzing-product-requirements| E[5. UX & Flow Optimization]
    E -->|optimizing-user-journeys| H[6. Analytics Specifying]
    H -->|tracking-product-analytics| F[7. Documentation & Release]
    F -->|documenting-product-specs| G[Ready for Engineering]
```

---

## 📦 Skills Directory

Here is the complete catalog of skills contained in this repository:

| Skill Directory | Purpose | Key Trigger Keywords |
|---|---|---|
| 🎛️ **[product-orchestrating](skills/product-orchestrating)** | Master coordinator for the end-to-end PDLC and reference routing. | `orchestrate lifecycle`, `features help` |
| 💡 **[product-brainstorming](skills/product-brainstorming)** | Brainstorm concepts, user personas, value proposition mapping, and product hooks. | `brainstorm`, `value proposition`, `hook model` |
| 📊 **[navigating-product-prioritization](skills/navigating-product-prioritization)** | Evaluate features backlog and MVP boundaries using RICE and MoSCoW. | `RICE framework`, `MoSCoW`, `prioritize backlog` |
| 🔍 **[benchmarking-product-features](skills/benchmarking-product-features)** | Benchmark against competitor features to find gaps and define USPs. | `competitor analysis`, `USP`, `market gaps` |
| 🗺️ **[architecting-product-features](skills/architecting-product-features)** | Design modular workflows, user flows, and layout mapping. | `feature modularization`, `WBS`, `user journey` |
| 📝 **[analyzing-product-requirements](skills/analyzing-product-requirements)** | Author user stories, Gherkin-style Acceptance Criteria, and functional specifications. | `user stories`, `acceptance criteria`, `Gherkin` |
| ⚙️ **[selecting-development-technology](skills/selecting-development-technology)** | Standalone developer/architect utility to select technology stack components, databases, and frameworks by reading files in `docs/`. | `tech stack`, `ADR`, `database selection` |
| 📈 **[analyzing-product-business](skills/analyzing-product-business)** | Map business process logic, stakeholder requirements, and calculate ROI metrics. | `business requirements`, `ROI models`, `KPIs` |
| 🎨 **[optimizing-user-journeys](skills/optimizing-user-journeys)** | Audit conversion funnels, reduce onboarding friction, and tune UX copy. | `UX audit`, `friction reduction`, `onboarding flow` |
| 🏷️ **[tracking-product-analytics](skills/tracking-product-analytics)** | Design Google Analytics 4 (GA4) custom dimensions and event-tracking schemas. | `GA4`, `event tracking`, `tracking plan` |
| 🗄️ **[documenting-product-specs](skills/documenting-product-specs)** | Publish specifications into folder structures with authority & status badges. | `documentation index`, `specs publishing`, `docs/` |

---

## 🚀 How to Use

### 1. Auto-Loading in Antigravity
Since this repository includes a symbolic link mapping the unhidden `skills/` directory to `.agents/skills/`, **no manual installation is required**. Simply run your Antigravity agent or Claude Code CLI inside this workspace directory, and the skills will be loaded automatically.

### 2. Triggering the Orchestrator
To begin planning or managing a new feature, prompt the agent:
> *"Orchestrate the development lifecycle for the new feature [Feature Name]."*

### 3. Running Individual Skills
If you want to use a specific skill directly without the full orchestrator:
> *"Run benchmarking-product-features to compare my feature with Competitor A"*
> *"Create a GA4 tracking plan using tracking-product-analytics"*

---

## 🛠️ Verification & Quality Check
The files in this repository have been validated against the CLI skill-development rules (including YAML formatting, trigger descriptions, and the 500-line limit). You can re-run the verification script by executing:
```bash
python3 skills/product-orchestrating/scripts/check_skills.py
```

---

## 🔗 Repository Reference
*   **GitHub Repos main branch:** `https://github.com/alperencinar/antigravity-expert-skills.git`
