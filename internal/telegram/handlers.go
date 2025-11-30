package telegram

import (
	"context"
	"fmt"
	"strings"

	"github.com/user/teleclaude/internal/claude"
	tele "gopkg.in/telebot.v4"
)

func (b *Bot) handleStart(c tele.Context) error {
	text := `Welcome to TeleClaude!

I'm your mobile interface to Claude Code.

Commands:
/new - Start a new session
/continue - Resume last session
/sessions - List your sessions
/cost - Show session costs
/help - Show this help

Just send me a message to chat with Claude in your active session.`

	return c.Send(text)
}

func (b *Bot) handleHelp(c tele.Context) error {
	return b.handleStart(c)
}

func (b *Bot) handleNew(c tele.Context) error {
	args := c.Args()

	// If path provided directly
	if len(args) > 0 {
		path := strings.Join(args, " ")

		// Check if it's a registered project name
		if projectPath, ok := b.cfg.Projects[path]; ok {
			return b.startSession(c, projectPath, path)
		}

		// Otherwise treat as path
		return b.startSession(c, path, "")
	}

	// Show project selector
	// TODO: Load recent from storage
	recent := []string{}

	markup := b.keyboards.ProjectSelector(b.cfg.Projects, recent)
	return c.Send("Select a project or enter a path:", markup)
}

func (b *Bot) handleContinue(c tele.Context) error {
	userID := c.Sender().ID

	// Get last active session
	sessions, err := b.sessions.GetUserSessions(userID)
	if err != nil || len(sessions) == 0 {
		return c.Send("No sessions found. Use /new to start one.")
	}

	// Find most recent
	var latest = sessions[0]
	for _, s := range sessions {
		if s.LastActive.After(latest.LastActive) {
			latest = s
		}
	}

	b.sessions.SetActiveSession(userID, latest)
	return c.Send(fmt.Sprintf("Resumed session: %s\nProject: %s", latest.ID[:8], latest.ProjectName))
}

func (b *Bot) handleSessions(c tele.Context) error {
	userID := c.Sender().ID

	sessions, err := b.sessions.GetUserSessions(userID)
	if err != nil || len(sessions) == 0 {
		return c.Send("No sessions found. Use /new to start one.")
	}

	markup := b.keyboards.SessionList(sessions)
	return c.Send("Your sessions:", markup)
}

func (b *Bot) handleSwitch(c tele.Context) error {
	args := c.Args()
	if len(args) == 0 {
		return b.handleSessions(c)
	}

	sessionID := args[0]
	userID := c.Sender().ID

	if err := b.sessions.SwitchSession(userID, sessionID); err != nil {
		return c.Send("Session not found.")
	}

	session, _ := b.sessions.GetSession(sessionID)
	return c.Send(fmt.Sprintf("Switched to: %s (%s)", session.ProjectName, session.ID[:8]))
}

func (b *Bot) handleCost(c tele.Context) error {
	userID := c.Sender().ID
	session := b.sessions.GetActiveSession(userID)

	if session == nil {
		return c.Send("No active session.")
	}

	// Get all sessions for total
	all, _ := b.sessions.GetUserSessions(userID)
	var total float64
	for _, s := range all {
		total += s.TotalCostUSD
	}

	text := fmt.Sprintf("Session: $%.4f\nTotal: $%.4f", session.TotalCostUSD, total)
	return c.Send(text)
}

func (b *Bot) handleCancel(c tele.Context) error {
	userID := c.Sender().ID
	session := b.sessions.GetActiveSession(userID)

	if session == nil {
		return c.Send("No active session.")
	}

	ctrl := b.getController(session.ID)
	if ctrl == nil || !ctrl.IsRunning() {
		return c.Send("No operation running.")
	}

	ctrl.Stop()
	return c.Send("Stopping operation...")
}

func (b *Bot) handleMessage(c tele.Context) error {
	userID := c.Sender().ID
	session := b.sessions.GetActiveSession(userID)

	if session == nil {
		return c.Send("No active session. Use /new to start one or /continue to resume.")
	}

	prompt := c.Text()

	// Check if there's already a running controller
	existingCtrl := b.getController(session.ID)
	if existingCtrl != nil && existingCtrl.IsRunning() {
		return c.Send("Claude is still working. Wait for completion or /cancel.")
	}

	// Create new controller
	ctrl := claude.NewController(
		session.ProjectPath,
		b.cfg.Claude.MaxTurns,
		b.cfg.Claude.PermissionMode,
	)

	// Set resume ID if available
	if session.ClaudeSessionID != "" {
		ctrl.SetSessionID(session.ClaudeSessionID)
	}

	b.setController(session.ID, ctrl)

	// Start Claude
	if err := ctrl.Start(context.Background(), prompt); err != nil {
		b.removeController(session.ID)
		return c.Send(fmt.Sprintf("Failed to start Claude: %v", err))
	}

	// Stream responses
	go func() {
		b.sendStreamingResponse(c, ctrl, session.ID)
		b.removeController(session.ID)
	}()

	return nil
}

// Callback handlers

func (b *Bot) handleProjectSelect(c tele.Context) error {
	projectName := c.Callback().Data
	projectPath, ok := b.cfg.Projects[projectName]
	if !ok {
		return c.Respond(&tele.CallbackResponse{Text: "Project not found"})
	}

	c.Respond(&tele.CallbackResponse{})
	return b.startSession(c, projectPath, projectName)
}

func (b *Bot) handleRecentSelect(c tele.Context) error {
	projectPath := c.Callback().Data
	c.Respond(&tele.CallbackResponse{})
	return b.startSession(c, projectPath, "")
}

func (b *Bot) handleSessionSwitch(c tele.Context) error {
	sessionID := c.Callback().Data
	userID := c.Sender().ID

	if err := b.sessions.SwitchSession(userID, sessionID); err != nil {
		return c.Respond(&tele.CallbackResponse{Text: "Session not found"})
	}

	session, _ := b.sessions.GetSession(sessionID)
	c.Respond(&tele.CallbackResponse{Text: "Switched!"})
	return c.Send(fmt.Sprintf("Switched to: %s", session.ProjectName))
}

func (b *Bot) handleApprove(c tele.Context) error {
	reqID := c.Callback().Data
	b.approval.Approve(reqID)
	c.Respond(&tele.CallbackResponse{Text: "Approved!"})
	return c.Edit("✅ Approved")
}

func (b *Bot) handleDeny(c tele.Context) error {
	reqID := c.Callback().Data
	b.approval.Deny(reqID)
	c.Respond(&tele.CallbackResponse{Text: "Denied"})
	return c.Edit("❌ Denied")
}

func (b *Bot) handleCancelCallback(c tele.Context) error {
	sessionID := c.Callback().Data

	ctrl := b.getController(sessionID)
	if ctrl == nil {
		return c.Respond(&tele.CallbackResponse{Text: "No operation running"})
	}

	if ctrl.IsRunning() {
		ctrl.Stop()
		c.Respond(&tele.CallbackResponse{Text: "Stopping..."})
	} else {
		ctrl.ForceStop()
		c.Respond(&tele.CallbackResponse{Text: "Force stopped"})
	}

	return nil
}

func (b *Bot) startSession(c tele.Context, projectPath, projectName string) error {
	userID := c.Sender().ID

	if projectName == "" {
		// Extract from path
		parts := strings.Split(projectPath, "/")
		if len(parts) > 0 {
			projectName = parts[len(parts)-1]
		}
	}

	session, err := b.sessions.CreateSession(userID, projectPath, projectName)
	if err != nil {
		return c.Send(fmt.Sprintf("Failed to create session: %v", err))
	}

	return c.Send(fmt.Sprintf("Started session: %s\nProject: %s\nPath: %s",
		session.ID[:8], projectName, projectPath))
}
