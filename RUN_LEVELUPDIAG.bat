@echo off
setlocal
set "HERE=%~dp0"
set "CAMPAIGN=%~1"
if "%CAMPAIGN%"=="" set "CAMPAIGN=standard"
if "%~2"=="" (
  python "%HERE%levelupdiag.py" run "%CAMPAIGN%"
) else (
  python "%HERE%levelupdiag.py" --target "%~2" run "%CAMPAIGN%"
)
exit /b %ERRORLEVEL%
