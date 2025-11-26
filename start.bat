@echo off
REM Set UTF-8 encoding
chcp 65001 >nul

REM Set console title
title Audio Remote Control System

echo ============================================
echo Audio Remote Control System Startup Script
echo ============================================

REM Check if conda environment directory exists
if not exist "conda_env" (
    echo ERROR: Conda environment directory conda_env does not exist
    echo Please create conda environment first
    pause
    exit /b 1
)

REM Activate conda environment
echo Activating conda environment...
call conda activate .\conda_env

if %ERRORLEVEL% neq 0 (
    echo ERROR: Conda environment activation failed
    pause
    exit /b 1
)

echo Conda environment activated successfully

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