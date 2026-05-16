@echo off
setlocal
title VidDrop Launcher
cls

echo ===========================================
echo         VidDrop - Video Downloader
echo ===========================================

:: 1. Check for FFmpeg
if not exist "ffmpeg.exe" (
    echo [WARNING] ffmpeg.exe is missing! Downloads might fail.
)

:: 2. Install dependencies
echo [1/3] Checking dependencies...
python -m pip install flask yt-dlp -q

:: 3. Prepare folders
if not exist "downloads" mkdir downloads

:: 4. Launch the Browser
echo [2/3] Opening VidDrop in your browser...
start http://127.0.0.1:5000

:: 5. Start the Server
echo [3/3] Starting server...
echo -------------------------------------------
echo  🌐 URL: http://localhost:5000
echo  🛑 Close this window to stop the server
echo -------------------------------------------
python -u app.py

pause