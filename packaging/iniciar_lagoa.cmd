@echo off
rem Sobe a Lagoa guardando os dados ao lado do instalador (pasta "data").
setlocal
set "RPA_PASTA_DADOS=%~dp0data"
"%~dp0lagoa.exe" %*
endlocal
