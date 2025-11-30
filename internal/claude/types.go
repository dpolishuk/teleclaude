package claude

import "encoding/json"

type MessageType string

const (
	MessageTypeInit       MessageType = "init"
	MessageTypeAssistant  MessageType = "assistant"
	MessageTypeToolUse    MessageType = "tool_use"
	MessageTypeToolResult MessageType = "tool_result"
	MessageTypeResult     MessageType = "result"
	MessageTypeError      MessageType = "error"
)

type Message struct {
	Type      MessageType     `json:"type"`
	SessionID string          `json:"session_id,omitempty"`
	Message   *AssistantMsg   `json:"message,omitempty"`
	ToolID    string          `json:"id,omitempty"`
	ToolName  string          `json:"name,omitempty"`
	ToolInput json.RawMessage `json:"input,omitempty"`
	Content   string          `json:"content,omitempty"`
	Result    string          `json:"result,omitempty"`
	CostUSD   float64         `json:"cost_usd,omitempty"`
	Usage     *Usage          `json:"usage,omitempty"`
	Error     string          `json:"error,omitempty"`
}

type AssistantMsg struct {
	Content []ContentBlock `json:"content"`
}

type ContentBlock struct {
	Type string `json:"type"`
	Text string `json:"text,omitempty"`
}

type Usage struct {
	InputTokens  int `json:"input_tokens"`
	OutputTokens int `json:"output_tokens"`
}

// ToolInput helpers for common tools

type ReadInput struct {
	FilePath string `json:"file_path"`
}

type WriteInput struct {
	FilePath string `json:"file_path"`
	Content  string `json:"content"`
}

type EditInput struct {
	FilePath  string `json:"file_path"`
	OldString string `json:"old_string"`
	NewString string `json:"new_string"`
}

type BashInput struct {
	Command string `json:"command"`
}

func (m *Message) GetText() string {
	if m.Message == nil {
		return ""
	}
	var text string
	for _, block := range m.Message.Content {
		if block.Type == "text" {
			text += block.Text
		}
	}
	return text
}

func (m *Message) ParseToolInput(v interface{}) error {
	return json.Unmarshal(m.ToolInput, v)
}
