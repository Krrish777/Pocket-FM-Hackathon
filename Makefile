# Story Engine — task shortcuts. Run `make help` for the list.
# Verification chain: `make check` is the single "is it done?" gate (see CLAUDE.md).

.DEFAULT_GOAL := help
.PHONY: help setup install dev run test test-e2e test-kb check lint format fmt-check typecheck eval eval-kernel clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Create the environment and install all dependencies (uv)
	uv sync

install: setup ## Alias for setup

dev: ## Run the API in dev mode (auto-reload)
	uv run uvicorn story_engine.api.app:app --reload

run: ## Run the API server
	uv run uvicorn story_engine.api.app:app

lint: ## Lint with Ruff
	uv run ruff check .

format: ## Auto-format with Ruff
	uv run ruff format .

fmt-check: ## Check formatting without writing changes
	uv run ruff format --check .

typecheck: ## Type-check with mypy (strict-ish)
	uv run mypy src

test: ## Run the test suite
	uv run pytest

test-e2e: ## Run ONLY the L3 end-to-end layer (real DB on disk, app boundary)
	uv run pytest -m e2e -v

test-kb: ## Run every Canon Kernel test (schema + invariants + store + e2e)
	uv run pytest tests/unit/domain tests/integration -k "canon or invariant or kernel" -v

check: lint fmt-check typecheck test ## FULL verification gate — the 3-layer Validation Hierarchy (see tests/README.md)
# L1 (syntax/static) = lint + fmt-check + typecheck · L2 (runtime) = unit + integration · L3 (system) = e2e.
# `test` runs all of tests/ (unit + integration + e2e). A layer must pass before the next is trusted.

eval: ## Run the LLM eval harness (non-blocking, costs money)
	uv run python evals/run_evals.py

eval-kernel: ## Canon Kernel with/without consistency comparison (KB-06). Fails until M5 lands.
	uv run python evals/run_kernel_eval.py

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build **/__pycache__ 2>/dev/null || true
