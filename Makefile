# Makefile for Promotion Letters Flask App

.PHONY: help build up down restart logs shell clean dev test

# Default target
help:
	@echo "Available commands:"
	@echo "  build    - Build the Docker image"
	@echo "  up       - Start the application"
	@echo "  down     - Stop the application"
	@echo "  restart  - Restart the application"
	@echo "  logs     - View application logs"
	@echo "  shell    - Access application shell"
	@echo "  clean    - Clean up containers and images"
	@echo "  dev      - Start in development mode"
	@echo "  test     - Run tests"
	@echo "  setup    - Initial setup (create .env file)"

# Build the Docker image
build:
	docker-compose build

# Start the application
up:
	docker-compose up -d
	@echo "Application started at http://localhost:5000"

# Stop the application
down:
	docker-compose down

# Restart the application
restart: down up

# View logs
logs:
	docker-compose logs -f promotion-letters

# Access application shell
shell:
	docker-compose exec promotion-letters bash

# Clean up
clean:
	docker-compose down -v --rmi all
	docker system prune -f

# Development mode (with file watching)
dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Run tests
test:
	docker-compose exec promotion-letters python -m pytest tests/

# Initial setup
setup:
	@if [ ! -f .env ]; then \
		echo "Creating .env file..."; \
		echo "# Claude API Configuration" > .env; \
		echo "CLAUDE_API_KEY=your_claude_api_key_here" >> .env; \
		echo "" >> .env; \
		echo "# Flask Configuration" >> .env; \
		echo "SECRET_KEY=$(openssl rand -base64 32)" >> .env; \
		echo "FLASK_ENV=production" >> .env; \
		echo "FLASK_DEBUG=false" >> .env; \
		echo "" >> .env; \
		echo "# Docker Configuration" >> .env; \
		echo "HOST_PORT=5000" >> .env; \
		echo "NAS_IP=192.168.0.134" >> .env; \
		echo ""; \
		echo ".env file created successfully!"; \
		echo "Please edit .env file and:"; \
		echo "1. Add your Claude API key"; \
		echo "2. Update NAS_IP if different from 192.168.0.134"; \
	else \
		echo ".env file already exists"; \
	fi

# Quick start (setup + build + up)
start: setup build up

# Status check
status:
	docker-compose ps

# View container stats
stats:
	docker stats promotion-letters-app promotion-letters-redis
