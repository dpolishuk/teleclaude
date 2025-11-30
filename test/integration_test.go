//go:build integration
// +build integration

package test

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/user/teleclaude/internal/approval"
	"github.com/user/teleclaude/internal/config"
	"github.com/user/teleclaude/internal/session"
	"github.com/user/teleclaude/internal/telegram"
)

func TestBotInitialization(t *testing.T) {
	token := os.Getenv("TELEGRAM_BOT_TOKEN")
	if token == "" {
		t.Skip("TELEGRAM_BOT_TOKEN not set")
	}

	// Create temp config
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "config.yaml")

	configContent := `
allowed_users:
  - 12345678
claude:
  max_turns: 10
`
	os.WriteFile(configPath, []byte(configContent), 0644)

	cfg, err := config.Load(configPath)
	if err != nil {
		t.Fatalf("Failed to load config: %v", err)
	}

	storage := session.NewStorage(tmpDir)
	sessionMgr := session.NewManager(storage)
	approvalWf := approval.NewWorkflow(5 * time.Minute)
	formatter := telegram.NewFormatter(3800)

	bot, err := telegram.NewBot(token, cfg, sessionMgr, approvalWf, formatter)
	if err != nil {
		t.Fatalf("Failed to create bot: %v", err)
	}

	// Just verify it was created
	if bot == nil {
		t.Fatal("Bot is nil")
	}
}
