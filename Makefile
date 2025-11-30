.PHONY: build test clean install

build:
	go build -o bin/teleclaude ./cmd/teleclaude

test:
	go test ./... -v

test-coverage:
	go test ./... -coverprofile=coverage.out
	go tool cover -html=coverage.out -o coverage.html

clean:
	rm -rf bin/ coverage.out coverage.html

install:
	go install ./cmd/teleclaude

lint:
	golangci-lint run

run:
	go run ./cmd/teleclaude
