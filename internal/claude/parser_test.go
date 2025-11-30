package claude

import (
	"strings"
	"testing"
)

func TestParserParseStream(t *testing.T) {
	input := `{"type":"init","session_id":"abc123"}
{"type":"assistant","message":{"content":[{"type":"text","text":"Hello"}]}}
{"type":"result","result":"Done","cost_usd":0.05}
`

	parser := NewParser()
	reader := strings.NewReader(input)
	messages := make(chan *Message, 10)

	go func() {
		parser.ParseStream(reader, messages)
		close(messages)
	}()

	var received []*Message
	for msg := range messages {
		received = append(received, msg)
	}

	if len(received) != 3 {
		t.Fatalf("Received %d messages, want 3", len(received))
	}

	if received[0].Type != MessageTypeInit {
		t.Errorf("Message 0 type = %s, want init", received[0].Type)
	}
	if received[0].SessionID != "abc123" {
		t.Errorf("Message 0 session_id = %s, want abc123", received[0].SessionID)
	}

	if received[1].Type != MessageTypeAssistant {
		t.Errorf("Message 1 type = %s, want assistant", received[1].Type)
	}

	if received[2].Type != MessageTypeResult {
		t.Errorf("Message 2 type = %s, want result", received[2].Type)
	}
	if received[2].CostUSD != 0.05 {
		t.Errorf("Message 2 cost_usd = %f, want 0.05", received[2].CostUSD)
	}
}

func TestParserSkipInvalidLines(t *testing.T) {
	input := `{"type":"init","session_id":"abc"}
not json at all
{"type":"result","result":"Done"}
`

	parser := NewParser()
	reader := strings.NewReader(input)
	messages := make(chan *Message, 10)

	go func() {
		parser.ParseStream(reader, messages)
		close(messages)
	}()

	var received []*Message
	for msg := range messages {
		received = append(received, msg)
	}

	// Should skip invalid line and continue
	if len(received) != 2 {
		t.Fatalf("Received %d messages, want 2 (skipping invalid)", len(received))
	}
}
