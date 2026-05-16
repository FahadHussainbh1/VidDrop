@echo off
title VidDrop Global Server
cls
echo Starting VidDrop Tunnel...
:: Replace YOUR_TOKEN_HERE with the long token you copied from Cloudflare
cloudflared.exe tunnel run --token YOUR_TOKEN_HERE
pause