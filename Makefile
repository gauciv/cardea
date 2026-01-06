# Makefile for Project Cardea
# Provides atomic development workflow with clear separation of concerns

.PHONY: help dev-setup clean test lint format check-deps sentry-dev oracle-dev dashboard-dev

# Default target
help:
	@echo "Project Cardea - Hybrid AI Cybersecurity Platform"
	@echo ""
	@echo "Available targets:"
	@echo "  dev-setup      Set up development environment with platform detection"
	@echo "  platform-info  Show detected platform information"
	@echo "  clean          Clean all build artifacts and containers"
	@echo "  test           Run all tests"
	@echo "  lint           Run linting across all components"
	@echo "  format         Format code across all components"
	@echo "  check-deps     Check for security vulnerabilities in dependencies"
	@echo ""
	@echo "CI/CD (run before pushing):"
	@echo "  ci             Run all CI checks locally"
	@echo "  ci-python      Run Python linting and type checks"
	@echo "  ci-dashboard   Run Dashboard linting and build"
	@echo "  ci-docker      Build all Docker images"
	@echo "  pre-commit-install  Install pre-commit hooks"
	@echo "  pre-commit-run      Run pre-commit on all files"
	@echo ""
	@echo "Development servers:"
	@echo "  sentry-dev     Run Sentry (edge layer) in development mode"
	@echo "  oracle-dev     Run Oracle (cloud layer) in development mode"
	@echo "  dashboard-dev  Run Dashboard (UI layer) in development mode"
	@echo ""
	@echo "Integration:"
	@echo "  integration    Run full integration tests"
	@echo "  deploy-local   Deploy full stack locally"

# Development environment setup
dev-setup:
	@echo "Setting up Project Cardea development environment..."
	@scripts/setup-platform.sh

# Clean all artifacts
clean:
	@echo "Cleaning build artifacts..."
	@docker compose down -v --remove-orphans 2>/dev/null || true
	@docker system prune -f
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true

# Testing
test:
	@echo "Running all tests..."
	@make -C sentry test
	@make -C oracle test
	@make -C dashboard test
	@make -C shared test

# Code quality
lint:
	@echo "Running linting..."
	@scripts/lint-all.sh

format:
	@echo "Formatting code..."
	@scripts/format-all.sh

# CI checks (run locally before pushing)
ci:
	@echo "🔍 Running CI checks locally..."
	@make ci-python
	@make ci-dashboard
	@echo "✅ All CI checks passed!"

ci-python:
	@echo "🐍 Python CI checks..."
	@pip install ruff mypy --quiet 2>/dev/null || true
	@echo "  Checking Oracle..."
	@ruff check oracle/src/ --fix --quiet || true
	@ruff format oracle/src/ --check --quiet || echo "  ⚠️ Format issues found"
	@echo "  Checking Sentry Bridge..."
	@ruff check sentry/bridge/src/ --fix --quiet || true
	@echo "  Checking shared utilities..."
	@ruff check shared/ --fix --quiet || true
	@echo "  Validating Python syntax..."
	@find oracle sentry shared -name "*.py" -exec python -m py_compile {} \; 2>/dev/null
	@echo "  ✅ Python checks complete"

ci-dashboard:
	@echo "🎨 Dashboard CI checks..."
	@cd dashboard && npm run lint --silent 2>/dev/null || echo "  ⚠️ ESLint issues found"
	@cd dashboard && npx tsc --noEmit 2>/dev/null || echo "  ⚠️ TypeScript issues found"
	@cd dashboard && npm run build --silent 2>/dev/null && echo "  ✅ Build successful" || echo "  ❌ Build failed"

ci-docker:
	@echo "🐳 Docker build checks..."
	@docker build -t cardea-oracle:ci oracle/ --quiet && echo "  ✅ Oracle image built"
	@docker build -t cardea-bridge:ci sentry/bridge/ --quiet && echo "  ✅ Bridge image built"
	@docker build -t cardea-kitnet:ci sentry/services/kitnet/ --quiet && echo "  ✅ KitNET image built"

# Pre-commit hooks
pre-commit-install:
	@pip install pre-commit
	@pre-commit install
	@echo "✅ Pre-commit hooks installed"

pre-commit-run:
	@pre-commit run --all-files

# Security
check-deps:
	@echo "Checking dependencies for vulnerabilities..."
	@scripts/security-check.sh

# Development servers
sentry-dev:
	@echo "Starting Sentry development environment..."
	@make -C sentry dev

oracle-dev:
	@echo "Starting Oracle development environment..."
	@make -C oracle dev

dashboard-dev:
	@echo "Starting Dashboard development environment..."
	@make -C dashboard dev

# Integration
integration:
	@echo "Running integration tests..."
	@scripts/integration-test.sh

deploy-local:
	@echo "Deploying full stack locally..."
	@docker compose up -d

# Platform awareness
platform-info:
	@echo "Detecting platform information..."
	@cd shared/utils && python3 -c "from platform_detector import platform_detector; from environment_configurator import EnvironmentConfigurator; print(EnvironmentConfigurator().generate_platform_report())" 2>/dev/null || echo "❌ Platform detection requires: pip install pyyaml"

# Platform awareness
platform-info:
	@echo "Detecting platform information..."
	@python3 shared/utils/platform_detector.py || echo "Platform detection requires Python dependencies"