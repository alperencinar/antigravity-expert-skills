# /growth-adtech — Mobile AdTech, SKAN 4/5, Media Mix Modeling & CPPs

This specialized sub-skill module is used to navigate post-ATT privacy frameworks (SKAdNetwork 4.0/5.0 and Apple AdAttributionKit), deploy Media Mix Modeling (Google Meridian / Meta Robyn), design incrementality geo-lift tests, and optimize Custom Product Pages (CPPs).

---

## 1. Apple SKAdNetwork 4.0 / 5.0 & AdAttributionKit (AAK)

Apple's 3-window privacy-preserving measurement architecture:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ Postback 1 (0–2 Days):   Fine Value (0–63) + Coarse Value (low, medium, high)           │
│ Postback 2 (3–7 Days):   Coarse Value only (low, medium, high)                          │
│ Postback 3 (8–35 Days):  Coarse Value only (low, medium, high)                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Strategic Conversion Value Schema
* **0 – 10:** Onboarding completion & quiz progression
* **11 – 30:** 7-Day Free Trial initiated
* **31 – 50:** Weekly or Monthly subscription purchased
* **51 – 63:** High-LTV Annual subscription ($39.99+) purchased

---

## 2. Media Mix Modeling (MMM): Google Meridian vs. Meta Robyn

When deterministic last-touch attribution degrades, use Bayesian hierarchical modeling to allocate ad spend across channels:

```python
import numpy as np

# 1. Geometric Adstock (Carryover effect over time)
def geometric_adstock(spend_series: np.ndarray, decay_rate: float = 0.6) -> np.ndarray:
    adstocked = np.zeros_like(spend_series, dtype=float)
    adstocked[0] = spend_series[0]
    for t in range(1, len(spend_series)):
        adstocked[t] = spend_series[t] + decay_rate * adstocked[t-1]
    return adstocked

# 2. Hill Saturation Function (Diminishing marginal returns)
def hill_saturation(spend_adstocked: np.ndarray, K: float, S: float) -> np.ndarray:
    return (spend_adstocked ** S) / ((spend_adstocked ** S) + (K ** S))
```

---

## 3. Custom Product Pages (CPP) for Creative Congruence

Match the exact visual theme and value hook of paid ads directly onto App Store product pages:

```
[TikTok Ad: "Lose 15 lbs in 90 Days"] ──> [Targeted CPP: Weight Loss Screenshots] ──> +34% CVR Lift!
[IG Ad: "Daily Guided Meditation"]    ──> [Targeted CPP: Mindfulness Screenshots]  ──> +28% CVR Lift!
```

---

## 📖 Reference Deep Research Documents
- [`02_subscription_monetization_paywalls_and_adtech.md`](../researches/02_subscription_monetization_paywalls_and_adtech.md)
