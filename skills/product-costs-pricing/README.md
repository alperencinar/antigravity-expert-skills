# product-costs-pricing Skill

Help developers analyze API execution costs, structure virtual credit systems, calculate gross margins, and automate pricing configuration setups on App Store Connect and Google Play Store.

## Installation

This skill is installed globally in your Antigravity agent configuration:
```
~/.gemini/config/skills/product-costs-pricing/
```

## Commands & Usage

### 1. Cost Calculations (`/costs`)
Calculate unit costs for any feature by inputting input/output token metrics and LLM models:
```bash
/costs analyze --input 1500 --output 500 --model deepseek-v4-pro
```

### 2. Pricing Matrix Designing (`/pricing`)
Define credits packages and subscriptions:
```bash
/pricing tiers --app "MySaaSApp"
```

Verify gross margins and safety thresholds under current parities:
```bash
/pricing margins --price 24.99 --credits 75 --run-cost-usd 0.0015
```

### 3. Developer Consoles Validation (`/pricing-sync`)
Validate App Store Connect and Google Play Console parameters prior to pushing them:
```bash
/pricing-sync verify --store apple
/pricing-sync verify --store google
```

## References
*   [cost-benchmarks.md](file:///Users/alperencnrr/.gemini/config/skills/product-costs-pricing/references/cost-benchmarks.md) - API and token pricing reference.
*   [cost_calculator.py](file:///Users/alperencnrr/.gemini/config/skills/product-costs-pricing/scripts/cost_calculator.py) - Calculation script.
