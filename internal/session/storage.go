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
