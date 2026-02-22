from __future__ import annotations
import subprocess


def _run_git(args: list[str]) -> str:
    p = subprocess.run(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{p.stderr.strip()}")
    return p.stdout


def get_diff(*, staged: bool, range_spec: str | None) -> str:
    base = ["diff", "--unified=3", "--no-color", "--no-ext-diff"]
    if staged:
        return _run_git([*base, "--staged"])
    if range_spec:
        return _run_git([*base, range_spec])
    # если ничего не указано — просто рабочие изменения
    return _run_git(base)