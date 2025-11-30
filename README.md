# TeleClaude

A Telegram bot for interacting with Claude Code from your mobile device.

## Features

- Real-time streaming of Claude responses
- Session management with resume support
- Category-based approval for dangerous operations
- Cost tracking per session
- Multi-project support

## Installation

```bash
go install github.com/user/teleclaude/cmd/teleclaude@latest
```

## Configuration

Create `~/.teleclaude/config.yaml`:

```yaml
allowed_users:
  - YOUR_TELEGRAM_USER_ID

projects:
  myapp: /path/to/project

claude:
  max_turns: 50
  permission_mode: "acceptEdits"

approval:
  require_for:
    - "Bash"
    - "delete"
    - "git push"
```

## Usage

1. Set your Telegram bot token:
   ```bash
   export TELEGRAM_BOT_TOKEN=your_token_here
   ```

2. Run the bot:
   ```bash
   teleclaude
   ```

3. In Telegram:
   - `/new` - Start a new session
   - `/continue` - Resume last session
   - Send any message to chat with Claude

## Commands

- `/start` - Welcome message
- `/new [project]` - Start new session
- `/continue` - Resume last session
- `/sessions` - List all sessions
- `/switch <id>` - Switch to session
- `/cost` - Show costs
- `/cancel` - Stop current operation
- `/help` - Show help

## License

MIT
