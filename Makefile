SHELL := /bin/bash

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: setup start stop restart status logs smoke check

setup:
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt
	test -f .env || cp .env.example .env
	$(PYTHON) scripts/init_db.py

start:
	bash scripts/start.sh

stop:
	bash scripts/stop.sh

restart:
	bash scripts/restart.sh

status:
	bash scripts/status.sh

logs:
	bash scripts/logs.sh

smoke:
	$(PYTHON) scripts/smoke_test.py

check:
	$(PYTHON) -m compileall app scripts
