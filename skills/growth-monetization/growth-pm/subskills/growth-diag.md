# /growth-diag — Mobile Funnel & Zero/Low Conversion Forensics

This specialized sub-skill module is used to diagnose zero-revenue states ($0 revenue), rare/trickle purchases, low paywall exposure rates, or funnel leaks using a 5-pillar forensic investigation protocol.

---

## 1. The 5-Pillar Forensic Diagnostic Framework

For any mobile funnel blockage or conversion anomaly, audit these 5 pillars systematically:

```
[1. Tech & IAP Plumbing] ──> [2. Quantitative Funnel] ──> [3. ASO & Intent] ──> [4. Value Timing] ──> [5. Session Replay]
```

### Pillar 1: Technical & In-App Purchase (IAP) Plumbing
* **Legal & Tax Status:** Verify that the *Paid Applications Agreement* in App Store Connect and the Google Play Merchant Profile are active. (If incomplete or pending, StoreKit/GPBL silently returns empty product arrays `products = []`).
* **Asynchronous Race Conditions:** Ensure that paywall UI rendering does not race ahead of StoreKit 2 / RevenueCat `offerings.current` resolution. If products are still loading, purchase CTAs must show a skeleton loader rather than a dead/disabled click.
* **SKU & Entitlement Mapping:** Confirm that product identifiers in code (`com.app.pro_annual`) match App Store Connect / Play Console identifiers and RevenueCat entitlement identifiers character-for-character.

### Pillar 2: Quantitative Telemetry & Funnel Forensics
Decompose the 7 micro-conversion steps:
1. `Install -> App_Open` (Healthy: 92%–95%)
2. `App_Open -> Onboarding_Complete` (Healthy: 65%–80%)
3. `Onboarding_Complete -> Paywall_Impression` (Healthy: 90%+, Hidden Storefront Trap: <15%)
4. `Paywall_Impression -> Plan_Selected` (Healthy: 60%–70%)
5. `Plan_Selected -> Purchase_Initiated` (Healthy: 25%–35%)
6. `Purchase_Initiated -> Purchase_Success` (Healthy: 75%–85%)

### Pillar 3: ASO & Traffic Intent Congruence
* Is organic traffic originating from zero-cost search terms (e.g., *"free pdf editor"*, *"free offline counter"*)?
* Is there an expectation mismatch between App Store screenshot promises and the actual Day-0 experience?
* For traffic originating from Tier-3 countries (India, Brazil, Egypt, Indonesia), is Purchasing Power Parity (PPP) active, or is a flat $49.99/yr pricing causing a 99.8% bounce rate?

### Pillar 4: Value Timing & Freemium Leakage
* **Freemium Leakage:** Does the free tier satisfy 95%+ of user utility with zero natural usage caps or gating? (No pain point = no upgrade urgency).
* **Premature Hard Gating:** Is the app demanding cold upfront cash before delivering any tangible "Aha! Moment" or value perception?

### Pillar 5: Qualitative Observability & Session Replay
* Inspect 30–50 session recordings in UXCam, PostHog, or Smartlook.
* Look for:
  * Rage taps on purchase CTAs (indicating frozen UI or unresponsive buttons).
  * Invisible or unclickable `X` (close) buttons causing immediate force-quits.
  * Instant bounces (Mean Time to Flee < 2.0s), signaling trust or pricing shock.

---

## 2. Production Diagnostic SQL Queries (BigQuery / Snowflake / PostHog)

### 4-Factor Funnel Decomposition & Bottleneck Isolation

```sql
WITH daily_funnel AS (
  SELECT
    DATE(event_timestamp) AS date,
    COUNT(DISTINCT CASE WHEN event_name = 'app_installed' THEN user_id END) AS installs,
    COUNT(DISTINCT CASE WHEN event_name = 'onboarding_completed' THEN user_id END) AS onboarding_done,
    COUNT(DISTINCT CASE WHEN event_name = 'paywall_impression' THEN user_id END) AS paywall_views,
    COUNT(DISTINCT CASE WHEN event_name = 'purchase_initiated' THEN user_id END) AS trial_starts,
    COUNT(DISTINCT CASE WHEN event_name = 'purchase_completed' THEN user_id END) AS paid_conversions
  FROM telemetry_events
  WHERE event_timestamp >= CURRENT_DATE - INTERVAL '30' DAY
  GROUP BY 1
)
SELECT
  date,
  installs,
  ROUND(paywall_views * 1.0 / NULLIF(installs, 0), 4) AS paywall_exposure_rate,
  ROUND(trial_starts * 1.0 / NULLIF(paywall_views, 0), 4) AS paywall_cvr,
  ROUND(paid_conversions * 1.0 / NULLIF(trial_starts, 0), 4) AS trial_to_paid_cvr,
  ROUND(paid_conversions * 1.0 / NULLIF(installs, 0), 4) AS gross_install_to_paid_cvr
FROM daily_funnel
ORDER BY date DESC;
```

---

## 3. Forensic Root-Cause Matrix

| Metric Finding | Root Cause | Prescribed Remediation |
| :--- | :--- | :--- |
| `Paywall Exposure < 15%` | **The Hidden Storefront Trap** | Move paywall to the final step of Day-0 Onboarding immediately. |
| `Paywall Exposure > 80%` but `CVR < 1.0%` | **Cold Direct-to-Paid / Flat Pricing** | Implement 7-Day Free Trial; deploy Weekly $6.99 Decoy Anchor. |
| `CTA Clicked` but `Success = 0` | **Technical StoreKit Bug / SKU Mismatch** | Audit StoreKit 2 error logs, product identifiers, and merchant contracts. |
| `Tier-3 Installs > 50%` but `CVR < 0.3%` | **Missing PPP Geo-Pricing** | Implement 3-tier PPP pricing offering 60%–75% discounts in local currency. |
| `Trial Starts High` but `D7 Cancellation > 80%` | **Trial Value Amnesia** | Deploy D1, D3, D5 automated push lifecycle sequences to build habit. |

---

## 📖 Reference Deep Research Documents
- [`04_zero_monetization_diagnostic_playbook.md`](../researches/04_zero_monetization_diagnostic_playbook.md)
- [`06_low_conversion_velocity_and_monetization_amplification.md`](../researches/06_low_conversion_velocity_and_monetization_amplification.md)
