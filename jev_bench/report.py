import csv
import os
import shutil

from . import metrics as m


def _fmt(value, digits=3):
    if value is None:
        return "-"
    return f"{value:.{digits}f}"


def _pct(value):
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"


def _ms(value):
    if value is None:
        return "-"
    return f"{value:.0f}ms"


def build_report(meta, tasks, models, rows, out_dir):
    per_model = {}
    for row in rows:
        per_model.setdefault(row["model"], []).append(row)
    aggregate_by_model = {}
    for name, model_rows in per_model.items():
        aggregate_by_model[name] = m.aggregate(model_rows)

    lines = []
    lines.append("## Results")
    lines.append("")
    lines.append("Run **%s** · mode **%s** · %d judgment rows · %d samples/task · %d repetitions" % (
        meta["run_id"], meta["mode"], len(rows), meta.get("samples_per_task", 0), meta.get("repeat", 1)))
    lines.append("")
    real_jev = meta.get("real_jev")
    real_llm = meta.get("real_llm")
    lines.append("Live model access: Jev %s · LLM %s" % (
        "yes (real API)" if real_jev else "NO (mock)", "yes (real API)" if real_llm else "NO (mock)"))
    lines.append("")

    lines.append("### Overall metrics")
    lines.append("")
    lines.append("| Model | Accuracy | Brier ↓ | ECE ↓ | Repeat-agreement | Type-validity | Latency p50 | Latency p95 | Cost per 1k queries |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for name, agg in aggregate_by_model.items():
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            name,
            _pct(agg["accuracy"]),
            _fmt(agg["brier"]),
            _fmt(agg["ece"]),
            _pct(agg["consistency"]),
            _pct(agg["type_validity"]),
            _ms(agg["latency_p50"]),
            _ms(agg["latency_p95"]),
            "$%.4f" % agg["cost_usd_per_1k"] if agg["cost_usd_per_1k"] is not None else "-"))
    lines.append("")

    lines.append("### Accuracy by task (primary decisions)")
    lines.append("")
    task_ids = list(tasks.keys())
    lines.append("| Model | " + " | ".join(task_ids) + " |")
    lines.append("|" + "---|" * (len(task_ids) + 1))
    for name, model_rows in per_model.items():
        per_task = m.per_task_accuracy(model_rows)
        lines.append("| %s | %s |" % (name, " | ".join(_pct(per_task.get(t)) for t in task_ids)))
    lines.append("")

    lines.append("### Reliability (calibration) by confidence bin")
    lines.append("")
    for name, agg in aggregate_by_model.items():
        lines.append("**%s** · ECE %s" % (name, _fmt(agg["ece"])))
        lines.append("")
        lines.append("| Confidence bin | n | Mean confidence | Accuracy | Gap |")
        lines.append("|---|---|---|---|---|")
        for row in agg["reliability"]:
            lines.append("| %s | %s | %s | %s | %s |" % (
                row["bin"], row["n"], _fmt(row["mean_confidence"]), _pct(row["accuracy"]), _fmt(row["gap"])))
        lines.append("")

    lines.append("### Speed and cost detail")
    lines.append("")
    lines.append("| Model | Calls | Tokens in | Tokens out | Total cost | Latency mean | p50 | p95 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for name, agg in aggregate_by_model.items():
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            name, agg["n_calls"], agg["tokens_in_total"], agg["tokens_out_total"],
            "$%.6f" % agg["cost_usd_total"], _ms(agg["latency_mean"]),
            _ms(agg["latency_p50"]), _ms(agg["latency_p95"])))
    lines.append("")

    lines.append("### Caveats")
    lines.append("")
    lines.append("- LLM results use the System-One-style wrapper over an OpenAI-compatible endpoint (single structured JSON, corrective retries, normalized probabilities) — the fairest structured-decision wrapper we know of, but still not identical to the native TypeSafe parallel sampler.")
    lines.append("- This run used mocked model responses (no API keys present); live runs require `TYPESAFE_API_KEY` and `OPENROUTER_API_KEY` / `OPENAI_API_KEY`. Mock latency/cost/token figures are synthetic.")
    lines.append("- Sample sizes are small; treat numbers as indicative, not definitive.")
    lines.append("")

    report_md = "\n".join(lines)

    with open(os.path.join(out_dir, "report.md"), "w") as fh:
        fh.write(report_md)

    metrics_csv = os.path.join(out_dir, "model_metrics.csv")
    with open(metrics_csv, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "model", "n_calls", "accuracy", "brier", "ece", "consistency", "prob_stability",
            "type_validity", "latency_p50_ms", "latency_p95_ms", "latency_mean_ms",
            "cost_usd_total", "cost_usd_per_1k", "tokens_in", "tokens_out",
        ])
        for name, agg in aggregate_by_model.items():
            writer.writerow([
                name, agg["n_calls"], _fmt(agg["accuracy"], 4), _fmt(agg["brier"], 4), _fmt(agg["ece"], 4),
                _fmt(agg["consistency"], 4), _fmt(agg["prob_stability"], 4), _fmt(agg["type_validity"], 4),
                _fmt(agg["latency_p50"]), _fmt(agg["latency_p95"]), _fmt(agg["latency_mean"]),
                "%.6f" % agg["cost_usd_total"], "%.6f" % agg["cost_usd_per_1k"] if agg["cost_usd_per_1k"] is not None else "",
                agg["tokens_in_total"], agg["tokens_out_total"],
            ])

    latest = os.path.join(out_dir.rsplit(os.sep, 1)[0], "latest")
    if os.path.exists(latest):
        shutil.rmtree(latest)
    shutil.copytree(out_dir, latest)
    return report_md, out_dir