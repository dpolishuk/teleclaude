package telegram

import (
	"testing"
	"time"

	"github.com/user/teleclaude/internal/session"
)

func TestProjectKeyboard(t *testing.T) {
	registered := map[string]string{
		"myapp":    "/home/user/myapp",
		"dotfiles": "/home/user/.dotfiles",
	}
	recent := []string{"/tmp/scratch", "/home/user/other"}

	kb := NewKeyboardBuilder()
	markup := kb.ProjectSelector(registered, recent)

	if markup == nil {
		t.Fatal("ProjectSelector() returned nil")
	}

	// Should have rows for registered and recent
	if len(markup.InlineKeyboard) < 2 {
		t.Errorf("Expected at least 2 rows, got %d", len(markup.InlineKeyboard))
	}
}

func TestSessionKeyboard(t *testing.T) {
	sessions := []*session.Session{
		{
			ID:          "s1",
			ProjectName: "myapp",
			Status:      session.StatusActive,
			TotalCostUSD: 1.23,
			LastActive:  time.Now(),
		},
		{
			ID:          "s2",
			ProjectName: "other",
			Status:      session.StatusIdle,
			TotalCostUSD: 0.45,
			LastActive:  time.Now().Add(-2 * time.Hour),
		},
	}

	kb := NewKeyboardBuilder()
	markup := kb.SessionList(sessions)

	if markup == nil {
		t.Fatal("SessionList() returned nil")
	}

	if len(markup.InlineKeyboard) != 2 {
		t.Errorf("Expected 2 rows, got %d", len(markup.InlineKeyboard))
	}
}

func TestApprovalKeyboard(t *testing.T) {
	kb := NewKeyboardBuilder()
	markup := kb.ApprovalButtons("req123")

	if markup == nil {
		t.Fatal("ApprovalButtons() returned nil")
	}

	if len(markup.InlineKeyboard) != 1 {
		t.Errorf("Expected 1 row, got %d", len(markup.InlineKeyboard))
	}

	// Should have approve and deny buttons
	if len(markup.InlineKeyboard[0]) != 2 {
		t.Errorf("Expected 2 buttons, got %d", len(markup.InlineKeyboard[0]))
	}
}

func TestCancelKeyboard(t *testing.T) {
	kb := NewKeyboardBuilder()
	markup := kb.CancelButton("sess123")

	if markup == nil {
		t.Fatal("CancelButton() returned nil")
	}

	if len(markup.InlineKeyboard) != 1 {
		t.Errorf("Expected 1 row, got %d", len(markup.InlineKeyboard))
	}
}
