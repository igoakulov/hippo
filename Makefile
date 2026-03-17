.PHONY: help test clean lint format

help:
	@echo "Available targets:"
	@echo "  make test     - Run CLI tests"
	@echo "  make clean    - Remove generated files and cache"
	@echo "  make lint     - Run linter"
	@echo "  make format   - Format code"

test:
	bash tests/test_cli.sh

clean:
	rm -rf graph.json
	rm -f topics/*.md
	rm -rf sources/
	rm -rf backups/
	rm -rf diffs/
	rm -rf logs/
	rm -rf render/
	rm -rf src/hippo/__pycache__
	rm -rf .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

lint:
	uv run ruff check src/

format:
	uv run ruff format src/
