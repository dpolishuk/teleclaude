# Unified Sessions Design

## Overview

Unify Claude Code sessions across TeleClaude (Telegram) and terminal interfaces. Sessions created in either interface become visible and resumable in both.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Session storage | SDK-managed `.jsonl` files | SDK handles format, less maintenance |
| SQLite role | Metadata layer only | Track telegram_user_id, costs, ownership |
| Primary key | `claude_session_id` (UUID) | Single ID across all interfaces |
| Session creation | Lazy (on SDK init response) | No orphaned records if SDK fails |
| UX | Unified `/sessions` command | Single list, origin icons (📱/💻) |

## Architecture

```
Telegram User → TeleClaude → SDK query(resume=session_id) → Claude API
                    ↓                      ↓
              SQLite (metadata)    ~/.claude/projects/*.jsonl (content)
```

**Session Lifecycle:**
1. User sends first message in new session
2. SDK query starts, returns `session_id` in init message
3. TeleClaude creates SQLite record with that `session_id`
4. Subsequent messages use `resume=session_id`
5. Session appears in both `claude --resume` and Telegram `/sessions`

## Database Schema

### Current Schema
```python
class Session(Base):
    id: str  # TeleClaude-generated (32-char)
    claude_session_id: Optional[str]  # SDK session ID
    telegram_user_id: int
    project_path: str
    project_name: Optional[str]
    current_directory: Optional[str]
    status: SessionStatus
    created_at: datetime
    last_active: Optional[datetime]
    total_cost_usd: float
```

### New Schema
```python
class Session(Base):
    id: str  # = claude_session_id (UUID from SDK)
    telegram_user_id: int
    project_path: str
    created_at: datetime
    last_active: datetime
    total_cost_usd: float
```

**Removed fields:**
- `claude_session_id` - redundant, now `id` IS the claude session ID
- `project_name` - derivable from `project_path`
- `status` - derivable from `.jsonl` existence and `last_active`
- `current_directory` - stored in `.jsonl` metadata

### Migration
1. For rows with `claude_session_id`: use that as new `id`
2. Delete rows without `claude_session_id` (orphaned)
3. Drop removed columns

## Unified `/sessions` Command

### User Flow
1. User types `/sessions`
2. TeleClaude scans `~/.claude/projects/<current_project>/*.jsonl` files
3. Merges with SQLite data (for ownership, cost tracking)
4. Shows unified list sorted by last modified time

### Display Format
```
📋 Sessions for teleclaude

💻 2h ago - "fix the voice message bug..."
📱 5h ago - "add dark mode to settings..."
💻 1d ago - "refactor the database layer..."
📱 2d ago - "implement MCP server management"
[Show more...]

💻 = Terminal  📱 = Telegram
```

### Origin Detection
- Scan `.jsonl` files in project directory
- If `session_id` exists in SQLite → show 📱 (Telegram origin)
- If `session_id` not in SQLite → show 💻 (Terminal origin)
- Parse first user message from `.jsonl` for preview text
- Use file mtime for "last active" timestamp

### Session Selection
- Tap session → Resume conversation with `resume=session_id`
- If terminal session selected → create SQLite record (claim ownership)

## Code Changes

### Files to Modify

1. **`src/storage/models.py`** - Simplify Session model
2. **`src/storage/repository.py`** - Update to new schema, add "get or create by session_id"
3. **`src/claude/sessions.py`** - Minor updates to return format
4. **`src/bot/handlers.py`** - Merge `/sessions` and `/resume` logic
5. **`src/bot/callbacks.py`** - Handle session selection, create SQLite record for terminal sessions
6. **`src/bot/keyboards.py`** - Update session list keyboard with origin icons
7. **`src/claude/streaming.py`** - Capture `session_id` from init message, trigger SQLite insert

### Files to Remove/Deprecate
- `/resume` command becomes alias or deprecated

## Error Handling

| Edge Case | Handling |
|-----------|----------|
| `.jsonl` deleted externally | Show "Session no longer exists" on resume, skip in list |
| SDK returns different session_id | Update SQLite record or create new one |
| Multiple Telegram users | Each has own SQLite records, terminal sessions visible to all |
| First message fails mid-stream | No SQLite record created (lazy), user can retry |
| Large `.jsonl` files | Only parse first lines for preview, use mtime for "last active" |

## Testing

### Unit Tests
- Session model with new schema
- `.jsonl` parsing for preview extraction
- Session merging logic (SQLite + filesystem)
- Origin detection (📱 vs 💻)

### Integration Tests
- Create session via SDK → verify SQLite record created
- Resume session → verify same `session_id` used
- `/sessions` command → verify unified list displayed
- Select terminal session → verify SQLite record created

### Manual Testing Checklist
1. Start new session in Telegram → chat → check `~/.claude/projects/` for `.jsonl` file
2. Run `claude --resume` in terminal → verify Telegram session appears
3. Start session in terminal → open Telegram `/sessions` → verify it shows with 💻 icon
4. Select terminal session in Telegram → continue conversation → verify works
5. Check terminal `claude --resume` again → should show same session
