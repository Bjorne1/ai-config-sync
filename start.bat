@echo off
set "DIR=%~dp0"
set "DIR=%DIR:~0,-1%"
powershell -Command "Start-Process wt -ArgumentList '-w 0 new-tab -d \"%DIR%\" pwsh -NoExit -Command \"node index.js\"' -Verb RunAs"
