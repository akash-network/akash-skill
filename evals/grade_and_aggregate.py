#!/usr/bin/env python3
"""Grade responses against assertions and aggregate into benchmark.json.

Reads:
  evals/evals.json          - assertions per eval
  <workspace>/<iter>/eval-N-<name>/<config>/outputs/response.md
  <workspace>/<iter>/eval-N-<name>/<config>/timing.json

Writes:
  <workspace>/<iter>/eval-N-<name>/<config>/run-1/grading.json
  <workspace>/<iter>/eval-N-<name>/<config>/run-1/timing.json   (copy)
  <workspace>/<iter>/benchmark.json
"""

import argparse
import json
import math
import re
import shutil
import statistics
from pathlib import Path


def check_assertion(response: str, assertion: dict) -> tuple[bool, str]:
    """Run one assertion. Returns (passed, evidence_string)."""
    a_type = assertion["type"]
    pattern = assertion["pattern"]
    flags = re.IGNORECASE if assertion.get("case_insensitive") else 0

    if a_type == "regex_present":
        match = re.search(pattern, response, flags)
        if match:
            ctx = response[max(0, match.start() - 30): min(len(response), match.end() + 30)]
            return True, f"matched: {ctx!r}"
        return False, "no match found"

    if a_type == "regex_absent":
        match = re.search(pattern, response, flags)
        if match:
            ctx = response[max(0, match.start() - 30): min(len(response), match.end() + 30)]
            return False, f"unexpected match: {ctx!r}"
        return True, "absent (good)"

    if a_type == "count_at_least":
        matches = re.findall(pattern, response, flags)
        n = len(matches)
        min_count = assertion["min_count"]
        if n >= min_count:
            return True, f"found {n} matches (>= {min_count})"
        return False, f"only found {n} matches (need {min_count})"

    raise ValueError(f"Unknown assertion type: {a_type}")


def grade_run(response_path: Path, assertions: list) -> dict:
    response = response_path.read_text()
    expectations = []
    passed = 0
    for a in assertions:
        ok, evidence = check_assertion(response, a)
        expectations.append({
            "text": f"[{a['id']}] {a['description']}",
            "passed": ok,
            "evidence": evidence,
        })
        if ok:
            passed += 1
    total = len(assertions)
    return {
        "expectations": expectations,
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "pass_rate": round(passed / total, 4) if total else 0.0,
        },
    }


def stats(values):
    if not values:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}
    n = len(values)
    mean = sum(values) / n
    sd = statistics.stdev(values) if n > 1 else 0.0
    return {
        "mean": round(mean, 4),
        "stddev": round(sd, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evals", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--skill-name", required=True)
    ap.add_argument("--baseline-config", default="old_skill", help="Config name of the baseline (default: old_skill, use iter1_skill for iteration-2)")
    args = ap.parse_args()

    evals = json.loads(Path(args.evals).read_text())["evals"]
    ws = Path(args.workspace)
    baseline = args.baseline_config

    per_eval_results = []
    config_runs = {"with_skill": [], baseline: []}

    for ev in evals:
        eval_dir = ws / f"eval-{ev['id']}-{ev['name']}"
        if not eval_dir.exists():
            print(f"missing eval dir: {eval_dir}")
            continue

        per_eval_entry = {"eval_id": ev["id"], "eval_name": ev["name"], "configs": {}}

        for config in ["with_skill", baseline]:
            config_dir = eval_dir / config
            response_path = config_dir / "outputs" / "response.md"
            timing_path = config_dir / "timing.json"

            if not response_path.exists():
                print(f"missing response: {response_path}")
                continue

            grading = grade_run(response_path, ev["assertions"])

            run_dir = config_dir / "run-1"
            run_dir.mkdir(exist_ok=True)
            (run_dir / "grading.json").write_text(json.dumps(grading, indent=2))

            if timing_path.exists():
                shutil.copy(timing_path, run_dir / "timing.json")
                timing = json.loads(timing_path.read_text())
            else:
                timing = {"total_duration_seconds": 0, "total_tokens": 0}

            run_entry = {
                "eval_id": ev["id"],
                "run_number": 1,
                "pass_rate": grading["summary"]["pass_rate"],
                "passed": grading["summary"]["passed"],
                "failed": grading["summary"]["failed"],
                "total": grading["summary"]["total"],
                "time_seconds": timing.get("total_duration_seconds", 0),
                "tokens": timing.get("total_tokens", 0),
                "tool_calls": 0,
                "errors": 0,
                "expectations": grading["expectations"],
                "notes": [],
            }
            config_runs[config].append(run_entry)
            per_eval_entry["configs"][config] = {
                "pass_rate": grading["summary"]["pass_rate"],
                "passed": grading["summary"]["passed"],
                "total": grading["summary"]["total"],
                "time_seconds": run_entry["time_seconds"],
                "tokens": run_entry["tokens"],
            }
        per_eval_results.append(per_eval_entry)

    # Aggregate
    run_summary = {}
    for config in ["with_skill", baseline]:
        runs = config_runs[config]
        run_summary[config] = {
            "pass_rate": stats([r["pass_rate"] for r in runs]),
            "time_seconds": stats([r["time_seconds"] for r in runs]),
            "tokens": stats([r["tokens"] for r in runs]),
            "runs": runs,
        }

    # Delta (new vs baseline)
    new_pr = run_summary["with_skill"]["pass_rate"]["mean"]
    base_pr = run_summary[baseline]["pass_rate"]["mean"]
    new_time = run_summary["with_skill"]["time_seconds"]["mean"]
    base_time = run_summary[baseline]["time_seconds"]["mean"]
    new_tok = run_summary["with_skill"]["tokens"]["mean"]
    base_tok = run_summary[baseline]["tokens"]["mean"]

    benchmark = {
        "skill_name": args.skill_name,
        "configs": ["with_skill", baseline],
        "baseline": baseline,
        "run_summary": run_summary,
        "delta": {
            "pass_rate_diff": round(new_pr - base_pr, 4),
            "time_seconds_diff": round(new_time - base_time, 4),
            "tokens_diff": round(new_tok - base_tok, 4),
        },
        "per_eval": per_eval_results,
    }

    out_path = ws / "benchmark.json"
    out_path.write_text(json.dumps(benchmark, indent=2))
    print(f"wrote {out_path}")

    # Pretty summary
    print("\n=== Per-eval pass rate ===")
    for e in per_eval_results:
        nw = e["configs"].get("with_skill", {}).get("pass_rate", 0.0)
        bl = e["configs"].get(baseline, {}).get("pass_rate", 0.0)
        nw_p = e["configs"].get("with_skill", {}).get("passed", 0)
        nw_total = e["configs"].get("with_skill", {}).get("total", 0)
        bl_p = e["configs"].get(baseline, {}).get("passed", 0)
        bl_total = e["configs"].get(baseline, {}).get("total", 0)
        diff = nw - bl
        sign = "+" if diff >= 0 else ""
        print(f"  eval-{e['eval_id']:>2} {e['eval_name']:<25} new={nw_p}/{nw_total} ({nw:.0%})  {baseline}={bl_p}/{bl_total} ({bl:.0%})  Δ={sign}{diff:+.0%}")

    print(f"\n=== Aggregate ===")
    print(f"  new plugin pass rate:  {new_pr:.1%}")
    print(f"  {baseline} pass rate: {base_pr:.1%}")
    print(f"  delta:                 {new_pr-base_pr:+.1%}")
    print(f"  new tokens (mean):     {new_tok:.0f}")
    print(f"  {baseline} tokens:    {base_tok:.0f}")
    print(f"  new time (mean):       {new_time:.1f}s")
    print(f"  {baseline} time:      {base_time:.1f}s")


if __name__ == "__main__":
    main()
