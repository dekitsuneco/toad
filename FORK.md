# How this fork differs from upstream Toad

This is an unofficial fork of [batrachianai/toad](https://github.com/batrachianai/toad) 0.6.20 by Will McGugan.
It is not affiliated with or endorsed by the upstream project.
Modifications are dated 2026-11-07 through 2026-11-08.

Like the original, this fork is licensed under the [GNU AGPL-3.0](./LICENSE).
The commercial license in [COMMERCIAL_LICENSE.md](./COMMERCIAL_LICENSE.md) is offered by the upstream author only and does not cover these changes.

Everything below is added on top of upstream 0.6.20. Behavior that is not listed here is unchanged.

## Model and mode pickers

Agents advertise the current model and mode through [Session Config Options](https://agentclientprotocol.com/protocol/session-config-options) (`configOptions`, categories `model` and `mode`) or through the older `models` and `modes` fields.
Toad reads both. Grouped model lists (a group containing options) are flattened.

Switching calls `session/set_config_option` when the agent uses config options, and `session/set_model` or `session/set_mode` otherwise.

Both values sit in pills beside the prompt, mode first, then model. They used to be docked on top of each other, so the mode was hidden.

| Action | Key |
| --- | --- |
| Switch model | <kbd>ctrl</kbd>+<kbd>l</kbd>, or click the model pill |
| Switch mode | <kbd>ctrl</kbd>+<kbd>o</kbd>, or click the mode pill |

OpenCode (`opencode acp`) only sends config options, so upstream Toad showed no mode at all. This fork shows `build` and `plan`.
The Cursor CLI advertises Agent, Ask, and Plan. Debug and Multitask exist in the Cursor IDE, but the CLI does not offer them, so Toad cannot show them.

## Cursor plans

Cursor asks the client to approve a plan with `cursor/create_plan`. Upstream Toad answered that the method was unknown, and Cursor continued on its own.
This fork shows the plan and asks you to accept it (<kbd>a</kbd>) or reject it (<kbd>r</kbd>).

`/toad:plan` prints the latest plan. When Cursor reports `Plan saved to file://…`, the command reads that file (`~/.cursor/plans/*.plan.md`).

After you approve a plan and say to implement it, Cursor switches to Agent with a `switch_mode` tool call and does not send `current_mode_update`.
The mode pill follows that tool call, so it no longer stays on Plan while files are being edited.

## Changes

The sidebar has a **Changes** section under Plan. It lists every file the agent edited in the session, with added and removed line counts, and updates as edits arrive.
Several edits to one file are collapsed into one diff, from the text at the start of the session to the text now. Failed tool calls are skipped.

| Action | How |
| --- | --- |
| Open every diff | <kbd>ctrl</kbd>+<kbd>g</kbd>, or `/toad:diff` |
| Open one file's diff | Select it in the Changes list |

The screen has the file list on the left and the diffs on the right. <kbd>esc</kbd> returns to the conversation.

Tool calls that edit a file are expanded immediately, so the diff is visible in the chat. Turn this off with **Expand file edits?** in settings (<kbd>f2</kbd>), key `tools.expand_diffs`. It stays off when tool-call expansion is set to Never.

## Session tabs

Tabs were stuck on "New Session" because Toad rejected Cursor's `session_info_update` as an unknown message. That message is accepted now, so a Cursor session is titled by the agent (for example "Fix Require Await").
Agents that never send a title, such as OpenCode, get the first line of the first prompt, cut at 40 characters.

Double-click a tab, or run `/toad:rename <name>`, to set the name yourself. A name you set is kept. The agent cannot replace it.
Resuming a saved session restores its name.

The glyph in front of the title is the agent: `◆` Cursor, `▣` OpenCode, `✻` Claude, `◎` OpenAI, `✦` Gemini, `◉` Copilot, `✕` Grok. Any other agent gets `●`.

## File viewer

Clicking a file in the project tree used to paste its path into the prompt. It now opens the file.

The viewer highlights syntax for the languages Textual ships, plus TypeScript and TSX (the `tree-sitter-typescript` package).
The line under the cursor shows its git blame: author, age, short commit hash, and subject. Uncommitted lines say so.

| Action | Key |
| --- | --- |
| Close | <kbd>esc</kbd>. A second press discards unsaved edits |
| Save | <kbd>ctrl</kbd>+<kbd>s</kbd> |
| Reload from disk | <kbd>ctrl</kbd>+<kbd>r</kbd> |
| Add the file to the prompt | <kbd>ctrl</kbd>+<kbd>t</kbd> |
| Open in `$EDITOR`, or in Cursor or VS Code | <kbd>ctrl</kbd>+<kbd>o</kbd> |
| Add the file to the prompt without opening it | <kbd>a</kbd> while the tree is focused |

Saving refuses to overwrite a file that changed on disk after it was opened (the agent may have written it). Press <kbd>ctrl</kbd>+<kbd>s</kbd> again to overwrite, or <kbd>ctrl</kbd>+<kbd>r</kbd> to reload.
A file has to be saved before it can be added to the prompt, so the agent sees your edits.

There is no language server. Hover types, go to definition, and completions are not available. <kbd>ctrl</kbd>+<kbd>o</kbd> opens the file in Cursor, which has them.

## Running this fork

```
uv tool install --editable ~/path/to/toad
```

or:

```
pip install git+https://github.com/dekitsuneco/toad.git
```

The command is `toad`. Pick the agent from the launcher.
