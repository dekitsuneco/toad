from textual import on
from textual.app import ComposeResult
from textual.content import Content
from textual.screen import Screen
from textual import containers
from textual import widgets
from textual.widgets.option_list import Option

from toad.widgets.changes import FileChange, render_change
from toad.widgets.diff_view import make_diff


class ChangesScreen(Screen):
    """Every diff the agent made in this session."""

    BINDINGS = [("escape", "dismiss", "Back to conversation")]

    DEFAULT_CSS = """
    ChangesScreen {
        #summary {
            padding: 0 1;
            background: $panel;
            width: 1fr;
        }
        #files {
            width: 40;
            height: 1fr;
            border-right: tall black 10%;
        }
        #diffs {
            width: 1fr;
            height: 1fr;
            DiffView {
                margin-bottom: 1;
            }
        }
    }
    """

    def __init__(self, changes: list[FileChange], path: str | None = None) -> None:
        self.changes = changes
        self.initial_path = path
        super().__init__()

    def compose(self) -> ComposeResult:
        added = sum(change.added for change in self.changes)
        removed = sum(change.removed for change in self.changes)
        yield widgets.Static(
            Content.assemble(
                (f"{len(self.changes)} file(s) changed  ", "bold"),
                (f"+{added}", "$text-success"),
                " ",
                (f"-{removed}", "$text-error"),
            ),
            id="summary",
        )
        with containers.Horizontal():
            yield widgets.OptionList(
                *[
                    Option(render_change(change), id=change.path)
                    for change in self.changes
                ],
                id="files",
            )
            with containers.VerticalScroll(id="diffs"):
                for index, change in enumerate(self.changes):
                    yield make_diff(
                        change.display_path,
                        change.display_path,
                        change.before,
                        change.after,
                        id=f"diff-{index}",
                    )
        yield widgets.Footer()

    def on_mount(self) -> None:
        files = self.query_one("#files", widgets.OptionList)
        files.focus()
        paths = [change.path for change in self.changes]
        if self.initial_path in paths:
            files.highlighted = paths.index(self.initial_path)

    @on(widgets.OptionList.OptionHighlighted, "#files")
    def on_file_highlighted(self, event: widgets.OptionList.OptionHighlighted) -> None:
        diff_view = self.query_one(f"#diff-{event.option_index}")
        self.query_one("#diffs").scroll_to_widget(diff_view, top=True, animate=False)

    @on(widgets.OptionList.OptionSelected, "#files")
    def on_file_selected(self, event: widgets.OptionList.OptionSelected) -> None:
        self.query_one("#diffs").focus()
