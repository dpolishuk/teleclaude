# TeleClaude

A Telegram bot for interacting with Claude Code from your mobile device.

Successor to [RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram) using the Claude Agent SDK.

## Architecture Overview

```mermaid
flowchart TB
    subgraph Telegram["Telegram"]
        User[("User")]
    end

    subgraph Bot["TeleClaude Bot"]
        TH["Telegram Handler<br/><i>python-telegram-bot</i>"]
        SM["Session Manager"]
        CC["Claude Controller<br/><i>PTY + JSON</i>"]

        subgraph Support["Support Services"]
            FMT["Formatter<br/><i>inline annotations</i>"]
            META["Metadata Storage<br/><i>YAML</i>"]
            ANSI["ANSI Parser"]
            APR["Approval Workflow"]
        end
    end

    subgraph Claude["Claude Code"]
        CLI["Claude Code CLI<br/><i>PTY subprocess</i>"]
    end

    subgraph Storage["Storage"]
        CFG[("~/.teleclaude/config.yaml")]
        SESS[("~/.teleclaude/sessions/*.yaml")]
    end

    User <-->|"Long Polling"| TH
    TH --> SM
    SM --> CC
    CC <-->|"stdin/stdout"| CLI

    TH --> FMT
    SM --> META
    CC --> ANSI
    SM --> APR

    META --> SESS
    TH --> CFG
```

## Message Flow

### Inbound (User → Claude)

```mermaid
sequenceDiagram
    participant U as User
    participant T as Telegram
    participant TH as Telegram Handler
    participant SM as Session Manager
    participant CC as Claude Controller
    participant CLI as Claude CLI

    U->>T: Send message
    T->>TH: Long poll delivers message

    TH->>TH: Auth check<br/>(user ID in whitelist?)

    alt Not authorized
        TH-->>T: Unauthorized
        T-->>U: Error message
    else Authorized
        TH->>SM: Route to session

        alt No active session
            SM-->>TH: No session
            TH-->>T: "Use /new to start"
            T-->>U: Prompt to create session
        else Has active session
            SM->>CC: Forward prompt
            CC->>CLI: Write to PTY stdin
            CLI-->>CC: ACK
        end
    end
```

### Outbound (Claude → Telegram)

```mermaid
sequenceDiagram
    participant CLI as Claude CLI
    participant CC as Claude Controller
    participant ANSI as ANSI Parser
    participant FMT as Formatter
    participant TH as Telegram Handler
    participant T as Telegram
    participant U as User

    CLI->>CC: PTY stdout (NDJSON stream)

    loop For each JSON line
        CC->>CC: Parse JSON message type
        CC->>ANSI: Strip ANSI codes
        ANSI-->>CC: Clean text

        CC->>FMT: Format with annotations
        Note over FMT: Read → [path]<br/>Edit → [path +/-]<br/>Bash → [cmd]
        FMT-->>CC: Annotated text

        CC->>CC: Accumulate in buffer

        alt Buffer > 3800 chars
            CC->>TH: Send new message
            TH->>T: bot.Send()
            T->>U: New message
            CC->>CC: Reset buffer
        else Throttle elapsed (1s)
            CC->>TH: Edit existing message
            TH->>T: bot.EditMessageText()
            T->>U: Updated message
        end
    end

    CC->>TH: Final edit (remove cursor)
    TH->>T: bot.EditMessageText()
    T->>U: Complete response
```

## Session Lifecycle

```mermaid
stateDiagram-v2
    [*] --> NEW: /new command

    NEW --> ACTIVE: Session created<br/>Claude CLI spawned

    ACTIVE --> ACTIVE: User sends message<br/>Claude responds

    ACTIVE --> IDLE: No activity timeout<br/>or task complete

    IDLE --> ACTIVE: /continue or<br/>new message

    IDLE --> ARCHIVED: Manual archive<br/>or expiration

    ARCHIVED --> [*]

    note right of ACTIVE
        PTY process running
        Real-time streaming
        Cost tracking active
    end note

    note right of IDLE
        PTY terminated
        Session ID preserved
        Can resume with --resume
    end note

    note left of ARCHIVED
        Metadata retained
        No resumption
        Historical record
    end note
```

## Features

- Real-time streaming of Claude responses
- Session management with resume support
- Category-based approval for dangerous operations
- Cost tracking per session
- Multi-project support
- Directory navigation commands
- Git integration

## Requirements

- Python 3.10+
- Claude Code CLI installed
- Telegram Bot Token

## Installation

```bash
# Clone the repository
git clone https://github.com/user/teleclaude-python.git
cd teleclaude-python

# Install with Poetry
poetry install

# Or with pip
pip install -r requirements.txt
```

## Configuration

1. Create config directory:
```bash
mkdir -p ~/.teleclaude
```

2. Copy example config:
```bash
cp config.example.yaml ~/.teleclaude/config.yaml
```

3. Edit `~/.teleclaude/config.yaml`:
```yaml
allowed_users:
  - YOUR_TELEGRAM_USER_ID

projects:
  myapp: /path/to/your/project
```

4. Set environment variables:
```bash
export TELEGRAM_BOT_TOKEN=your_bot_token_here
```

## Usage

```bash
# Run with Poetry
poetry run python -m src.main

# Or directly
python -m src.main
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Show all commands |
| `/new [project]` | Start new session |
| `/continue` | Resume last session |
| `/sessions` | List all sessions |
| `/switch <id>` | Switch to session |
| `/cost` | Show usage costs |
| `/cancel` | Stop operation |
| `/cd <path>` | Change directory |
| `/ls [path]` | List directory |
| `/pwd` | Show current directory |
| `/git [cmd]` | Git operations |
| `/export [fmt]` | Export session |

## Inline Annotations

| Icon | Tool | Format |
|------|------|--------|
| 📁 | Read | `[📁 path]` |
| 📝 | Edit/Write | `[📝 path +add/-del]` |
| ⚡ | Bash | `[⚡ command]` |
| 🔍 | Grep/Glob | `[🔍 pattern]` |
| 🌐 | WebFetch | `[🌐 domain]` |

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linting
ruff check .

# Run type checking
mypy src/
```

## License

MIT
