package telegram

import (
	"encoding/json"
	"strings"

	"github.com/user/teleclaude/internal/claude"
)

type Formatter struct {
	chunkSize int
}

func NewFormatter(chunkSize int) *Formatter {
	return &Formatter{chunkSize: chunkSize}
}

var toolIcons = map[string]string{
	"Read":     "📁",
	"Write":    "📝",
	"Edit":     "📝",
	"Bash":     "⚡",
	"Grep":     "🔍",
	"Glob":     "🔍",
	"WebFetch": "🌐",
}

func (f *Formatter) FormatToolUse(msg *claude.Message) string {
	icon := toolIcons[msg.ToolName]
	if icon == "" {
		icon = "🔧"
	}

	var detail string
	var wasTruncated bool

	switch msg.ToolName {
	case "Read":
		var input claude.ReadInput
		if err := json.Unmarshal(msg.ToolInput, &input); err == nil {
			detail = input.FilePath
		}
	case "Write", "Edit":
		var input struct {
			FilePath string `json:"file_path"`
		}
		if err := json.Unmarshal(msg.ToolInput, &input); err == nil {
			detail = input.FilePath
		}
	case "Bash":
		var input claude.BashInput
		if err := json.Unmarshal(msg.ToolInput, &input); err == nil {
			detail, wasTruncated = truncateWithFlag(input.Command, 40)
		}
	case "Grep", "Glob":
		var input struct {
			Pattern string `json:"pattern"`
		}
		if err := json.Unmarshal(msg.ToolInput, &input); err == nil {
			detail = input.Pattern
		}
	case "WebFetch":
		var input struct {
			URL string `json:"url"`
		}
		if err := json.Unmarshal(msg.ToolInput, &input); err == nil {
			// Extract domain
			detail = extractDomain(input.URL)
		}
	default:
		detail = msg.ToolName
	}

	if wasTruncated {
		return "[" + icon + " " + detail
	}
	return "[" + icon + " " + detail + "]"
}

func (f *Formatter) FormatApprovalRequest(toolName, reason, command string) string {
	var sb strings.Builder
	sb.WriteString("🔒 Approval needed\n\n")
	sb.WriteString("Claude wants to: ")
	sb.WriteString(reason)
	sb.WriteString("\n")
	sb.WriteString("Command: `")
	sb.WriteString(command)
	sb.WriteString("`")
	return sb.String()
}

func (f *Formatter) ChunkText(text string) []string {
	if len(text) <= f.chunkSize {
		return []string{text}
	}

	var chunks []string
	for len(text) > 0 {
		end := f.chunkSize
		if end > len(text) {
			end = len(text)
		}

		// Try to break at newline or space
		if end < len(text) {
			for i := end - 1; i > end-200 && i > 0; i-- {
				if text[i] == '\n' || text[i] == ' ' {
					end = i + 1
					break
				}
			}
		}

		chunks = append(chunks, text[:end])
		text = text[end:]
	}

	return chunks
}

func (f *Formatter) EscapeMarkdown(text string) string {
	replacer := strings.NewReplacer(
		"_", "\\_",
		"*", "\\*",
		"[", "\\[",
		"]", "\\]",
		"(", "\\(",
		")", "\\)",
		"~", "\\~",
		"`", "\\`",
		">", "\\>",
		"#", "\\#",
		"+", "\\+",
		"-", "\\-",
		"=", "\\=",
		"|", "\\|",
		"{", "\\{",
		"}", "\\}",
		".", "\\.",
		"!", "\\!",
	)
	return replacer.Replace(text)
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}

func truncateWithFlag(s string, maxLen int) (string, bool) {
	if len(s) <= maxLen {
		return s, false
	}
	return s[:maxLen-3] + "...", true
}

func extractDomain(url string) string {
	// Simple domain extraction
	url = strings.TrimPrefix(url, "https://")
	url = strings.TrimPrefix(url, "http://")
	if idx := strings.Index(url, "/"); idx > 0 {
		url = url[:idx]
	}
	return url
}
