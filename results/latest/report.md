## Results

Run **20260918T070719Z** · mode **auto** · 528 judgment rows · 12 samples/task · 3 repetitions

Live model access: Jev yes (real API) · LLM yes (real API)

### Overall metrics

| Model | Accuracy | Brier ↓ | ECE ↓ | Repeat-agreement | Type-validity | Latency p50 | Latency p95 | Cost per 1k queries |
|---|---|---|---|---|---|---|---|---|
| jev (typesafe) | 88.2% | 0.089 | 0.067 | 100.0% | 100.0% | 627ms | 701ms | $0.0189 |
| gpt-5.6-luna | 86.8% | 0.113 | 0.077 | 88.6% | 100.0% | 2766ms | 4052ms | $0.2923 |

### Accuracy by task (primary decisions)

| Model | churn_likelihood | content_moderation | field_extraction | support_routing |
|---|---|---|---|---|
| jev (typesafe) | 66.7% | 100.0% | 100.0% | 82.1% |
| gpt-5.6-luna | 66.7% | 97.2% | 93.1% | 85.7% |

### Reliability (calibration) by confidence bin

**jev (typesafe)** · ECE 0.067

| Confidence bin | n | Mean confidence | Accuracy | Gap |
|---|---|---|---|---|
| 0.6-0.7 | 12 | 0.657 | 25.0% | 0.407 |
| 0.7-0.8 | 18 | 0.745 | 77.8% | 0.033 |
| 0.8-0.9 | 26 | 0.849 | 92.3% | 0.074 |
| 0.9-1.0 | 172 | 0.976 | 93.0% | 0.046 |

**gpt-5.6-luna** · ECE 0.077

| Confidence bin | n | Mean confidence | Accuracy | Gap |
|---|---|---|---|---|
| 0.5-0.6 | 1 | 0.550 | 100.0% | 0.450 |
| 0.6-0.7 | 6 | 0.618 | 33.3% | 0.285 |
| 0.7-0.8 | 10 | 0.756 | 70.0% | 0.056 |
| 0.8-0.9 | 26 | 0.837 | 80.8% | 0.030 |
| 0.9-1.0 | 185 | 0.979 | 90.3% | 0.076 |

### Speed and cost detail

| Model | Calls | Tokens in | Tokens out | Total cost | Latency mean | p50 | p95 |
|---|---|---|---|---|---|---|---|
| jev (typesafe) | 150 | 67521 | 7356 | $0.002836 | 644ms | 627ms | 701ms |
| gpt-5.6-luna | 150 | 89478 | 21626 | $0.043847 | 2886ms | 2766ms | 4052ms |

### Caveats

- LLM results use the System-One-style wrapper over an OpenAI-compatible endpoint (single structured JSON, corrective retries, normalized probabilities) — the fairest structured-decision wrapper we know of, but still not identical to the native TypeSafe parallel sampler.
- This run used live responses from both Jev and the reference LLM(s).
- Sample sizes are small; treat numbers as indicative, not definitive.
