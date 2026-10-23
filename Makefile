.PHONY: help venv setup validate test sim new-app devs repl deploy mount ls reset clean

VENV ?= .venv
VENV_PYTHON = $(VENV)/bin/python3
VENV_PIP = $(VENV)/bin/pip

# Prefer virtualenv Python when available, unless explicitly overridden
ifeq ($(wildcard $(VENV_PYTHON)),)
  PYTHON ?= $(shell which python3)
else
  PYTHON ?= $(VENV_PYTHON)
endif

help:
	@echo "GitHub Universe 2026 Badge Development Commands:"
	@echo "  make setup            - Set up local Python virtual environment & dependencies"
	@echo "  make sim [APP=name]   - Run Universe 2026 Badge Simulator (default: menu)"
	@echo "  make validate         - Validate all 2026 badge apps, syntax, and guidelines"
	@echo "  make test             - Run validation suite and tests"
	@echo "  make new-app APP=name - Scaffold a new 2026 badge app with icon & boilerplate"
	@echo "  make devs             - Scan for connected badge USB serial ports"
	@echo "  make repl             - Connect to badge interactive MicroPython REPL"
	@echo "  make deploy APP=name  - Deploy app to connected badge"
	@echo "  make mount APP=name   - Live-mount badge directory for host-based testing"
	@echo "  make ls [PATH=path]   - List files on the badge filesystem (default: :/system/apps)"
	@echo "  make reset            - Soft-reset the connected badge"
	@echo "  make clean            - Remove cache and temporary files"

venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment in $(VENV)..."; \
		$(PYTHON) -m venv $(VENV); \
	fi

setup: venv
	@echo "Installing development dependencies..."
	@$(VENV_PIP) install --upgrade pip
	@$(VENV_PIP) install -r requirements.txt
	@echo "\nSetup complete! Activate with: source $(VENV)/bin/activate"

sim:
	@$(PYTHON) tools/badge.py sim $(if $(APP),$(APP),menu) $(if $(SCALE),--scale $(SCALE),) $(if $(FRAMES),--frames $(FRAMES),)

validate:
	@$(PYTHON) tools/badge.py validate

test: validate
	@$(PYTHON) -m unittest discover tests

new-app:
	@if [ -z "$(APP)" ]; then \
		echo "Error: Specify APP name. Example: make new-app APP=my_awesome_app"; \
		exit 1; \
	fi
	@$(PYTHON) tools/badge.py new-app $(APP)

devs:
	@$(PYTHON) tools/badge.py devs

repl:
	@$(PYTHON) tools/badge.py repl $(if $(PORT),--port $(PORT),)

deploy:
	@if [ -z "$(APP)" ]; then \
		echo "Error: Specify APP name. Example: make deploy APP=flappy_mona"; \
		exit 1; \
	fi
	@$(PYTHON) tools/badge.py deploy $(APP) $(if $(PORT),--port $(PORT),)

mount:
	@if [ -z "$(APP)" ]; then \
		echo "Error: Specify APP name. Example: make mount APP=flappy_mona"; \
		exit 1; \
	fi
	@$(PYTHON) tools/badge.py deploy $(APP) --mount $(if $(PORT),--port $(PORT),)

ls:
	@$(PYTHON) tools/badge.py ls $(if $(PATH),$(PATH),) $(if $(PORT),--port $(PORT),)

reset:
	@$(PYTHON) tools/badge.py reset $(if $(PORT),--port $(PORT),)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
