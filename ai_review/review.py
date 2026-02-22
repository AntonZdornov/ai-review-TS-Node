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
Role: senior engineer (TypeScript/React + Node.js).
You are reviewing code changes from git diffs.

Priorities:
1) correctness/bugs: async/await, error handling, edge cases, race conditions, null/undefined
2) React: useEffect/useMemo/useCallback deps, stale closures, cleanup, key in lists, controlled/uncontrolled inputs, SSR hazards (window/document)
3) TypeScript: avoid any, unsafe assertions, unknown narrowing, broken types in DTOs
4) Security: input validation, injection risks, secrets in logs, auth boundaries
5) Maintainability/Testability: readability, missing tests, brittle logic
6) Performance: unnecessary re-renders, expensive loops

Rules:
- Do NOT nitpick formatting/whitespace/Prettier unless it affects quality.
- Provide concrete fixes.
- If uncertain, set severity="low" and phrase it as a note.
- Output STRICT JSON ONLY. No extra text.

Schema:
{
  "summary": string,
  "issues": [
    {
      "file": string,
      "line": number,
      "severity": "low"|"medium"|"high",
      "type": "bug"|"security"|"quality"|"perf"|"tests",
      "message": string,
      "suggestion": string
    }
  ],
  "positives": [string]
}
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
    depth = (
        "Be brief. Only include medium/high issues and keep messages short."
        if mode == "quick"
        else "Be thorough. Include test suggestions (edge cases)."
    )
    return f"""\
Review this git diff chunk.

{depth}
Return JSON only and match the schema exactly. No extra text.

```diff
{diff_chunk}
```
"""


def _extract_text(resp) -> str:
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text
    # Chat completions shape (local OpenAI-compatible servers)
    if hasattr(resp, "choices") and resp.choices:
        msg = getattr(resp.choices[0], "message", None)
        if msg and getattr(msg, "content", None):
            return msg.content
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
        if provider == "local":
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
        else:
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
