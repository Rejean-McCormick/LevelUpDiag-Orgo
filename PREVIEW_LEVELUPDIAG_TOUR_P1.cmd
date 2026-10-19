@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  py -3 "%~dp0tools\tandem_tour7\manager.py" preview
) else (
  python "%~dp0tools\tandem_tour7\manager.py" preview
)
set "STATUS=%ERRORLEVEL%"
echo.
if not "%STATUS%"=="0" echo [ECHEC] Code: %STATUS%
pause
exit /b %STATUS%
