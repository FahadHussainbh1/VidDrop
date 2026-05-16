#!/bin/bash
echo ""
echo "  ==========================="
echo "   VidDrop - Video Downloader"
echo "  ==========================="
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python3 not found. Install from https://python.org"
    exit 1
fi

# Install dependencies
echo "[1/2] Installing dependencies..."
pip3 install flask yt-dlp -q

echo "[2/2] Starting VidDrop server..."
echo ""
echo "  Open your browser at: http://localhost:5000"
echo "  Press Ctrl+C to stop the server."
echo ""
python3 app.py
