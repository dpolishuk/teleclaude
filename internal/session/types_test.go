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
