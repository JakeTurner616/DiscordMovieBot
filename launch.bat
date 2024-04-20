@echo off
setlocal

rem Define the path to qBittorrent executable
set QB_PATH=C:\Program Files\qBittorrent\qbittorrent.exe

rem Loop to ensure qBittorrent is running
:check_qb
echo Checking if qBittorrent is running...
tasklist /FI "IMAGENAME eq qbittorrent.exe" | find /I "qbittorrent.exe" > NUL
if errorlevel 1 (
    echo qBittorrent is not running. Starting qBittorrent...
    start "" "%QB_PATH%"
    timeout /t 5 /nobreak > NUL
    goto check_qb
) else (
    echo qBittorrent is running.
)

rem Start the bot
echo Starting the bot...
call discordmoviebot\Scripts\activate
python bot.py
echo Bot script execution has ended.
pause

endlocal
