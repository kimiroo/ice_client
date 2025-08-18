@echo off
setlocal
pushd ~dp0

>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"

if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    set params = %*:"=""
    echo UAC.ShellExecute "cmd.exe", "/c %~s0 %params%", "", "runas", 1 >> "%temp%\getadmin.vbs"

    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    pushd "%CD%"
    CD /D "%~dp0"

set "VENV_DIR=.venv"
set "ACTIVATE_SCRIPT=%VENV_DIR%\Scripts\activate.bat"

REM Check if the virtual environment directory exists
if not exist "%VENV_DIR%" (
    echo Virtual environment not found. Creating a new one...
    python -m venv "%VENV_DIR%"
    if not exist "%PYTHON_EXE%" (
        echo Error: Failed to create virtual environment.
        goto :EOF
    )
    echo Virtual environment created successfully.
)

REM Activate the virtual environment
echo Activating virtual environment...
call "%ACTIVATE_SCRIPT%"

REM Check if dependencies need to be installed or updated
echo Installing dependencies...
python dependencies.py

REM Run the main application
echo Running main application...
python main.py

popd