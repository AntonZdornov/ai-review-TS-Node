from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
from .llm import make_client


Severity = Literal["low", "medium", "high"]
IssueType = Literal["bug", "security", "quality", "perf", "tests"]


class Issue(BaseModel):
    file: str = ""
    line: int = 0
    severity: Severity
    type: IssueType
    message: str
    suggestion: str = ""


class Report(BaseModel):
    summary: str
    issues: list[Issue] = Field(default_factory=list)
    positives: list[str] = Field(default_factory=list)


SYSTEM_PROMPT = """\
You are a senior engineer reviewing TypeScript/React and Node.js code changes from git diffs.

Focus on:
- correctness/bugs (async/await, error handling, edge cases)
- React hooks correctness (deps, stale closures, cleanup)
- TypeScript safety (any, unsafe casts, narrowing)
- security (input validation, injections, secrets, auth)
- maintainability/testability (clear API contracts, missing tests)
- performance pitfalls (unnecessary rerenders, heavy loops)

Rules:
- Do NOT nitpick formatting.
- Provide concrete fixes.
- If uncertain, mark severity=low and phrase as a note.
Return STRICT JSON matching schema: {summary, issues[], positives[]}.
"""


def chunk_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    out = []
    i = 0
    while i < len(text):
        out.append(text[i : i + max_chars])
        i += max_chars
    return out


def build_user_prompt(diff_chunk: str, mode: str) -> str:
    depth = "Be brief. Only medium/high issues." if mode == "quick" else "Be thorough. Include test suggestions."
    return f"""\
Review this git diff chunk.

{depth}

```diff
{diff_chunk}
```
"""


def _extract_text(resp) -> str:
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text
    # Best-effort for SDK response shapes
    if hasattr(resp, "output") and resp.output:
        parts = []
        for item in resp.output:
            if getattr(item, "type", "") == "message":
                for c in getattr(item, "content", []):
                    if getattr(c, "type", "") in {"output_text", "text"}:
                        parts.append(getattr(c, "text", ""))
        if parts:
            return "\n".join(p for p in parts if p)
    return str(resp)


def _parse_report(text: str) -> Report:
    import json

    try:
        data = json.loads(text)
        return Report.model_validate(data)
    except Exception:
        # Try to salvage JSON if the model wrapped it in text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return Report.model_validate(data)
            except Exception:
                pass

    return Report(
        summary="Failed to parse model output as JSON.",
        issues=[],
        positives=[],
    )


def run_review(
    diff: str,
    provider: str,
    model: str,
    base_url: str | None,
    mode: str,
    max_chars: int,
) -> Report:
    client = make_client(provider, base_url=base_url)
    chunks = chunk_text(diff, max_chars)

    summaries: list[str] = []
    issues: list[Issue] = []
    positives: list[str] = []

    for idx, chunk in enumerate(chunks, start=1):
        prompt = build_user_prompt(chunk, mode=mode)
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        text = _extract_text(resp)
        report = _parse_report(text)

        if report.summary:
            if len(chunks) == 1:
                summaries.append(report.summary)
            else:
                summaries.append(f"Chunk {idx}: {report.summary}")
        if report.issues:
            issues.extend(report.issues)
        if report.positives:
            positives.extend(report.positives)

    summary = " ".join(summaries).strip() or "No summary."
    return Report(summary=summary, issues=issues, positives=positives)
