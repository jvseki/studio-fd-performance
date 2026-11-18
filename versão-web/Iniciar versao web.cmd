@echo off
setlocal
cd /d "%~dp0backend"
set "PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Ambiente Python nao encontrado. Veja o README.md.
  pause
  exit /b 1
)
if not exist "%~dp0frontend\dist\index.html" (
  echo Site ainda nao montado. Rode: cd frontend ^&^& npm install ^&^& npm run build
  pause
  exit /b 1
)
echo Studio FD - versao web ligada.
echo Neste computador: http://localhost:8000
echo No tablet/celular (mesmo Wi-Fi): http://IP-DESTE-COMPUTADOR:8000
echo Para desligar, feche esta janela.
"%PY%" -m uvicorn app:app --host 0.0.0.0 --port 8000
pause
