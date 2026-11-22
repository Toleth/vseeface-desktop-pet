@echo off
REM Build the single-file Windows executable.
REM Usage: run in a "Developer Command Prompt" or any cmd with Python 3.11+ on PATH.
python -m pip install -r requirements-dev.txt
python -m PyInstaller --noconfirm --onefile --windowed --name VSeeFaceDesktopPet --collect-all SpoutGL --hidden-import numpy vseeface_desktop.py
if errorlevel 1 (
    echo BUILD FAILED
    exit /b 1
)
copy /Y dist\VSeeFaceDesktopPet.exe .\VSeeFaceDesktopPet.exe
echo.
echo Done -^> VSeeFaceDesktopPet.exe
