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
