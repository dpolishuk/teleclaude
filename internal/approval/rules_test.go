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
