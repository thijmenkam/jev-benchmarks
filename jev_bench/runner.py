import csv
import datetime
import json
import os

from . import config
from .clients import LLMAdapterClient, MockModelClient, TypeSafeClient
from .tasks import label_to_reference

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(REPO_ROOT, "results")


def build_models(mode="auto"):
    dry = mode == "dry"
    jev_real = config.has_jev_key() and not dry
    llm_real = config.has_llm_key() and not dry
    models = []
    if jev_real:
        models.append({"key": "jev", "name": "jev (typesafe)", "client": TypeSafeClient(), "real": True})
    else:
        models.append({
            "key": "jev",
            "name": "jev (mock)",
            "client": MockModelClient("jev-mock", accuracy=0.88, median_latency_ms=150, temperature=0.0, malformed_rate=0.0),
            "real": False,
        })
    llm_models = config.LLM_MODELS or ["openai/gpt-5-mini"]
    if llm_real:
        for model_id in llm_models:
            models.append({
                "key": "llm",
                "name": model_id,
                "client": LLMAdapterClient(
                    model=model_id,
                    protocol="responses" if model_id in config.LLM_RESPONSES_MODELS else "chat",
                ),
                "real": True,
            })
    elif not jev_real:
        for i, model_id in enumerate(llm_models):
            short = model_id.rsplit("/", 1)[-1]
            models.append({
                "key": "llm",
                "name": f"{short} (mock)",
                "client": MockModelClient(
                    f"{short}-mock",
                    accuracy=0.84 - 0.02 * i,
                    median_latency_ms=1800 + 600 * i,
                    temperature=0.4,
                    malformed_rate=0.03,
                ),
                "real": False,
            })
    return models


def run_benchmark(tasks, models, repeat=3, mode="auto"):
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = os.path.join(RESULTS_DIR, run_id)
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for model in models:
        for task_id, task in tasks.items():
            for sample in task.samples:
                for rep in range(repeat):
                    call_seed = rep if model["real"] else (0 if model["client"].temperature == 0 else rep)
                    try:
                        response = model["client"].timed_evaluate(sample.state, task.questions, label=sample.label, call_seed=call_seed)
                        if isinstance(response.raw, dict) and response.raw.get("latency_ms"):
                            latency = response.raw["latency_ms"]
                        else:
                            latency = response.latency_ms
                    except Exception as exc:
                        response = None
                        latency = 0.0
                        for qid, qdef in task.questions.items():
                            rows.append({
                                "model": model["name"], "provider": model["client"].provider, "real": model["real"],
                                "task": task_id, "sample_id": sample.id, "repetition": rep, "question_id": qid,
                                "qtype": qdef["type"],
                                "label": label_to_reference(qdef["type"], sample.label.get(qid, "")),
                                "prediction": "ERROR", "correct": None, "prob_true": None, "confidence": None,
                                "valid": False, "latency_ms": latency, "input_tokens": 0, "output_tokens": 0,
                                "cost_usd": 0.0, "n_retries": 0, "malformed_retries": 0,
                                "error": str(exc),
                            })
                        continue
                    for qid, qdef in task.questions.items():
                        label_ref = label_to_reference(qdef["type"], sample.label.get(qid, ""))
                        result = response.answers.get(qid)
                        if result is None:
                            rows.append({
                                "model": model["name"], "provider": model["client"].provider, "real": model["real"],
                                "task": task_id, "sample_id": sample.id, "repetition": rep, "question_id": qid,
                                "qtype": qdef["type"], "label": label_ref, "prediction": "ERROR",
                                "correct": None, "prob_true": None, "confidence": None, "valid": False,
                                "latency_ms": latency, "input_tokens": response.input_tokens,
                                "output_tokens": response.output_tokens, "cost_usd": response.cost_usd,
                                "n_retries": response.n_retries, "malformed_retries": response.malformed_retries,
                                "error": "missing answer",
                            })
                            continue
                        correct = result.prediction == label_ref if label_ref != "" else None
                        prob_true = result.probability_of(label_ref) if label_ref != "" else None
                        rows.append({
                            "model": model["name"], "provider": model["client"].provider, "real": model["real"],
                            "task": task_id, "sample_id": sample.id, "repetition": rep, "question_id": qid,
                            "qtype": qdef["type"], "label": label_ref, "prediction": result.prediction,
                            "correct": correct, "prob_true": prob_true, "confidence": result.confidence,
                            "valid": result.valid, "latency_ms": latency,
                            "input_tokens": response.input_tokens, "output_tokens": response.output_tokens,
                            "cost_usd": response.cost_usd, "n_retries": response.n_retries,
                            "malformed_retries": response.malformed_retries, "error": "",
                            "probabilities": json.dumps(result.probabilities, sort_keys=True),
                        })
    csv_path = os.path.join(out_dir, "results.csv")
    write_results_csv(csv_path, rows)
    meta = {
        "run_id": run_id,
        "mode": mode,
        "real_jev": bool(config.has_jev_key()),
        "real_llm": bool(config.has_llm_key()),
        "repeat": repeat,
        "models": [{"name": m["name"], "provider": m["client"].provider, "real": m["real"]} for m in models],
        "tasks": sorted(tasks.keys()),
        "created_at": run_id,
    }
    with open(os.path.join(out_dir, "meta.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    return out_dir, rows, meta


def write_results_csv(path, rows):
    fieldnames = [
        "model", "provider", "real", "task", "sample_id", "repetition", "question_id", "qtype",
        "label", "prediction", "correct", "prob_true", "confidence", "valid", "latency_ms",
        "input_tokens", "output_tokens", "cost_usd", "n_retries", "malformed_retries", "error",
        "probabilities",
    ]
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})