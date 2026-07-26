@echo off
setlocal
cd /d "%~dp0"
pyw "%CD%\levelupdiag_wrapper.pyw"
if errorlevel 1 (
  py "%CD%\levelupdiag_wrapper.pyw"
  pause
)
