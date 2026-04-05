Option Explicit

Dim shell, fso, repoDir, cmd
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

repoDir = fso.GetParentFolderName(WScript.ScriptFullName)
cmd = "cmd.exe /d /c cd /d """ & repoDir & """ && pyw -3.13 -m python_app"
shell.Run cmd, 0, False
