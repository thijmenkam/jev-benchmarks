## Results

Run **20260917T183908Z** · mode **dry** · 792 judgment rows · 12 samples/task · 3 repetitions

Live model access: Jev NO (mock) · LLM NO (mock)

### Overall metrics

| Model | Accuracy | Brier ↓ | ECE ↓ | Repeat-agreement | Type-validity | Latency p50 | Latency p95 | Cost per 1k queries |
|---|---|---|---|---|---|---|---|---|
| jev (mock) | 93.4% | 0.104 | 0.134 | 100.0% | 100.0% | 154ms | 255ms | $0.0071 |
| gpt-5-mini (mock) | 94.7% | 0.110 | 0.154 | 72.7% | 94.7% | 1688ms | 3023ms | $2.4107 |
| claude-sonnet-4.5 (mock) | 93.9% | 0.112 | 0.150 | 75.0% | 94.0% | 2300ms | 3820ms | $3.8057 |

### Accuracy by task (primary decisions)

| Model | churn_likelihood | content_moderation | field_extraction | support_routing |
|---|---|---|---|---|
| jev (mock) | 75.0% | 100.0% | 95.8% | 96.4% |
| gpt-5-mini (mock) | 94.4% | 100.0% | 95.8% | 91.7% |
| claude-sonnet-4.5 (mock) | 88.9% | 100.0% | 91.7% | 95.2% |

### Reliability (calibration) by confidence bin

**jev (mock)** · ECE 0.134

| Confidence bin | n | Mean confidence | Accuracy | Gap |
|---|---|---|---|---|
| 0.3-0.4 | 9 | 0.400 | 33.3% | 0.067 |
| 0.4-0.5 | 12 | 0.421 | 100.0% | 0.579 |
| 0.5-0.6 | 15 | 0.516 | 80.0% | 0.284 |
| 0.7-0.8 | 78 | 0.769 | 92.3% | 0.154 |
| 0.9-1.0 | 114 | 0.940 | 100.0% | 0.060 |

**gpt-5-mini (mock)** · ECE 0.154

| Confidence bin | n | Mean confidence | Accuracy | Gap |
|---|---|---|---|---|
| 0.3-0.4 | 1 | 0.400 | 100.0% | 0.600 |
| 0.4-0.5 | 17 | 0.415 | 94.1% | 0.526 |
| 0.5-0.6 | 18 | 0.516 | 94.4% | 0.428 |
| 0.7-0.8 | 78 | 0.760 | 87.2% | 0.112 |
| 0.9-1.0 | 114 | 0.920 | 100.0% | 0.080 |

**claude-sonnet-4.5 (mock)** · ECE 0.150

| Confidence bin | n | Mean confidence | Accuracy | Gap |
|---|---|---|---|---|
| 0.3-0.4 | 3 | 0.400 | 100.0% | 0.600 |
| 0.4-0.5 | 14 | 0.418 | 85.7% | 0.439 |
| 0.5-0.6 | 19 | 0.516 | 89.5% | 0.379 |
| 0.7-0.8 | 78 | 0.758 | 87.2% | 0.114 |
| 0.8-0.9 | 9 | 0.899 | 100.0% | 0.101 |
| 0.9-1.0 | 105 | 0.912 | 100.0% | 0.088 |

### Speed and cost detail

| Model | Calls | Tokens in | Tokens out | Total cost | Latency mean | p50 | p95 |
|---|---|---|---|---|---|---|---|
| jev (mock) | 150 | 25287 | 33000 | $0.001062 | 161ms | 154ms | 255ms |
| gpt-5-mini (mock) | 150 | 25287 | 33000 | $0.361609 | 1820ms | 1688ms | 3023ms |
| claude-sonnet-4.5 (mock) | 150 | 25287 | 33000 | $0.570861 | 2482ms | 2300ms | 3820ms |

### Caveats

- LLM results use the System-One-style wrapper over an OpenAI-compatible endpoint (single structured JSON, corrective retries, normalized probabilities) — the fairest structured-decision wrapper we know of, but still not identical to the native TypeSafe parallel sampler.
- This run used mocked model responses (no API keys present); live runs require `TYPESAFE_API_KEY` and `OPENROUTER_API_KEY` / `OPENAI_API_KEY`. Mock latency/cost/token figures are synthetic.
- Sample sizes are small; treat numbers as indicative, not definitive.
