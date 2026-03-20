@echo off
setlocal
set "DIR=%~dp0"
pushd "%DIR%"
py -3.13 -m python_app
if errorlevel 1 pause
popd
