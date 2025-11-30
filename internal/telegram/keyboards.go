package telegram

import (
	"fmt"
	"path/filepath"
	"time"

	"github.com/user/teleclaude/internal/session"
	tele "gopkg.in/telebot.v4"
)

type KeyboardBuilder struct{}

func NewKeyboardBuilder() *KeyboardBuilder {
	return &KeyboardBuilder{}
}

func (kb *KeyboardBuilder) ProjectSelector(registered map[string]string, recent []string) *tele.ReplyMarkup {
	markup := &tele.ReplyMarkup{}
	var rows []tele.Row

	// Registered projects
	if len(registered) > 0 {
		var regBtns []tele.Btn
		for name := range registered {
			btn := markup.Data("📁 "+name, "project", name)
			regBtns = append(regBtns, btn)
		}
		// Split into rows of 3
		for i := 0; i < len(regBtns); i += 3 {
			end := i + 3
			if end > len(regBtns) {
				end = len(regBtns)
			}
			rows = append(rows, markup.Row(regBtns[i:end]...))
		}
	}

	// Recent projects
	if len(recent) > 0 {
		var recentBtns []tele.Btn
		for _, path := range recent {
			name := filepath.Base(path)
			btn := markup.Data("🕐 "+name, "recent", path)
			recentBtns = append(recentBtns, btn)
		}
		for i := 0; i < len(recentBtns); i += 2 {
			end := i + 2
			if end > len(recentBtns) {
				end = len(recentBtns)
			}
			rows = append(rows, markup.Row(recentBtns[i:end]...))
		}
	}

	// Enter path button
	rows = append(rows, markup.Row(
		markup.Data("📂 Enter path...", "enterpath", ""),
	))

	markup.Inline(rows...)
	return markup
}

func (kb *KeyboardBuilder) SessionList(sessions []*session.Session) *tele.ReplyMarkup {
	markup := &tele.ReplyMarkup{}
	var rows []tele.Row

	for _, s := range sessions {
		status := "💤"
		if s.Status == session.StatusActive {
			status = "🟢"
		}

		age := formatAge(s.LastActive)
		label := fmt.Sprintf("%s %s · $%.2f · %s", status, s.ProjectName, s.TotalCostUSD, age)

		btn := markup.Data(label, "switch", s.ID)
		rows = append(rows, markup.Row(btn))
	}

	markup.Inline(rows...)
	return markup
}

func (kb *KeyboardBuilder) ApprovalButtons(requestID string) *tele.ReplyMarkup {
	markup := &tele.ReplyMarkup{}

	approve := markup.Data("✅ Approve", "approve", requestID)
	deny := markup.Data("❌ Deny", "deny", requestID)

	markup.Inline(markup.Row(approve, deny))
	return markup
}

func (kb *KeyboardBuilder) CancelButton(sessionID string) *tele.ReplyMarkup {
	markup := &tele.ReplyMarkup{}

	cancel := markup.Data("🛑 Cancel", "cancel", sessionID)

	markup.Inline(markup.Row(cancel))
	return markup
}

func formatAge(t time.Time) string {
	d := time.Since(t)

	switch {
	case d < time.Minute:
		return "now"
	case d < time.Hour:
		return fmt.Sprintf("%dm ago", int(d.Minutes()))
	case d < 24*time.Hour:
		return fmt.Sprintf("%dh ago", int(d.Hours()))
	default:
		return fmt.Sprintf("%dd ago", int(d.Hours()/24))
	}
}
