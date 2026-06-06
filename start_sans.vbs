Set objShell = CreateObject("WScript.Shell")
objShell.CurrentDirectory = "E:\sans\voice-assistant"
objShell.Run "pythonw main.py", 0, False
