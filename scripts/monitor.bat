@echo off
rem Sobe o painel de monitoramento dos robôs - Windows
rem   scripts\monitor.bat              -> sobe o painel
rem   scripts\monitor.bat --exemplos   -> popula o banco com dados de exemplo e sobe

setlocal
set ROOT=%~dp0..
cd /d "%ROOT%"

if not exist ".venv" (
    echo Ambiente virtual nao encontrado. Rode primeiro: scripts\install.bat
    exit /b 1
)

call .venv\Scripts\activate.bat

if "%~1"=="--exemplos" (
    python -m core.monitor.dados_exemplo
    shift
)

python -m core.monitor.servidor %*
