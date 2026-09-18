# jev-benchmarks

A small, reproducible harness that compares **Jev** — TypeSafe's first *System One* model
(unstructured/structured state in, **typed probabilistic decisions out**) — against
frontier LLMs on the same structured decision tasks.

It mirrors the setup TypeSafe describes in the [System One announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev):
every model answers the same typed questions about the same state, and decisions are scored on
**accuracy, calibration, consistency, latency, cost, and schema validity**.

---

## Latest results (live, 2026-09-18)

Run `20260918T070719Z` · 4 tasks · 3 repetitions · **150 calls per model** (528 judgment rows, 0 errors).

| Model | Accuracy | Brier ↓ | ECE ↓ | Repeat-agreement | Latency p50 | Cost / 1k |
|---|---|---|---|---|---|---|
| **jev (typesafe)** | **88.2%** | **0.089** | **0.067** | **100%** | **627ms** | **$0.019** |
| gpt-5.6-luna (OpenCode Go) | 86.8% | 0.113 | 0.077 | 88.6% | 2766ms | $0.292 |

What stands out:

- **Jev wins (or ties) 3 of 4 tasks** — churn 66.7%↔66.7% (tie), moderation 100% vs 97.2%,
  extraction 100% vs 93.1%. Luna wins only support routing (85.7% vs 82.1%).
- **Better calibrated:** Jev's Brier (0.089) and ECE (0.067, nearly ideal at near-1 confidences)
  beat Luna's 0.113 / 0.077.
- **Much faster and cheaper:** ~4× lower latency (627ms vs 2.8s p50) and ~15× lower cost ($0.019 vs $0.29 per 1k queries).
- Jev is fully self-consistent across repetitions (100%); Luna agrees with itself 88.6% of the time.

Full per-task and calibration detail: [`results/latest/report.md`](results/latest/report.md)
(+ `results.csv` with every query, and `model_metrics.csv`).

> The comparative LLM wrapper is the fairest one we could build, but see
> [Caveats](#caveats-read-before-citing-numbers) before quoting these numbers to anyone.

---

## What it does

1. **Tasks** (`tasks/*.json`) each define typed TypeSafe questions (`choice`, `score`, `noul`)
   over labeled states — support-ticket routing, churn likelihood, content moderation, field extraction.
2. **Models** answer every question on every state:
   - **Jev** natively, through the TypeSafe API (one request, calibrated probabilities per question);
   - a **reference LLM** through a System-One-style adapter (one structured JSON response covering
     all questions, `json_schema` outputs when supported, corrective retries, normalized probabilities).
3. **Metrics & report** compare the two on accuracy, Brier score, calibration (ECE), repeat
   consistency, latency, cost, and type validity. Results land in `results/<run-id>/` and
   `results/latest/`.

## Quickstart

```bash
pip install -r requirements.txt

python run_benchmark.py --mode dry    # no API keys needed — deterministic mocks, whole pipeline runs
```

Running without keys uses **dry/mocked mode** (mock output is clearly labeled and *not* real
measurement). With a Jev key but no LLM key you get a **Jev-only** run. With keys for both, the
run is fully live:

```bash
export TYPESAFE_API_KEY="sk-..."            # or JEV_API_KEY
export OPENAI_API_KEY="sk-..."              # or OPENROUTER_API_KEY
python run_benchmark.py --mode auto         # live Jev + reference LLM
python run_benchmark.py --tasks support_routing,churn_likelihood --repeat 3
```

## Configuration (env vars)

| Variable | What it does |
| --- | --- |
| `TYPESAFE_API_KEY` (alias `JEV_API_KEY`) | Jev via the TypeSafe API. |
| `OPENROUTER_API_KEY` / `OPENAI_API_KEY` | Reference LLM via any OpenAI-compatible endpoint (default OpenRouter). |
| `LLM_MODELS` | Space-separated reference model ids (default `openai/gpt-5-mini anthropic/claude-sonnet-4.5`). |
| `LLM_BASE_URL` | Endpoint override (default `https://openrouter.ai/api/v1`). |
| `LLM_STRUCTURED_OUTPUTS` | `json_schema` (default) / `json_object` / `none`. |
| `LLM_RESPONSES_MODELS` | Model ids served via the `/responses` protocol instead of `/chat/completions` (default `gpt-5.6-luna grok-4.6`). |
| `LLM_USER_AGENT`, `LLM_EXTRA_HEADERS` | Headers for gateways that require them (e.g. OpenCode Go). |
| `PRICE_PER_MT_IN_USD` / `PRICE_PER_MT_OUT_USD` | Override approximate LLM pricing. |

### Reference LLM via an OpenCode Go subscription

The harness works against OpenCode Go (`LLM_BASE_URL=https://opencode.ai/zen/go/v1`) for both its
`/chat/completions` models (DeepSeek, Kimi, GLM, …) and `/responses` models such as **GPT 5.6 Luna**
(which the latest run used). Go needs a non-generic `User-Agent` and a stable `x-opencode-session`
header.

```bash
export OPENAI_API_KEY=<opencode-go key>               # from ~/.local/share/opencode/auth.json
export LLM_BASE_URL=https://opencode.ai/zen/go/v1
export LLM_MODELS="gpt-5.6-luna"                      # auto-routed to /responses
export LLM_USER_AGENT=jev-benchmarks/0.1
export LLM_EXTRA_HEADERS='{"x-opencode-session":"jev-bench-run-1"}'
python run_benchmark.py --mode auto
```

> Go's `/responses` validator is strict: schemas must be fully typed (`const` / open map
> `propertyNames` are rejected, and `temperature` is not accepted). The harness generates a
> strict-compliant schema, so Luna keeps the default `json_schema` mode. For `/chat/completions`
> Go models, use `LLM_STRUCTURED_OUTPUTS=json_object` instead.

## Tasks

Each task pairs a JSON schema of TypeSafe questions with labeled test data.

| Task | Primary decision | Question schema |
| --- | --- | --- |
| `support_routing` | Which team handles this ticket? | `choice` (billing/technical/account/sales/other) + `urgency` `noul` |
| `churn_likelihood` | Churn risk level (0–4) | single `score` rubric |
| `content_moderation` | Block this content? | `should_block` `noul` + `severity` `score` |
| `field_extraction` | Product line + promo present? | `product_category` `choice` + `has_promo_code` `noul` |

## Method — why the comparison is fair

- **Jev** (`jev-latest`) is queried natively against `/v1/systemone`. One request carries every
  question; answers return with calibrated probabilities and confidence.
- **LLMs** are wrapped with the same contract as `system-one-adapter`: one structured JSON response
  covering all questions, native `json_schema` structured outputs when the endpoint supports it
  (prompted JSON otherwise), corrective retries on malformed output, and normalized probabilities.

This makes LLM outputs structurally comparable to Jev's by construction — but forcing a text
generator into the System One shape is still slower, costlier, and less native than unstructured
prompting, which TypeSafe itself notes.

## Metrics

- **Accuracy** — top-1 discrete decision matches the label.
- **Brier score** — mean squared error over the full predicted distribution; lower is better.
- **ECE / reliability** — bucketed confidence vs observed accuracy; a calibrated model traces the diagonal.
- **Consistency** — `--repeat`-run agreement on the discrete answer per sample·question.
- **Type validity** — share of schema-valid responses.
- **Latency** — p50/p95 end-to-end per call. **Cost** — from token usage and pricing, per 1k queries.

## Outputs

`results/<run-id>/` (with `results/latest/` mirroring the newest run):

- `results.csv` — every query: model, task, sample, question, prediction, label, correctness,
  true-label probability, confidence, latency, tokens, cost, validity.
- `model_metrics.csv` — aggregate metrics per model.
- `report.md` — the comparison write-up (also printed to stdout).

## Caveats — read before citing numbers

- Sample sizes are small (4 tasks, 12–14 samples each); treat numbers as indicative, not a verdict.
- The LLM wrapper is the most apples-to-apples option available, not a free prompt.
- Jev's 100% type validity is structural — schema conformance is guaranteed by the API; the LLM's
  type validity is measured empirically.
- Jev is early-access / waitlisted; keys govern whether a run is live or mocked.
- LLM numbers inherit endpoint routing and pricing behavior of the provider used.