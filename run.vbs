Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

appDir = fso.GetParentFolderName(WScript.ScriptFullName)
If Right(appDir, 1) <> "\" Then appDir = appDir & "\"

' Launch GUI entry directly (embeddable Python does not put project root on sys.path).
scriptPath = appDir & "src\ytdl_gui.py"
runtimeDir = appDir & "runtime\flet"
pythonw = appDir & "python\pythonw.exe"
python = appDir & "python\python.exe"

Function Q(path)
  Q = Chr(34) & path & Chr(34)
End Function

Function HasModule(pythonExe, moduleName)
  HasModule = False
  If pythonExe = "" Then Exit Function
  If Not fso.FileExists(pythonExe) Then Exit Function
  cmd = Q(pythonExe) & " -c " & Q("import " & moduleName)
  HasModule = (shell.Run(cmd, 0, True) = 0)
End Function

If Not fso.FileExists(pythonw) Or Not fso.FileExists(python) Then
  MsgBox "Bundled Python was not found." & vbCrLf & vbCrLf & _
    "Expected:" & vbCrLf & pythonw & vbCrLf & vbCrLf & _
    "This folder should contain the python\ directory.", 16, "YTDL"
  WScript.Quit 1
End If

If Not fso.FileExists(scriptPath) Then
  MsgBox "App script not found:" & vbCrLf & scriptPath, 16, "YTDL"
  WScript.Quit 1
End If

If Not HasModule(python, "flet") Or Not HasModule(python, "yt_dlp") Or Not HasModule(python, "imageio_ffmpeg") Then
  MsgBox "Bundled Python packages are incomplete." & vbCrLf & _
    "Python: " & python, 16, "YTDL"
  WScript.Quit 1
End If

If fso.FolderExists(runtimeDir) And fso.FileExists(runtimeDir & "\flet.exe") Then
  Set env = shell.Environment("PROCESS")
  env("FLET_VIEW_PATH") = runtimeDir
End If

shell.CurrentDirectory = Left(appDir, Len(appDir) - 1)
shell.Run Q(pythonw) & " " & Q(scriptPath), 0, False
