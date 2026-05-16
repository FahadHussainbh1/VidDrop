from flask import Flask, request, jsonify, send_from_directory, render_template
import subprocess
import os
import re
import uuid
import threading
import time
import json

app = Flask(__name__)

# This ensures the script always knows exactly where it is running from
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
FFMPEG_PATH = r"D:\viddrop\viddrop"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

jobs = {}

def detect_platform(url):
    url = url.lower()
    if "youtube.com" in url or "youtu.be" in url: return "youtube"
    if "instagram.com" in url: return "instagram"
    if "facebook.com" in url or "fb.watch" in url: return "facebook"
    if "tiktok.com" in url: return "tiktok"
    if "pinterest.com" in url or "pin.it" in url: return "pinterest"
    return "other"

def get_video_info(url):
    try:
        # Added --ffmpeg-location and errors='replace'
        result = subprocess.run(
            ["python", "-m", "yt_dlp", "--ffmpeg-location", FFMPEG_PATH, "--dump-json", "--no-playlist", url],
            capture_output=True, text=True, timeout=30, errors='replace'
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "title": data.get("title", "Video"),
                "thumbnail": data.get("thumbnail", ""),
                "formats": [{"ext": f.get("ext"), "resolution": f.get("resolution")} for f in data.get("formats", [])]
            }
    except Exception as e:
        print(f"Info Error: {e}")
    return None

def download_video(job_id, url, quality, fmt):
    try:
        jobs[job_id]["status"] = "downloading"
        
        # Template uses job_id to keep it unique
        output_template = os.path.join(DOWNLOAD_DIR, f"{job_id}_%(title).80s.%(ext)s")

        # The FIXED Command
        # Use the full path directly to the exe
        ffmpeg_exe = os.path.join(FFMPEG_PATH, "ffmpeg.exe")

        cmd = [
            "python", "-m", "yt_dlp", 
            "--ffmpeg-location", ffmpeg_exe, 
            "--no-playlist", 
            "-o", output_template,
            "--merge-output-format", "mp4",
            "--fixup", "detect_or_warn", # Helps fix stream errors
            url
        ]

        # Quality Logic
        # Quality Logic - More flexible for Pinterest/Facebook
        if quality == "best":
            # This asks for high quality MP4, but falls back to ANY best quality if that fails
            cmd += ["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"]
        elif quality == "audio":
            cmd += ["-f", "bestaudio", "-x", "--audio-format", "mp3"]
        else:
            # Standard quality fallback
            cmd += ["-f", "best"]

        cmd.append(url)

        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace'
        )

        for line in process.stdout:
            print(f"DEBUG: {line.strip()}") # Watch this in your CMD window!
            prog_match = re.search(r'(\d+\.?\d*)%', line)
            if prog_match:
                jobs[job_id]["progress"] = float(prog_match.group(1))

        process.wait()

        if process.returncode == 0:
            # Look for the file and RENAME it to be safe for browsers
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(job_id):
                    old_path = os.path.join(DOWNLOAD_DIR, f)
                    # Safe Name: No spaces, no weird characters
                    safe_name = re.sub(r'[^\w\d.]', '_', f)
                    new_path = os.path.join(DOWNLOAD_DIR, safe_name)
                    
                    if os.path.exists(new_path): os.remove(new_path) # Clean old if exists
                    os.rename(old_path, new_path)
                    
                    jobs[job_id]["status"] = "done"
                    jobs[job_id]["filename"] = safe_name
                    jobs[job_id]["download_url"] = f"/file/{safe_name}"
                    return

        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = "Download failed. Check terminal for FFmpeg errors."
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)

@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/info", methods=["POST"])
def video_info():
    url = request.json.get("url", "")
    info = get_video_info(url)
    return jsonify({"info": info}) if info else jsonify({"error": "Failed"}), 400

@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.json
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "queued", "progress": 0}
    threading.Thread(target=download_video, args=(job_id, data['url'], data.get('quality'), data.get('format'))).start()
    return jsonify({"job_id": job_id})

@app.route("/api/status/<job_id>")
def job_status(job_id): return jsonify(jobs.get(job_id, {"error": "Not found"}))

@app.route("/file/<path:filename>") # Fixed path route
def serve_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)