@echo off
REM Navigate to the proxy directory
cd /d %~dp0\..\proxy

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Run the proxy server
uv run main.py
