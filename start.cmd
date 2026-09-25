@echo off
rem One-command dev startup: sync dependencies, run colored diagnostics,
rem then start the tray application. Run from the repo root (works in
rem both cmd.exe and PowerShell - unlike a .ps1, this isn't affected by
rem PowerShell's script execution policy):
rem
rem     start.cmd

echo ==^> Syncing dependencies...
uv sync
if errorlevel 1 (
    echo uv sync failed.
    exit /b %errorlevel%
)

echo.
echo ==^> Starting ATLAS ^(diagnostics + tray^)...
uv run atlas --start
exit /b %errorlevel%
