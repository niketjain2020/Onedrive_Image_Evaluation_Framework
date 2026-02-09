#!/usr/bin/env python3
"""
Compare two benchmark runs and compute per-style score deltas.

Usage:
    python compare_runs.py --current Run_2026_02_04 --baseline Run_2026_02_03
    python compare_runs.py --history            # Show all runs chronologically
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from config import RUNS_DIR, get_grade, MAX_SCORE


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_run_results(run_id: str) -> dict:
    """Load synthesis.json (preferred) or gemini.json from a run directory.

    Returns a dict keyed by style name with score/percentage/grade.
    """
    run_dir = RUNS_DIR / run_id

    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    # Try synthesis.json first (has both judge rankings merged)
    synthesis_path = run_dir / "synthesis.json"
    gemini_path = run_dir / "gemini.json"
    acrue_path = run_dir / "acrue.json"

    styles = {}

    if synthesis_path.exists():
        with open(synthesis_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for r in data.get("rankings", []):
            styles[r["style"]] = {
                "final_score": r.get("final_score"),
                "gemini_rank": r.get("gemini_rank"),
                "opus_rank": r.get("opus_rank"),
            }

    if gemini_path.exists():
        with open(gemini_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for r in data.get("rankings", []):
            style = r["style"]
            if style not in styles:
                styles[style] = {}
            styles[style].update({
                "avg_score": r.get("avg_score", 0),
                "avg_percentage": r.get("avg_percentage", 0),
                "avg_grade": r.get("avg_grade", "N/A"),
            })

    if acrue_path.exists():
        with open(acrue_path, "r", encoding="utf-8") as f:
            acrue_data = json.load(f)

        # acrue.json is a list of per-image evaluations; aggregate by style
        # summary can be a dict (with percentage/weighted_total) or a string
        style_scores = {}
        for entry in acrue_data:
            style = entry.get("style", "")
            if not style:
                continue
            summary = entry.get("summary", {})
            if isinstance(summary, dict):
                pct = summary.get("percentage", 0)
                wt = summary.get("weighted_total", 0)
                grade = summary.get("grade", "N/A")
            else:
                # summary is a string; percentage/grade at top level
                pct = entry.get("percentage", 0)
                wt = entry.get("weighted_total", 0)
                grade = entry.get("grade", "N/A")
            style_scores.setdefault(style, []).append({
                "percentage": pct,
                "weighted_total": wt,
                "grade": grade,
            })

        for style, scores in style_scores.items():
            if style not in styles:
                styles[style] = {}
            avg_pct = sum(s["percentage"] for s in scores) / len(scores)
            avg_wt = sum(s["weighted_total"] for s in scores) / len(scores)
            styles[style].setdefault("avg_score", round(avg_wt, 2))
            styles[style].setdefault("avg_percentage", round(avg_pct, 1))
            styles[style].setdefault("avg_grade", get_grade(avg_pct))

    # Load run_spec for metadata
    spec_path = run_dir / "run_spec.json"
    spec = {}
    if spec_path.exists():
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

    return {"run_id": run_id, "styles": styles, "spec": spec}


# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------

def compare_runs(current_id: str, baseline_id: str) -> dict:
    """Compare two runs and produce per-style deltas."""
    current = load_run_results(current_id)
    baseline = load_run_results(baseline_id)

    all_styles = sorted(set(current["styles"].keys()) | set(baseline["styles"].keys()))

    style_deltas = []
    improved = 0
    regressed = 0
    unchanged = 0

    for style in all_styles:
        cur = current["styles"].get(style, {})
        base = baseline["styles"].get(style, {})

        cur_pct = cur.get("avg_percentage", 0)
        base_pct = base.get("avg_percentage", 0)
        cur_score = cur.get("avg_score", 0)
        base_score = base.get("avg_score", 0)

        delta_pct = round(cur_pct - base_pct, 1)
        delta_score = round(cur_score - base_score, 2)

        if abs(delta_pct) < 0.5:
            status = "unchanged"
            unchanged += 1
        elif delta_pct > 0:
            status = "improved"
            improved += 1
        else:
            status = "REGRESSION"
            regressed += 1

        style_deltas.append({
            "style": style,
            "current_pct": cur_pct,
            "baseline_pct": base_pct,
            "delta_pct": delta_pct,
            "current_score": cur_score,
            "baseline_score": base_score,
            "delta_score": delta_score,
            "current_grade": cur.get("avg_grade", "N/A"),
            "baseline_grade": base.get("avg_grade", "N/A"),
            "status": status,
        })

    if regressed > 0:
        verdict = "REGRESSION_DETECTED"
    elif improved > 0:
        verdict = "IMPROVED"
    else:
        verdict = "UNCHANGED"

    return {
        "current_run_id": current_id,
        "baseline_run_id": baseline_id,
        "timestamp": datetime.now().isoformat(),
        "styles": style_deltas,
        "summary": {
            "improved": improved,
            "regressed": regressed,
            "unchanged": unchanged,
            "overall_verdict": verdict,
        },
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_comparison_report(comparison: dict) -> str:
    """Produce a human-readable markdown comparison."""
    lines = [
        f"# Comparison: {comparison['current_run_id']} vs {comparison['baseline_run_id']}",
        "",
        f"Generated: {comparison['timestamp']}",
        "",
        "## Per-Style Deltas",
        "",
        "| Style | Baseline | Current | Delta | Status |",
        "|-------|----------|---------|-------|--------|",
    ]

    for s in comparison["styles"]:
        sign = "+" if s["delta_pct"] > 0 else ""
        flag = " REGRESSION" if s["status"] == "REGRESSION" else ""
        lines.append(
            f"| {s['style']} | {s['baseline_pct']:.1f}% ({s['baseline_grade']}) "
            f"| {s['current_pct']:.1f}% ({s['current_grade']}) "
            f"| {sign}{s['delta_pct']:.1f}% | {s['status']}{flag} |"
        )

    summary = comparison["summary"]
    lines.extend([
        "",
        "## Verdict",
        "",
        f"- Improved: {summary['improved']}",
        f"- Regressed: {summary['regressed']}",
        f"- Unchanged: {summary['unchanged']}",
        f"- **Overall: {summary['overall_verdict']}**",
        "",
    ])

    return "\n".join(lines)


def print_comparison_console(comparison: dict) -> None:
    """Print a concise console summary."""
    print()
    print(f"=== COMPARISON vs {comparison['baseline_run_id']} ===")
    for s in comparison["styles"]:
        sign = "+" if s["delta_pct"] > 0 else ""
        tag = "IMPROVED" if s["status"] == "improved" else (
            "REGRESSION" if s["status"] == "REGRESSION" else "UNCHANGED"
        )
        print(
            f"  {s['style']:<15} {s['baseline_pct']:5.1f}% -> {s['current_pct']:5.1f}%  "
            f"({sign}{s['delta_pct']:.1f}%)  {tag}"
        )

    summary = comparison["summary"]
    print()
    print(
        f"  VERDICT: {summary['improved']} improved, "
        f"{summary['regressed']} regressed, "
        f"{summary['unchanged']} unchanged"
    )
    print()


def save_comparison(comparison: dict, output_dir: Path = None) -> Path:
    """Write comparison.json to the current run directory (or supplied path)."""
    if output_dir is None:
        output_dir = RUNS_DIR / comparison["current_run_id"]
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / "comparison.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)
    print(f"Comparison saved to: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# History view
# ---------------------------------------------------------------------------

def show_history() -> None:
    """Show all runs chronologically."""
    if not RUNS_DIR.exists():
        print("No runs directory found.")
        return

    run_dirs = sorted(
        [d for d in RUNS_DIR.iterdir() if d.is_dir() and (d / "run_spec.json").exists()],
        key=lambda d: d.name,
    )

    if not run_dirs:
        print("No completed runs found.")
        return

    print(f"\n{'Run ID':<40} {'Styles':<30} {'Winner':<15}")
    print("-" * 85)

    for rd in run_dirs:
        spec_path = rd / "run_spec.json"
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        styles = ", ".join(spec.get("styles", []))

        # Try to get winner from synthesis
        winner = "N/A"
        synthesis_path = rd / "synthesis.json"
        if synthesis_path.exists():
            with open(synthesis_path, "r", encoding="utf-8") as f:
                syn = json.load(f)
            winner = syn.get("winner", "N/A")

        print(f"  {spec.get('run_id', rd.name):<38} {styles:<30} {winner:<15}")

    print()


# ---------------------------------------------------------------------------
# Find latest previous run
# ---------------------------------------------------------------------------

def find_latest_prior_run(current_run_id: str) -> str | None:
    """Find the most recent run before the current one (by directory name sort)."""
    if not RUNS_DIR.exists():
        return None

    run_dirs = sorted(
        [d.name for d in RUNS_DIR.iterdir() if d.is_dir() and d.name != current_run_id],
    )

    return run_dirs[-1] if run_dirs else None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compare two benchmark runs and compute per-style deltas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python compare_runs.py --current Run_2026_02_04 --baseline Run_2026_02_03
  python compare_runs.py --history
        """,
    )
    parser.add_argument("--current", "-c", help="Current run ID")
    parser.add_argument("--baseline", "-b", help="Baseline run ID to compare against")
    parser.add_argument("--history", action="store_true", help="Show all runs chronologically")
    parser.add_argument("--output", "-o", help="Directory to save comparison.json")

    args = parser.parse_args()

    if args.history:
        show_history()
        return

    if not args.current or not args.baseline:
        parser.error("--current and --baseline are required (or use --history)")

    comparison = compare_runs(args.current, args.baseline)
    print_comparison_console(comparison)

    output_dir = Path(args.output) if args.output else None
    save_comparison(comparison, output_dir)

    # Also write markdown report
    report = generate_comparison_report(comparison)
    md_path = (output_dir or RUNS_DIR / comparison["current_run_id"]) / "comparison.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Markdown report saved to: {md_path}")


if __name__ == "__main__":
    main()
