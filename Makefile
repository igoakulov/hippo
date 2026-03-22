.PHONY: test clean lint format

test:
	python -m unittest discover tests/
	zsh tests/test_cli.sh

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .hippo/ sources/ topics/

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/
