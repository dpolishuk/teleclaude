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
