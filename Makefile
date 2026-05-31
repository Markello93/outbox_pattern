black_formatter:
	poetry run black ./app/ --config pyproject.toml

black_check:
	poetry run black ./app/ --config pyproject.toml --check

isort_formatter:
	poetry run isort . --settings-path pyproject.toml

isort_check:
	poetry run isort . --check-only --settings-path pyproject.toml

ruff_checker:
	poetry run ruff check . --config pyproject.toml

run_formatters: black_formatter isort_formatter

run_linters: black_check isort_check ruff_checker
