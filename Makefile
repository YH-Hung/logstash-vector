.PHONY: test install clean help

help:
	@echo "Available targets:"
	@echo "  make test      - Run all tests using uv run pytest"
	@echo "  make install   - Install dependencies using uv sync"
	@echo "  make clean     - Clean temporary files"

install:
	uv sync

test:
	uv run pytest -v

clean:
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".pytest_cache" -delete
	rm -rf .pytest_cache
