# jev-benchmarks

Benchmark harness comparing **Jev** (TypeSafe's first System One model — unstructured/structured state in, typed probabilistic decisions out) against frontier LLMs on structured decision tasks.

The harness mirrors the setup TypeSafe describes in the [System One announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev): every model is asked the same typed questions about the same state, and decisions are compared on accuracy, calibration, consistency, latency, cost, and schema validity.

## Setup

Requires Python >= 3.10 and `requests`:

```bash
pip install -r requirements.txt
```

Optional but recommended for real runs: the official packages in the same style

```bash
pip install typesafe-sdk system-one-adapter
```

## API keys (env vars only, never committed)

| Key | Purpose |
| --- | --- |
| `TYPESAFE_API_KEY` | Jev queries through the TypeSafe API (`POST https://api.typesafe.ai/v1/systemone`). |
| `OPENROUTER_API_KEY` or `OPENAI_API_KEY` | Reference LLM through an OpenAI-compatible endpoint (defaults to OpenRouter). |
| `LLM_MODELS` | Space-separated model ids for the reference LLM(s). Default: `openai/gpt-5-mini anthropic/claude-sonnet-4.5`. |
| `LLM_BASE_URL` | Override the OpenAI-compatible endpoint (default `https://openrouter.ai/api/v1`). |
| `PRICE_PER_MT_IN_USD` / `PRICE_PER_MT_OUT_USD` | Override approximate pricing for your LLM model. |

Without keys the harness runs in **dry/mocked mode**: Jev and the reference LLM are replaced by deterministic mock models so the full pipeline (collection → metrics → report) still runs end to end. Mock output is clearly labeled and must not be read as real measurements.

## Run

```bash
python run_benchmark.py --mode auto            # real APIs when keys are present, else mocked
python run_benchmark.py --mode dry             # force mocked models
python run_benchmark.py --tasks support_routing,churn_likelihood
```

Outputs go to `results/<run-id>/` (plus a `results/latest/` mirror):

- `results.csv` — per-query rows: model, task, sample, repetition, question, prediction, label, correctness, probability of the true label, confidence, latency, tokens, cost, validity.
- `model_metrics.csv` — aggregate metrics per model.
- `report.md` — the comparison write-up (printed to stdout as well).

## Tasks

Each task in `tasks/` defines a JSON schema of TypeSafe questions (`choice`, `score`, `noul`) plus labeled test data:

| Task | Primary decision | Question schema |
| --- | --- | --- |
| `support_routing` | Which team handles this ticket? | `choice` (billing/technical/account/sales/other) + `urgency` `noul` |
| `churn_likelihood` | Churn risk level (0–4) | single `score` rubric |
| `content_moderation` | Block this content? | `should_block` `noul` + `severity` `score` |
| `field_extraction` | Which product line + promo present? | `product_category` `choice` + `has_promo_code` `noul` |

## Models under test

- **Jev** (`jev-latest`) — native TypeSafe client against `/v1/systemone`. One request carries every question; answers return with calibrated probabilities and confidence.
- **Reference LLM(s)** — an OpenAI-compatible model called through a System-One-style wrapper (same contract as `system-one-adapter`): one structured JSON response covering all questions, native `json_schema` structured outputs when the endpoint supports it (fallback: prompted JSON), corrective retries on malformed output, and probability normalization. This is the fairest structured-decision wrapper we know of — outputs are comparable to native Jev answers by construction.

## Metrics

- **Accuracy** — top-1 discrete decision matches the label.
- **Brier score** — per-question mean squared error over the full predicted probability distribution; lower is better.
- **ECE / reliability** — bucketed confidence vs observed accuracy; a calibrated model traces the diagonal.
- **Consistency** — each sample is repeated `--repeat` times; fraction of sample·question groups where every repetition agrees on the discrete answer.
- **Type validity** — share of calls that needed no corrective retry / produced schema-valid answers.
- **Latency** — p50 / p95 end-to-end per call.
- **Cost** — per-query cost from token usage and model pricing; reported per 1k queries.

## Caveats (read before citing numbers)

- Fair comparison is hard: the LLM wrapper forces a text generator into the System One shape, which TypeSafe explicitly notes is slower and more expensive than unstructured prompting. It is the most apples-to-apples wrapper available, not a free prompt.
- LLM numbers inherit OpenRouter's model routing and cost behavior.
- Jev's "no type errors" property is structural (schema matching is guaranteed), so its type-validity is expected to be 100% by construction; the LLM's type-validity is empirical.
- Jev is early access / waitlisted; keys govern whether runs are live or mocked.
- Small sample sizes: numbers are indicative, not a substitute for a larger eval.