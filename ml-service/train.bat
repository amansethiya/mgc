@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe train.py --dataset dataset/genres_original
