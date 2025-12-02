# CLAUDE.md

## Project Overview

TeleClaude is a Telegram bot for interacting with Claude Code from mobile devices. Built with Python 3.10+, it uses the Claude Agent SDK for AI integration and python-telegram-bot for Telegram communication.

## Tech Stack

- **Language**: Python 3.10+
- **Framework**: python-telegram-bot v21 (async)
- **AI**: Claude Agent SDK
- **Database**: SQLite via SQLAlchemy + aiosqlite
- **Config**: YAML files, python-dotenv

## Project Structure

```
src/
├── main.py              # Entry point
├── config/              # Settings and config loading
├── bot/                 # Telegram bot
│   ├── application.py   # Application factory with post_init() for async setup
│   ├── handlers.py      # Command handlers (/start, /help, /new, /resume, /mcp, etc.)
│   ├── callbacks.py     # Callback query handlers (permissions, project/session selection)
│   ├── keyboards.py     # Inline keyboard builders (projects, sessions, modes)
│   ├── command_handler.py # Dynamic Claude command execution
│   └── middleware.py    # Request middleware
├── claude/              # Claude SDK integration
│   ├── client.py        # TeleClaudeClient wrapper
│   ├── sessions.py      # Project/session scanning from ~/.claude/projects/
│   ├── streaming.py     # MessageStreamer with HTML formatting
│   ├── formatting.py    # Claude Code style tool/status formatting (⏵ symbol)
│   ├── permissions.py   # Interactive tool permission approval UI
│   └── hooks.py         # SDK event hooks (MCP tools, permissions)
├── storage/             # Database models and repository
├── commands/            # Command discovery and registry
│   ├── discovery.py     # Scans ~/.claude/commands/, plugins, project commands
│   ├── models.py        # ClaudeCommand dataclass
│   └── registry.py      # CommandRegistry - manages commands and Telegram menu
├── security/            # Sandbox utilities
├── mcp/                 # MCP server management (auto-testing, enable/disable)
└── utils/               # Formatting utilities
tests/                   # pytest tests (asyncio_mode=auto)
docs/                    # Design docs and plans
```

## Key Commands

```bash
# Run the bot
python -m src.main

# Run tests
pytest

# Linting
ruff check .

# Type checking
mypy src/
```

## Bot Commands

- `/start` - Initialize bot, select project
- `/new` - Start new session in current project
- `/resume` - Resume Claude Code sessions from terminal
- `/sessions` - List and switch between sessions
- `/mcp` - Manage MCP servers (list, test, enable/disable)
- `/refresh` - Rescan Claude commands for current project
- `/help` - Show help
- `/cancel` - Cancel current operation
- Voice/Audio messages - Transcribed and sent to Claude with confirmation

## Configuration

- Bot token: `TELEGRAM_BOT_TOKEN` env var
- Config file: `~/.teleclaude/config.yaml`
- Database: SQLite (path in config)
- MCP servers: Configured in config.yaml with stdio/http support

## Code Style

- Line length: 100 chars
- Use async/await for all I/O
- Type hints encouraged
- Ruff for linting

## Key Features

### Claude Commands Integration
- Execute `.claude/commands/*.md` files via Telegram's native `/` menu
- Supports personal (`~/.claude/commands/`), plugin, and project-scoped commands
- Commands with `$ARGUMENTS` or `$1`, `$2` placeholders prompt for input
- Dynamic command menu updates per project/session

### Session Resume
- Browse and resume Claude Code terminal sessions in Telegram
- Three-step UI: Project → Session → Mode (Fork/Continue)
- Session previews show first user message
- Persists `claude_session_id` for SDK continuity

### MCP Server Management
- List servers with status indicators
- Test individual or all servers
- Enable/disable servers at runtime

### Message Formatting
- Minimalistic Claude Code style with `⏵` symbol for tool calls
- Compact inline format: `⏵ Tool filename` or `⏵ Command args`
- Smart HTML tag balancing for streamed messages
- Tool result formatting with error indicators
- **Code diffs**: Unified diff style with ✅ (added) / ❌ (removed) emoji indicators
- **Smart truncation**: Long code shows context around errors, matches, and interesting regions
- **Hierarchical todos**: Tree structure with 📋 progress header, compact mode for >10 items

### Interactive Permissions
- Telegram inline buttons for tool approval (Allow/Always/Deny)
- Always-allow list persisted per user
- Async event-based response handling

### Voice Messages
- Send voice notes or audio files to chat with Claude
- Transcription via OpenAI Whisper API (default: Russian)
- Confirmation UI: Send / Edit / Cancel before sending to Claude
- Configurable duration and file size limits

## Architecture Notes

- `post_init()` hook loads CommandRegistry and MCPManager at startup
- `concurrent_updates(True)` enabled for responsive permission handling
- Session model includes `claude_session_id` for SDK session persistence
- TypingIndicator class sends typing action every 4 seconds during processing
