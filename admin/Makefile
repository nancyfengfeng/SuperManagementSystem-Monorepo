APP=main:app
HOST=0.0.0.0
PORT=5023

export PYTHONPATH=..

install:
	pip install -r requirements.txt

run:
	uvicorn $(APP) --host $(HOST) --port $(PORT)