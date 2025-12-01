# Claude Code Session Resume Feature

## Overview

Allow TeleClaude users to resume Claude Code sessions that were previously worked on in the terminal. This enables seamless continuation of work from Telegram.

## User Flow

```
/resume
    ↓
[Project Selection] - Inline keyboard with project buttons
    ↓
[Session Selection] - 5 most recent sessions with first message preview
    ↓
[Mode Selection] - Fork (safe) or Continue (same thread)
    ↓
Session resumed, user can continue conversation
```

## Design Decisions

| Question | Decision |
|----------|----------|
| Use case | Resume terminal sessions from Telegram (same machine) |
| Interaction model | Inline keyboard flow (3 steps) |
| Fork vs Continue | Ask each time - give user choice per resume |
| Sessions shown | 5 most recent |
| Session preview | First user message (truncated) |

## Technical Details

### Session Storage

Claude Code stores sessions at:
```
~/.claude/projects/<project-name>/<session-id>.jsonl
```

Project names are path-encoded (e.g., `-root-work-teleclaude` for `/root/work/teleclaude`).

### JSONL Session Format

Each line is a JSON object:
```json
{"type":"user","message":{"role":"user","content":"user message here..."}}
{"type":"assistant","message":{"role":"assistant","content":"..."}}
{"type":"tool_use",...}
{"type":"tool_result",...}
```

### Claude Agent SDK Integration

The SDK supports two resume modes:

1. **`resume`** - Continue exact same session (same thread ID)
2. **`fork_session`** - Branch from session (new thread, inherits history)

Current implementation in `src/claude/client.py:75-76`:
```python
if session and session.claude_session_id:
    options.fork_session = session.claude_session_id
```

## Components

### 1. Session Scanner (`src/claude/sessions.py`)

```python
def scan_projects() -> list[Project]:
    """Scan ~/.claude/projects/ for available projects."""

def scan_sessions(project: str) -> list[SessionInfo]:
    """Get sessions for a project, sorted by mtime desc, limit 5."""
```

### 2. Session Parser (`src/claude/sessions.py`)

```python
def parse_session_preview(session_path: Path) -> str:
    """Extract first user message from JSONL for preview."""
```

### 3. Keyboard Builder (`src/bot/keyboards.py`)

```python
def build_project_keyboard(projects: list[Project]) -> InlineKeyboardMarkup:
    """Build project selection keyboard."""

def build_session_keyboard(sessions: list[SessionInfo]) -> InlineKeyboardMarkup:
    """Build session selection with previews."""

def build_mode_keyboard(session_id: str) -> InlineKeyboardMarkup:
    """Build Fork/Continue mode selection."""
```

### 4. Resume Handler (`src/bot/handlers.py`)

```python
async def resume_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /resume command - show project selection."""
```

### 5. Callback Handlers (`src/bot/callbacks.py`)

Handle callback patterns:
- `resume_project:<project_name>` - Show sessions for project
- `resume_session:<session_id>` - Show mode selection
- `resume_mode:<session_id>:<fork|continue>` - Execute resume

## UI Examples

### Project Selection
```
Resume Claude Code Session

Select a project:

[teleclaude]
[my-other-project]
[another-project]
```

### Session Selection
```
Select a session from teleclaude:

[fix permission buttons...]
[implement MCP support...]
[add session storage...]
[refactor handlers...]
[initial setup...]
```

### Mode Selection
```
How do you want to resume?

Session: "fix permission buttons..."

[Fork (safe)] [Continue (same)]
```

Fork = new branch from session history
Continue = same session thread

## Error Handling

- No projects found: "No Claude Code sessions found in ~/.claude/projects/"
- No sessions in project: "No sessions found for this project"
- Session file corrupted: Skip session, show others
- Resume fails: Show error, offer retry

## Future Enhancements

- Session search/filter
- Delete old sessions
- Session export to file
- Cross-machine session sync (would require Claude API changes)
