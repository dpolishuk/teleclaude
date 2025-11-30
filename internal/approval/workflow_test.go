package approval

import (
	"context"
	"testing"
	"time"
)

func TestWorkflowRequestAndApprove(t *testing.T) {
	wf := NewWorkflow(5 * time.Second)

	reqID := wf.CreateRequest("sess123", "Bash", "Run tests", "go test ./...")

	if reqID == "" {
		t.Fatal("CreateRequest() returned empty ID")
	}

	// Approve in background
	go func() {
		time.Sleep(10 * time.Millisecond)
		wf.Approve(reqID)
	}()

	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()

	approved, err := wf.WaitForDecision(ctx, reqID)
	if err != nil {
		t.Fatalf("WaitForDecision() error = %v", err)
	}
	if !approved {
		t.Error("WaitForDecision() = false, want true")
	}
}

func TestWorkflowRequestAndDeny(t *testing.T) {
	wf := NewWorkflow(5 * time.Second)

	reqID := wf.CreateRequest("sess123", "Bash", "Delete files", "rm -rf /tmp/test")

	go func() {
		time.Sleep(10 * time.Millisecond)
		wf.Deny(reqID)
	}()

	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()

	approved, err := wf.WaitForDecision(ctx, reqID)
	if err != nil {
		t.Fatalf("WaitForDecision() error = %v", err)
	}
	if approved {
		t.Error("WaitForDecision() = true, want false")
	}
}

func TestWorkflowTimeout(t *testing.T) {
	wf := NewWorkflow(50 * time.Millisecond) // Short timeout

	reqID := wf.CreateRequest("sess123", "Bash", "Test", "echo test")

	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	approved, err := wf.WaitForDecision(ctx, reqID)
	if err == nil {
		t.Error("WaitForDecision() should return error on timeout")
	}
	if approved {
		t.Error("WaitForDecision() should return false on timeout")
	}
}

func TestWorkflowGetPendingRequest(t *testing.T) {
	wf := NewWorkflow(5 * time.Second)

	reqID := wf.CreateRequest("sess123", "Bash", "Test reason", "echo test")

	req := wf.GetRequest(reqID)
	if req == nil {
		t.Fatal("GetRequest() returned nil")
	}

	if req.SessionID != "sess123" {
		t.Errorf("SessionID = %s, want sess123", req.SessionID)
	}
	if req.Reason != "Test reason" {
		t.Errorf("Reason = %s, want 'Test reason'", req.Reason)
	}
	if req.Command != "echo test" {
		t.Errorf("Command = %s, want 'echo test'", req.Command)
	}
}
