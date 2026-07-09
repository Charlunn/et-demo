# spark-pricing Makefile (SPEC §6). Windows 上若无 make, 请用 README 里的 uv 直接命令.
.PHONY: install migrate test lint type serve backtest frontend clean

install:
	uv sync --extra dev
	cd frontend && uv venv --python 3.12 .venv && uv pip install -r requirements.txt pytest

migrate:
	uv run alembic upgrade head

test:
	uv run pytest --cov

lint:
	uv run ruff check app tests scripts
	uv run ruff format --check app tests scripts

type:
	uv run mypy

serve:
	uv run python -m app.cli serve --port 8000

backtest:
	uv run python -m app.cli backtest --days 1 --line-limit 80 --model persistence

frontend:
	cd frontend && streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

clean:
	rm -rf .venv frontend/.venv .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	rm -f spark.db spark-test.db ci-test.db