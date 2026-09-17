import statistics

N_BINS = 10


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def labeled_rows(rows):
    return [r for r in rows if r.get("label") not in (None, "")]


def call_groups(rows):
    groups = {}
    for row in rows:
        key = (row["model"], row["task"], row["sample_id"], row["repetition"])
        groups.setdefault(key, []).append(row)
    return groups


def brier_for_row(row):
    p_true = _as_float(row.get("prob_true"))
    if p_true is None:
        return None
    return (1.0 - p_true) ** 2


def aggregate(rows):
    calls = call_groups(rows)
    total_cost = 0.0
    total_in = 0
    total_out = 0
    latencies = []
    malformed_calls = 0
    invalid_calls = 0
    error_calls = 0
    for key, group in calls.items():
        first = group[0]
        total_cost += _as_float(first.get("cost_usd")) or 0.0
        total_in += int(first.get("input_tokens") or 0)
        total_out += int(first.get("output_tokens") or 0)
        latency = _as_float(first.get("latency_ms"))
        if latency is not None:
            latencies.append(latency)
        if any(str(r.get("error")) for r in group):
            error_calls += 1
        if any(r.get("valid") is False for r in group):
            invalid_calls += 1
        if int(first.get("malformed_retries") or 0) > 0:
            malformed_calls += 1
    corrects = [_as_float(r.get("correct")) for r in labeled_rows(rows)]
    corrects = [c for c in corrects if c is not None]
    briers = [b for b in (brier_for_row(r) for r in labeled_rows(rows)) if b is not None]
    peaks = [_as_float(r.get("confidence")) for r in labeled_rows(rows)]
    peaks = [p for p in peaks if p is not None]
    accuracy = statistics.mean(corrects) if corrects else None
    brier = statistics.mean(briers) if briers else None
    n_calls = len(calls)
    return {
        "n_calls": n_calls,
        "n_judgments": len(rows),
        "accuracy": accuracy,
        "brier": brier,
        "ece": ece(labeled_rows(rows)),
        "type_validity": 1.0 - malformed_calls / n_calls if n_calls else None,
        "answer_schema_valid": 1.0 - invalid_calls / n_calls if n_calls else None,
        "latency_p50": percentile(latencies, 50),
        "latency_p95": percentile(latencies, 95),
        "latency_mean": statistics.mean(latencies) if latencies else None,
        "cost_usd_total": total_cost,
        "cost_usd_per_1k": total_cost / n_calls * 1000 if n_calls else None,
        "tokens_in_total": total_in,
        "tokens_out_total": total_out,
        "consistency": consistency(rows),
        "prob_stability": prob_stability(rows),
        "reliability": reliability(labeled_rows(rows)),
    }


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct / 100.0
    f = int(k)
    c = f + 1 if f + 1 < len(ordered) else f
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def ece(rows):
    if not rows:
        return None
    buckets = {i: {"conf": [], "acc": []} for i in range(N_BINS)}
    for row in rows:
        conf = _as_float(row.get("confidence"))
        acc = _as_float(row.get("correct"))
        if conf is None or acc is None:
            continue
        idx = min(int(conf * N_BINS), N_BINS - 1)
        buckets[idx]["conf"].append(conf)
        buckets[idx]["acc"].append(acc)
    total = 0.0
    n = 0
    for bucket in buckets.values():
        if not bucket["acc"]:
            continue
        mean_conf = statistics.mean(bucket["conf"])
        mean_acc = statistics.mean(bucket["acc"])
        total += len(bucket["acc"]) * abs(mean_acc - mean_conf)
        n += len(bucket["acc"])
    return total / n if n else None


def reliability(rows):
    table = []
    buckets = {i: {"conf": [], "acc": []} for i in range(N_BINS)}
    for row in rows:
        conf = _as_float(row.get("confidence"))
        acc = _as_float(row.get("correct"))
        if conf is None or acc is None:
            continue
        idx = min(int(conf * N_BINS), N_BINS - 1)
        buckets[idx]["conf"].append(conf)
        buckets[idx]["acc"].append(acc)
    for i, bucket in buckets.items():
        if not bucket["acc"]:
            continue
        table.append({
            "bin": f"{i / N_BINS:.1f}-{(i + 1) / N_BINS:.1f}",
            "n": len(bucket["acc"]),
            "mean_confidence": statistics.mean(bucket["conf"]),
            "accuracy": statistics.mean(bucket["acc"]),
            "gap": abs(statistics.mean(bucket["acc"]) - statistics.mean(bucket["conf"])),
        })
    return table


def consistency(rows):
    by_group = {}
    for row in rows:
        key = (row["model"], row["task"], row["sample_id"], row["question_id"])
        by_group.setdefault(key, []).append(row)
    groups = [g for g in by_group.values() if len(g) >= 2]
    if not groups:
        return None
    agreements = 0
    for group in groups:
        predictions = {r["prediction"] for r in group}
        agreements += 1 if len(predictions) == 1 else 0
    return agreements / len(groups)


def prob_stability(rows):
    by_group = {}
    for row in rows:
        key = (row["model"], row["task"], row["sample_id"], row["question_id"])
        by_group.setdefault(key, []).append(row)
    groups = [g for g in by_group.values() if len(g) >= 2]
    if not groups:
        return None
    diffs = []
    for group in groups:
        values = [_as_float(r.get("prob_true")) for r in group]
        values = [v for v in values if v is not None]
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                diffs.append(abs(values[i] - values[j]))
    return statistics.mean(diffs) if diffs else None


def per_task_accuracy(rows):
    result = {}
    for row in labeled_rows(rows):
        task = row["task"]
        result.setdefault(task, []).append(_as_float(row.get("correct")))
    out = {}
    for task, corrects in result.items():
        corrects = [c for c in corrects if c is not None]
        out[task] = statistics.mean(corrects) if corrects else None
    return out


def per_question_accuracy(rows, question_ids):
    out = {}
    for row in labeled_rows(rows):
        qid = row["question_id"]
        key = f"{row['task']}.{qid}"
        out.setdefault(key, []).append(_as_float(row.get("correct")))
    final = {}
    for key, corrects in out.items():
        corrects = [c for c in corrects if c is not None]
        final[key] = statistics.mean(corrects) if corrects else None
    return final