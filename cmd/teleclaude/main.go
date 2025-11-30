package main

import (
	"fmt"
	"os"
)

func main() {
	fmt.Println("TeleClaude starting...")

	token := os.Getenv("TELEGRAM_BOT_TOKEN")
	if token == "" {
		fmt.Fprintln(os.Stderr, "TELEGRAM_BOT_TOKEN environment variable required")
		os.Exit(1)
	}

	fmt.Println("Token found, bot ready to initialize")
}
