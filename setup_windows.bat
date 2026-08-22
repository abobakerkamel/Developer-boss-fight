@echo off
setlocal
py -3.12 -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Setup complete.
echo Run with: run_windows.bat
pause
