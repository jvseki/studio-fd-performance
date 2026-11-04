@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo O ambiente Python do projeto nao foi encontrado. Consulte docs\ATUALIZACOES.md.
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -X utf8 "%~dp0tools\release.py" --interactive
set "studio_release_result=%ERRORLEVEL%"
echo.
pause
exit /b %studio_release_result%
