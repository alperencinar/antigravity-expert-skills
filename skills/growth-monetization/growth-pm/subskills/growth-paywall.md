# /growth-paywall — Mobile Monetization, Dynamic Paywalls & Pricing Architecture

This specialized sub-skill module is used to architect high-converting dynamic paywalls, asymmetric decoy pricing matrices, Blinkist-style transparent billing timelines, Server-Driven UI (Superwall / RevenueCat SDUI), and exit-intent downsell flows.

---

## 1. High-Converting Asymmetric Decoy Pricing Matrix

The industry-standard model that drives 80%+ of converting users into the Annual Plan:

```
┌───────────────────────────────────────┬───────────────────────────────────────┐
│           PLAN A: DECOY               │          PLAN B: HERO (TARGET)        │
│           Weekly Plan                 │          Annual Plan (MOST POPULAR)   │
├───────────────────────────────────────┼───────────────────────────────────────┤
│ Price: $6.99 / Week                   │ Price: $39.99 / Year ($0.77 / Week)   │
│ Annualized Equivalent: $363.48 / Year │ Savings: SAVE 89% BADGE               │
│ Trial: NO Free Trial                  │ Trial: 7-DAY FREE TRIAL               │
│ Billing: Billed Immediately           │ Billing: Billed on Day 7              │
└───────────────────────────────────────┴───────────────────────────────────────┘
```

> **Psychological Heuristic:** The weekly plan establishes a high reference anchor ($363/yr) with upfront risk. The annual plan appears completely risk-free (7-day trial) and framed as just pennies per week ($0.77/week), making it the obvious rational choice.

---

## 2. Blinkist-Style Transparent Billing Timeline (Trust Architecture)

Eliminates the fear of surprise charges through a clear 3-node visual timeline:

```
[Today: Pay $0] ──────> [Day 5: Reminder Push] ──────> [Day 7: Subscription Begins]
 (7-Day Trial)           (Alert 2 Days Prior)           (Cancel Anytime in Settings)
```

### The Push Permission Bridge
Place this toggle below the timeline:
* **"Remind me 2 days before trial ends"** $\to$ Trigger native `UNUserNotificationCenter.requestAuthorization`. This context elevates push opt-in rates from **~30% to 75%+** while cutting billing dispute support tickets by **55%**.

---

## 3. In-App Contextual Gating & Dynamic Triggers

Trigger paywalls at peak emotional intent rather than only at app launch:

```
                               CONTEXTUAL PAYWALL TRIGGERS
┌─────────────────────────┬─────────────────────────┬─────────────────────────┐
│ 1. USAGE QUOTA METERING │ 2. FEATURE GATE         │ 3. STREAK PRESERVATION  │
│ "You've used your 3     │ "4K HD Export / AI      │ "Preserve your 5-day    │
│ daily free edits. Go Pro│ Summary is a Pro        │ streak by unlocking     │
│ for unlimited access."  │ feature."               │ Streak Freeze."         │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
```

---

## 4. Exit-Intent Downsell Modals

When a user taps the `X` (close) button on the onboarding paywall, present a high-affinity fallback:

* **Offer A (50% Introductory Discount):** *"New member special: Get your first year for 50% off ($19.99/yr)."*
* **Offer B ($0.99 Introductory Pass):** *"$0.99 for a 30-Day Starter Pass."*
* **Rule:** Enforce a 14-day anti-cannibalization cooldown so downsell offers are not exploited repeatedly.

---

## 5. Superwall / RevenueCat Server-Driven UI (Swift Implementation)

```swift
import SwiftUI
import SuperwallKit
import RevenueCat

struct ProFeatureGateView: View {
    @State private var isSubscribed = false
    
    var body: some View {
        Button(action: {
            // Register Superwall dynamic placement trigger
            Superwall.shared.register(placement: "export_hd_feature") {
                // Executes when user has an active entitlement
                self.isSubscribed = true
                performHDExport()
            }
        }) {
            Label("Export in 4K HD (Pro)", systemImage: "sparkles")
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(12)
        }
    }
    
    private func performHDExport() {
        print("Executing 4K HD export...")
    }
}
```

---

## 📖 Reference Deep Research Documents
- [`02_subscription_monetization_paywalls_and_adtech.md`](../researches/02_subscription_monetization_paywalls_and_adtech.md)
- [`05_monetization_turnaround_case_study_and_experiments.md`](../researches/05_monetization_turnaround_case_study_and_experiments.md)
- [`06_low_conversion_velocity_and_monetization_amplification.md`](../researches/06_low_conversion_velocity_and_monetization_amplification.md)
