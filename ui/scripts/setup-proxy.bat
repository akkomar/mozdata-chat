@echo off
REM Navigate to the proxy directory
cd /d "%~dp0\..\proxy" || exit /b 1

uv sync
