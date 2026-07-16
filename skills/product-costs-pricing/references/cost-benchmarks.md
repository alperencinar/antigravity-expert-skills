# API Cost Benchmarks (LLM & OCR)

This reference file lists pricing parameters (input/output per 1M tokens) for core models as of July 2026.

## 1. Google Gemini Models

| Model Name | Input Price (per 1M) | Output Price (per 1M) | Context Cache Input (per 1M) |
| :--- | :---: | :---: | :---: |
| `gemini-2.5-flash-lite` | $0.075 | $0.300 | $0.01875 |
| `gemini-2.5-flash` | $0.150 | $0.600 | $0.03750 |
| `gemini-2.5-pro` | $1.250 | $5.000 | $0.31250 |
| `gemini-3.1-flash-lite` | $0.070 | $0.280 | $0.01750 |
| `gemini-3.1-flash` | $0.140 | $0.560 | $0.03500 |

---

## 2. DeepSeek Models

| Model Name | Input Price (per 1M) | Output Price (per 1M) | Prompt Cache Hit (per 1M) |
| :--- | :---: | :---: | :---: |
| `deepseek-v4-pro` (API) | $0.140 | $0.280 | $0.050 |
| `deepseek-chat` / `v3` | $0.140 | $0.280 | $0.014 |
| `deepseek-coder` | $0.140 | $0.280 | $0.014 |

---

## 3. Anthropic Claude Models

| Model Name | Input Price (per 1M) | Output Price (per 1M) | Prompt Cache Write (per 1M) | Prompt Cache Read (per 1M) |
| :--- | :---: | :---: | :---: | :---: |
| `claude-3-5-haiku` | $0.80 | $4.00 | $1.00 | $0.08 |
| `claude-3-5-sonnet` | $3.00 | $15.00 | $3.75 | $0.30 |
| `claude-3-opus` | $15.00 | $75.00 | $18.75 | $1.50 |

---

## 4. OCR & Vision API Costs

*   **Google Cloud Vision API (Text Detection):** $1.50 per 1,000 units (first 1,000 units free per month).
*   **AWS Rekognition (Text in Image):** $1.00 per 1,000 images.
