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
