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
