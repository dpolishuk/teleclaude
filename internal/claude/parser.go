package claude

import (
	"bufio"
	"encoding/json"
	"io"
	"log"
)

type Parser struct{}

func NewParser() *Parser {
	return &Parser{}
}

func (p *Parser) ParseStream(reader io.Reader, messages chan<- *Message) {
	scanner := bufio.NewScanner(reader)
	// Increase buffer for large messages
	scanner.Buffer(make([]byte, 64*1024), 1024*1024)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}

		var msg Message
		if err := json.Unmarshal(line, &msg); err != nil {
			log.Printf("Failed to parse JSON line: %v", err)
			continue
		}

		messages <- &msg
	}

	if err := scanner.Err(); err != nil && err != io.EOF {
		log.Printf("Scanner error: %v", err)
	}
}

func (p *Parser) ParseLine(line []byte) (*Message, error) {
	var msg Message
	if err := json.Unmarshal(line, &msg); err != nil {
		return nil, err
	}
	return &msg, nil
}
