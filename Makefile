.PHONY: clean install dev test lint docker-build docker-run setup-env create-config run serve help

# Project variables
PROJECT_NAME := maap-agent-builder
PYTHON := python3
PIP := $(PYTHON) -m pip
CONFIG_DIR := config
LOGS_DIR := logs
CONFIG_PATH := $(CONFIG_DIR)/agents.yaml

help:
	@echo "MAAP Agent Builder"
	@echo ""
	@echo "Usage:"
	@echo "  make setup-env       Create virtual environment and install dependencies"
	@echo "  make install         Install the package in development mode"
	@echo "  make dev             Install dev dependencies"
	@echo "  make create-config   Create default configuration directories and files"
	@echo "  make lint            Run linting checks"
	@echo "  make test            Run tests"
	@echo "  make clean           Remove build artifacts and cache directories"
	@echo "  make docker-build    Build Docker image"
	@echo "  make docker-run      Run Docker container"
	@echo "  make run             Run the agent server using local configuration"
	@echo "  make serve           Alias for 'make run'"

# Setup the environment and install dependencies
setup-env:
	@echo "Creating virtual environment and installing dependencies..."
	$(PYTHON) -m venv .venv
	@echo "Virtual environment created. Activate it with: source .venv/bin/activate"
	@echo "Then run: make install"

# Install the package in development mode
install:
	@echo "Installing package in development mode..."
	$(PIP) install -e .
	@echo "Installation complete."

# Install dev dependencies
dev:
	@echo "Installing development dependencies..."
	$(PIP) install -r requirements-dev.txt
	@echo "Development dependencies installed."

# Create default configuration directories and files
create-config:
	@echo "Creating configuration directories..."
	mkdir -p $(CONFIG_DIR) $(LOGS_DIR) prompts
	@if [ ! -f $(CONFIG_PATH) ]; then \
		cp mdb_agent_builder/agents.yaml $(CONFIG_DIR)/; \
		echo "Default configuration copied to $(CONFIG_PATH)"; \
	else \
		echo "Configuration file already exists at $(CONFIG_PATH)"; \
	fi
	@echo "Creating sample system prompt..."
	@if [ ! -f prompts/rag_system_prompt.txt ]; then \
		echo "You are a helpful, respectful and honest assistant. You are provided with a set of tools to help you answer the user's question.\n\nYou must think step-by-step and use the tools in order to provide accurate and relevant responses.\n\nAlways acknowledge and disclose when you're using information retrieved from tools." > prompts/rag_system_prompt.txt; \
		echo "Sample system prompt created at prompts/rag_system_prompt.txt"; \
	else \
		echo "System prompt already exists at prompts/rag_system_prompt.txt"; \
	fi

# Run linting
lint:
	@echo "Running linting checks..."
	flake8 mdb_agent_builder
	black --check mdb_agent_builder
	isort --check-only mdb_agent_builder

# Run tests
test:
	@echo "Running tests..."
	pytest tests/

# Clean up build artifacts and cache directories
clean:
	@echo "Cleaning build artifacts and cache directories..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.pyc" -delete
	@echo "Cleaned."

# Build the Docker image
docker-build:
	@echo "Building Docker image..."
	docker build -t $(PROJECT_NAME) -f Dockerfile .
	@echo "Docker image built: $(PROJECT_NAME)"

# Run the Docker container
docker-run:
	@echo "Running Docker container..."
	docker run -p 5000:5000 \
		-v $(PWD)/$(CONFIG_DIR):/app/config \
		-v $(PWD)/$(LOGS_DIR):/app/logs \
		-v $(PWD)/prompts:/app/prompts \
		--env-file .env \
		$(PROJECT_NAME)

# Run the agent server
run:
	@echo "Running MAAP Agent Builder server..."
	export AGENT_CONFIG_PATH=$(CONFIG_PATH) && \
	python -m mdb_agent_builder.cli serve --config $(CONFIG_PATH) --port 5000

# Alias for run
serve: run

# Default target
.DEFAULT_GOAL := help
