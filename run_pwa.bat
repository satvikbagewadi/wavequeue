@echo off
cd /d "%~dp0"
rem One-click startup: start the local downloader and open the hosted PWA.
if not defined YTDLP_BROWSER set YTDLP_BROWSER=chrome
start "WaveQueue Local Bridge" /min cmd /c "cd /d "%~dp0" && set YTDLP_BROWSER=%YTDLP_BROWSER% && python server.py"
start "" "https://wavequeue.onrender.com/?v=3"
