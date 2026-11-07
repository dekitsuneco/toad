from difflib import unified_diff
from pathlib import Path
from typing import NamedTuple

from textual import on
from textual.content import Content
from textual.message import Message
from textual.reactive import var
from textual.widgets import OptionList
from textual.widgets.option_list import Option


class FileChange(NamedTuple):
    """The net change to one file."""

    path: str
    """Absolute path."""
    display_path: str
    """Path relative to the project, where possible."""
    before: str | None
    after: str
    added: int
    removed: int


def count_changed_lines(before: str | None, after: str) -> tuple[int, int]:
    """Count added and removed lines."""
    added = removed = 0
    diff = unified_diff(
        (before or "").splitlines(), after.splitlines(), lineterm="", n=0
    )
    for line in list(diff)[2:]:
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added, removed


def get_file_changes(
    edits: list[tuple[str, str | None, str]], project_path: Path
) -> list[FileChange]:
    """Summarize the edits reported by an agent."""
    changes: list[FileChange] = []
    for path, before, after in edits:
        try:
            display_path = str(Path(path).relative_to(project_path))
        except ValueError:
            display_path = path
        added, removed = count_changed_lines(before, after)
        changes.append(FileChange(path, display_path, before, after, added, removed))
    return changes


def render_change_stats(change: FileChange) -> Content:
    return Content.assemble(
        (f"+{change.added}", "$text-success"),
        " ",
        (f"-{change.removed}", "$text-error"),
    )


def render_change(change: FileChange) -> Content:
    """File name and stats, with the directory dimmed on the next line."""
    path = Path(change.display_path)
    directory = str(path.parent)
    return Content.assemble(
        (path.name, "bold"),
        " ",
        render_change_stats(change),
        *(("\n", (directory, "dim")) if directory != "." else ()),
    )


class ChangesList(OptionList):
    """Files the agent changed in this session."""

    BINDING_GROUP_TITLE = "Changes"
    HELP = """\
## Changes

Files the agent changed in this session.

- **enter** show the diff of every changed file
"""

    changes: var[list[FileChange]] = var(list, init=False)

    class Open(Message):
        """Show the changes, starting from the given file."""

        def __init__(self, path: str | None) -> None:
            self.path = path
            super().__init__()

    def on_mount(self) -> None:
        self.watch_changes(self.changes)

    def watch_changes(self, changes: list[FileChange]) -> None:
        self.clear_options()
        if not changes:
            self.add_option(Option("No changes yet", disabled=True))
            return
        self.add_options(
            Option(render_change(change), id=change.path)
            for change in changes
        )

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        self.post_message(self.Open(event.option.id))
