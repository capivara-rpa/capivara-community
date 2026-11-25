@echo off
REM Roda o robô usando o ambiente virtual - Windows
cd /d "%~dp0\.."

if not exist ".venv" (
    echo ❌ Ambiente virtual não encontrado. Rode primeiro:  scripts\install.bat
    exit /b 1
)

call .venv\Scripts\activate
python app\main.py %*