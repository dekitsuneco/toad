import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

UNCOMMITTED_SHA = "0" * 40


@dataclass(frozen=True)
class BlameCommit:
    sha: str
    author: str
    time: datetime
    summary: str

    @property
    def is_uncommitted(self) -> bool:
        return self.sha == UNCOMMITTED_SHA


def parse_blame_porcelain(output: str) -> list[BlameCommit | None]:
    """Parse `git blame --porcelain`.

    Returns:
        The commit for each line of the file (index 0 is line 1).
    """
    commits: dict[str, dict[str, str]] = {}
    lines: dict[int, str] = {}
    sha = ""
    final_line = 0
    for line in output.splitlines():
        if line.startswith("\t"):
            lines[final_line] = sha
            continue
        key, _, value = line.partition(" ")
        if len(key) == 40 and all(c in "0123456789abcdef" for c in key):
            sha = key
            final_line = int(value.split()[1])
            commits.setdefault(sha, {})
        elif sha:
            commits[sha].setdefault(key, value)

    def make_commit(sha: str) -> BlameCommit:
        info = commits[sha]
        return BlameCommit(
            sha,
            info.get("author", ""),
            datetime.fromtimestamp(int(info.get("author-time", "0"))),
            info.get("summary", ""),
        )

    blame_commits = {sha: make_commit(sha) for sha in commits}
    line_count = max(lines, default=0)
    return [
        blame_commits.get(lines.get(line_no, ""))
        for line_no in range(1, line_count + 1)
    ]


async def git_blame(path: Path) -> list[BlameCommit | None] | None:
    """Blame a file, or return `None` if it isn't tracked by git."""
    try:
        process = await asyncio.create_subprocess_exec(
            "git",
            "blame",
            "--porcelain",
            "--",
            path.name,
            cwd=path.parent,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except OSError:
        return None
    stdout, _ = await process.communicate()
    if process.returncode != 0:
        return None
    return parse_blame_porcelain(stdout.decode("utf-8", "replace"))


def format_age(time: datetime, now: datetime | None = None) -> str:
    seconds = int(((now or datetime.now()) - time).total_seconds())
    for unit, size in (
        ("year", 365 * 86400),
        ("month", 30 * 86400),
        ("day", 86400),
        ("hour", 3600),
        ("minute", 60),
    ):
        if seconds >= size:
            count = seconds // size
            return f"{count} {unit}{'s' if count > 1 else ''} ago"
    return "just now"
