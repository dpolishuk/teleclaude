package approval

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"sync"
	"time"
)

type Request struct {
	ID        string
	SessionID string
	ToolName  string
	Reason    string
	Command   string
	CreatedAt time.Time
	decision  chan bool
}

type Workflow struct {
	timeout  time.Duration
	requests map[string]*Request
	mu       sync.RWMutex
}

func NewWorkflow(timeout time.Duration) *Workflow {
	return &Workflow{
		timeout:  timeout,
		requests: make(map[string]*Request),
	}
}

func (w *Workflow) CreateRequest(sessionID, toolName, reason, command string) string {
	id := generateRequestID()

	req := &Request{
		ID:        id,
		SessionID: sessionID,
		ToolName:  toolName,
		Reason:    reason,
		Command:   command,
		CreatedAt: time.Now(),
		decision:  make(chan bool, 1),
	}

	w.mu.Lock()
	w.requests[id] = req
	w.mu.Unlock()

	// Auto-cleanup after timeout
	go func() {
		time.Sleep(w.timeout + time.Second)
		w.cleanup(id)
	}()

	return id
}

func (w *Workflow) GetRequest(id string) *Request {
	w.mu.RLock()
	defer w.mu.RUnlock()
	return w.requests[id]
}

func (w *Workflow) Approve(id string) {
	w.mu.RLock()
	req := w.requests[id]
	w.mu.RUnlock()

	if req != nil {
		select {
		case req.decision <- true:
		default:
		}
	}
}

func (w *Workflow) Deny(id string) {
	w.mu.RLock()
	req := w.requests[id]
	w.mu.RUnlock()

	if req != nil {
		select {
		case req.decision <- false:
		default:
		}
	}
}

func (w *Workflow) WaitForDecision(ctx context.Context, id string) (bool, error) {
	w.mu.RLock()
	req := w.requests[id]
	w.mu.RUnlock()

	if req == nil {
		return false, context.DeadlineExceeded
	}

	timeoutCtx, cancel := context.WithTimeout(ctx, w.timeout)
	defer cancel()

	select {
	case approved := <-req.decision:
		w.cleanup(id)
		return approved, nil
	case <-timeoutCtx.Done():
		w.cleanup(id)
		return false, timeoutCtx.Err()
	}
}

func (w *Workflow) cleanup(id string) {
	w.mu.Lock()
	delete(w.requests, id)
	w.mu.Unlock()
}

func (w *Workflow) GetPendingForSession(sessionID string) []*Request {
	w.mu.RLock()
	defer w.mu.RUnlock()

	var pending []*Request
	for _, req := range w.requests {
		if req.SessionID == sessionID {
			pending = append(pending, req)
		}
	}
	return pending
}

func (w *Workflow) DenyAllForSession(sessionID string) {
	w.mu.RLock()
	var toCancel []string
	for id, req := range w.requests {
		if req.SessionID == sessionID {
			toCancel = append(toCancel, id)
		}
	}
	w.mu.RUnlock()

	for _, id := range toCancel {
		w.Deny(id)
	}
}

func generateRequestID() string {
	b := make([]byte, 8)
	rand.Read(b)
	return hex.EncodeToString(b)
}
