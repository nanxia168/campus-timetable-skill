@echo off
rem run.cmd - run a script with whatever Python this machine has
rem usage:  run.cmd scripts\to_ics.py courses.json --check
setlocal
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYEXE=
for /f "delims=" %%A in ('python -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%A"
if defined PYEXE goto run
for /f "delims=" %%A in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%A"
if defined PYEXE goto run
if exist "C:\Users\naxia\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" set "PYEXE=C:\Users\naxia\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if defined PYEXE goto run
echo [run] No usable Python found.
echo [run] Install Python 3.9+ first:
echo [run]     winget install -e --id Python.Python.3.12
exit /b 1
:run
"%PYEXE%" %*
exit /b %ERRORLEVEL%
