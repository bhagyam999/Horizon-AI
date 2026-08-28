@echo off
cd /d "%~dp0"
py -3.14 -m pip install -r requirements.txt
if not exist .env copy .env.example .env
 echo.
echo Setup finished. Open .env, add DISCORD_TOKEN and GEMINI_API_KEY, then run start.bat
pause
