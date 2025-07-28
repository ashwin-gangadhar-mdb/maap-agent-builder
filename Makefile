.PHONY: clean install dev test lint format docker-build docker-run docker-debug setup-env create-config create-agent validate-config add-tool run serve build-package help

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
	@echo "  make create-agent    Create a new agent configuration template"
	@echo "  make validate-config Validate the agents.yaml configuration"
	@echo "  make add-tool        Add a new tool to the agents.yaml configuration"
	@echo "  make lint            Run linting checks"
	@echo "  make format          Format code using black and isort"
	@echo "  make test            Run tests"
	@echo "  make build-package   Build package distribution files"
	@echo "  make clean           Remove build artifacts and cache directories"
	@echo "  make docker-build    Build Docker image"
	@echo "  make docker-run      Run Docker container"
	@echo "  make docker-debug    Start Docker container in interactive mode for debugging"
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
	$(PIP) install -e ".[dev]"
	@echo "Installation complete."

# Install dev dependencies (kept for backwards compatibility)
dev:
	@echo "Installing development dependencies..."
	$(PIP) install -e ".[dev]"
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

# Create a new agent configuration template
create-agent:
	@echo "Creating new agent configuration template..."
	@read -p "Enter agent name: " agent_name; \
	read -p "Enter agent type (react/tool_call/reflect/plan_execute_replan/long_term_memory): " agent_type; \
	read -p "Enter LLM provider (openai/anthropic/fireworks/etc): " llm_provider; \
	read -p "Enter model name: " model_name; \
	mkdir -p $(CONFIG_DIR); \
	if [ -f $(CONFIG_PATH) ]; then \
		echo "\n# New agent configuration for $$agent_name" >> $(CONFIG_PATH); \
		echo "llms:" >> $(CONFIG_PATH); \
		echo "  - name: $${agent_name}_llm" >> $(CONFIG_PATH); \
		echo "    provider: $$llm_provider" >> $(CONFIG_PATH); \
		echo "    model_name: $$model_name" >> $(CONFIG_PATH); \
		echo "    temperature: 0.7" >> $(CONFIG_PATH); \
		echo "    streaming: True" >> $(CONFIG_PATH); \
		echo "" >> $(CONFIG_PATH); \
		echo "agent:" >> $(CONFIG_PATH); \
		echo "  name: $$agent_name" >> $(CONFIG_PATH); \
		echo "  agent_type: $$agent_type" >> $(CONFIG_PATH); \
		echo "  llm: $${agent_name}_llm" >> $(CONFIG_PATH); \
		echo "  system_prompt_path: ./prompts/rag_system_prompt.txt" >> $(CONFIG_PATH); \
		echo "  tools: []" >> $(CONFIG_PATH); \
		echo "Created new agent configuration for $$agent_name in $(CONFIG_PATH)"; \
	else \
		echo "llms:" > $(CONFIG_PATH); \
		echo "  - name: $${agent_name}_llm" >> $(CONFIG_PATH); \
		echo "    provider: $$llm_provider" >> $(CONFIG_PATH); \
		echo "    model_name: $$model_name" >> $(CONFIG_PATH); \
		echo "    temperature: 0.7" >> $(CONFIG_PATH); \
		echo "    streaming: True" >> $(CONFIG_PATH); \
		echo "" >> $(CONFIG_PATH); \
		echo "agent:" >> $(CONFIG_PATH); \
		echo "  name: $$agent_name" >> $(CONFIG_PATH); \
		echo "  agent_type: $$agent_type" >> $(CONFIG_PATH); \
		echo "  llm: $${agent_name}_llm" >> $(CONFIG_PATH); \
		echo "  system_prompt_path: ./prompts/rag_system_prompt.txt" >> $(CONFIG_PATH); \
		echo "  tools: []" >> $(CONFIG_PATH); \
		echo "Created new agent configuration at $(CONFIG_PATH)"; \
	fi
	@if [ ! -f prompts/rag_system_prompt.txt ]; then \
		mkdir -p prompts; \
		echo "You are a helpful, respectful and honest assistant. You are provided with a set of tools to help you answer the user's question.\n\nYou must think step-by-step and use the tools in order to provide accurate and relevant responses.\n\nAlways acknowledge and disclose when you're using information retrieved from tools." > prompts/rag_system_prompt.txt; \
	fi

# Validate the agents.yaml configuration
validate-config:
	@echo "Validating agent configuration..."
	@if [ -f $(CONFIG_PATH) ]; then \
		$(PYTHON) -c "import yaml; yaml.safe_load(open('$(CONFIG_PATH)'))" && echo "Configuration is valid YAML."; \
		echo "Checking for required keys..."; \
		$(PYTHON) -c "import yaml; config = yaml.safe_load(open('$(CONFIG_PATH)')); assert 'agent' in config, 'Missing agent section'; assert 'name' in config['agent'], 'Missing agent name'; assert 'agent_type' in config['agent'], 'Missing agent type'; assert 'llm' in config['agent'], 'Missing LLM reference'; llm_name = config['agent']['llm']; llms = [l['name'] for l in config.get('llms', [])]; assert llm_name in llms, f'Referenced LLM {llm_name} not defined in llms section'" && echo "Configuration contains all required fields."; \
	else \
		echo "Configuration file not found at $(CONFIG_PATH). Use 'make create-config' to create it."; \
		exit 1; \
	fi

# Run linting
lint:
	@echo "Running linting checks..."
	flake8 mdb_agent_builder
	black --check mdb_agent_builder
	isort --check-only mdb_agent_builder
	ruff check mdb_agent_builder

# Format code
format:
	@echo "Formatting code..."
	black mdb_agent_builder
	isort mdb_agent_builder
	@echo "Code formatted."

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

# Build package distribution files
build-package:
	@echo "Building package distribution files..."
	$(PYTHON) -m pip install --upgrade build
	$(PYTHON) -m build
	@echo "Package built. Distribution files available in dist/"

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
		$(foreach env,$(filter-out $@,$(MAKECMDGOALS)),$(if $(findstring =,$(env)),-e $(env),)) \
		-e PYTHONPATH=/app \
		-e AGENT_CONFIG_PATH=/app/config/agents.yaml \
		$(PROJECT_NAME)

# Run the agent server
run:
	@echo "Running MAAP Agent Builder server..."
	export AGENT_CONFIG_PATH=$(CONFIG_PATH) && \
	python -m mdb_agent_builder.cli serve --config $(CONFIG_PATH) --port 5000

# Alias for run
serve: run

# Debug the Docker container with a shell
docker-debug:
	@echo "Starting Docker container in interactive mode..."
	docker run -it --rm \
		-p 5000:5000 \
		-v $(PWD)/$(CONFIG_DIR):/app/config \
		-v $(PWD)/$(LOGS_DIR):/app/logs \
		-v $(PWD)/prompts:/app/prompts \
		--env-file .env \
		-e PYTHONPATH=/app \
		-e LOG_LEVEL=DEBUG \
		-e AGENT_CONFIG_PATH=/app/config/agents.yaml \
		$(PROJECT_NAME) /bin/bash

# Default target
.DEFAULT_GOAL := help

# Full setup (creates venv, installs package, creates config)
setup: setup-env
	@echo "Running full setup process..."
	@echo "NOTE: Please activate the virtual environment with 'source .venv/bin/activate'"
	@echo "Then run: make install-and-config"

# Install and create config in one step (requires activated venv)
install-and-config: install create-config
	@echo "Installation and configuration complete."

# Add a tool to an existing agent configuration
add-tool:
	@echo "Adding a new tool to the agent configuration..."
	@if [ ! -f $(CONFIG_PATH) ]; then \
		echo "Configuration file not found at $(CONFIG_PATH). Use 'make create-config' to create it."; \
		exit 1; \
	fi; \
	read -p "Enter tool name: " tool_name; \
	read -p "Enter tool type (vector_search/web_search/calculator/etc): " tool_type; \
	read -p "Enter tool description: " tool_description; \
	echo "\n# New tool configuration for $$tool_name" >> $(CONFIG_PATH); \
	echo "tools:" >> $(CONFIG_PATH); \
	echo "  - name: $$tool_name" >> $(CONFIG_PATH); \
	echo "    tool_type: $$tool_type" >> $(CONFIG_PATH); \
	echo "    description: \"$$tool_description\"" >> $(CONFIG_PATH); \
	echo "" >> $(CONFIG_PATH); \
	echo "# Update agent to use the new tool" >> $(CONFIG_PATH); \
	echo "# Add this to your agent tools list:" >> $(CONFIG_PATH); \
	echo "#   tools:" >> $(CONFIG_PATH); \
	echo "#     - $$tool_name" >> $(CONFIG_PATH); \
	echo "Added new tool $$tool_name to $(CONFIG_PATH)"; \
	echo "NOTE: You need to manually add the tool to your agent's tools list."
