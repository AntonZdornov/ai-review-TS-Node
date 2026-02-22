
from __future__ import annotations
import argparse
import json
import os
from .git_utils import get_diff
from .review import run_review


def format_report_text(r) -> str:
    lines = []
    lines.append("=== AI Code Review ===")
    lines.append(f"Summary:\n{r.summary or '-'}\n")

    lines.append("Issues:")
    if not r.issues:
        lines.append("- none")
    else:
        for i, it in enumerate(r.issues, start=1):
            loc = f"{it.file}:{it.line}" if it.file else "(unknown)"
            lines.append(f"{i}. [{it.severity}/{it.type}] {loc} — {it.message}")
            if it.suggestion:
                lines.append(f"   Fix: {it.suggestion}")

    lines.append("\nPositives:")
    if not r.positives:
        lines.append("- none")
    else:
        for i, p in enumerate(r.positives, start=1):
            lines.append(f"{i}. {p}")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(prog="ai-review")
    ap.add_argument("--provider", choices=["openai", "local"], default="openai")
    ap.add_argument("--model", default="")
    ap.add_argument("--base-url", dest="base_url", default="")
    ap.add_argument("--range", dest="range_spec", default="")
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--mode", choices=["quick", "deep"], default="quick")
    ap.add_argument("--max-chars", type=int, default=12000)
    ap.add_argument("--out", default="", help="Write JSON report to file")
    args = ap.parse_args()

    diff = get_diff(staged=args.staged, range_spec=args.range_spec or None)
    if not diff.strip():
        print("No diff to review.")
        return

    # дефолтные модели под твой стек
    if args.provider == "openai":
        model = args.model or os.getenv("OPENAI_MODEL", "gpt-4.1")
    else:
        model = args.model or os.getenv("LOCAL_LLM_MODEL", "qwen2.5-coder")

    report = run_review(
        diff=diff,
        provider=args.provider,
        model=model,
        base_url=(args.base_url or None),
        mode=args.mode,
        max_chars=args.max_chars,
    )

    print(format_report_text(report))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))
        print(f"\nSaved JSON: {args.out}")