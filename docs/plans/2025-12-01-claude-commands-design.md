# Claude Commands Integration Design

## Overview

Integrate Claude Code slash commands into TeleClaude, allowing users to access `.claude/commands/*.md` files through Telegram's native `/` command menu.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Menu style | Native Telegram `/` menu | Most natural UX |
| Execution | Hybrid (immediate or prompt for args) | Best UX for both simple and parameterized commands |
| Discovery timing | Per-project dynamic | Commands differ per project |
| User scope | Single user | Simplifies implementation |
| Command locations | Both merged (project overrides personal) | Mirrors Claude Code behavior |

## Command Discovery

### Locations scanned (in order)
1. `~/.claude/commands/*.md` - personal commands
2. `{project_path}/.claude/commands/*.md` - project commands (override personal)

### Parsing `.md` files
- Filename becomes command name (e.g., `fix-bug.md` → `/fix-bug`)
- Parse YAML frontmatter for `description` and `allowed-tools`
- Body content is the prompt template
- Detect if `$ARGUMENTS` or `$1`, `$2` placeholders exist

### Data structure
```python
@dataclass
class ClaudeCommand:
    name: str           # "fix-bug"
    description: str    # from frontmatter or first line
    prompt: str         # body content
    needs_args: bool    # True if $ARGUMENTS in prompt
    source: str         # "personal" or "project"
```

### When discovery runs
- On `/new <project>` - scan both locations, update Telegram menu
- On project switch - rescan and update menu
- On `/refresh` - manual rescan

## Telegram Menu Registration

### Built-in commands (always present)
```
/new - Start new session
/continue - Resume last session
/help - Show help
/cancel - Stop current operation
/cost - Show usage costs
/refresh - Rescan Claude commands
```

### Dynamic Claude commands
- Registered via `bot.set_my_commands()` after built-in commands
- Max 100 commands total (Telegram limit) - warn if exceeded
- Description from frontmatter, truncated to 256 chars (Telegram limit)

### Update flow
```
User: /new webapp
Bot: 1. Create session with project_path
     2. Scan ~/.claude/commands/ + {project}/.claude/commands/
     3. Merge commands (project overrides personal)
     4. Call set_my_commands([built_in + claude_commands])
     5. Reply "Session started. X commands available."
```

### Command naming
- Claude commands keep their original names (`/fix-bug`, `/review`)
- If a Claude command conflicts with built-in (e.g., `/help`), skip it with warning

## Command Execution

### Case A - No arguments needed
```
User: /review
Bot: 1. Look up command in loaded commands
     2. Get prompt content: "Review this code for bugs and improvements"
     3. Send prompt to Claude (same as regular message)
     4. Stream response back
```

### Case B - Arguments required
```
User: /fix-bug
Bot: "🔧 /fix-bug requires input. What should I fix?"
User: "the login validation is broken"
Bot: 1. Replace $ARGUMENTS with user input
     2. Final prompt: "Fix this bug: the login validation is broken"
     3. Send to Claude, stream response
```

### State tracking
```python
# In user_data
context.user_data["pending_command"] = {
    "name": "fix-bug",
    "prompt": "Fix this bug: $ARGUMENTS",
}
```

### Message handler update
- Check if `pending_command` exists
- If yes: substitute arguments, execute command, clear pending
- If no: treat as regular Claude message

## File Structure

### New files
```
src/
  commands/
    __init__.py
    discovery.py    # scan dirs, parse .md files
    models.py       # ClaudeCommand dataclass
    registry.py     # store/lookup commands, update Telegram menu
```

### Key functions

```python
# discovery.py
def scan_commands(project_path: str | None) -> list[ClaudeCommand]:
    """Scan personal + project commands, merge with priority."""

def parse_command_file(path: Path) -> ClaudeCommand:
    """Parse .md file: frontmatter + body."""

# registry.py
class CommandRegistry:
    commands: dict[str, ClaudeCommand]

    async def refresh(self, bot, project_path: str | None):
        """Rescan and update Telegram menu."""

    def get(self, name: str) -> ClaudeCommand | None:
        """Lookup command by name."""

    def substitute_args(self, cmd: ClaudeCommand, args: str) -> str:
        """Replace $ARGUMENTS, $1, $2 in prompt."""
```

### Integration points
- `handlers.py`: Add handler for dynamic commands
- `application.py`: Initialize `CommandRegistry` in `bot_data`
- `new_session()`: Call `registry.refresh()` after session created

## Edge Cases & Error Handling

| Situation | Behavior |
|-----------|----------|
| No `.claude/commands/` dirs exist | Only built-in commands shown |
| Command file has no frontmatter | Use filename as description |
| Command name conflicts with built-in | Skip Claude command, log warning |
| >100 total commands | Warn user, truncate to 100 |
| Invalid YAML frontmatter | Skip file, log error |
| User sends `/unknown` | "Unknown command. Use /help" |
| No active session when running command | "Start a session first with /new" |

### Argument timeout
- If user doesn't respond within 5 minutes after argument prompt, clear `pending_command`
- User can cancel with `/cancel`
