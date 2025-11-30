package main

import (
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/user/teleclaude/internal/approval"
	"github.com/user/teleclaude/internal/config"
	"github.com/user/teleclaude/internal/session"
	"github.com/user/teleclaude/internal/telegram"
)

func main() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	// Get token from env
	token := os.Getenv("TELEGRAM_BOT_TOKEN")
	if token == "" {
		log.Fatal("TELEGRAM_BOT_TOKEN environment variable required")
	}

	// Determine config path
	configPath := os.Getenv("TELECLAUDE_CONFIG")
	if configPath == "" {
		home, _ := os.UserHomeDir()
		configPath = filepath.Join(home, ".teleclaude", "config.yaml")
	}

	// Load config
	cfg, err := config.Load(configPath)
	if err != nil {
		log.Fatalf("Failed to load config from %s: %v", configPath, err)
	}

	if len(cfg.AllowedUsers) == 0 {
		log.Fatal("No allowed users configured. Add your Telegram user ID to config.")
	}

	// Initialize components
	home, _ := os.UserHomeDir()
	dataDir := filepath.Join(home, ".teleclaude")

	storage := session.NewStorage(dataDir)
	sessionMgr := session.NewManager(storage)
	approvalWf := approval.NewWorkflow(5 * time.Minute)
	formatter := telegram.NewFormatter(cfg.Streaming.ChunkSize)

	// Create bot
	bot, err := telegram.NewBot(token, cfg, sessionMgr, approvalWf, formatter)
	if err != nil {
		log.Fatalf("Failed to create bot: %v", err)
	}

	// Handle shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigChan
		log.Println("Shutdown signal received")
		sessionMgr.MarkAllIdle()
		bot.Stop()
		os.Exit(0)
	}()

	// Start bot
	log.Printf("TeleClaude starting with %d allowed users", len(cfg.AllowedUsers))
	bot.Start()
}
