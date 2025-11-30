package claude

import (
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strconv"
	"sync"
	"syscall"

	"github.com/creack/pty"
)

type Controller struct {
	workDir        string
	sessionID      string
	maxTurns       int
	permissionMode string

	cmd    *exec.Cmd
	ptmx   *os.File
	Output chan *Message
	parser *Parser

	mu      sync.Mutex
	running bool
	cancel  context.CancelFunc
}

func NewController(workDir string, maxTurns int, permissionMode string) *Controller {
	return &Controller{
		workDir:        workDir,
		maxTurns:       maxTurns,
		permissionMode: permissionMode,
		Output:         make(chan *Message, 100),
		parser:         NewParser(),
	}
}

func (c *Controller) SetSessionID(id string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.sessionID = id
}

func (c *Controller) buildArgs(prompt string) []string {
	args := []string{
		"-p", prompt,
		"--output-format", "stream-json",
		"--max-turns", strconv.Itoa(c.maxTurns),
	}

	if c.permissionMode != "" {
		args = append(args, "--permission-mode", c.permissionMode)
	}

	if c.sessionID != "" {
		args = append(args, "--resume", c.sessionID)
	}

	return args
}

func (c *Controller) Start(ctx context.Context, prompt string) error {
	c.mu.Lock()
	if c.running {
		c.mu.Unlock()
		return fmt.Errorf("controller already running")
	}
	c.running = true
	c.mu.Unlock()

	ctx, cancel := context.WithCancel(ctx)
	c.cancel = cancel

	args := c.buildArgs(prompt)
	c.cmd = exec.CommandContext(ctx, "claude", args...)
	c.cmd.Dir = c.workDir

	// Use process group for clean termination
	c.cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	var err error
	c.ptmx, err = pty.Start(c.cmd)
	if err != nil {
		c.mu.Lock()
		c.running = false
		c.mu.Unlock()
		return fmt.Errorf("failed to start PTY: %w", err)
	}

	// Stream output
	go c.streamOutput()

	// Wait for completion
	go func() {
		c.cmd.Wait()
		c.mu.Lock()
		c.running = false
		c.mu.Unlock()
		if c.ptmx != nil {
			c.ptmx.Close()
		}
	}()

	return nil
}

func (c *Controller) streamOutput() {
	defer close(c.Output)

	messages := make(chan *Message, 100)
	go func() {
		c.parser.ParseStream(c.ptmx, messages)
		close(messages)
	}()

	for msg := range messages {
		c.Output <- msg

		// Capture session ID from init message
		if msg.Type == MessageTypeInit && msg.SessionID != "" {
			c.SetSessionID(msg.SessionID)
		}
	}
}

func (c *Controller) SendInput(input string) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.ptmx == nil {
		return fmt.Errorf("PTY not available")
	}

	_, err := io.WriteString(c.ptmx, input+"\n")
	return err
}

func (c *Controller) Stop() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if !c.running {
		return nil
	}

	if c.cancel != nil {
		c.cancel()
	}

	// Graceful termination via SIGTERM to process group
	if c.cmd != nil && c.cmd.Process != nil {
		syscall.Kill(-c.cmd.Process.Pid, syscall.SIGTERM)
	}

	return nil
}

func (c *Controller) ForceStop() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.cmd != nil && c.cmd.Process != nil {
		syscall.Kill(-c.cmd.Process.Pid, syscall.SIGKILL)
	}

	return nil
}

func (c *Controller) IsRunning() bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.running
}

func (c *Controller) GetSessionID() string {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.sessionID
}
