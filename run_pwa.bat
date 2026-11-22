@echo off
cd /d "%~dp0"
rem Use the signed-in Chrome profile for YouTube authentication.
if not defined YTDLP_BROWSER set YTDLP_BROWSER=chrome
python server.py
