---
name: product-frontend-clean-architecture-development
description: Use clean architecture principles to write modular, high-quality, and
  maintainable frontend code, ensuring strict separation between UI presentation,
  domain business logic, and infrastructure/data layers. Enforce consistent localization
  key usage, adherence to project design system tokens/themes, and responsive mobile-first
  layouts with keyboard and safe area handling.
category: development
triggers:
- develop frontend screen
- write clean architecture component
- refactor page to modular structure
- create frontend module
- implement clean view
user-invocable: true
---
# product-frontend-clean-architecture-development

## Purpose
To guide the creation, refactoring, and maintenance of clean, modular, and scalable frontend codebases (supporting React, React Native, Expo, etc.) adhering to strict Clean Architecture principles, complete separation of concerns, design system consistency, absolute localization, and responsive layout designs.

---

## 🚫 CRITICAL ARCHITECTURAL CONSTRAINTS (STRICT & MANDATORY)

### 1. No Monolithic Components (Strict Modularity)
*   **The 150-Line Rule:** Any screen or component that exceeds 150-200 lines of code or renders multiple logical sub-views (e.g., multi-step wizard screens, conditional panels, tabs, complex forms) **MUST NOT** be kept in a single monolithic file.
*   **Orchestrator Pattern:** You must split monolithic components into:
    *   A **Parent Orchestrator** component that manages only state, state transitions, coordinates data flows, and renders the container wrapper.
    *   **Atomic Child Components** representing each separate step, view, or tab, grouped cleanly in a sub-folder (e.g., `components/onboarding/steps/`).
*   **Single-file multi-step wizards or compound conditional renderers are strictly forbidden.**

### 2. Mandatory Audit & Review Phase
Before editing or writing any frontend code, you **MUST** run a strict architecture audit on the target files:
1.  **Check for Monoliths:** Does this file render multiple steps, screens, or panels?
2.  **Check for Hardcoded Strings:** Are there raw text strings in the UI instead of dynamic/static `t()` translations?
3.  **Check for Infrastructure Leakage:** Are there direct API calls, fetch requests, or Supabase DB queries inside the UI layer?
4.  **Action:** If any violation is found, **do not proceed** with the requested feature immediately. First, present a clear refactoring recommendation to the user detailing how to modularize the code, and obtain their approval.

---

## Core Pillars of Clean Frontend Architecture

### 1. Presentation Layer (UI & Routes)
*   **Separation of Router and Screens:** Route entry files (e.g., `/app` directory) should only mount their corresponding screen layouts and manage routing/authorization. Visual designs and layout styling must be grouped in screen components (`/screens`).
*   **Pure Reusable UI Elements (`/components`):** Small, reusable UI units reside in this directory. Components are only responsible for rendering UI based on passed props.
*   **No Direct Data Fetching:** No screen or UI component should ever make direct database queries, API calls, or fetch requests. All data transactions must be handled via hooks or services in the Domain/Data layers.

### 2. Domain (Business Logic & State) Layer
*   **Zustand Stores & Custom Hooks (`/hooks`):** State management and business logic detached from the UI are managed inside Zustand stores or custom hooks.
*   **Responsibility:** Handles how user interactions (clicks, files uploads) are routed to services, how error states are processed, and coordinates navigation flows.

### 3. Data & Infrastructure Layer
*   **Service Providers (`/services` or `/utils`):** API clients, database context wrappers (`useSupabase`), native hardware integrations (camera, filesystem), and i18n configurations belong here.
*   **Responsibility:** Fetches raw data from external sources and maps them to clean data structures/contracts utilized by the Domain layer.

---

## Coding Standards and Guidelines

### 🌐 1. Localization Standards
*   **No Hardcoded Strings:** UI screens and components must never contain raw text strings.
*   **Translation JSON Files (`/locale`):** All translations must reside in JSON configuration files (e.g., `tr.json`, `en.json`) using mapped keys.
*   **Usage:** Text elements must be called via `t('module.key')`. Dynamic variables must be passed properly using translation keys:
    ```tsx
    // Correct
    t('profile.creditsCount', { count: totalCredits })
    ```

### 🎨 2. Design System Alignment
*   **Read Design Guidelines:** Before building, inspect active design configurations (`tailwind.config.js`, `docs/design/`, theme files) to read branding color palettes, typography styles, and border-radius rules.
*   **Consistency:** Ensure UI components use primary action branding colors. Always implement support for dark mode (`dark:bg-slate-900`, etc.) when adding colors.

### 📱 3. Responsive & Adaptive Layouts
*   **Fluid Sizing:** Do not use fixed pixel dimensions for layout components. Prefer percentages (`w-[48%]`), flexible layout adapters (`flex-1`), or aspect ratios (`aspect-square`).
*   **Prevent Character Clipping:** When aligning text tags side-by-side, use Flexbox baseline alignment (`flex-row items-baseline`) instead of nested text elements, ensuring text wraps cleanly when clipped.

### 📱 4. Keyboard & SafeArea Integration
*   **Respect SafeArea:** To avoid notch overlays, home indicator cutoffs, and device corner clipping, wrap page roots inside `SafeAreaView` from `react-native-safe-area-context`.
*   **Keyboard Overlapping Prevention:** When using inputs (`TextInput`, `TextBox`), prevent them from getting covered by the system software keyboard:
    *   Wrap screens in `KeyboardAvoidingView` with `behavior="padding"` on iOS and `behavior="height"` on Android.
    *   Implement a scroll wrapper using `ScrollView` and dismiss the keyboard on outside taps using `TouchableWithoutFeedback` / `Keyboard.dismiss`.
