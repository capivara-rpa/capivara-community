@echo off
rem Sobe o agente desta máquina apontando para a Lagoa local.
rem Aceita argumentos extras (ex.: --tags win,sp --token segredo).
setlocal
set "RPA_PASTA_DADOS=%~dp0data"
"%~dp0robo_agente.exe" --lagoa http://127.0.0.1:8765 --maquina %COMPUTERNAME% --tags win %*
endlocal
