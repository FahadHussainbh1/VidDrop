from flask import Flask, request, jsonify, send_from_directory, render_template
import os
import re
import uuid
import threading
import json
import imageio_ffmpeg
import yt_dlp

app = Flask(__name__)

# System paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

# Fetches built-in FFmpeg path cleanly
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

jobs = {}

def detect_platform(url):
    url = url.lower()
    if "instagram.com" in url: return "instagram"
    if "facebook.com" in url or "fb.watch" in url: return "facebook"
    if "tiktok.com" in url: return "tiktok"
    if "pinterest.com" in url or "pin.it" in url: return "pinterest"
    return "other"

def get_video_info(url):
    try:
        ydl_opts = {
            'ffmpeg_location': FFMPEG_PATH,
            'no_playlist': True,
            'quiet': True,
            # 👇 FORAN BYPASS ADDED HERE (FOR INFO FETCHING)
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'geo_bypass': True,
            'username': 'oauth2',
            'password': '',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)
            if data:
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
        output_template = os.path.join(DOWNLOAD_DIR, f"{job_id}_%(title).80s.%(ext)s")

        def progress_hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    jobs[job_id]["progress"] = round((downloaded / total) * 100, 2)

        ydl_opts = {
            'ffmpeg_location': FFMPEG_PATH,
            'no_playlist': True,
            'outtmpl': output_template,
            'merge_output_format': 'mp4',
            'fixup': 'detect_or_warn',
            'progress_hooks': [progress_hook],
            # 👇 FORAN BYPASS ADDED HERE (FOR ACTUAL DOWNLOADING)
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'geo_bypass': True,
            'username': 'oauth2',
            'password': '',
        }

        if quality == "audio":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            ydl_opts['format'] = 'bestvideo+bestaudio/bestvideo/bestaudio/best'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(job_id):
                old_path = os.path.join(DOWNLOAD_DIR, f)
                safe_name = re.sub(r'[^\w\d.]', '_', f)
                new_path = os.path.join(DOWNLOAD_DIR, safe_name)
                
                if os.path.exists(new_path): os.remove(new_path) 
                os.rename(old_path, new_path)
                
                jobs[job_id]["status"] = "done"
                jobs[job_id]["filename"] = safe_name
                jobs[job_id]["download_url"] = f"/file/{safe_name}"
                return

        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = "File processing complete but target output file missing."
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = f"Download failed: {str(e)}"

@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/info", methods=["POST"])
def video_info():
    url = request.json.get("url", "")
    info = get_video_info(url)
    return jsonify({"info": info}) if info else jsonify({"error": "Failed to fetch info"}), 400

@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.json
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "queued", "progress": 0}
    threading.Thread(target=download_video, args=(job_id, data['url'], data.get('quality'), data.get('format'))).start()
    return jsonify({"job_id": job_id})

@app.route("/api/status/<job_id>")
def job_status(job_id): return jsonify(jobs.get(job_id, {"error": "Not found"}))

@app.route("/file/<path:filename>") 
def serve_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

@app.route("/api/feedback", methods=["POST"])
def receive_feedback():
    data = request.json
    feedback_message = data.get("message", "").strip()
    
    if not feedback_message:
        return jsonify({"error": "Feedback message cannot be empty"}), 400
        
    # Append feedback to a local text file inside your project structure
    feedback_file = os.path.join(BASE_DIR, "user_feedback.txt")
    try:
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(f"--- New Feedback ---\n{feedback_message}\n\n")
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to save feedback: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)