# TeleClaude Python Rewrite Design

> Successor to [RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram) using the Claude Agent SDK

## Overview

TeleClaude Python is a Telegram bot providing mobile access to Claude Code, built on the official Claude Agent SDK for native streaming, session management, and tool integration.

## Architecture Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Claude Integration | Claude Agent SDK (`ClaudeSDKClient`) | Official SDK, native streaming, hooks, session continuity |
| Telegram Library | `python-telegram-bot` v20+ | Predecessor compatibility, well-documented, async-native |
| Session Storage | SQLite + SQLAlchemy | Rich queries, audit logs, cost tracking |
| Project Structure | RichardAtCT-style modules | Successor compatibility, easy migration |
| Configuration | YAML + env vars | Human-readable config, secrets in environment |
| Approval Workflow | SDK `PreToolUse` hooks | Native interception, clean async flow |
| Streaming | Throttled edits (1000ms) | Smooth UX, respects Telegram rate limits |
| Authentication | Config whitelist | Simple, effective for personal use |
| Packaging | Poetry | Modern Python, lockfile, predecessor approach |

## Project Structure

```
teleclaude-python/
├── pyproject.toml
├── poetry.lock
├── README.md
├── config.example.yaml
├── .env.example
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── exceptions.py           # Custom exceptions
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── application.py      # Telegram Application setup
│   │   ├── handlers.py         # Command handlers
│   │   ├── callbacks.py        # Inline keyboard callbacks
│   │   └── middleware.py       # Auth middleware
│   ├── claude/
│   │   ├── __init__.py
│   │   ├── client.py           # ClaudeSDKClient wrapper
│   │   ├── hooks.py            # PreToolUse/PostToolUse hooks
│   │   └── streaming.py        # Message streaming to Telegram
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py         # YAML + env config loading
│   ├── security/
│   │   ├── __init__.py
│   │   ├── auth.py             # User authentication
│   │   └── sandbox.py          # Directory sandboxing
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py         # SQLAlchemy setup
│   │   ├── models.py           # Session, Usage, AuditLog models
│   │   └── repository.py       # Data access layer
│   └── utils/
│       ├── __init__.py
│       ├── formatting.py       # Telegram markdown formatting
│       └── keyboards.py        # Inline keyboard builders
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_handlers.py
    └── test_claude.py
```

## Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.10"
claude-agent-sdk = "^0.1"
python-telegram-bot = {extras = ["job-queue"], version = "^21.0"}
sqlalchemy = "^2.0"
aiosqlite = "^0.19"
pyyaml = "^6.0"
python-dotenv = "^1.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.23"
ruff = "^0.4"
mypy = "^1.10"
```

## Configuration

### ~/.teleclaude/config.yaml

```yaml
# Authentication - Telegram user IDs allowed
allowed_users:
  - 12345678

# Registered projects
projects:
  myapp: /home/user/projects/myapp
  dotfiles: /home/user/.dotfiles

# Directory sandbox - allowed base paths
sandbox:
  allowed_paths:
    - /home/user/projects
    - /home/user/.dotfiles

# Claude settings
claude:
  max_turns: 50
  permission_mode: "acceptEdits"
  max_budget_usd: 10.0

# Approval rules - patterns requiring confirmation
approval:
  dangerous_commands:
    - "rm -rf"
    - "git push --force"
    - "sudo"
    - "chmod 777"
  require_approval_for:
    - "Bash"
    - "Write"
    - "Edit"

# Streaming behavior
streaming:
  edit_throttle_ms: 1000
  chunk_size: 3800

# Database
database:
  path: ~/.teleclaude/teleclaude.db
```

### Environment Variables

```bash
# .env
TELEGRAM_BOT_TOKEN=your_bot_token_here
# Optional: override Claude CLI path
CLAUDE_CLI_PATH=/usr/local/bin/claude
```

## Database Schema

### Sessions Table

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    claude_session_id TEXT,
    telegram_user_id INTEGER NOT NULL,
    project_path TEXT NOT NULL,
    project_name TEXT,
    current_directory TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP,
    total_cost_usd REAL DEFAULT 0.0
);
```

### Usage Table

```sql
CREATE TABLE usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(id),
    telegram_user_id INTEGER NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0.0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Audit Log Table

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL,
    session_id TEXT,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and quick actions |
| `/help` | Show all commands |
| `/new [project]` | Start new Claude session |
| `/continue` | Resume last session |
| `/sessions` | List all sessions |
| `/switch <id>` | Switch to specific session |
| `/cost` | Show usage costs |
| `/cancel` | Stop current operation |
| `/cd <path>` | Change working directory |
| `/ls [path]` | List directory contents |
| `/pwd` | Show current directory |
| `/git [command]` | Git operations (status, log, diff) |
| `/export [format]` | Export session (md, html, json) |

## Claude SDK Integration

### Client Wrapper

```python
# src/claude/client.py
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from .hooks import create_approval_hooks

class TeleClaudeClient:
    def __init__(self, config: Config, session: Session):
        self.config = config
        self.session = session
        self._client: ClaudeSDKClient | None = None

    async def __aenter__(self):
        options = ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
            permission_mode=self.config.claude.permission_mode,
            max_turns=self.config.claude.max_turns,
            max_budget_usd=self.config.claude.max_budget_usd,
            cwd=self.session.current_directory,
            hooks=create_approval_hooks(self.config.approval),
        )

        if self.session.claude_session_id:
            options.resume = self.session.claude_session_id

        self._client = ClaudeSDKClient(options=options)
        await self._client.connect()
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.disconnect()

    async def query(self, prompt: str):
        """Send prompt and yield messages."""
        await self._client.query(prompt)
        async for message in self._client.receive_messages():
            yield message
```

### Approval Hooks

```python
# src/claude/hooks.py
from claude_agent_sdk import HookMatcher

DANGEROUS_PATTERNS = [
    "rm -rf", "rm -r /", "sudo rm",
    "git push --force", "git push -f",
    "chmod 777", "chmod -R 777",
    "> /dev/sd", "mkfs.", "dd if=",
]

async def check_dangerous_command(input_data, tool_use_id, context):
    """PreToolUse hook to intercept dangerous operations."""
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        for pattern in DANGEROUS_PATTERNS:
            if pattern in command:
                # Signal approval needed - handled by Telegram callback
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "ask",
                        "permissionDecisionReason": f"Command contains: {pattern}",
                    }
                }

    return {}  # Allow

def create_approval_hooks(approval_config):
    """Create hooks dict for ClaudeAgentOptions."""
    return {
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[check_dangerous_command]),
            HookMatcher(matcher="Write", hooks=[check_dangerous_command]),
        ]
    }
```

### Streaming to Telegram

```python
# src/claude/streaming.py
import asyncio
from telegram import Message
from claude_agent_sdk import AssistantMessage, TextBlock, ToolUseBlock, ResultMessage

class TelegramStreamer:
    def __init__(self, message: Message, throttle_ms: int = 1000):
        self.message = message
        self.throttle_ms = throttle_ms
        self.buffer = ""
        self.last_edit = 0

    async def stream_messages(self, client: TeleClaudeClient):
        """Stream Claude messages to Telegram with throttled edits."""
        async for msg in client.query(self.prompt):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        self.buffer += block.text
                        await self._maybe_edit()
                    elif isinstance(block, ToolUseBlock):
                        annotation = self._format_tool_use(block)
                        self.buffer += f"\n{annotation}\n"
                        await self._maybe_edit()

            elif isinstance(msg, ResultMessage):
                # Final edit with complete content
                await self._final_edit()
                return msg.total_cost_usd

        return 0.0

    async def _maybe_edit(self):
        """Edit message if throttle time has passed."""
        now = asyncio.get_event_loop().time() * 1000
        if now - self.last_edit >= self.throttle_ms:
            await self.message.edit_text(
                self._truncate(self.buffer),
                parse_mode="MarkdownV2"
            )
            self.last_edit = now

    async def _final_edit(self):
        """Final message edit with complete content."""
        await self.message.edit_text(
            self._truncate(self.buffer),
            parse_mode="MarkdownV2"
        )

    def _format_tool_use(self, block: ToolUseBlock) -> str:
        """Format tool use as inline annotation."""
        icons = {"Read": "📁", "Write": "📝", "Edit": "✏️", "Bash": "⚡", "Grep": "🔍"}
        icon = icons.get(block.name, "🔧")
        return f"[{icon} {block.name}]"

    def _truncate(self, text: str, max_len: int = 4096) -> str:
        """Truncate to Telegram message limit."""
        if len(text) <= max_len:
            return text
        return text[:max_len-3] + "..."
```

## Telegram Bot Structure

### Application Setup

```python
# src/bot/application.py
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from .handlers import (
    start, help_cmd, new_session, continue_session,
    list_sessions, switch_session, show_cost, cancel,
    cd, ls, pwd, git, export_session, handle_message
)
from .callbacks import handle_callback
from .middleware import auth_middleware

def create_application(config: Config) -> Application:
    """Create and configure Telegram Application."""
    app = Application.builder().token(config.telegram_token).build()

    # Store config in bot_data
    app.bot_data["config"] = config

    # Add handlers
    app.add_handler(CommandHandler("start", auth_middleware(start)))
    app.add_handler(CommandHandler("help", auth_middleware(help_cmd)))
    app.add_handler(CommandHandler("new", auth_middleware(new_session)))
    app.add_handler(CommandHandler("continue", auth_middleware(continue_session)))
    app.add_handler(CommandHandler("sessions", auth_middleware(list_sessions)))
    app.add_handler(CommandHandler("switch", auth_middleware(switch_session)))
    app.add_handler(CommandHandler("cost", auth_middleware(show_cost)))
    app.add_handler(CommandHandler("cancel", auth_middleware(cancel)))
    app.add_handler(CommandHandler("cd", auth_middleware(cd)))
    app.add_handler(CommandHandler("ls", auth_middleware(ls)))
    app.add_handler(CommandHandler("pwd", auth_middleware(pwd)))
    app.add_handler(CommandHandler("git", auth_middleware(git)))
    app.add_handler(CommandHandler("export", auth_middleware(export_session)))

    # Message handler for Claude interactions
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        auth_middleware(handle_message)
    ))

    # Callback handler for inline keyboards
    app.add_handler(CallbackQueryHandler(handle_callback))

    return app
```

### Auth Middleware

```python
# src/bot/middleware.py
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

def auth_middleware(handler):
    """Decorator to check user authentication."""
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        config = context.bot_data["config"]
        user_id = update.effective_user.id

        if user_id not in config.allowed_users:
            await update.message.reply_text("⛔ Unauthorized")
            return

        return await handler(update, context)
    return wrapper
```

## Message Flow

```
User sends message
        ↓
┌───────────────────┐
│  Auth Middleware  │ → Reject if not in whitelist
└─────────┬─────────┘
          ↓
┌───────────────────┐
│  Get/Create       │ → Load from SQLite or create new
│  Session          │
└─────────┬─────────┘
          ↓
┌───────────────────┐
│  ClaudeSDKClient  │ → Connect with session ID
│  (with hooks)     │
└─────────┬─────────┘
          ↓
┌───────────────────┐
│  Stream Messages  │ → Throttled edits to Telegram
│  to Telegram      │
└─────────┬─────────┘
          ↓
   PreToolUse Hook
          ↓
┌───────────────────┐
│  Dangerous?       │ → Yes: Show approval keyboard
└─────────┬─────────┘         Wait for callback
          ↓ No
┌───────────────────┐
│  Tool Executes    │
└─────────┬─────────┘
          ↓
   PostToolUse Hook
          ↓
┌───────────────────┐
│  Continue Stream  │ → More tool uses or final result
└─────────┬─────────┘
          ↓
┌───────────────────┐
│  Update Session   │ → Save cost, last_active to SQLite
└───────────────────┘
```

## Error Handling

```python
# src/exceptions.py
class TeleClaudeError(Exception):
    """Base exception for TeleClaude."""
    pass

class AuthenticationError(TeleClaudeError):
    """User not authorized."""
    pass

class SessionError(TeleClaudeError):
    """Session-related error."""
    pass

class SandboxError(TeleClaudeError):
    """Directory access violation."""
    pass

class ClaudeError(TeleClaudeError):
    """Claude SDK error."""
    pass
```

## Entry Point

```python
# src/main.py
import asyncio
import logging
from dotenv import load_dotenv

from config.settings import load_config
from storage.database import init_database
from bot.application import create_application

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    load_dotenv()

    config = load_config()
    await init_database(config.database.path)

    app = create_application(config)

    logger.info("TeleClaude starting...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
```

## Migration from RichardAtCT

Key differences from predecessor:

| Aspect | RichardAtCT | TeleClaude Python |
|--------|-------------|-------------------|
| Claude Integration | CLI subprocess or direct API | Claude Agent SDK |
| Streaming | Manual chunking | SDK native + throttled edits |
| Approval | Custom implementation | SDK PreToolUse hooks |
| Session Resume | Manual | SDK native resume |
| Config | Pure .env | YAML + env vars |

Compatible features preserved:
- Project structure
- SQLite storage
- Command set
- Directory sandboxing
- Authentication model
