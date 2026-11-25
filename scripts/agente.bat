@echo off
REM Roda o agente (runner) da Lagoa a partir do codigo-fonte - Windows
REM   scripts\agente.bat
REM   scripts\agente.bat --maquina meu-pc --tags windows
REM   scripts\agente.bat --lagoa http://10.0.0.5:8765
setlocal

set "ROOT=%~dp0.."
cd /d "%ROOT%"

if not exist ".venv\Scripts\activate.bat" (
    echo Ambiente virtual nao encontrado. Rode primeiro: scripts\install.bat
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m core.control_room.agente %*
