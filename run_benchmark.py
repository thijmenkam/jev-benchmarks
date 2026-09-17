#!/usr/bin/env python3
import argparse
import json
import os
import sys

from jev_bench import config, metrics, report
from jev_bench.report import build_report
from jev_bench.runner import build_models, run_benchmark
from jev_bench.tasks import load_tasks


def main(argv=None):
    parser = argparse.ArgumentParser(description="Jev (System One) vs LLM benchmark harness")
    parser.add_argument("--tasks", default="all", help="comma-separated task ids, or 'all'")
    parser.add_argument("--repeat", type=int, default=3, help="repetitions per sample (consistency)")
    parser.add_argument("--mode", choices=["auto", "dry"], default="auto",
                        help="auto = use real APIs when keys are present; dry = force mock models")
    parser.add_argument("--json-meta", action="store_true", help="print machine-readable run metadata")
    args = parser.parse_args(argv)

    tasks = load_tasks(args.tasks)
    if not tasks:
        print("no tasks selected; available:", file=sys.stderr)
        for tid in load_tasks("all"):
            print(f"  {tid}", file=sys.stderr)
        return 2

    models = build_models(mode=args.mode)
    out_dir, rows, meta = run_benchmark(tasks, models, repeat=args.repeat, mode=args.mode)
    meta["samples_per_task"] = len(next(iter(tasks.values())).samples)

    results_dir = out_dir
    report_md, out_dir = build_report(meta, tasks, models, rows, out_dir)
    print(report_md)
    print("---")
    print(f"raw results:   {os.path.join(results_dir, 'results.csv')}")
    print(f"model metrics: {os.path.join(results_dir, 'model_metrics.csv')}")
    print(f"report:        {os.path.join(out_dir, 'report.md')}")
    if args.json_meta:
        print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())