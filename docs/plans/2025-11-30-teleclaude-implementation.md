# TeleClaude Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Telegram bot that provides mobile access to Claude Code via PTY-based CLI integration with real-time streaming output.

**Architecture:** Go application using telebot v4 for Telegram long polling, creack/pty for Claude CLI process control, YAML for configuration and session metadata. Single active session per user with category-based approval for dangerous operations.

**Tech Stack:** Go 1.21+, telebot v4, creack/pty, go-ansi-parser, yaml.v3

---

## Task 1: Project Scaffolding

**Files:**
- Create: `go.mod`
- Create: `cmd/teleclaude/main.go`
- Create: `config.example.yaml`

**Step 1: Initialize Go module**

Run:
```bash
go mod init github.com/user/teleclaude
```

Expected: `go.mod` created with module path

**Step 2: Create minimal main.go**

Create `cmd/teleclaude/main.go`:

```go
package main

import (
	"fmt"
	"os"
)

func main() {
	fmt.Println("TeleClaude starting...")

	token := os.Getenv("TELEGRAM_BOT_TOKEN")
	if token == "" {
		fmt.Fprintln(os.Stderr, "TELEGRAM_BOT_TOKEN environment variable required")
		os.Exit(1)
	}

	fmt.Println("Token found, bot ready to initialize")
}
```

**Step 3: Create example config**

Create `config.example.yaml`:

```yaml
# TeleClaude Configuration
# Copy to ~/.teleclaude/config.yaml and customize

# Authentication - Telegram user IDs allowed to use the bot
allowed_users:
  - 12345678  # Replace with your Telegram user ID

# Registered projects (optional)
projects:
  # myapp: /home/user/projects/myapp
  # dotfiles: /home/user/.dotfiles

# Claude Code settings
claude:
  max_turns: 50
  permission_mode: "acceptEdits"

# Approval rules - operations requiring user confirmation
approval:
  require_for:
    - "Bash"
    - "delete"
    - "git push"
    - "git force"

# Streaming behavior
streaming:
  edit_throttle_ms: 1000
  chunk_size: 3800
```

**Step 4: Verify build**

Run:
```bash
go build ./cmd/teleclaude
```

Expected: Binary created successfully

**Step 5: Commit**

```bash
git add go.mod cmd/ config.example.yaml
git commit -m "feat: project scaffolding with main entry point"
```

---

## Task 2: Configuration Package

**Files:**
- Create: `internal/config/config.go`
- Create: `internal/config/config_test.go`

**Step 1: Write failing test for config loading**

Create `internal/config/config_test.go`:

```go
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
```

**Step 2: Run test to verify it fails**

Run:
```bash
go test ./internal/config/... -v
```

Expected: FAIL - package does not exist

**Step 3: Implement config package**

Create `internal/config/config.go`:

```go
package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

type Config struct {
	AllowedUsers []int64           `yaml:"allowed_users"`
	Projects     map[string]string `yaml:"projects"`
	Claude       ClaudeConfig      `yaml:"claude"`
	Approval     ApprovalConfig    `yaml:"approval"`
	Streaming    StreamingConfig   `yaml:"streaming"`
}

type ClaudeConfig struct {
	MaxTurns       int    `yaml:"max_turns"`
	PermissionMode string `yaml:"permission_mode"`
}

type ApprovalConfig struct {
	RequireFor []string `yaml:"require_for"`
}

type StreamingConfig struct {
	EditThrottleMs int `yaml:"edit_throttle_ms"`
	ChunkSize      int `yaml:"chunk_size"`
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	cfg := &Config{}
	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, err
	}

	applyDefaults(cfg)
	return cfg, nil
}

func applyDefaults(cfg *Config) {
	if cfg.Claude.MaxTurns == 0 {
		cfg.Claude.MaxTurns = 50
	}
	if cfg.Claude.PermissionMode == "" {
		cfg.Claude.PermissionMode = "acceptEdits"
	}
	if cfg.Streaming.EditThrottleMs == 0 {
		cfg.Streaming.EditThrottleMs = 1000
	}
	if cfg.Streaming.ChunkSize == 0 {
		cfg.Streaming.ChunkSize = 3800
	}
	if cfg.Projects == nil {
		cfg.Projects = make(map[string]string)
	}
	if cfg.Approval.RequireFor == nil {
		cfg.Approval.RequireFor = []string{"Bash", "delete", "git push", "git force"}
	}
}

func (c *Config) IsUserAllowed(userID int64) bool {
	for _, id := range c.AllowedUsers {
		if id == userID {
			return true
		}
	}
	return false
}
```

**Step 4: Add yaml dependency and run tests**

Run:
```bash
go get gopkg.in/yaml.v3
go test ./internal/config/... -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add internal/config/ go.mod go.sum
git commit -m "feat: add config package with YAML loading and defaults"
```

---

## Task 3: Session Types

**Files:**
- Create: `internal/session/types.go`
- Create: `internal/session/types_test.go`

**Step 1: Write failing test for session types**

Create `internal/session/types_test.go`:

```go
package session

import (
	"testing"
	"time"
)

func TestSessionStatus(t *testing.T) {
	s := &Session{
		Status: StatusActive,
	}

	if s.Status != StatusActive {
		t.Errorf("Status = %s, want %s", s.Status, StatusActive)
	}
}

func TestSessionIsActive(t *testing.T) {
	active := &Session{Status: StatusActive}
	idle := &Session{Status: StatusIdle}
	archived := &Session{Status: StatusArchived}

	if !active.IsActive() {
		t.Error("active.IsActive() = false, want true")
	}
	if idle.IsActive() {
		t.Error("idle.IsActive() = true, want false")
	}
	if archived.IsActive() {
		t.Error("archived.IsActive() = true, want false")
	}
}

func TestNewSession(t *testing.T) {
	s := New("abc123", 12345678, "/home/user/myapp", "myapp")

	if s.ID == "" {
		t.Error("ID should not be empty")
	}
	if s.ClaudeSessionID != "abc123" {
		t.Errorf("ClaudeSessionID = %s, want abc123", s.ClaudeSessionID)
	}
	if s.TelegramUser != 12345678 {
		t.Errorf("TelegramUser = %d, want 12345678", s.TelegramUser)
	}
	if s.ProjectPath != "/home/user/myapp" {
		t.Errorf("ProjectPath = %s, want /home/user/myapp", s.ProjectPath)
	}
	if s.Status != StatusActive {
		t.Errorf("Status = %s, want %s", s.Status, StatusActive)
	}
	if s.CreatedAt.IsZero() {
		t.Error("CreatedAt should not be zero")
	}
	if time.Since(s.CreatedAt) > time.Second {
		t.Error("CreatedAt should be recent")
	}
}
```

**Step 2: Run test to verify it fails**

Run:
```bash
go test ./internal/session/... -v
```

Expected: FAIL - package does not exist

**Step 3: Implement session types**

Create `internal/session/types.go`:

```go
package session

import (
	"crypto/rand"
	"encoding/hex"
	"time"
)

type Status string

const (
	StatusActive   Status = "active"
	StatusIdle     Status = "idle"
	StatusArchived Status = "archived"
)

type Session struct {
	ID              string    `yaml:"session_id"`
	ClaudeSessionID string    `yaml:"claude_session_id"`
	TelegramUser    int64     `yaml:"telegram_user"`
	ProjectPath     string    `yaml:"project_path"`
	ProjectName     string    `yaml:"project_name"`
	CreatedAt       time.Time `yaml:"created_at"`
	LastActive      time.Time `yaml:"last_active"`
	TotalCostUSD    float64   `yaml:"total_cost_usd"`
	Status          Status    `yaml:"status"`
}

func New(claudeSessionID string, telegramUser int64, projectPath, projectName string) *Session {
	now := time.Now()
	return &Session{
		ID:              generateID(),
		ClaudeSessionID: claudeSessionID,
		TelegramUser:    telegramUser,
		ProjectPath:     projectPath,
		ProjectName:     projectName,
		CreatedAt:       now,
		LastActive:      now,
		TotalCostUSD:    0,
		Status:          StatusActive,
	}
}

func (s *Session) IsActive() bool {
	return s.Status == StatusActive
}

func (s *Session) MarkIdle() {
	s.Status = StatusIdle
	s.LastActive = time.Now()
}

func (s *Session) MarkActive() {
	s.Status = StatusActive
	s.LastActive = time.Now()
}

func (s *Session) AddCost(cost float64) {
	s.TotalCostUSD += cost
	s.LastActive = time.Now()
}

func generateID() string {
	b := make([]byte, 8)
	rand.Read(b)
	return hex.EncodeToString(b)
}
```

**Step 4: Run tests**

Run:
```bash
go test ./internal/session/... -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add internal/session/types.go internal/session/types_test.go
git commit -m "feat: add session types with status management"
```

---

## Task 4: Session Storage

**Files:**
- Create: `internal/session/storage.go`
- Create: `internal/session/storage_test.go`

**Step 1: Write failing test for session storage**

Create `internal/session/storage_test.go`:

```go
package session

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestStorageSaveAndLoad(t *testing.T) {
	tmpDir := t.TempDir()
	storage := NewStorage(tmpDir)

	session := &Session{
		ID:              "test123",
		ClaudeSessionID: "claude456",
		TelegramUser:    12345678,
		ProjectPath:     "/home/user/myapp",
		ProjectName:     "myapp",
		CreatedAt:       time.Now(),
		LastActive:      time.Now(),
		TotalCostUSD:    1.23,
		Status:          StatusActive,
	}

	// Save
	if err := storage.Save(session); err != nil {
		t.Fatalf("Save() error = %v", err)
	}

	// Verify file exists
	expectedPath := filepath.Join(tmpDir, "sessions", "test123.yaml")
	if _, err := os.Stat(expectedPath); os.IsNotExist(err) {
		t.Fatalf("Session file not created at %s", expectedPath)
	}

	// Load
	loaded, err := storage.Load("test123")
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}

	if loaded.ID != session.ID {
		t.Errorf("ID = %s, want %s", loaded.ID, session.ID)
	}
	if loaded.TelegramUser != session.TelegramUser {
		t.Errorf("TelegramUser = %d, want %d", loaded.TelegramUser, session.TelegramUser)
	}
	if loaded.TotalCostUSD != session.TotalCostUSD {
		t.Errorf("TotalCostUSD = %f, want %f", loaded.TotalCostUSD, session.TotalCostUSD)
	}
}

func TestStorageListByUser(t *testing.T) {
	tmpDir := t.TempDir()
	storage := NewStorage(tmpDir)

	// Create sessions for two users
	s1 := &Session{ID: "s1", TelegramUser: 111, Status: StatusActive}
	s2 := &Session{ID: "s2", TelegramUser: 111, Status: StatusIdle}
	s3 := &Session{ID: "s3", TelegramUser: 222, Status: StatusActive}

	storage.Save(s1)
	storage.Save(s2)
	storage.Save(s3)

	// List user 111's sessions
	sessions, err := storage.ListByUser(111)
	if err != nil {
		t.Fatalf("ListByUser() error = %v", err)
	}

	if len(sessions) != 2 {
		t.Errorf("ListByUser(111) returned %d sessions, want 2", len(sessions))
	}
}

func TestStorageDelete(t *testing.T) {
	tmpDir := t.TempDir()
	storage := NewStorage(tmpDir)

	session := &Session{ID: "todelete", TelegramUser: 111}
	storage.Save(session)

	if err := storage.Delete("todelete"); err != nil {
		t.Fatalf("Delete() error = %v", err)
	}

	_, err := storage.Load("todelete")
	if err == nil {
		t.Error("Load() should fail after Delete()")
	}
}
```

**Step 2: Run test to verify it fails**

Run:
```bash
go test ./internal/session/... -v
```

Expected: FAIL - NewStorage not defined

**Step 3: Implement session storage**

Create `internal/session/storage.go`:

```go
package session

import (
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

type Storage struct {
	baseDir string
}

func NewStorage(baseDir string) *Storage {
	return &Storage{baseDir: baseDir}
}

func (s *Storage) sessionsDir() string {
	return filepath.Join(s.baseDir, "sessions")
}

func (s *Storage) sessionPath(id string) string {
	return filepath.Join(s.sessionsDir(), id+".yaml")
}

func (s *Storage) Save(session *Session) error {
	if err := os.MkdirAll(s.sessionsDir(), 0755); err != nil {
		return err
	}

	data, err := yaml.Marshal(session)
	if err != nil {
		return err
	}

	return os.WriteFile(s.sessionPath(session.ID), data, 0644)
}

func (s *Storage) Load(id string) (*Session, error) {
	data, err := os.ReadFile(s.sessionPath(id))
	if err != nil {
		return nil, err
	}

	session := &Session{}
	if err := yaml.Unmarshal(data, session); err != nil {
		return nil, err
	}

	return session, nil
}

func (s *Storage) Delete(id string) error {
	return os.Remove(s.sessionPath(id))
}

func (s *Storage) ListByUser(userID int64) ([]*Session, error) {
	entries, err := os.ReadDir(s.sessionsDir())
	if err != nil {
		if os.IsNotExist(err) {
			return []*Session{}, nil
		}
		return nil, err
	}

	var sessions []*Session
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".yaml") {
			continue
		}

		id := strings.TrimSuffix(entry.Name(), ".yaml")
		session, err := s.Load(id)
		if err != nil {
			continue // Skip corrupted files
		}

		if session.TelegramUser == userID {
			sessions = append(sessions, session)
		}
	}

	return sessions, nil
}

func (s *Storage) ListAll() ([]*Session, error) {
	entries, err := os.ReadDir(s.sessionsDir())
	if err != nil {
		if os.IsNotExist(err) {
			return []*Session{}, nil
		}
		return nil, err
	}

	var sessions []*Session
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".yaml") {
			continue
		}

		id := strings.TrimSuffix(entry.Name(), ".yaml")
		session, err := s.Load(id)
		if err != nil {
			continue
		}
		sessions = append(sessions, session)
	}

	return sessions, nil
}
```

**Step 4: Run tests**

Run:
```bash
go test ./internal/session/... -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add internal/session/storage.go internal/session/storage_test.go
git commit -m "feat: add session storage with YAML persistence"
```

---

## Task 5: Session Manager

**Files:**
- Create: `internal/session/manager.go`
- Create: `internal/session/manager_test.go`

**Step 1: Write failing test for session manager**

Create `internal/session/manager_test.go`:

```go
package session

import (
	"testing"
)

func TestManagerGetActiveSession(t *testing.T) {
	tmpDir := t.TempDir()
	storage := NewStorage(tmpDir)
	manager := NewManager(storage)

	// No active session initially
	if s := manager.GetActiveSession(12345); s != nil {
		t.Error("GetActiveSession() should return nil when no session exists")
	}

	// Create and set active session
	session := New("claude123", 12345, "/home/user/app", "app")
	manager.SetActiveSession(12345, session)

	// Now should return the session
	active := manager.GetActiveSession(12345)
	if active == nil {
		t.Fatal("GetActiveSession() returned nil after SetActiveSession()")
	}
	if active.ID != session.ID {
		t.Errorf("GetActiveSession().ID = %s, want %s", active.ID, session.ID)
	}
}

func TestManagerCreateSession(t *testing.T) {
	tmpDir := t.TempDir()
	storage := NewStorage(tmpDir)
	manager := NewManager(storage)

	session, err := manager.CreateSession(12345, "/home/user/app", "app")
	if err != nil {
		t.Fatalf("CreateSession() error = %v", err)
	}

	if session.TelegramUser != 12345 {
		t.Errorf("TelegramUser = %d, want 12345", session.TelegramUser)
	}
	if session.ProjectPath != "/home/user/app" {
		t.Errorf("ProjectPath = %s, want /home/user/app", session.ProjectPath)
	}

	// Should be set as active
	active := manager.GetActiveSession(12345)
	if active == nil || active.ID != session.ID {
		t.Error("CreateSession() should set the new session as active")
	}

	// Should be persisted
	loaded, err := storage.Load(session.ID)
	if err != nil {
		t.Fatalf("Session not persisted: %v", err)
	}
	if loaded.ID != session.ID {
		t.Error("Persisted session ID mismatch")
	}
}

func TestManagerSwitchSession(t *testing.T) {
	tmpDir := t.TempDir()
	storage := NewStorage(tmpDir)
	manager := NewManager(storage)

	// Create two sessions
	s1, _ := manager.CreateSession(12345, "/app1", "app1")
	s2, _ := manager.CreateSession(12345, "/app2", "app2")

	// s2 should be active (most recent)
	if active := manager.GetActiveSession(12345); active.ID != s2.ID {
		t.Error("Most recent session should be active")
	}

	// Switch to s1
	if err := manager.SwitchSession(12345, s1.ID); err != nil {
		t.Fatalf("SwitchSession() error = %v", err)
	}

	if active := manager.GetActiveSession(12345); active.ID != s1.ID {
		t.Error("SwitchSession() did not change active session")
	}
}

func TestManagerUpdateClaudeSessionID(t *testing.T) {
	tmpDir := t.TempDir()
	storage := NewStorage(tmpDir)
	manager := NewManager(storage)

	session, _ := manager.CreateSession(12345, "/app", "app")

	if err := manager.UpdateClaudeSessionID(session.ID, "claude-xyz"); err != nil {
		t.Fatalf("UpdateClaudeSessionID() error = %v", err)
	}

	// Reload and check
	loaded, _ := storage.Load(session.ID)
	if loaded.ClaudeSessionID != "claude-xyz" {
		t.Errorf("ClaudeSessionID = %s, want claude-xyz", loaded.ClaudeSessionID)
	}
}
```

**Step 2: Run test to verify it fails**

Run:
```bash
go test ./internal/session/... -v
```

Expected: FAIL - NewManager not defined

**Step 3: Implement session manager**

Create `internal/session/manager.go`:

```go
package session

import (
	"errors"
	"sync"
)

var ErrSessionNotFound = errors.New("session not found")

type Manager struct {
	storage        *Storage
	activeSessions map[int64]*Session // userID -> active session
	mu             sync.RWMutex
}

func NewManager(storage *Storage) *Manager {
	return &Manager{
		storage:        storage,
		activeSessions: make(map[int64]*Session),
	}
}

func (m *Manager) GetActiveSession(userID int64) *Session {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.activeSessions[userID]
}

func (m *Manager) SetActiveSession(userID int64, session *Session) {
	m.mu.Lock()
	defer m.mu.Unlock()

	// Mark previous session as idle
	if prev, exists := m.activeSessions[userID]; exists && prev.ID != session.ID {
		prev.MarkIdle()
		m.storage.Save(prev)
	}

	session.MarkActive()
	m.activeSessions[userID] = session
	m.storage.Save(session)
}

func (m *Manager) CreateSession(userID int64, projectPath, projectName string) (*Session, error) {
	session := New("", userID, projectPath, projectName)

	if err := m.storage.Save(session); err != nil {
		return nil, err
	}

	m.SetActiveSession(userID, session)
	return session, nil
}

func (m *Manager) SwitchSession(userID int64, sessionID string) error {
	session, err := m.storage.Load(sessionID)
	if err != nil {
		return ErrSessionNotFound
	}

	if session.TelegramUser != userID {
		return ErrSessionNotFound // Don't expose other users' sessions
	}

	m.SetActiveSession(userID, session)
	return nil
}

func (m *Manager) UpdateClaudeSessionID(sessionID, claudeSessionID string) error {
	session, err := m.storage.Load(sessionID)
	if err != nil {
		return err
	}

	session.ClaudeSessionID = claudeSessionID
	return m.storage.Save(session)
}

func (m *Manager) AddCost(sessionID string, cost float64) error {
	session, err := m.storage.Load(sessionID)
	if err != nil {
		return err
	}

	session.AddCost(cost)

	// Update in-memory if active
	m.mu.Lock()
	for _, s := range m.activeSessions {
		if s.ID == sessionID {
			s.AddCost(cost)
			break
		}
	}
	m.mu.Unlock()

	return m.storage.Save(session)
}

func (m *Manager) GetUserSessions(userID int64) ([]*Session, error) {
	return m.storage.ListByUser(userID)
}

func (m *Manager) GetSession(sessionID string) (*Session, error) {
	return m.storage.Load(sessionID)
}

func (m *Manager) MarkAllIdle() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	for userID, session := range m.activeSessions {
		session.MarkIdle()
		m.storage.Save(session)
		delete(m.activeSessions, userID)
	}
	return nil
}
```

**Step 4: Run tests**

Run:
```bash
go test ./internal/session/... -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add internal/session/manager.go internal/session/manager_test.go
git commit -m "feat: add session manager with active session tracking"
```

---

## Task 6: Claude JSON Types

**Files:**
- Create: `internal/claude/types.go`
- Create: `internal/claude/types_test.go`

**Step 1: Write failing test for Claude message types**

Create `internal/claude/types_test.go`:

```go
package claude

import (
	"encoding/json"
	"testing"
)

func TestParseInitMessage(t *testing.T) {
	raw := `{"type":"init","session_id":"abc123","cwd":"/home/user"}`

	var msg Message
	if err := json.Unmarshal([]byte(raw), &msg); err != nil {
		t.Fatalf("Unmarshal error = %v", err)
	}

	if msg.Type != MessageTypeInit {
		t.Errorf("Type = %s, want %s", msg.Type, MessageTypeInit)
	}
	if msg.SessionID != "abc123" {
		t.Errorf("SessionID = %s, want abc123", msg.SessionID)
	}
}

func TestParseAssistantMessage(t *testing.T) {
	raw := `{"type":"assistant","message":{"content":[{"type":"text","text":"Hello world"}]}}`

	var msg Message
	if err := json.Unmarshal([]byte(raw), &msg); err != nil {
		t.Fatalf("Unmarshal error = %v", err)
	}

	if msg.Type != MessageTypeAssistant {
		t.Errorf("Type = %s, want %s", msg.Type, MessageTypeAssistant)
	}
}

func TestParseToolUseMessage(t *testing.T) {
	raw := `{"type":"tool_use","id":"toolu_123","name":"Read","input":{"file_path":"/src/main.go"}}`

	var msg Message
	if err := json.Unmarshal([]byte(raw), &msg); err != nil {
		t.Fatalf("Unmarshal error = %v", err)
	}

	if msg.Type != MessageTypeToolUse {
		t.Errorf("Type = %s, want %s", msg.Type, MessageTypeToolUse)
	}
	if msg.ToolName != "Read" {
		t.Errorf("ToolName = %s, want Read", msg.ToolName)
	}
	if msg.ToolID != "toolu_123" {
		t.Errorf("ToolID = %s, want toolu_123", msg.ToolID)
	}
}

func TestParseResultMessage(t *testing.T) {
	raw := `{"type":"result","result":"Done","cost_usd":0.05,"usage":{"input_tokens":100,"output_tokens":200}}`

	var msg Message
	if err := json.Unmarshal([]byte(raw), &msg); err != nil {
		t.Fatalf("Unmarshal error = %v", err)
	}

	if msg.Type != MessageTypeResult {
		t.Errorf("Type = %s, want %s", msg.Type, MessageTypeResult)
	}
	if msg.CostUSD != 0.05 {
		t.Errorf("CostUSD = %f, want 0.05", msg.CostUSD)
	}
	if msg.Result != "Done" {
		t.Errorf("Result = %s, want Done", msg.Result)
	}
}
```

**Step 2: Run test to verify it fails**

Run:
```bash
go test ./internal/claude/... -v
```

Expected: FAIL - package does not exist

**Step 3: Implement Claude types**

Create `internal/claude/types.go`:

```go
package claude

import "encoding/json"

type MessageType string

const (
	MessageTypeInit       MessageType = "init"
	MessageTypeAssistant  MessageType = "assistant"
	MessageTypeToolUse    MessageType = "tool_use"
	MessageTypeToolResult MessageType = "tool_result"
	MessageTypeResult     MessageType = "result"
	MessageTypeError      MessageType = "error"
)

type Message struct {
	Type      MessageType     `json:"type"`
	SessionID string          `json:"session_id,omitempty"`
	Message   *AssistantMsg   `json:"message,omitempty"`
	ToolID    string          `json:"id,omitempty"`
	ToolName  string          `json:"name,omitempty"`
	ToolInput json.RawMessage `json:"input,omitempty"`
	Content   string          `json:"content,omitempty"`
	Result    string          `json:"result,omitempty"`
	CostUSD   float64         `json:"cost_usd,omitempty"`
	Usage     *Usage          `json:"usage,omitempty"`
	Error     string          `json:"error,omitempty"`
}

type AssistantMsg struct {
	Content []ContentBlock `json:"content"`
}

type ContentBlock struct {
	Type string `json:"type"`
	Text string `json:"text,omitempty"`
}

type Usage struct {
	InputTokens  int `json:"input_tokens"`
	OutputTokens int `json:"output_tokens"`
}

// ToolInput helpers for common tools

type ReadInput struct {
	FilePath string `json:"file_path"`
}

type WriteInput struct {
	FilePath string `json:"file_path"`
	Content  string `json:"content"`
}

type EditInput struct {
	FilePath  string `json:"file_path"`
	OldString string `json:"old_string"`
	NewString string `json:"new_string"`
}

type BashInput struct {
	Command string `json:"command"`
}

func (m *Message) GetText() string {
	if m.Message == nil {
		return ""
	}
	var text string
	for _, block := range m.Message.Content {
		if block.Type == "text" {
			text += block.Text
		}
	}
	return text
}

func (m *Message) ParseToolInput(v interface{}) error {
	return json.Unmarshal(m.ToolInput, v)
}
```

**Step 4: Run tests**

Run:
```bash
go test ./internal/claude/... -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add internal/claude/types.go internal/claude/types_test.go
git commit -m "feat: add Claude stream-json message types"
```

---

## Task 7: Claude JSON Parser

**Files:**
- Create: `internal/claude/parser.go`
- Create: `internal/claude/parser_test.go`

**Step 1: Write failing test for NDJSON parser**

Create `internal/claude/parser_test.go`:

```go
package claude

import (
	"strings"
	"testing"
)

func TestParserParseStream(t *testing.T) {
	input := `{"type":"init","session_id":"abc123"}
{"type":"assistant","message":{"content":[{"type":"text","text":"Hello"}]}}
{"type":"result","result":"Done","cost_usd":0.05}
`

	parser := NewParser()
	reader := strings.NewReader(input)
	messages := make(chan *Message, 10)

	go func() {
		parser.ParseStream(reader, messages)
		close(messages)
	}()

	var received []*Message
	for msg := range messages {
		received = append(received, msg)
	}

	if len(received) != 3 {
		t.Fatalf("Received %d messages, want 3", len(received))
	}

	if received[0].Type != MessageTypeInit {
		t.Errorf("Message 0 type = %s, want init", received[0].Type)
	}
	if received[0].SessionID != "abc123" {
		t.Errorf("Message 0 session_id = %s, want abc123", received[0].SessionID)
	}

	if received[1].Type != MessageTypeAssistant {
		t.Errorf("Message 1 type = %s, want assistant", received[1].Type)
	}

	if received[2].Type != MessageTypeResult {
		t.Errorf("Message 2 type = %s, want result", received[2].Type)
	}
	if received[2].CostUSD != 0.05 {
		t.Errorf("Message 2 cost_usd = %f, want 0.05", received[2].CostUSD)
	}
}

func TestParserSkipInvalidLines(t *testing.T) {
	input := `{"type":"init","session_id":"abc"}
not json at all
{"type":"result","result":"Done"}
`

	parser := NewParser()
	reader := strings.NewReader(input)
	messages := make(chan *Message, 10)

	go func() {
		parser.ParseStream(reader, messages)
		close(messages)
	}()

	var received []*Message
	for msg := range messages {
		received = append(received, msg)
	}

	// Should skip invalid line and continue
	if len(received) != 2 {
		t.Fatalf("Received %d messages, want 2 (skipping invalid)", len(received))
	}
}
```

**Step 2: Run test to verify it fails**

Run:
```bash
go test ./internal/claude/... -v -run TestParser
```

Expected: FAIL - NewParser not defined

**Step 3: Implement parser**

Create `internal/claude/parser.go`:

```go
package claude

import (
	"bufio"
	"encoding/json"
	"io"
	"log"
)

type Parser struct{}

func NewParser() *Parser {
	return &Parser{}
}

func (p *Parser) ParseStream(reader io.Reader, messages chan<- *Message) {
	scanner := bufio.NewScanner(reader)
	// Increase buffer for large messages
	scanner.Buffer(make([]byte, 64*1024), 1024*1024)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}

		var msg Message
		if err := json.Unmarshal(line, &msg); err != nil {
			log.Printf("Failed to parse JSON line: %v", err)
			continue
		}

		messages <- &msg
	}

	if err := scanner.Err(); err != nil && err != io.EOF {
		log.Printf("Scanner error: %v", err)
	}
}

func (p *Parser) ParseLine(line []byte) (*Message, error) {
	var msg Message
	if err := json.Unmarshal(line, &msg); err != nil {
		return nil, err
	}
	return &msg, nil
}
```

**Step 4: Run tests**

Run:
```bash
go test ./internal/claude/... -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add internal/claude/parser.go internal/claude/parser_test.go
git commit -m "feat: add NDJSON stream parser for Claude output"
```

---

## Task 8: Claude Controller (PTY Management)

**Files:**
- Create: `internal/claude/controller.go`
- Create: `internal/claude/controller_test.go`

**Step 1: Write failing test for controller**

Create `internal/claude/controller_test.go`:

```go
package claude

import (
	"testing"
)

func TestControllerBuildArgs(t *testing.T) {
	ctrl := &Controller{
		workDir:        "/home/user/app",
		maxTurns:       25,
		permissionMode: "acceptEdits",
	}

	args := ctrl.buildArgs("hello world")

	// Should contain required flags
	hasPrompt := false
	hasOutputFormat := false
	hasMaxTurns := false

	for i, arg := range args {
		if arg == "-p" && i+1 < len(args) && args[i+1] == "hello world" {
			hasPrompt = true
		}
		if arg == "--output-format" && i+1 < len(args) && args[i+1] == "stream-json" {
			hasOutputFormat = true
		}
		if arg == "--max-turns" && i+1 < len(args) && args[i+1] == "25" {
			hasMaxTurns = true
		}
	}

	if !hasPrompt {
		t.Error("Args missing -p flag with prompt")
	}
	if !hasOutputFormat {
		t.Error("Args missing --output-format stream-json")
	}
	if !hasMaxTurns {
		t.Error("Args missing --max-turns")
	}
}

func TestControllerBuildArgsWithResume(t *testing.T) {
	ctrl := &Controller{
		workDir:        "/home/user/app",
		sessionID:      "abc123",
		maxTurns:       50,
		permissionMode: "acceptEdits",
	}

	args := ctrl.buildArgs("continue task")

	hasResume := false
	for i, arg := range args {
		if arg == "--resume" && i+1 < len(args) && args[i+1] == "abc123" {
			hasResume = true
		}
	}

	if !hasResume {
		t.Error("Args missing --resume flag when sessionID is set")
	}
}

func TestNewController(t *testing.T) {
	ctrl := NewController("/home/user/app", 50, "acceptEdits")

	if ctrl.workDir != "/home/user/app" {
		t.Errorf("workDir = %s, want /home/user/app", ctrl.workDir)
	}
	if ctrl.maxTurns != 50 {
		t.Errorf("maxTurns = %d, want 50", ctrl.maxTurns)
	}
	if ctrl.Output == nil {
		t.Error("Output channel should be initialized")
	}
}
```

**Step 2: Run test to verify it fails**

Run:
```bash
go test ./internal/claude/... -v -run TestController
```

Expected: FAIL - Controller not defined

**Step 3: Implement controller**

Create `internal/claude/controller.go`:

```go
package claude

import (
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strconv"
	"sync"
	"syscall"

	"github.com/creack/pty"
)

type Controller struct {
	workDir        string
	sessionID      string
	maxTurns       int
	permissionMode string

	cmd    *exec.Cmd
	ptmx   *os.File
	Output chan *Message
	parser *Parser

	mu       sync.Mutex
	running  bool
	cancel   context.CancelFunc
}

func NewController(workDir string, maxTurns int, permissionMode string) *Controller {
	return &Controller{
		workDir:        workDir,
		maxTurns:       maxTurns,
		permissionMode: permissionMode,
		Output:         make(chan *Message, 100),
		parser:         NewParser(),
	}
}

func (c *Controller) SetSessionID(id string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.sessionID = id
}

func (c *Controller) buildArgs(prompt string) []string {
	args := []string{
		"-p", prompt,
		"--output-format", "stream-json",
		"--max-turns", strconv.Itoa(c.maxTurns),
	}

	if c.permissionMode != "" {
		args = append(args, "--permission-mode", c.permissionMode)
	}

	if c.sessionID != "" {
		args = append(args, "--resume", c.sessionID)
	}

	return args
}

func (c *Controller) Start(ctx context.Context, prompt string) error {
	c.mu.Lock()
	if c.running {
		c.mu.Unlock()
		return fmt.Errorf("controller already running")
	}
	c.running = true
	c.mu.Unlock()

	ctx, cancel := context.WithCancel(ctx)
	c.cancel = cancel

	args := c.buildArgs(prompt)
	c.cmd = exec.CommandContext(ctx, "claude", args...)
	c.cmd.Dir = c.workDir

	// Use process group for clean termination
	c.cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	var err error
	c.ptmx, err = pty.Start(c.cmd)
	if err != nil {
		c.mu.Lock()
		c.running = false
		c.mu.Unlock()
		return fmt.Errorf("failed to start PTY: %w", err)
	}

	// Stream output
	go c.streamOutput()

	// Wait for completion
	go func() {
		c.cmd.Wait()
		c.mu.Lock()
		c.running = false
		c.mu.Unlock()
		if c.ptmx != nil {
			c.ptmx.Close()
		}
	}()

	return nil
}

func (c *Controller) streamOutput() {
	defer close(c.Output)

	messages := make(chan *Message, 100)
	go func() {
		c.parser.ParseStream(c.ptmx, messages)
		close(messages)
	}()

	for msg := range messages {
		c.Output <- msg

		// Capture session ID from init message
		if msg.Type == MessageTypeInit && msg.SessionID != "" {
			c.SetSessionID(msg.SessionID)
		}
	}
}

func (c *Controller) SendInput(input string) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.ptmx == nil {
		return fmt.Errorf("PTY not available")
	}

	_, err := io.WriteString(c.ptmx, input+"\n")
	return err
}

func (c *Controller) Stop() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if !c.running {
		return nil
	}

	if c.cancel != nil {
		c.cancel()
	}

	// Graceful termination via SIGTERM to process group
	if c.cmd != nil && c.cmd.Process != nil {
		syscall.Kill(-c.cmd.Process.Pid, syscall.SIGTERM)
	}

	return nil
}

func (c *Controller) ForceStop() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.cmd != nil && c.cmd.Process != nil {
		syscall.Kill(-c.cmd.Process.Pid, syscall.SIGKILL)
	}

	return nil
}

func (c *Controller) IsRunning() bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.running
}

func (c *Controller) GetSessionID() string {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.sessionID
}
```

**Step 4: Add pty dependency and run tests**

Run:
```bash
go get github.com/creack/pty
go test ./internal/claude/... -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add internal/claude/controller.go internal/claude/controller_test.go go.mod go.sum
git commit -m "feat: add Claude controller with PTY subprocess management"
```

---

## Task 9: Telegram Formatter

**Files:**
- Create: `internal/telegram/formatter.go`
- Create: `internal/telegram/formatter_test.go`

**Step 1: Write failing test for formatter**

Create `internal/telegram/formatter_test.go`:

```go
package telegram

import (
	"testing"

	"github.com/user/teleclaude/internal/claude"
)

func TestFormatToolUseRead(t *testing.T) {
	msg := &claude.Message{
		Type:     claude.MessageTypeToolUse,
		ToolName: "Read",
		ToolInput: []byte(`{"file_path":"/src/main.go"}`),
	}

	f := NewFormatter(3800)
	result := f.FormatToolUse(msg)

	expected := "[📁 /src/main.go]"
	if result != expected {
		t.Errorf("FormatToolUse() = %s, want %s", result, expected)
	}
}

func TestFormatToolUseBash(t *testing.T) {
	msg := &claude.Message{
		Type:     claude.MessageTypeToolUse,
		ToolName: "Bash",
		ToolInput: []byte(`{"command":"go build ./..."}`),
	}

	f := NewFormatter(3800)
	result := f.FormatToolUse(msg)

	expected := "[⚡ go build ./...]"
	if result != expected {
		t.Errorf("FormatToolUse() = %s, want %s", result, expected)
	}
}

func TestFormatToolUseBashTruncate(t *testing.T) {
	msg := &claude.Message{
		Type:     claude.MessageTypeToolUse,
		ToolName: "Bash",
		ToolInput: []byte(`{"command":"this is a very long command that should be truncated at forty characters"}`),
	}

	f := NewFormatter(3800)
	result := f.FormatToolUse(msg)

	// Should truncate to 40 chars + ellipsis
	if len(result) > 50 { // icon + space + 40 chars + ...
		t.Errorf("FormatToolUse() too long: %s", result)
	}
	if result[len(result)-3:] != "..." {
		t.Errorf("FormatToolUse() should end with ...: %s", result)
	}
}

func TestFormatToolUseGrep(t *testing.T) {
	msg := &claude.Message{
		Type:     claude.MessageTypeToolUse,
		ToolName: "Grep",
		ToolInput: []byte(`{"pattern":"TODO"}`),
	}

	f := NewFormatter(3800)
	result := f.FormatToolUse(msg)

	expected := "[🔍 TODO]"
	if result != expected {
		t.Errorf("FormatToolUse() = %s, want %s", result, expected)
	}
}

func TestChunkText(t *testing.T) {
	f := NewFormatter(100) // Small chunk size for testing

	text := "This is a test message that is longer than one hundred characters and should be split into multiple chunks for telegram."

	chunks := f.ChunkText(text)

	if len(chunks) < 2 {
		t.Errorf("ChunkText() returned %d chunks, expected >= 2", len(chunks))
	}

	for i, chunk := range chunks {
		if len(chunk) > 100 {
			t.Errorf("Chunk %d exceeds max size: %d", i, len(chunk))
		}
	}
}

func TestEscapeMarkdown(t *testing.T) {
	f := NewFormatter(3800)

	tests := []struct {
		input    string
		expected string
	}{
		{"hello_world", "hello\\_world"},
		{"*bold*", "\\*bold\\*"},
		{"[link](url)", "\\[link\\]\\(url\\)"},
		{"`code`", "\\`code\\`"},
	}

	for _, tt := range tests {
		result := f.EscapeMarkdown(tt.input)
		if result != tt.expected {
			t.Errorf("EscapeMarkdown(%s) = %s, want %s", tt.input, result, tt.expected)
		}
	}
}
```

**Step 2: Run test to verify it fails**

Run:
```bash
go test ./internal/telegram/... -v
```

Expected: FAIL - package does not exist

**Step 3: Implement formatter**

Create `internal/telegram/formatter.go`:

```go
package telegram

import (
	"encoding/json"
	"strings"

	"github.com/user/teleclaude/internal/claude"
)

type Formatter struct {
	chunkSize int
}

func NewFormatter(chunkSize int) *Formatter {
	return &Formatter{chunkSize: chunkSize}
}

var toolIcons = map[string]string{
	"Read":     "📁",
	"Write":    "📝",
	"Edit":     "📝",
	"Bash":     "⚡",
	"Grep":     "🔍",
	"Glob":     "🔍",
	"WebFetch": "🌐",
}

func (f *Formatter) FormatToolUse(msg *claude.Message) string {
	icon := toolIcons[msg.ToolName]
	if icon == "" {
		icon = "🔧"
	}

	var detail string

	switch msg.ToolName {
	case "Read":
		var input claude.ReadInput
		if err := json.Unmarshal(msg.ToolInput, &input); err == nil {
			detail = input.FilePath
		}
	case "Write", "Edit":
		var input struct {
			FilePath string `json:"file_path"`
		}
		if err := json.Unmarshal(msg.ToolInput, &input); err == nil {
			detail = input.FilePath
		}
	case "Bash":
		var input claude.BashInput
		if err := json.Unmarshal(msg.ToolInput, &input); err == nil {
			detail = truncate(input.Command, 40)
		}
	case "Grep", "Glob":
		var input struct {
			Pattern string `json:"pattern"`
		}
		if err := json.Unmarshal(msg.ToolInput, &input); err == nil {
			detail = input.Pattern
		}
	case "WebFetch":
		var input struct {
			URL string `json:"url"`
		}
		if err := json.Unmarshal(msg.ToolInput, &input); err == nil {
			// Extract domain
			detail = extractDomain(input.URL)
		}
	default:
		detail = msg.ToolName
	}

	return "[" + icon + " " + detail + "]"
}

func (f *Formatter) FormatApprovalRequest(toolName, reason, command string) string {
	var sb strings.Builder
	sb.WriteString("🔒 Approval needed\n\n")
	sb.WriteString("Claude wants to: ")
	sb.WriteString(reason)
	sb.WriteString("\n")
	sb.WriteString("Command: `")
	sb.WriteString(command)
	sb.WriteString("`")
	return sb.String()
}

func (f *Formatter) ChunkText(text string) []string {
	if len(text) <= f.chunkSize {
		return []string{text}
	}

	var chunks []string
	for len(text) > 0 {
		end := f.chunkSize
		if end > len(text) {
			end = len(text)
		}

		// Try to break at newline or space
		if end < len(text) {
			for i := end - 1; i > end-200 && i > 0; i-- {
				if text[i] == '\n' || text[i] == ' ' {
					end = i + 1
					break
				}
			}
		}

		chunks = append(chunks, text[:end])
		text = text[end:]
	}

	return chunks
}

func (f *Formatter) EscapeMarkdown(text string) string {
	replacer := strings.NewReplacer(
		"_", "\\_",
		"*", "\\*",
		"[", "\\[",
		"]", "\\]",
		"(", "\\(",
		")", "\\)",
		"~", "\\~",
		"`", "\\`",
		">", "\\>",
		"#", "\\#",
		"+", "\\+",
		"-", "\\-",
		"=", "\\=",
		"|", "\\|",
		"{", "\\{",
		"}", "\\}",
		".", "\\.",
		"!", "\\!",
	)
	return replacer.Replace(text)
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}

func extractDomain(url string) string {
	// Simple domain extraction
	url = strings.TrimPrefix(url, "https://")
	url = strings.TrimPrefix(url, "http://")
	if idx := strings.Index(url, "/"); idx > 0 {
		url = url[:idx]
	}
	return url
}
```

**Step 4: Run tests**

Run:
```bash
go test ./internal/telegram/... -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add internal/telegram/formatter.go internal/telegram/formatter_test.go
git commit -m "feat: add Telegram formatter with inline tool annotations"
```

---

## Task 10: Telegram Keyboards

**Files:**
- Create: `internal/telegram/keyboards.go`
- Create: `internal/telegram/keyboards_test.go`

**Step 1: Write failing test for keyboards**

Create `internal/telegram/keyboards_test.go`:

```go
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
```

**Step 2: Run test to verify it fails**

Run:
```bash
go test ./internal/telegram/... -v -run TestKeyboard
```

Expected: FAIL - NewKeyboardBuilder not defined

**Step 3: Add telebot dependency**

Run:
```bash
go get gopkg.in/telebot.v4
```

**Step 4: Implement keyboards**

Create `internal/telegram/keyboards.go`:

```go
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
```

**Step 5: Run tests**

Run:
```bash
go test ./internal/telegram/... -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add internal/telegram/keyboards.go internal/telegram/keyboards_test.go go.mod go.sum
git commit -m "feat: add Telegram inline keyboard builders"
```

---

## Task 11: Approval Rules

**Files:**
- Create: `internal/approval/rules.go`
- Create: `internal/approval/rules_test.go`

**Step 1: Write failing test for approval rules**

Create `internal/approval/rules_test.go`:

```go
package approval

import (
	"testing"

	"github.com/user/teleclaude/internal/claude"
)

func TestRequiresApprovalBash(t *testing.T) {
	rules := NewRules([]string{"Bash", "delete", "git push"})

	msg := &claude.Message{
		Type:     claude.MessageTypeToolUse,
		ToolName: "Bash",
		ToolInput: []byte(`{"command":"ls -la"}`),
	}

	if !rules.RequiresApproval(msg) {
		t.Error("Bash should require approval")
	}
}

func TestRequiresApprovalRead(t *testing.T) {
	rules := NewRules([]string{"Bash", "delete", "git push"})

	msg := &claude.Message{
		Type:     claude.MessageTypeToolUse,
		ToolName: "Read",
		ToolInput: []byte(`{"file_path":"/src/main.go"}`),
	}

	if rules.RequiresApproval(msg) {
		t.Error("Read should not require approval")
	}
}

func TestRequiresApprovalGitPush(t *testing.T) {
	rules := NewRules([]string{"Bash", "delete", "git push", "git force"})

	// git push command
	msg := &claude.Message{
		Type:     claude.MessageTypeToolUse,
		ToolName: "Bash",
		ToolInput: []byte(`{"command":"git push origin main"}`),
	}

	if !rules.RequiresApproval(msg) {
		t.Error("git push should require approval")
	}
}

func TestRequiresApprovalDelete(t *testing.T) {
	rules := NewRules([]string{"Bash", "delete"})

	// rm command
	msg := &claude.Message{
		Type:     claude.MessageTypeToolUse,
		ToolName: "Bash",
		ToolInput: []byte(`{"command":"rm -rf ./build"}`),
	}

	if !rules.RequiresApproval(msg) {
		t.Error("rm command should require approval")
	}
}

func TestExtractReason(t *testing.T) {
	rules := NewRules([]string{"Bash"})

	msg := &claude.Message{
		Type:     claude.MessageTypeToolUse,
		ToolName: "Bash",
		ToolInput: []byte(`{"command":"go build ./...","description":"Build the project"}`),
	}

	reason := rules.ExtractReason(msg)
	if reason != "Build the project" {
		t.Errorf("ExtractReason() = %s, want 'Build the project'", reason)
	}
}

func TestExtractCommand(t *testing.T) {
	rules := NewRules([]string{"Bash"})

	msg := &claude.Message{
		Type:     claude.MessageTypeToolUse,
		ToolName: "Bash",
		ToolInput: []byte(`{"command":"go test ./..."}`),
	}

	cmd := rules.ExtractCommand(msg)
	if cmd != "go test ./..." {
		t.Errorf("ExtractCommand() = %s, want 'go test ./...'", cmd)
	}
}
```

**Step 2: Run test to verify it fails**

Run:
```bash
go test ./internal/approval/... -v
```

Expected: FAIL - package does not exist

**Step 3: Implement approval rules**

Create `internal/approval/rules.go`:

```go
package approval

import (
	"encoding/json"
	"strings"

	"github.com/user/teleclaude/internal/claude"
)

type Rules struct {
	requireFor []string
}

func NewRules(requireFor []string) *Rules {
	return &Rules{requireFor: requireFor}
}

func (r *Rules) RequiresApproval(msg *claude.Message) bool {
	if msg.Type != claude.MessageTypeToolUse {
		return false
	}

	// Check if tool itself requires approval
	for _, rule := range r.requireFor {
		if strings.EqualFold(msg.ToolName, rule) {
			return true
		}
	}

	// For Bash commands, check for dangerous patterns
	if msg.ToolName == "Bash" {
		var input claude.BashInput
		if err := json.Unmarshal(msg.ToolInput, &input); err == nil {
			return r.isDangerousCommand(input.Command)
		}
	}

	return false
}

func (r *Rules) isDangerousCommand(cmd string) bool {
	cmd = strings.ToLower(cmd)

	dangerousPatterns := []string{
		"rm ",
		"rm\t",
		"rmdir",
		"git push",
		"git force",
		"--force",
		"-f ",
		"sudo ",
		"chmod ",
		"chown ",
		"> /",     // Redirect to root
		"| sudo",
		"dd ",
		"mkfs",
		"fdisk",
		"format",
	}

	for _, pattern := range dangerousPatterns {
		if strings.Contains(cmd, pattern) {
			return true
		}
	}

	// Also check configured patterns
	for _, rule := range r.requireFor {
		if strings.Contains(cmd, strings.ToLower(rule)) {
			return true
		}
	}

	return false
}

func (r *Rules) ExtractReason(msg *claude.Message) string {
	if msg.ToolName == "Bash" {
		var input struct {
			Command     string `json:"command"`
			Description string `json:"description"`
		}
		if err := json.Unmarshal(msg.ToolInput, &input); err == nil {
			if input.Description != "" {
				return input.Description
			}
			// Generate a generic reason based on command
			return describeCommand(input.Command)
		}
	}
	return "Execute " + msg.ToolName + " operation"
}

func (r *Rules) ExtractCommand(msg *claude.Message) string {
	if msg.ToolName == "Bash" {
		var input claude.BashInput
		if err := json.Unmarshal(msg.ToolInput, &input); err == nil {
			return input.Command
		}
	}
	return string(msg.ToolInput)
}

func describeCommand(cmd string) string {
	cmd = strings.TrimSpace(cmd)
	parts := strings.Fields(cmd)
	if len(parts) == 0 {
		return "Run shell command"
	}

	switch parts[0] {
	case "rm", "rmdir":
		return "Delete files/directories"
	case "git":
		if len(parts) > 1 {
			return "Git " + parts[1] + " operation"
		}
		return "Git operation"
	case "go":
		if len(parts) > 1 {
			return "Go " + parts[1]
		}
		return "Go command"
	case "npm", "yarn", "pnpm":
		if len(parts) > 1 {
			return parts[0] + " " + parts[1]
		}
		return parts[0] + " command"
	default:
		return "Run: " + truncate(cmd, 30)
	}
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}
```

**Step 4: Run tests**

Run:
```bash
go test ./internal/approval/... -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add internal/approval/rules.go internal/approval/rules_test.go
git commit -m "feat: add approval rules for dangerous operations"
```

---

## Task 12: Approval Workflow

**Files:**
- Create: `internal/approval/workflow.go`
- Create: `internal/approval/workflow_test.go`

**Step 1: Write failing test for workflow**

Create `internal/approval/workflow_test.go`:

```go
package approval

import (
	"context"
	"testing"
	"time"
)

func TestWorkflowRequestAndApprove(t *testing.T) {
	wf := NewWorkflow(5 * time.Second)

	reqID := wf.CreateRequest("sess123", "Bash", "Run tests", "go test ./...")

	if reqID == "" {
		t.Fatal("CreateRequest() returned empty ID")
	}

	// Approve in background
	go func() {
		time.Sleep(10 * time.Millisecond)
		wf.Approve(reqID)
	}()

	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()

	approved, err := wf.WaitForDecision(ctx, reqID)
	if err != nil {
		t.Fatalf("WaitForDecision() error = %v", err)
	}
	if !approved {
		t.Error("WaitForDecision() = false, want true")
	}
}

func TestWorkflowRequestAndDeny(t *testing.T) {
	wf := NewWorkflow(5 * time.Second)

	reqID := wf.CreateRequest("sess123", "Bash", "Delete files", "rm -rf /tmp/test")

	go func() {
		time.Sleep(10 * time.Millisecond)
		wf.Deny(reqID)
	}()

	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()

	approved, err := wf.WaitForDecision(ctx, reqID)
	if err != nil {
		t.Fatalf("WaitForDecision() error = %v", err)
	}
	if approved {
		t.Error("WaitForDecision() = true, want false")
	}
}

func TestWorkflowTimeout(t *testing.T) {
	wf := NewWorkflow(50 * time.Millisecond) // Short timeout

	reqID := wf.CreateRequest("sess123", "Bash", "Test", "echo test")

	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	approved, err := wf.WaitForDecision(ctx, reqID)
	if err == nil {
		t.Error("WaitForDecision() should return error on timeout")
	}
	if approved {
		t.Error("WaitForDecision() should return false on timeout")
	}
}

func TestWorkflowGetPendingRequest(t *testing.T) {
	wf := NewWorkflow(5 * time.Second)

	reqID := wf.CreateRequest("sess123", "Bash", "Test reason", "echo test")

	req := wf.GetRequest(reqID)
	if req == nil {
		t.Fatal("GetRequest() returned nil")
	}

	if req.SessionID != "sess123" {
		t.Errorf("SessionID = %s, want sess123", req.SessionID)
	}
	if req.Reason != "Test reason" {
		t.Errorf("Reason = %s, want 'Test reason'", req.Reason)
	}
	if req.Command != "echo test" {
		t.Errorf("Command = %s, want 'echo test'", req.Command)
	}
}
```

**Step 2: Run test to verify it fails**

Run:
```bash
go test ./internal/approval/... -v -run TestWorkflow
```

Expected: FAIL - NewWorkflow not defined

**Step 3: Implement workflow**

Create `internal/approval/workflow.go`:

```go
package approval

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"sync"
	"time"
)

type Request struct {
	ID        string
	SessionID string
	ToolName  string
	Reason    string
	Command   string
	CreatedAt time.Time
	decision  chan bool
}

type Workflow struct {
	timeout  time.Duration
	requests map[string]*Request
	mu       sync.RWMutex
}

func NewWorkflow(timeout time.Duration) *Workflow {
	return &Workflow{
		timeout:  timeout,
		requests: make(map[string]*Request),
	}
}

func (w *Workflow) CreateRequest(sessionID, toolName, reason, command string) string {
	id := generateRequestID()

	req := &Request{
		ID:        id,
		SessionID: sessionID,
		ToolName:  toolName,
		Reason:    reason,
		Command:   command,
		CreatedAt: time.Now(),
		decision:  make(chan bool, 1),
	}

	w.mu.Lock()
	w.requests[id] = req
	w.mu.Unlock()

	// Auto-cleanup after timeout
	go func() {
		time.Sleep(w.timeout + time.Second)
		w.cleanup(id)
	}()

	return id
}

func (w *Workflow) GetRequest(id string) *Request {
	w.mu.RLock()
	defer w.mu.RUnlock()
	return w.requests[id]
}

func (w *Workflow) Approve(id string) {
	w.mu.RLock()
	req := w.requests[id]
	w.mu.RUnlock()

	if req != nil {
		select {
		case req.decision <- true:
		default:
		}
	}
}

func (w *Workflow) Deny(id string) {
	w.mu.RLock()
	req := w.requests[id]
	w.mu.RUnlock()

	if req != nil {
		select {
		case req.decision <- false:
		default:
		}
	}
}

func (w *Workflow) WaitForDecision(ctx context.Context, id string) (bool, error) {
	w.mu.RLock()
	req := w.requests[id]
	w.mu.RUnlock()

	if req == nil {
		return false, context.DeadlineExceeded
	}

	timeoutCtx, cancel := context.WithTimeout(ctx, w.timeout)
	defer cancel()

	select {
	case approved := <-req.decision:
		w.cleanup(id)
		return approved, nil
	case <-timeoutCtx.Done():
		w.cleanup(id)
		return false, timeoutCtx.Err()
	}
}

func (w *Workflow) cleanup(id string) {
	w.mu.Lock()
	delete(w.requests, id)
	w.mu.Unlock()
}

func (w *Workflow) GetPendingForSession(sessionID string) []*Request {
	w.mu.RLock()
	defer w.mu.RUnlock()

	var pending []*Request
	for _, req := range w.requests {
		if req.SessionID == sessionID {
			pending = append(pending, req)
		}
	}
	return pending
}

func (w *Workflow) DenyAllForSession(sessionID string) {
	w.mu.RLock()
	var toCancel []string
	for id, req := range w.requests {
		if req.SessionID == sessionID {
			toCancel = append(toCancel, id)
		}
	}
	w.mu.RUnlock()

	for _, id := range toCancel {
		w.Deny(id)
	}
}

func generateRequestID() string {
	b := make([]byte, 8)
	rand.Read(b)
	return hex.EncodeToString(b)
}
```

**Step 4: Run tests**

Run:
```bash
go test ./internal/approval/... -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add internal/approval/workflow.go internal/approval/workflow_test.go
git commit -m "feat: add approval workflow with async decision handling"
```

---

## Task 13: Telegram Bot Core

**Files:**
- Create: `internal/telegram/bot.go`
- Create: `internal/telegram/bot_test.go`

**Step 1: Write test for bot initialization**

Create `internal/telegram/bot_test.go`:

```go
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
```

**Step 2: Run test**

Run:
```bash
go test ./internal/telegram/... -v -run TestBot
```

Expected: FAIL - NewBot not defined

**Step 3: Implement bot core**

Create `internal/telegram/bot.go`:

```go
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
```

**Step 4: Run tests**

Run:
```bash
go test ./internal/telegram/... -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add internal/telegram/bot.go internal/telegram/bot_test.go
git commit -m "feat: add Telegram bot core with auth and streaming"
```

---

## Task 14: Telegram Command Handlers

**Files:**
- Modify: `internal/telegram/bot.go` (add handlers)
- Create: `internal/telegram/handlers.go`

**Step 1: Create handlers file**

Create `internal/telegram/handlers.go`:

```go
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
```

**Step 2: Run tests**

Run:
```bash
go test ./internal/telegram/... -v
```

Expected: All tests PASS

**Step 3: Commit**

```bash
git add internal/telegram/handlers.go
git commit -m "feat: add Telegram command handlers"
```

---

## Task 15: Main Entry Point

**Files:**
- Modify: `cmd/teleclaude/main.go`

**Step 1: Implement full main**

Update `cmd/teleclaude/main.go`:

```go
package main

import (
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/user/teleclaude/internal/approval"
	"github.com/user/teleclaude/internal/config"
	"github.com/user/teleclaude/internal/session"
	"github.com/user/teleclaude/internal/telegram"
)

func main() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	// Get token from env
	token := os.Getenv("TELEGRAM_BOT_TOKEN")
	if token == "" {
		log.Fatal("TELEGRAM_BOT_TOKEN environment variable required")
	}

	// Determine config path
	configPath := os.Getenv("TELECLAUDE_CONFIG")
	if configPath == "" {
		home, _ := os.UserHomeDir()
		configPath = filepath.Join(home, ".teleclaude", "config.yaml")
	}

	// Load config
	cfg, err := config.Load(configPath)
	if err != nil {
		log.Fatalf("Failed to load config from %s: %v", configPath, err)
	}

	if len(cfg.AllowedUsers) == 0 {
		log.Fatal("No allowed users configured. Add your Telegram user ID to config.")
	}

	// Initialize components
	home, _ := os.UserHomeDir()
	dataDir := filepath.Join(home, ".teleclaude")

	storage := session.NewStorage(dataDir)
	sessionMgr := session.NewManager(storage)
	approvalWf := approval.NewWorkflow(5 * time.Minute)
	formatter := telegram.NewFormatter(cfg.Streaming.ChunkSize)

	// Create bot
	bot, err := telegram.NewBot(token, cfg, sessionMgr, approvalWf, formatter)
	if err != nil {
		log.Fatalf("Failed to create bot: %v", err)
	}

	// Handle shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigChan
		log.Println("Shutdown signal received")
		sessionMgr.MarkAllIdle()
		bot.Stop()
		os.Exit(0)
	}()

	// Start bot
	log.Printf("TeleClaude starting with %d allowed users", len(cfg.AllowedUsers))
	bot.Start()
}
```

**Step 2: Build and verify**

Run:
```bash
go build ./cmd/teleclaude
```

Expected: Binary builds successfully

**Step 3: Commit**

```bash
git add cmd/teleclaude/main.go
git commit -m "feat: implement main entry point with graceful shutdown"
```

---

## Task 16: Integration Test

**Files:**
- Create: `test/integration_test.go`

**Step 1: Create integration test**

Create `test/integration_test.go`:

```go
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
```

**Step 2: Run integration test (requires token)**

Run:
```bash
go test ./test/... -v -tags=integration
```

Expected: SKIP if no token, PASS if token provided

**Step 3: Commit**

```bash
git add test/integration_test.go
git commit -m "feat: add integration test for bot initialization"
```

---

## Task 17: ANSI Cleaning

**Files:**
- Modify: `internal/claude/controller.go`

**Step 1: Add ANSI cleaning**

Add to imports in `internal/claude/controller.go`:

```go
import (
	// ... existing imports
	ansi "github.com/leaanthony/go-ansi-parser"
)
```

Add method:

```go
func cleanANSI(text string) string {
	cleaned, err := ansi.Cleanse(text)
	if err != nil {
		return text
	}
	return cleaned
}
```

Modify `streamOutput` to clean ANSI codes before parsing.

**Step 2: Add dependency**

Run:
```bash
go get github.com/leaanthony/go-ansi-parser
```

**Step 3: Run tests**

Run:
```bash
go test ./internal/claude/... -v
```

Expected: All tests PASS

**Step 4: Commit**

```bash
git add internal/claude/controller.go go.mod go.sum
git commit -m "feat: add ANSI escape code cleaning for Claude output"
```

---

## Task 18: Final Build and Documentation

**Files:**
- Create: `README.md`
- Create: `Makefile`

**Step 1: Create README**

Create `README.md`:

```markdown
# TeleClaude

A Telegram bot for interacting with Claude Code from your mobile device.

## Features

- Real-time streaming of Claude responses
- Session management with resume support
- Category-based approval for dangerous operations
- Cost tracking per session
- Multi-project support

## Installation

```bash
go install github.com/user/teleclaude/cmd/teleclaude@latest
```

## Configuration

Create `~/.teleclaude/config.yaml`:

```yaml
allowed_users:
  - YOUR_TELEGRAM_USER_ID

projects:
  myapp: /path/to/project

claude:
  max_turns: 50
  permission_mode: "acceptEdits"

approval:
  require_for:
    - "Bash"
    - "delete"
    - "git push"
```

## Usage

1. Set your Telegram bot token:
   ```bash
   export TELEGRAM_BOT_TOKEN=your_token_here
   ```

2. Run the bot:
   ```bash
   teleclaude
   ```

3. In Telegram:
   - `/new` - Start a new session
   - `/continue` - Resume last session
   - Send any message to chat with Claude

## Commands

- `/start` - Welcome message
- `/new [project]` - Start new session
- `/continue` - Resume last session
- `/sessions` - List all sessions
- `/switch <id>` - Switch to session
- `/cost` - Show costs
- `/cancel` - Stop current operation
- `/help` - Show help

## License

MIT
```

**Step 2: Create Makefile**

Create `Makefile`:

```makefile
.PHONY: build test clean install

build:
	go build -o bin/teleclaude ./cmd/teleclaude

test:
	go test ./... -v

test-coverage:
	go test ./... -coverprofile=coverage.out
	go tool cover -html=coverage.out -o coverage.html

clean:
	rm -rf bin/ coverage.out coverage.html

install:
	go install ./cmd/teleclaude

lint:
	golangci-lint run

run:
	go run ./cmd/teleclaude
```

**Step 3: Final build test**

Run:
```bash
make build
make test
```

Expected: Build succeeds, all tests pass

**Step 4: Commit**

```bash
git add README.md Makefile
git commit -m "docs: add README and Makefile"
```

---

## Summary

This plan implements TeleClaude in 18 tasks:

1. **Project scaffolding** - go.mod, main.go, config.example.yaml
2. **Config package** - YAML loading with defaults
3. **Session types** - Session struct with status management
4. **Session storage** - YAML file persistence
5. **Session manager** - Active session tracking, CRUD operations
6. **Claude types** - stream-json message definitions
7. **Claude parser** - NDJSON streaming parser
8. **Claude controller** - PTY process management
9. **Telegram formatter** - Inline annotations, chunking
10. **Telegram keyboards** - Inline keyboard builders
11. **Approval rules** - Dangerous operation detection
12. **Approval workflow** - Async decision handling
13. **Telegram bot core** - Bot setup, auth, streaming
14. **Command handlers** - /new, /sessions, /cost, etc.
15. **Main entry point** - Wiring, graceful shutdown
16. **Integration test** - Bot initialization test
17. **ANSI cleaning** - Strip escape codes
18. **Documentation** - README, Makefile

Each task follows TDD: write failing test, implement, verify pass, commit.
