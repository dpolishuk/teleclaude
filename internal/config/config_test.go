package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadConfig(t *testing.T) {
	// Create temp config file
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "config.yaml")

	configContent := `
allowed_users:
  - 12345678
  - 87654321

projects:
  myapp: /home/user/myapp

claude:
  max_turns: 25
  permission_mode: "acceptEdits"

approval:
  require_for:
    - "Bash"

streaming:
  edit_throttle_ms: 500
  chunk_size: 4000
`
	if err := os.WriteFile(configPath, []byte(configContent), 0644); err != nil {
		t.Fatal(err)
	}

	cfg, err := Load(configPath)
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}

	if len(cfg.AllowedUsers) != 2 {
		t.Errorf("AllowedUsers = %d, want 2", len(cfg.AllowedUsers))
	}
	if cfg.AllowedUsers[0] != 12345678 {
		t.Errorf("AllowedUsers[0] = %d, want 12345678", cfg.AllowedUsers[0])
	}
	if cfg.Projects["myapp"] != "/home/user/myapp" {
		t.Errorf("Projects[myapp] = %s, want /home/user/myapp", cfg.Projects["myapp"])
	}
	if cfg.Claude.MaxTurns != 25 {
		t.Errorf("Claude.MaxTurns = %d, want 25", cfg.Claude.MaxTurns)
	}
	if cfg.Streaming.ChunkSize != 4000 {
		t.Errorf("Streaming.ChunkSize = %d, want 4000", cfg.Streaming.ChunkSize)
	}
}

func TestLoadConfigDefaults(t *testing.T) {
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "config.yaml")

	// Minimal config
	configContent := `
allowed_users:
  - 12345678
`
	if err := os.WriteFile(configPath, []byte(configContent), 0644); err != nil {
		t.Fatal(err)
	}

	cfg, err := Load(configPath)
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}

	// Check defaults applied
	if cfg.Claude.MaxTurns != 50 {
		t.Errorf("Claude.MaxTurns default = %d, want 50", cfg.Claude.MaxTurns)
	}
	if cfg.Streaming.EditThrottleMs != 1000 {
		t.Errorf("Streaming.EditThrottleMs default = %d, want 1000", cfg.Streaming.EditThrottleMs)
	}
	if cfg.Streaming.ChunkSize != 3800 {
		t.Errorf("Streaming.ChunkSize default = %d, want 3800", cfg.Streaming.ChunkSize)
	}
}

func TestIsUserAllowed(t *testing.T) {
	cfg := &Config{
		AllowedUsers: []int64{12345678, 87654321},
	}

	if !cfg.IsUserAllowed(12345678) {
		t.Error("IsUserAllowed(12345678) = false, want true")
	}
	if cfg.IsUserAllowed(99999999) {
		t.Error("IsUserAllowed(99999999) = true, want false")
	}
}
