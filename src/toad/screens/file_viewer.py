import asyncio
import os
import shlex
import shutil
import subprocess
from pathlib import Path

from textual import on, work
from textual.css.query import NoMatches
from textual.app import ComposeResult
from textual.binding import Binding
from textual.content import Content
from textual.screen import Screen
from textual import getters
from textual import widgets

from toad.git_blame import BlameCommit, format_age, git_blame

MAX_FILE_SIZE = 5 * 1024 * 1024

LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "tsx",
    ".json": "json",
    ".md": "markdown",
    ".css": "css",
    ".scss": "css",
    ".html": "html",
    ".htm": "html",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".sql": "sql",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
}


def register_extra_languages(text_area: widgets.TextArea) -> None:
    """Add TypeScript and TSX, which Textual doesn't bundle."""
    if "typescript" in text_area.available_languages:
        return
    try:
        import tree_sitter_typescript
        from tree_sitter import Language
    except ImportError:
        return
    import textual

    javascript_highlights = (
        Path(textual.__file__).parent / "tree-sitter/highlights/javascript.scm"
    ).read_text()
    highlights = f"{javascript_highlights}\n{tree_sitter_typescript.HIGHLIGHTS_QUERY}"
    text_area.register_language(
        "typescript", Language(tree_sitter_typescript.language_typescript()), highlights
    )
    text_area.register_language(
        "tsx", Language(tree_sitter_typescript.language_tsx()), highlights
    )


def read_text_file(path: Path) -> tuple[str, float]:
    """Read a text file and its modification time.

    Raises:
        ValueError: If the file is too large or binary.
    """
    stat = path.stat()
    if stat.st_size > MAX_FILE_SIZE:
        raise ValueError("File is too large to view")
    data = path.read_bytes()
    if b"\0" in data[:8192]:
        raise ValueError("Binary files can't be viewed")
    return data.decode("utf-8", "replace"), stat.st_mtime


class FileViewerScreen(Screen[Path | None]):
    """View and edit a project file.

    Dismisses with the path when the user asks to add the file to the prompt.
    """

    BINDING_GROUP_TITLE = "File"
    BINDINGS = [
        # Priority: TextArea consumes escape itself (it moves focus) and the
        # key never reaches a normal screen binding.
        Binding("escape", "close", "Close", priority=True),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+t", "add_to_prompt", "Add to prompt"),
        Binding("ctrl+o", "open_external", "Open in editor"),
        Binding("ctrl+r", "reload", "Reload"),
    ]

    DEFAULT_CSS = """
    FileViewerScreen {
        #file-title {
            padding: 0 1;
            background: $panel;
            width: 1fr;
        }
        TextArea {
            height: 1fr;
            border: none;
            padding: 0;
        }
        #blame {
            padding: 0 1;
            background: $panel;
            color: $text-muted;
            width: 1fr;
        }
    }
    """

    text_area = getters.query_one(widgets.TextArea)

    def __init__(self, path: Path, project_path: Path) -> None:
        self.path = path
        try:
            self.display_path = str(path.relative_to(project_path))
        except ValueError:
            self.display_path = str(path)
        self._saved_text = ""
        self._mtime = 0.0
        self._blame: list[BlameCommit | None] | None = None
        self._confirm_close = False
        self._confirm_overwrite = False
        super().__init__()

    @property
    def is_modified(self) -> bool:
        return self.text_area.text != self._saved_text

    def compose(self) -> ComposeResult:
        yield widgets.Static(id="file-title")
        yield widgets.TextArea.code_editor(soft_wrap=False)
        yield widgets.Static(id="blame")
        yield widgets.Footer()

    async def on_mount(self) -> None:
        register_extra_languages(self.text_area)
        language = LANGUAGES.get(self.path.suffix.lower())
        if language in self.text_area.available_languages:
            self.text_area.language = language
        if await self.load():
            self.text_area.focus()

    async def load(self) -> bool:
        try:
            text, self._mtime = await asyncio.to_thread(read_text_file, self.path)
        except (OSError, ValueError) as error:
            self.notify(str(error), title=self.display_path, severity="error")
            self.dismiss(None)
            return False
        self._saved_text = text
        self.text_area.load_text(text)
        self.update_title()
        self.load_blame()
        return True

    @work(exclusive=True, group="blame")
    async def load_blame(self) -> None:
        blame = await git_blame(self.path)
        if not self.is_mounted:
            return
        self._blame = blame
        self.update_blame()

    def update_title(self) -> None:
        if not self.is_mounted:
            return
        try:
            title = self.query_one("#file-title", widgets.Static)
        except NoMatches:
            return
        title.update(
            Content.assemble(
                (self.display_path, "bold"),
                ("  ● modified", "$text-warning") if self.is_modified else "",
            )
        )

    def update_blame(self) -> None:
        if not self.is_mounted:
            return
        try:
            blame = self.query_one("#blame", widgets.Static)
        except NoMatches:
            return
        row, column = self.text_area.cursor_location
        position = f"Ln {row + 1}, Col {column + 1}"
        if self.is_modified:
            blame.update(f"{position}  ·  Unsaved changes (ctrl+s to save)")
            return
        if self._blame is None:
            blame.update(f"{position}  ·  Not tracked by git")
            return
        commit = self._blame[row] if row < len(self._blame) else None
        if commit is None:
            blame.update(position)
        elif commit.is_uncommitted:
            blame.update(f"{position}  ·  Not committed yet")
        else:
            blame.update(
                Content.assemble(
                    position,
                    "  ·  ",
                    (commit.author, "bold"),
                    f", {format_age(commit.time)}  ·  ",
                    (commit.sha[:8], "$text-accent"),
                    f"  {commit.summary}",
                )
            )

    @on(widgets.TextArea.SelectionChanged)
    def on_selection_changed(self) -> None:
        self.update_blame()

    @on(widgets.TextArea.Changed)
    def on_text_changed(self) -> None:
        self._confirm_close = False
        self.update_title()
        self.update_blame()

    async def action_save(self) -> None:
        mtime = await asyncio.to_thread(lambda: self.path.stat().st_mtime)
        if mtime != self._mtime and not self._confirm_overwrite:
            self._confirm_overwrite = True
            self.notify(
                "The file changed on disk since it was opened (maybe by the agent).\n"
                "Press ctrl+s again to overwrite it, or ctrl+r to reload.",
                title="Save",
                severity="warning",
            )
            return
        text = self.text_area.text
        await asyncio.to_thread(self.path.write_text, text, "utf-8")
        self._saved_text = text
        self._mtime = await asyncio.to_thread(lambda: self.path.stat().st_mtime)
        self._confirm_overwrite = False
        self.update_title()
        self.load_blame()
        self.notify(f"Saved {self.display_path}", title="Save")

    async def action_reload(self) -> None:
        location = self.text_area.cursor_location
        self._confirm_overwrite = False
        if await self.load():
            self.text_area.move_cursor(location)

    def action_close(self) -> None:
        if self.is_modified and not self._confirm_close:
            self._confirm_close = True
            self.notify(
                "Unsaved changes. Press esc again to discard them, or ctrl+s to save.",
                title=self.display_path,
                severity="warning",
            )
            return
        self.dismiss(None)

    def action_add_to_prompt(self) -> None:
        if self.is_modified:
            self.notify(
                "Save the file first, so the agent sees your changes",
                title="Add to prompt",
                severity="warning",
            )
            return
        self.dismiss(self.path)

    async def action_open_external(self) -> None:
        line = self.text_area.cursor_location[0] + 1
        if editor := os.environ.get("VISUAL") or os.environ.get("EDITOR"):
            with self.app.suspend():
                subprocess.call([*shlex.split(editor), f"+{line}", str(self.path)])
            await self.action_reload()
            return
        for command in ("cursor", "code"):
            if shutil.which(command):
                subprocess.Popen(
                    [command, "-g", f"{self.path}:{line}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.notify(
                    f"Opened in {command}. Press ctrl+r here after editing.",
                    title=self.display_path,
                )
                return
        self.notify(
            "Set $EDITOR (or install the cursor / code command) to open files externally",
            title="Open in editor",
            severity="warning",
        )
