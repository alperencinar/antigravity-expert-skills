# /growth-abtest — Mobile Experimentation, Statistical Rigor & CUPED

This specialized sub-skill module is used to prevent the continuous peeking problem ($\alpha$-inflation), deploy sequential testing (mSPRT), reduce variance via CUPED to halve experiment duration, and conduct Sample Ratio Mismatch (SRM) audits.

---

## 1. The Continuous Peeking Problem & $\alpha$-Inflation

Checking standard p-values daily and stopping the test early when $p < 0.05$ causes severe false positive inflation ($\alpha^*$). Across $k$ peeks:

$$\alpha^* = 1 - (1 - \alpha)^k \quad (\text{For } \alpha=0.05 \text{ and } k=10, \; \alpha^* \approx \mathbf{40.1\%})$$

> **Consequence:** You have a ~40% chance of declaring a neutral variant a "winner" simply due to random noise.

---

## 2. mSPRT (Mixture Sequential Probability Ratio Test)

To enable safe, continuous real-time monitoring, replace standard fixed-horizon t-tests with **mSPRT**. The test safely terminates whenever the mixture log-likelihood ratio crosses the boundary:

$$\Lambda_n = \int \prod_{i=1}^n \frac{f(X_i; \theta)}{f(X_i; 0)} dH(\theta) \ge \frac{1}{\alpha}$$

---

## 3. CUPED (Controlled-Experiment Using Pre-Experiment Data)

Developed by Microsoft Research, **CUPED** utilizes pre-experiment user behavioral data ($X$) as a covariate to strip out unexplained variance from the metric ($Y$):

$$\tilde{Y} = Y - \theta (X - E[X]), \quad \text{where } \theta = \frac{\text{Cov}(Y, X)}{\text{Var}(X)}$$

Variance reduction factor:
$$\text{Var}(\tilde{Y}) = \text{Var}(Y) \cdot (1 - \rho^2)$$

> **Practical Impact:** If pre-experiment telemetry correlates with outcome at $\rho = 0.70$, required sample size is **reduced by 51%**. A 14-day experiment completes in **7 days** with identical statistical power.

---

## 4. Sample Ratio Mismatch (SRM) $\chi^2$ Audit (Python)

Detect hidden assignment bias or logging drops between experiment variants:

```python
import numpy as np
from scipy import stats

def detect_sample_ratio_mismatch(control_count: int, variant_count: int, expected_ratio: float = 0.5) -> dict:
    total = control_count + variant_count
    expected_control = total * expected_ratio
    expected_variant = total * (1.0 - expected_ratio)
    
    # Pearson Chi-Square Goodness-of-Fit Test
    chi2_stat = ((control_count - expected_control)**2 / expected_control) + \
                ((variant_count - expected_variant)**2 / expected_variant)
    p_value = 1.0 - stats.chi2.cdf(chi2_stat, df=1)
    
    has_srm = p_value < 0.001  # Strict threshold for telemetry bias
    return {
        "chi2_stat": round(chi2_stat, 4),
        "p_value": float(p_value),
        "has_srm": has_srm,
        "verdict": "INVALID EXPERIMENT! (SRM Detected)" if has_srm else "VALID (No SRM Detected)"
    }

# Example: Control = 4,850, Variant = 5,150
print(detect_sample_ratio_mismatch(4850, 5150))
```

---

## 5. Modern Experimentation Tooling Matrix

| Platform | Statistical Engine | Native CUPED | Dynamic Remote Config / SDUI |
| :--- | :--- | :--- | :--- |
| **Statsig** | Frequentist + CUPED + Sequential | Yes (Built-in) | Yes (Dynamic Configs & Feature Gates) |
| **Eppo** | Bayesian / mSPRT + CUPED | Yes (Built-in) | SDK / Feature Flagging Bridge |
| **PostHog** | Standard Bayesian | Partial | Built-in Feature Flags |
| **Firebase A/B**| Standard Bayesian | No | Firebase Remote Config |

---

## 📖 Reference Deep Research Documents
- [`01_mobile_growth_pm_anatomy_and_scaling.md`](../researches/01_mobile_growth_pm_anatomy_and_scaling.md)
- [`03_retention_lifecycle_and_experimentation_engine.md`](../researches/03_retention_lifecycle_and_experimentation_engine.md)
