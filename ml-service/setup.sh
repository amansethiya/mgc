#!/usr/bin/env bash
cd "$(dirname "$0")"
command -v python3.11 >/dev/null || { echo "Python 3.11 not found"; exit 1; }
[ -d .venv ] || python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-lock.txt || .venv/bin/python -m pip install -r requirements.txt
echo "Setup done. Next: ./train.sh (needs dataset) or ./run.sh (needs models/genre_model.joblib)"
