@echo off
echo DiscoFlow Installer
echo.
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
python "%~dp0install.py"
pause
