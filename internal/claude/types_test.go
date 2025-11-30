package claude

import (
	"encoding/json"
	"testing"
)

func TestParseInitMessage(t *testing.T) {
	raw := `{"type":"init","session_id":"abc123","cwd":"/home/user"}`

	var msg Message
	if err := json.Unmarshal([]byte(raw), &msg); err != nil {
		t.Fatalf("Unmarshal error = %v", err)
	}

	if msg.Type != MessageTypeInit {
		t.Errorf("Type = %s, want %s", msg.Type, MessageTypeInit)
	}
	if msg.SessionID != "abc123" {
		t.Errorf("SessionID = %s, want abc123", msg.SessionID)
	}
}

func TestParseAssistantMessage(t *testing.T) {
	raw := `{"type":"assistant","message":{"content":[{"type":"text","text":"Hello world"}]}}`

	var msg Message
	if err := json.Unmarshal([]byte(raw), &msg); err != nil {
		t.Fatalf("Unmarshal error = %v", err)
	}

	if msg.Type != MessageTypeAssistant {
		t.Errorf("Type = %s, want %s", msg.Type, MessageTypeAssistant)
	}
}

func TestParseToolUseMessage(t *testing.T) {
	raw := `{"type":"tool_use","id":"toolu_123","name":"Read","input":{"file_path":"/src/main.go"}}`

	var msg Message
	if err := json.Unmarshal([]byte(raw), &msg); err != nil {
		t.Fatalf("Unmarshal error = %v", err)
	}

	if msg.Type != MessageTypeToolUse {
		t.Errorf("Type = %s, want %s", msg.Type, MessageTypeToolUse)
	}
	if msg.ToolName != "Read" {
		t.Errorf("ToolName = %s, want Read", msg.ToolName)
	}
	if msg.ToolID != "toolu_123" {
		t.Errorf("ToolID = %s, want toolu_123", msg.ToolID)
	}
}

func TestParseResultMessage(t *testing.T) {
	raw := `{"type":"result","result":"Done","cost_usd":0.05,"usage":{"input_tokens":100,"output_tokens":200}}`

	var msg Message
	if err := json.Unmarshal([]byte(raw), &msg); err != nil {
		t.Fatalf("Unmarshal error = %v", err)
	}

	if msg.Type != MessageTypeResult {
		t.Errorf("Type = %s, want %s", msg.Type, MessageTypeResult)
	}
	if msg.CostUSD != 0.05 {
		t.Errorf("CostUSD = %f, want 0.05", msg.CostUSD)
	}
	if msg.Result != "Done" {
		t.Errorf("Result = %s, want Done", msg.Result)
	}
}
