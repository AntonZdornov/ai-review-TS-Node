from __future__ import annotations


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
