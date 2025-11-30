package telegram

import (
	"testing"

	"github.com/user/teleclaude/internal/config"
)

func TestNewBotRequiresToken(t *testing.T) {
	cfg := &config.Config{
		AllowedUsers: []int64{12345},
	}

	_, err := NewBot("", cfg, nil, nil, nil)
	if err == nil {
		t.Error("NewBot() should fail with empty token")
	}
}

func TestBotAuthMiddleware(t *testing.T) {
	cfg := &config.Config{
		AllowedUsers: []int64{12345, 67890},
	}

	// Test user allowed check
	if !cfg.IsUserAllowed(12345) {
		t.Error("IsUserAllowed(12345) = false, want true")
	}
	if cfg.IsUserAllowed(99999) {
		t.Error("IsUserAllowed(99999) = true, want false")
	}
}
