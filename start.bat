@echo off
setlocal
set "DIR=%~dp0"
pushd "%DIR%"
if /I "%~1"=="--console" (
    py -3.13 -m python_app
    if errorlevel 1 pause
) else (
    wscript //nologo "%DIR%start.vbs"
)
popd
echo(%CMDCMDLINE% | find /I "%~nx0" >nul
if not errorlevel 1 exit
