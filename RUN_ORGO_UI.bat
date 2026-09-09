@echo off
setlocal
py -3 "%~dp0LEVELUPDIAG_CONSOLE.pyw"
if errorlevel 1 (
  echo Could not start the console. Check Python 3.10+ with Tcl/Tk support.
  pause
)
