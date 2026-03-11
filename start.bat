@echo off
setlocal
set "DIR=%~dp0"
pushd "%DIR%"
python -m python_app
if errorlevel 1 pause
popd
