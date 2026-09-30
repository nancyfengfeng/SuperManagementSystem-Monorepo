APP=main:app
HOST=0.0.0.0
PORT=5023

PYTHON=venv/bin/python
PIP=venv/bin/pip

export PYTHONPATH=..

install:
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) -m uvicorn $(APP) --host $(HOST) --port $(PORT)

dev:
	$(PYTHON) -m uvicorn $(APP) --host $(HOST) --port $(PORT) --reload