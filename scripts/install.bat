@echo off
REM Instala o template (cria venv + dependências) - Windows
cd /d "%~dp0\.."

echo ► Criando ambiente virtual (.venv)...
py -3.11 -m venv .venv

echo ► Ativando ambiente e atualizando pip...
call .venv\Scripts\activate
python -m pip install --upgrade pip

echo ► Instalando dependências...
pip install -r requirements.txt

echo.
echo ✅ Instalação concluída!
echo    Ative o ambiente com:  .venv\Scripts\activate
echo    Rode o robô com:       python app\main.py
pause