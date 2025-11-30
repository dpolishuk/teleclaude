package telegram

import (
	"context"
	"errors"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/user/teleclaude/internal/approval"
	"github.com/user/teleclaude/internal/claude"
	"github.com/user/teleclaude/internal/config"
	"github.com/user/teleclaude/internal/session"
	tele "gopkg.in/telebot.v4"
)

type Bot struct {
	bot        *tele.Bot
	cfg        *config.Config
	sessions   *session.Manager
	approval   *approval.Workflow
	formatter  *Formatter
	keyboards  *KeyboardBuilder

	controllers map[string]*claude.Controller // sessionID -> controller
	mu          sync.RWMutex
}

func NewBot(token string, cfg *config.Config, sessions *session.Manager, approvalWf *approval.Workflow, formatter *Formatter) (*Bot, error) {
	if token == "" {
		return nil, errors.New("telegram token required")
	}

	pref := tele.Settings{
		Token:  token,
		Poller: &tele.LongPoller{Timeout: 10 * time.Second},
	}

	teleBot, err := tele.NewBot(pref)
	if err != nil {
		return nil, fmt.Errorf("failed to create bot: %w", err)
	}

	b := &Bot{
		bot:         teleBot,
		cfg:         cfg,
		sessions:    sessions,
		approval:    approvalWf,
		formatter:   formatter,
		keyboards:   NewKeyboardBuilder(),
		controllers: make(map[string]*claude.Controller),
	}

	b.setupMiddleware()
	b.setupHandlers()

	return b, nil
}

func (b *Bot) setupMiddleware() {
	// Auth middleware
	b.bot.Use(func(next tele.HandlerFunc) tele.HandlerFunc {
		return func(c tele.Context) error {
			if !b.cfg.IsUserAllowed(c.Sender().ID) {
				return c.Send("Unauthorized. Your user ID is not in the allowed list.")
			}
			return next(c)
		}
	})
}

func (b *Bot) setupHandlers() {
	b.bot.Handle("/start", b.handleStart)
	b.bot.Handle("/help", b.handleHelp)
	b.bot.Handle("/new", b.handleNew)
	b.bot.Handle("/continue", b.handleContinue)
	b.bot.Handle("/sessions", b.handleSessions)
	b.bot.Handle("/switch", b.handleSwitch)
	b.bot.Handle("/cost", b.handleCost)
	b.bot.Handle("/cancel", b.handleCancel)

	// Callback queries for inline keyboards
	b.bot.Handle(&tele.Btn{Unique: "project"}, b.handleProjectSelect)
	b.bot.Handle(&tele.Btn{Unique: "recent"}, b.handleRecentSelect)
	b.bot.Handle(&tele.Btn{Unique: "switch"}, b.handleSessionSwitch)
	b.bot.Handle(&tele.Btn{Unique: "approve"}, b.handleApprove)
	b.bot.Handle(&tele.Btn{Unique: "deny"}, b.handleDeny)
	b.bot.Handle(&tele.Btn{Unique: "cancel"}, b.handleCancelCallback)

	// Text messages
	b.bot.Handle(tele.OnText, b.handleMessage)
}

func (b *Bot) Start() {
	log.Println("TeleClaude bot starting...")
	b.bot.Start()
}

func (b *Bot) Stop() {
	log.Println("TeleClaude bot stopping...")

	// Stop all controllers
	b.mu.Lock()
	for _, ctrl := range b.controllers {
		ctrl.Stop()
	}
	b.mu.Unlock()

	b.bot.Stop()
}

func (b *Bot) getController(sessionID string) *claude.Controller {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return b.controllers[sessionID]
}

func (b *Bot) setController(sessionID string, ctrl *claude.Controller) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.controllers[sessionID] = ctrl
}

func (b *Bot) removeController(sessionID string) {
	b.mu.Lock()
	defer b.mu.Unlock()
	delete(b.controllers, sessionID)
}

func (b *Bot) sendStreamingResponse(c tele.Context, ctrl *claude.Controller, sessionID string) {
	ctx := context.Background()

	// Send initial message with cancel button
	msg, err := b.bot.Send(c.Recipient(), "▌", b.keyboards.CancelButton(sessionID))
	if err != nil {
		log.Printf("Failed to send initial message: %v", err)
		return
	}

	var buffer string
	lastEdit := time.Now()
	rules := approval.NewRules(b.cfg.Approval.RequireFor)

	for claudeMsg := range ctrl.Output {
		switch claudeMsg.Type {
		case claude.MessageTypeInit:
			// Update session with Claude's session ID
			b.sessions.UpdateClaudeSessionID(sessionID, claudeMsg.SessionID)

		case claude.MessageTypeAssistant:
			text := claudeMsg.GetText()
			if text != "" {
				buffer += text
			}

		case claude.MessageTypeToolUse:
			// Format tool use annotation
			annotation := b.formatter.FormatToolUse(claudeMsg)
			buffer += "\n" + annotation + " "

			// Check if approval needed
			if rules.RequiresApproval(claudeMsg) {
				// Pause for approval
				b.handleApprovalRequest(ctx, c, ctrl, claudeMsg, sessionID)
			}

		case claude.MessageTypeResult:
			// Add cost
			if claudeMsg.CostUSD > 0 {
				b.sessions.AddCost(sessionID, claudeMsg.CostUSD)
			}
			// Final result
			if claudeMsg.Result != "" {
				buffer += "\n\n" + claudeMsg.Result
			}
		}

		// Throttled edit
		if time.Since(lastEdit) >= time.Duration(b.cfg.Streaming.EditThrottleMs)*time.Millisecond {
			displayText := buffer
			if ctrl.IsRunning() {
				displayText += "▌"
			}

			// Chunk if needed
			if len(displayText) > b.cfg.Streaming.ChunkSize {
				// Send current buffer and start new message
				b.bot.Edit(msg, buffer)
				msg, _ = b.bot.Send(c.Recipient(), "▌", b.keyboards.CancelButton(sessionID))
				buffer = ""
			} else {
				b.bot.Edit(msg, displayText, b.keyboards.CancelButton(sessionID))
			}
			lastEdit = time.Now()
		}
	}

	// Final edit without cursor or cancel button
	if buffer != "" {
		b.bot.Edit(msg, buffer)
	}
}

func (b *Bot) handleApprovalRequest(ctx context.Context, c tele.Context, ctrl *claude.Controller, msg *claude.Message, sessionID string) {
	rules := approval.NewRules(b.cfg.Approval.RequireFor)
	reason := rules.ExtractReason(msg)
	command := rules.ExtractCommand(msg)

	// Create approval request
	reqID := b.approval.CreateRequest(sessionID, msg.ToolName, reason, command)

	// Send approval prompt
	text := b.formatter.FormatApprovalRequest(msg.ToolName, reason, command)
	b.bot.Send(c.Recipient(), text, b.keyboards.ApprovalButtons(reqID))

	// Wait for decision
	approved, err := b.approval.WaitForDecision(ctx, reqID)
	if err != nil {
		b.bot.Send(c.Recipient(), "⏰ Approval timed out. Operation denied.")
		ctrl.SendInput("n") // Deny
		return
	}

	if approved {
		ctrl.SendInput("y") // Approve
	} else {
		ctrl.SendInput("n") // Deny
	}
}

// Handler implementations moved to handlers.go (Task 14)
