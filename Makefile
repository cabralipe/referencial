.PHONY: up worker beat celery flower sockets test lint format

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

sockets:
	daphne -b 0.0.0.0 -p 8001 config.asgi:application

test:
	pytest --cov=.

lint:
	ruff check .

format:
	ruff check --select F401,F841 .
