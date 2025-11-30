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
