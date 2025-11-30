package telegram

import (
	"testing"

	"github.com/user/teleclaude/internal/claude"
)

func TestFormatToolUseRead(t *testing.T) {
	msg := &claude.Message{
		Type:      claude.MessageTypeToolUse,
		ToolName:  "Read",
		ToolInput: []byte(`{"file_path":"/src/main.go"}`),
	}

	f := NewFormatter(3800)
	result := f.FormatToolUse(msg)

	expected := "[📁 /src/main.go]"
	if result != expected {
		t.Errorf("FormatToolUse() = %s, want %s", result, expected)
	}
}

func TestFormatToolUseBash(t *testing.T) {
	msg := &claude.Message{
		Type:      claude.MessageTypeToolUse,
		ToolName:  "Bash",
		ToolInput: []byte(`{"command":"go build ./..."}`),
	}

	f := NewFormatter(3800)
	result := f.FormatToolUse(msg)

	expected := "[⚡ go build ./...]"
	if result != expected {
		t.Errorf("FormatToolUse() = %s, want %s", result, expected)
	}
}

func TestFormatToolUseBashTruncate(t *testing.T) {
	msg := &claude.Message{
		Type:      claude.MessageTypeToolUse,
		ToolName:  "Bash",
		ToolInput: []byte(`{"command":"this is a very long command that should be truncated at forty characters"}`),
	}

	f := NewFormatter(3800)
	result := f.FormatToolUse(msg)

	// Should truncate to 40 chars + ellipsis
	if len(result) > 50 { // icon + space + 40 chars + ...
		t.Errorf("FormatToolUse() too long: %s", result)
	}
	if result[len(result)-3:] != "..." {
		t.Errorf("FormatToolUse() should end with ...: %s", result)
	}
}

func TestFormatToolUseGrep(t *testing.T) {
	msg := &claude.Message{
		Type:      claude.MessageTypeToolUse,
		ToolName:  "Grep",
		ToolInput: []byte(`{"pattern":"TODO"}`),
	}

	f := NewFormatter(3800)
	result := f.FormatToolUse(msg)

	expected := "[🔍 TODO]"
	if result != expected {
		t.Errorf("FormatToolUse() = %s, want %s", result, expected)
	}
}

func TestChunkText(t *testing.T) {
	f := NewFormatter(100) // Small chunk size for testing

	text := "This is a test message that is longer than one hundred characters and should be split into multiple chunks for telegram."

	chunks := f.ChunkText(text)

	if len(chunks) < 2 {
		t.Errorf("ChunkText() returned %d chunks, expected >= 2", len(chunks))
	}

	for i, chunk := range chunks {
		if len(chunk) > 100 {
			t.Errorf("Chunk %d exceeds max size: %d", i, len(chunk))
		}
	}
}

func TestEscapeMarkdown(t *testing.T) {
	f := NewFormatter(3800)

	tests := []struct {
		input    string
		expected string
	}{
		{"hello_world", "hello\\_world"},
		{"*bold*", "\\*bold\\*"},
		{"[link](url)", "\\[link\\]\\(url\\)"},
		{"`code`", "\\`code\\`"},
	}

	for _, tt := range tests {
		result := f.EscapeMarkdown(tt.input)
		if result != tt.expected {
			t.Errorf("EscapeMarkdown(%s) = %s, want %s", tt.input, result, tt.expected)
		}
	}
}
