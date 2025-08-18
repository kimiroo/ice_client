@echo off
setlocal

>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"

if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    goto PreUACPrompt
) else ( goto gotAdmin )

:PreUACPrompt
WHERE wt.exe >nul 2>&1
if '%errorlevel%' NEQ '0' (
    goto UACPrompt_CMD
) else (
    goto UACPrompt_WT
)

:UACPrompt_CMD
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    set params = %*:"=""
    echo UAC.ShellExecute "cmd.exe", "/c %~s0 %params%", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B

:UACPrompt_WT
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    set params = %*:"=""
    echo UAC.ShellExecute "wt.exe", "cmd.exe /c \""%~s0\"" %params%", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    pushd "%CD%"
    CD /D "%~dp0"

REM Check if the virtual environment directory exists
if not exist "%~dp0.venv\Scripts\activate.bat" (
    echo Virtual environment not found. Creating a new one...
    python -m venv .venv
    if not exist "%~dp0.venv\Scripts\activate.bat" (
        echo Error: Failed to create virtual environment.
        goto :EOF
    )
    echo Virtual environment created successfully.
)

REM Activate the virtual environment
echo Activating virtual environment...
call %~dp0.venv\Scripts\activate.bat

REM Check if dependencies need to be installed or updated
echo Installing dependencies...
python dependencies.py

REM Run the main application
echo Running main application...
python main.py

popd