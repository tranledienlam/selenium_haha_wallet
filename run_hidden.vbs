Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Chạy batch file với tham số --auto --headless
WshShell.Run "run_menu.bat --auto --headless", 0

Set WshShell = Nothing 