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
