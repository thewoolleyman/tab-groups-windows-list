#!/bin/bash
set -e

echo ">> Running ruff..."
uv run ruff check adws/

echo ">> Running mypy..."
uv run mypy adws/

echo ">> Running pytest..."
uv run pytest
