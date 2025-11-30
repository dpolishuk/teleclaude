# TeleClaude - Design Document

## Overview

A personal Telegram bot that provides a mobile interface to Claude Code, enabling real-time interaction with Claude's agentic coding capabilities from anywhere.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Bot (Go)                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌────────────────┐  │
│  │  Telegram   │    │   Session   │    │    Claude      │  │
│  │  Handler    │───▶│   Manager   │───▶│   Controller   │  │
│  │ (telebot v4)│    │             │    │  (PTY + JSON)  │  │
│  └──────┬──────┘    └──────┬──────┘    └───────┬────────┘  │
│         │                  │                    │           │
│         ▼                  ▼                    ▼           │
│  ┌─────────────┐    ┌─────────────┐    ┌────────────────┐  │
│  │  Formatter  │    │  Metadata   │    │  ANSI Parser   │  │
│  │ (inline     │    │  Storage    │    │ (go-ansi)      │  │
│  │  annotations)│   │  (YAML)     │    └────────────────┘  │
│  └─────────────┘    └─────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │   Claude Code CLI   │
                   │  (PTY subprocess)   │
                   └─────────────────────┘
```

### Key Decisions

- **CLI + PTY** integration via `creack/pty` (not SDK)
- **Long polling** via `gopkg.in/telebot.v4` (not webhooks)
- **Single active session** per user
- **Metadata mirroring** to bot storage (not full transcript duplication)
- **User ID whitelist** in config file for authentication

## Session Management

### Session States

```
NEW → ACTIVE → IDLE → (resume) → ACTIVE
                 ↓
              ARCHIVED
```

### Metadata Storage

Location: `~/.teleclaude/sessions/<session_id>.yaml`

```yaml
session_id: "abc123"
claude_session_id: "abc123"  # For --resume flag
telegram_user: 12345678
project_path: "/home/user/projects/myapp"
project_name: "myapp"
created_at: "2024-01-15T10:30:00Z"
last_active: "2024-01-15T14:22:00Z"
total_cost_usd: 0.42
status: "idle"  # active | idle | archived
```

### Project Management

Hybrid approach supporting:
- Registered projects by name (`/new myapp`)
- Recent project picker (`/new` shows inline keyboard)
- Arbitrary paths (`/new /full/path`)

## Message Flow & Formatting

### Inbound (User → Claude)

```
Telegram message
       ↓
Auth check (user ID in whitelist?)
       ↓
Route to active session (or prompt to /new)
       ↓
Write prompt to PTY stdin
```

### Outbound (Claude → Telegram)

```
PTY stdout (stream-json NDJSON)
       ↓
Parse JSON lines → identify message type
       ↓
Format with inline annotations
       ↓
Accumulate in buffer
       ↓
Throttled edit (1/second) or new message (>3800 chars)
```

### Inline Annotation Format

```
[📁 src/main.go] The file contains a basic HTTP server
with two endpoints...

[📝 src/main.go +12/-3] I've added error handling to
wrap the connection logic in a recover block.

[⚡ go build ./...] Build completed successfully.
```

| Icon | Tool | Format |
|------|------|--------|
| 📁 | Read | `[📁 path]` |
| 📝 | Edit/Write | `[📝 path +add/-del]` |
| ⚡ | Bash | `[⚡ command]` (truncated to 40 chars) |
| 🔍 | Grep/Glob | `[🔍 pattern]` |
| 🌐 | WebFetch | `[🌐 domain]` |

## Approval Workflow

### Category-Based Rules

| Category | Operations | Behavior |
|----------|-----------|----------|
| Auto-accept | Read, Glob, Grep, WebFetch | Execute immediately |
| Auto-accept | Write, Edit (create/modify) | Execute immediately |
| Require approval | Bash (any command) | Prompt user |
| Require approval | File deletion | Prompt user |
| Require approval | Git push, force operations | Prompt user |

### Approval Message Format

```
🔒 Approval needed

Claude wants to: Clean build directory before fresh compile
Command: rm -rf ./build && go build ./...

[✅ Approve]  [❌ Deny]
```

### Cancellation

Inline `[🛑 Cancel]` button attached to streaming messages:
- First tap: SIGTERM (graceful)
- Second tap within 10s: SIGKILL (force)

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message, show usage |
| `/new` | Inline keyboard: registered + recent projects |
| `/new <name>` | Start session in registered project |
| `/new /path` | Start session in arbitrary directory |
| `/continue` | Resume last active session |
| `/sessions` | List sessions with inline keyboard to switch |
| `/switch <id>` | Switch to specific session |
| `/cost` | Show current session cost + total spend |
| `/cancel` | Stop current operation |
| `/help` | Command reference |

Non-command messages route to active session as prompts.

## Error Handling

### Process Failures

| Scenario | Response |
|----------|----------|
| Claude CLI not found | "❌ Claude Code not installed" |
| PTY spawn fails | "❌ Failed to start session. Check server logs." |
| Process crashes mid-response | "⚠️ Session interrupted. Use /continue to resume." |
| JSON parse error | Log and skip malformed line, continue |

### Telegram Failures

| Scenario | Response |
|----------|----------|
| Rate limited (429) | Back off, accumulate more, retry |
| Message too long | Split at 3800 chars, new message |
| Send fails | Retry 3x with exponential backoff |

### Graceful Shutdown

```
SIGTERM received
       ↓
Stop accepting new messages
       ↓
Send "🔄 Bot restarting..." to active sessions
       ↓
SIGTERM to all Claude processes, wait 10s
       ↓
SIGKILL any remaining, cleanup PTYs
       ↓
Exit
```

## Configuration

Location: `~/.teleclaude/config.yaml`

```yaml
# Required
telegram_token: "${TELEGRAM_BOT_TOKEN}"

# Authentication
allowed_users:
  - 12345678

# Registered projects
projects:
  myapp: /home/user/projects/myapp
  dotfiles: /home/user/.dotfiles

# Claude Code settings
claude:
  max_turns: 50
  permission_mode: "acceptEdits"

# Approval rules
approval:
  require_for:
    - "Bash"
    - "delete"
    - "git push"
    - "git force"

# Behavior
streaming:
  edit_throttle_ms: 1000
  chunk_size: 3800
```

## Project Structure

```
teleclaude/
├── cmd/
│   └── teleclaude/
│       └── main.go              # Entry point
├── internal/
│   ├── config/
│   │   └── config.go            # YAML parsing, validation
│   ├── telegram/
│   │   ├── bot.go               # telebot setup, long polling
│   │   ├── handlers.go          # Command handlers
│   │   ├── keyboards.go         # Inline keyboard builders
│   │   └── formatter.go         # Annotations, chunking
│   ├── claude/
│   │   ├── controller.go        # PTY management
│   │   ├── parser.go            # stream-json parsing
│   │   └── types.go             # Message types
│   ├── session/
│   │   ├── manager.go           # Session CRUD
│   │   ├── storage.go           # YAML metadata I/O
│   │   └── types.go             # Session structs
│   └── approval/
│       ├── rules.go             # Dangerous op detection
│       └── workflow.go          # Approval prompts
├── config.example.yaml
├── go.mod
└── README.md
```

## Dependencies

```go
require (
    gopkg.in/telebot.v4
    github.com/creack/pty
    github.com/leaanthony/go-ansi-parser
    gopkg.in/yaml.v3
)
```

## Deployment

Systemd service:

```ini
[Unit]
Description=TeleClaude
After=network.target

[Service]
Type=simple
User=youruser
Environment=TELEGRAM_BOT_TOKEN=xxx
ExecStart=/usr/local/bin/teleclaude
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```
