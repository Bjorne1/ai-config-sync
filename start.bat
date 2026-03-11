@echo off
setlocal
set "DIR=%~dp0"
pushd "%DIR%"
call npm start
if errorlevel 1 pause
popd
