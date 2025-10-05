.PHONY: up worker beat celery flower test lint format

POETRY ?= poetry
PYTHON ?= python
MANAGE ?= $(PYTHON) manage.py

up:
	$(MANAGE) migrate
	$(MANAGE) runserver 0.0.0.0:8000

worker:
	celery -A config worker -l info

beat:
	celery -A config beat -l info

celery:
	celery -A config worker -l info --beat

test:
	pytest --cov=.

lint:
	ruff check .

format:
	ruff check --select F401,F841 .
