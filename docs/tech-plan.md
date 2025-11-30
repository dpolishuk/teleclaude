# Technical Research Report: Claude Code Telegram Bot Plugin

Claude Code offers **robust programmatic APIs** for external control, making a Telegram integration highly feasible. Multiple open-source implementations already exist, and the combination of Claude’s streaming JSON output with Telegram’s message editing provides an effective real-time experience. This report synthesizes findings across five research domains to support building a comprehensive technical specification.

## Claude Code provides two powerful integration paths

Anthropic offers both a **CLI interface** and a **full SDK** (recently renamed from Claude Code SDK to **Claude Agent SDK**) for programmatic control.   For a Telegram bot, the CLI approach with `--output-format stream-json` is the most practical starting point, while the SDK enables deeper integration.

### CLI headless mode essentials

The critical flags for non-interactive operation:

- `-p, --print` — Non-interactive mode (essential for scripting) 
- `--output-format stream-json` — NDJSON streaming output 
- `--input-format stream-json` — Accept streaming JSON via stdin 
- `--resume <session-id>` — Resume specific session 
- `-c, --continue` — Resume most recent conversation 
- `--permission-mode acceptEdits` — Auto-accept file changes 
- `--max-turns <n>` — Limit agentic turns 

A typical integration command looks like:

```bash
claude -p "Your prompt" --output-format stream-json | process_output
```

### Stream-JSON message types

The streaming output provides rich structured data:

```json
{"type": "init", "session_id": "abc123", ...}
{"type": "assistant", "message": {...}, "usage": {"input_tokens": 100, "output_tokens": 200}}
{"type": "tool_use", "id": "toolu_xxx", "name": "Write", "input": {...}}
{"type": "tool_result", "tool_use_id": "toolu_xxx", "content": "Success"}
{"type": "result", "result": "...", "cost_usd": 0.05, "usage": {...}}
```

This enables real-time streaming to Telegram, tool execution visibility, cost tracking per session, and session ID capture for resumption.

### SDK alternative (Python/TypeScript)

For deeper integration, the SDK provides async streaming:

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage

options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Bash"],
    permission_mode='acceptEdits',
    cwd="/path/to/project"
)

async for message in query(prompt="Your task", options=options):
    # Process each message in real-time
    stream_to_telegram(message)
```

### Transcript and configuration locations

|Resource           |Location                                              |
|-------------------|------------------------------------------------------|
|Session transcripts|`~/.claude/projects/{project-path}/{session-id}.jsonl`|
|User config        |`~/.claude.json`                                      |
|Project MCP config |`.mcp.json` (project root)                            |
|Cost data          |Embedded in JSON output (`cost_usd` field)            |

## Long polling wins for local Telegram deployment

For a locally-deployed personal bot without public IP, **long polling is definitively the correct choice**. Webhooks require a public HTTPS endpoint, SSL certificates, and reverse proxy configuration— unnecessary complexity for single-user deployment.

### Rate limits to design around

|Constraint          |Limit                    |Impact                      |
|--------------------|-------------------------|----------------------------|
|Single chat messages|~1/second (burst allowed)|Throttle streaming updates  |
|Message edits       |~20/minute per group chat|Use progressive accumulation|
|Message length      |**4096 UTF-8 characters**|Implement chunking strategy |
|Global API requests |~30/second               |Use backoff on HTTP 429     |

### Recommended Go libraries

**Primary recommendation: `telebot` (gopkg.in/telebot.v4)** — 4.1k stars, excellent middleware system, built-in keyboard builders, and context-based handlers ideal for session management.

**Alternative: `go-telegram/bot`** — Zero dependencies, latest Bot API support, built-in auto-retry on rate limits with `RetryAfter` field parsing.

### Streaming pattern for Telegram

Since Telegram doesn’t support true streaming, use **progressive message editing**:

```go
// Send initial message
msg, _ := bot.Send(chatID, "▌")
messageID := msg.MessageID

var buffer strings.Builder
lastEdit := time.Now()

for chunk := range claudeOutputChan {
    buffer.WriteString(chunk)
    content := buffer.String()
    
    // Handle 4096 char limit
    if len(content) > 3800 {
        msg, _ = bot.Send(chatID, "▌")  // New message
        messageID = msg.MessageID
        buffer.Reset()
        buffer.WriteString(chunk)
        content = chunk
    }
    
    // Throttle to 1 edit/second
    if time.Since(lastEdit) >= time.Second {
        bot.EditMessageText(chatID, messageID, content+"▌")
        lastEdit = time.Now()
    }
}
// Final edit without cursor
bot.EditMessageText(chatID, messageID, buffer.String())
```

### Long-running operation handling

For 30+ minute operations, use a **background pattern with periodic indicators**:

```go
// Acknowledge immediately
bot.Send(chatID, "✅ Task started. Updates will follow.")

// Loop typing indicator every 4 seconds
ctx, cancel := context.WithCancel(context.Background())
go func() {
    ticker := time.NewTicker(4 * time.Second)
    for {
        select {
        case <-ctx.Done(): return
        case <-ticker.C: bot.SendChatAction(chatID, "typing")
        }
    }
}()

// Progress updates via message editing
progressMsg, _ := bot.Send(chatID, "Progress: 0%")
for progress := range progressChan {
    bot.EditMessageText(chatID, progressMsg.MessageID, 
        fmt.Sprintf("Progress: %d%%", progress))
}
cancel()  // Stop typing
```

## PTY-based IPC is the optimal integration approach

For controlling Claude Code CLI, **pseudo-terminal (PTY) via creack/pty** is the recommended approach. It handles interactive behavior correctly and provides combined stdout/stderr in a single stream.

### Core PTY control pattern

```go
import (
    "github.com/creack/pty"
    "os/exec"
)

type ClaudeController struct {
    cmd    *exec.Cmd
    pty    *os.File
    output chan []byte
}

func NewClaudeController(workDir, prompt string) (*ClaudeController, error) {
    cmd := exec.Command("claude", "-p", prompt, 
        "--output-format", "stream-json")
    cmd.Dir = workDir
    
    ptmx, err := pty.Start(cmd)
    if err != nil {
        return nil, err
    }
    
    c := &ClaudeController{
        cmd:    cmd,
        pty:    ptmx,
        output: make(chan []byte, 100),
    }
    
    // Stream output
    go func() {
        buf := make([]byte, 4096)
        for {
            n, err := ptmx.Read(buf)
            if err != nil {
                close(c.output)
                return
            }
            c.output <- append([]byte{}, buf[:n]...)
        }
    }()
    
    return c, nil
}
```

### ANSI escape code handling

Claude Code outputs ANSI codes for formatting. Use **leaanthony/go-ansi-parser** to clean output:

```go
import "github.com/leaanthony/go-ansi-parser"

cleanText, _ := ansi.Cleanse(rawOutput)  // Strips all ANSI codes
```

For preserving formatting while parsing, **hinshun/vt10x** provides full terminal emulation.

### Process lifecycle considerations

Critical edge cases to handle:

- **Zombie processes**: Always call `cmd.Wait()` after exit
- **Subprocess orphans**: Use process groups with `Setpgid: true` and kill with negative PID
- **Graceful shutdown**: Send SIGTERM first, then SIGKILL after timeout
- **Context cancellation**: Standard context cancellation may not kill child processes

```go
// Kill entire process group
cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
cmd.Start()
// Later...
syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
```

## Four existing open-source implementations provide reference patterns

### errogaht/claude-code-telegram-bot (Node.js)

The most feature-complete existing implementation:

- Real-time streaming with smart 4096-char chunking
- Voice message transcription
- Multi-bot instance support (different projects)
- Web file browser with ngrok tunneling
- PM2 process management
- Session resume via `--resume` flag

**Architecture pattern:**

```
Telegram Bot API ↔ Bot Handler ↔ Claude CLI Process
                        ↓
              ClaudeStream Processor → TelegramFormatter
```

### RichardAtCT/claude-code-telegram (Python)

Comprehensive Python implementation:

- Full CLI navigation (cd, ls, pwd)
- Session persistence across conversations
- Git integration (status, diff, log)
- Multi-layer auth: whitelist + token-based
- Rate limiting with token bucket 
- Quick action inline keyboards

### JessyTsui/Claude-Code-Remote (Multi-platform)

Hook-based notification system using Claude Code’s native hooks (`~/.claude/settings.json`):

- Supports Email, Telegram, LINE, Desktop notifications 
- tmux session integration for command injection
- Token-based session isolation (8-char tokens)
- 24-hour auto-expiration
- Two-way control via message replies

### Feature gaps to fill

Existing solutions lack:

- **Unified MCP visibility**: No project exposes MCP server status in Telegram
- **Cost tracking integration**: No real-time token/cost monitoring
- **Conversation branching**: Can’t fork from specific conversation points
- **Approval workflows**: Missing permission prompts for dangerous operations
- **Multi-session management**: Limited orchestration of concurrent Claude instances

## MCP integration offers enhanced capabilities

Seven Telegram MCP servers exist that could enhance your bot:

|Server                                |Key Feature                      |
|--------------------------------------|---------------------------------|
|`sparfenyuk/mcp-telegram`             |MTProto-based, read-only access  |
|`chigwell/telegram-mcp`               |Full Telethon integration        |
|`juanhuttemann/telegram-assistant-mcp`|Approval workflows, notifications|

### Claude Code MCP configuration access

MCP configuration lives in `.mcp.json` (project) or `~/.claude.json` (user):

```json
{
  "mcpServers": {
    "my-server": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
    }
  }
}
```

CLI commands for MCP management: `claude mcp list`, `claude mcp add`, `claude mcp remove`.

## Security architecture recommendations

### Authentication layers

Implement multi-layer authentication following existing patterns:

1. **Telegram User ID whitelist**: Primary gate, stored in config
1. **Token-based sessions**: 8-character tokens for session isolation
1. **Rate limiting**: Token bucket algorithm (existing `RichardAtCT` implementation)
1. **Command restrictions**: Whitelist allowed operations

### Secure token storage

```go
// Never expose bot token in logs or error messages
token := os.Getenv("TELEGRAM_BOT_TOKEN")
if token == "" {
    log.Fatal("TELEGRAM_BOT_TOKEN not set")
}

// Validate user on every message
func isAuthorized(userID int64) bool {
    return allowedUsers[userID]
}
```

### Local service hardening

- Run service as unprivileged user
- Use Unix domain socket for internal IPC (not TCP)
- Implement command sanitization before shell execution
- Set `--max-turns` limits to prevent runaway costs
- Consider `--permission-mode plan` for read-only review mode

## Recommended architecture for Go implementation

```
┌─────────────────────────────────────────────────────────────────┐
│                     Telegram Bot Service                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────────┐│
│  │   Telegram   │    │   Session    │    │   Claude Code       ││
│  │   Handler    │───▶│   Manager    │───▶│   Controller        ││
│  │  (telebot)   │    │              │    │   (PTY + JSON)      ││
│  └──────────────┘    └──────────────┘    └──────────┬──────────┘│
│         │                   │                        │           │
│         ▼                   ▼                        ▼           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   Message    │    │   Transcript │    │   ANSI Parser    │   │
│  │   Formatter  │    │   Storage    │    │   (go-ansi)      │   │
│  │   (chunking) │    │   (JSONL)    │    └──────────────────┘   │
│  └──────────────┘    └──────────────┘                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────────┐│
│  │   Cost       │    │   MCP        │    │   Config           ││
│  │   Tracker    │    │   Monitor    │    │   Manager          ││
│  │              │    │              │    │                     ││
│  └──────────────┘    └──────────────┘    └─────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │   Claude Code CLI   │
                   │   (PTY subprocess)  │
                   └─────────────────────┘
```

### Key components

|Component        |Responsibility                                 |Implementation             |
|-----------------|-----------------------------------------------|---------------------------|
|Telegram Handler |Long polling, message routing, rate limiting   |`gopkg.in/telebot.v4`      |
|Session Manager  |Track multiple sessions, persistence, switching|In-memory + file-backed    |
|Claude Controller|PTY subprocess, JSON parsing, output streaming |`creack/pty` + JSON decoder|
|Message Formatter|4096 chunking, Markdown escaping, progress bars|Custom                     |
|Cost Tracker     |Aggregate `cost_usd` from JSON output          |Per-session accumulator    |
|MCP Monitor      |Read `.mcp.json`, display server status        |File watcher + parser      |

### Telegram command structure

|Command         |Function                              |
|----------------|--------------------------------------|
|`/start`        |Initialize bot, show welcome          |
|`/new [project]`|Start new Claude session              |
|`/continue`     |Resume last session                   |
|`/sessions`     |List all sessions with inline keyboard|
|`/switch <id>`  |Switch to session                     |
|`/cost`         |Show current session cost             |
|`/mcp`          |Display MCP server status             |
|`/cancel`       |Cancel current operation              |
|Direct message  |Send prompt to active session         |

## Key technical specifications summary

|Aspect                     |Specification                                          |
|---------------------------|-------------------------------------------------------|
|**Claude Code Integration**|CLI with `--output-format stream-json` or Python/TS SDK|
|**Telegram Transport**     |Long polling via `telebot` v4                          |
|**IPC Mechanism**          |PTY via `creack/pty`                                   |
|**Message Streaming**      |Progressive edit with 1s throttle, 4096 char chunks    |
|**Session Storage**        |JSONL files in `~/.claude-telegram/sessions/`          |
|**Cost Tracking**          |Parse `cost_usd` from stream-json `result` message     |
|**Authentication**         |Telegram user ID whitelist + optional token            |
|**Config Location**        |`~/.claude-telegram/config.yaml`                       |

## Implementation challenges and mitigations

**Challenge 1: Telegram edit rate limits**

- *Mitigation*: Accumulate output, throttle edits to 1/second, switch to new message at 3800 chars

**Challenge 2: Long-running operations (30+ min)**

- *Mitigation*: Background goroutine with periodic typing indicators + progress message updates

**Challenge 3: ANSI escape codes in output**

- *Mitigation*: Use `go-ansi-parser` to cleanse before sending to Telegram

**Challenge 4: Process group cleanup**

- *Mitigation*: Use `Setpgid: true`, kill with negative PID on shutdown

**Challenge 5: Session resumption across bot restarts**

- *Mitigation*: Persist session IDs to disk, use `--resume <id>` flag  

This research provides the technical foundation for a comprehensive ТЗ. The combination of Claude Code’s stream-json output, PTY-based process control, and Telegram’s message editing creates a viable architecture for real-time bidirectional communication.
