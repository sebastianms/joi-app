# Joi-App Backend

Backend del sistema Joi-App construido con FastAPI + Python.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run dev server

```bash
uvicorn app.main:app --reload
```

## Run tests

```bash
pytest --cov=app --cov-report=term-missing
```
