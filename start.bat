@echo off
setlocal
set "DIR=%~dp0"
pushd "%DIR%"
if /I "%~1"=="--console" (
    py -3.13 -m python_app
    if errorlevel 1 pause
) else (
    pyw -3.13 -m python_app
)
popd
