from textual import on
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual import widgets
from textual import containers
from textual import getters


class RenameModal(ModalScreen[str | None]):
    """Ask the user for a new session name."""

    BINDINGS = [("escape", "dismiss(None)", "Dismiss")]

    DEFAULT_CSS = """
    RenameModal {
        align: center middle;
        #container {
            width: 60;
            height: auto;
            padding: 1 2;
            border: round $primary;
            background: $panel;
        }
        Label {
            margin-bottom: 1;
        }
    }
    """

    input = getters.query_one(widgets.Input)

    def __init__(self, title: str) -> None:
        self.session_title = title
        super().__init__()

    def compose(self) -> ComposeResult:
        with containers.VerticalGroup(id="container"):
            yield widgets.Label("[b]Rename session")
            yield widgets.Input(self.session_title)

    def on_mount(self) -> None:
        self.input.focus()
        self.input.select_all()

    @on(widgets.Input.Submitted)
    def on_input_submitted(self, event: widgets.Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)
