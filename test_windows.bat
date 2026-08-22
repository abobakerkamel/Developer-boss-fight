@echo off
setlocal
if not exist .venv\Scripts\python.exe (
  echo Virtual environment not found. Run setup_windows.bat first.
  exit /b 1
)
call .venv\Scripts\activate
python -m unittest discover -s tests -v
