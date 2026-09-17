## Results

Run **20260917T184210Z** · mode **auto** · 264 judgment rows · 12 samples/task · 3 repetitions

Live model access: Jev yes (real API) · LLM not evaluated (no API key)

### Overall metrics

| Model | Accuracy | Brier ↓ | ECE ↓ | Repeat-agreement | Type-validity | Latency p50 | Latency p95 | Cost per 1k queries |
|---|---|---|---|---|---|---|---|---|
| jev (typesafe) | 88.2% | 0.089 | 0.068 | 100.0% | 100.0% | 667ms | 918ms | $0.0189 |

### Accuracy by task (primary decisions)

| Model | churn_likelihood | content_moderation | field_extraction | support_routing |
|---|---|---|---|---|
| jev (typesafe) | 66.7% | 100.0% | 100.0% | 82.1% |

### Reliability (calibration) by confidence bin

**jev (typesafe)** · ECE 0.068

| Confidence bin | n | Mean confidence | Accuracy | Gap |
|---|---|---|---|---|
| 0.6-0.7 | 12 | 0.654 | 25.0% | 0.404 |
| 0.7-0.8 | 19 | 0.747 | 73.7% | 0.011 |
| 0.8-0.9 | 24 | 0.849 | 95.8% | 0.109 |
| 0.9-1.0 | 173 | 0.976 | 93.1% | 0.045 |

### Speed and cost detail

| Model | Calls | Tokens in | Tokens out | Total cost | Latency mean | p50 | p95 |
|---|---|---|---|---|---|---|---|
| jev (typesafe) | 150 | 67521 | 7356 | $0.002836 | 691ms | 667ms | 918ms |

### Caveats

- LLM results use the System-One-style wrapper over an OpenAI-compatible endpoint (single structured JSON, corrective retries, normalized probabilities) — the fairest structured-decision wrapper we know of, but still not identical to the native TypeSafe parallel sampler.
- This run used live responses from Jev only. No OpenRouter/OpenAI key was available, so the LLM axis is pending — no LLM numbers (live or mocked) are included here.
- Sample sizes are small; treat numbers as indicative, not definitive.
