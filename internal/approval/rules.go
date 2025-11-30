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
