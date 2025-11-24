@echo off
REM Set UTF-8 encoding
chcp 65001 >nul

REM Set console title
title Audio Remote Control System

echo ============================================
echo Audio Remote Control System Startup Script
echo ============================================

REM Check if virtual environment directory exists
if not exist ".venv" (
    echo ERROR: Virtual environment directory .venv does not exist
    echo Please create virtual environment: python -m venv .venv
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

if %ERRORLEVEL% neq 0 (
    echo ERROR: Virtual environment activation failed
    pause
    exit /b 1
)

echo Virtual environment activated successfully

REM Check if dependencies are installed
echo Checking dependency installation status...
python -c "import uvicorn, quart, socketio" 2>nul
if %ERRORLEVEL% neq 0 (
    echo Missing dependencies detected, installing...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Dependency installation failed
        pause
        exit /b 1
    )
    echo Dependencies installed successfully
) else (
    echo Dependencies already installed
)

REM Start the application
echo ============================================
echo Starting application...
echo ============================================

python run.py

REM Pause if the program exits to view error messages
echo.
echo Application has exited
pause