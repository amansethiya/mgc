@echo off
cd /d "%~dp0"
py -3.11 --version >nul 2>&1 || (echo Python 3.11 not found. Install it from python.org & exit /b 1)
if not exist .venv py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt || .venv\Scripts\python.exe -m pip install -r requirements.txt
echo Setup done. Next: train.bat (needs dataset) or run.bat (needs models\genre_model.joblib)
