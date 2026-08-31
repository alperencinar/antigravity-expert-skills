# /growth-ai — AI-Driven Growth, Dynamic Bandits & Predictive LTV

This specialized sub-skill module is used to deploy Contextual Multi-Armed Bandits (LinUCB) for real-time dynamic paywall selection, orchestrate LLM-driven adaptive onboarding quizzes, and train D365 predictive LTV (pLTV) models from early session telemetry.

---

## 1. Real-Time Paywall Routing via LinUCB Contextual Bandits

Rather than waiting weeks for static A/B tests to reach significance, dynamically route each incoming user to the paywall variant that maximizes expected revenue given their context (country, device, hour, intent score):

```python
import numpy as np

class LinUCBPaywallBandit:
    def __init__(self, n_arms: int, n_features: int, alpha: float = 0.5):
        self.n_arms = n_arms
        self.n_features = n_features
        self.alpha = alpha
        self.A = [np.identity(n_features) for _ in range(n_arms)]
        self.b = [np.zeros((n_features, 1)) for _ in range(n_arms)]

    def select_paywall(self, context_vector: np.ndarray) -> int:
        x = context_vector.reshape(-1, 1)
        p = np.zeros(self.n_arms)
        for a in range(self.n_arms):
            A_inv = np.linalg.inv(self.A[a])
            theta = np.dot(A_inv, self.b[a])
            confidence = self.alpha * np.sqrt(np.dot(x.T, np.dot(A_inv, x)))
            p[a] = np.dot(theta.T, x) + confidence
        return int(np.argmax(p))

    def update(self, chosen_arm: int, reward: float, context_vector: np.ndarray):
        x = context_vector.reshape(-1, 1)
        self.A[chosen_arm] += np.dot(x, x.T)
        self.b[chosen_arm] += reward * x
```

---

## 2. LLM-Powered Adaptive Onboarding & Dynamic Value Propositions

Dynamically synthesize the paywall headline and bullet points to match the user's specific answers from the onboarding quiz:

```
[User: "I have 15 mins/day, preparing for TOEFL vocabulary exam"]
                               │
                               ▼
[Dynamic LLM Paywall]: "Master TOEFL Vocabulary with Just 15 Minutes a Day — 94% Pass Rate!"
```

---

## 3. Predictive D365 LTV (pLTV) Regression Modeling

Train LightGBM or XGBoost regressors on early user telemetry to forecast 1-year realized LTV ($rLTV_{365}$):

* **Input Features:** Steps completed in session 1, video completion rate, paywall dwell time, push notification opt-in status, device hardware tier.
* **Prescriptive Action:** Route high-pLTV users to Annual/VIP plans; route lower-pLTV users to micro-subscriptions or $0.99 introductory passes.

---

## 📖 Reference Deep Research Documents
- [`03_retention_lifecycle_and_experimentation_engine.md`](../researches/03_retention_lifecycle_and_experimentation_engine.md)
- [`06_low_conversion_velocity_and_monetization_amplification.md`](../researches/06_low_conversion_velocity_and_monetization_amplification.md)
