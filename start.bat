@echo off
cd /d "%~dp0"
if not exist .env (
  echo .env is missing. Copy .env.example to .env and add your keys.
  pause
  exit /b 1
)
py -3.14 bot.py
pause
