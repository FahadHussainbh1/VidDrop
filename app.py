from flask import Flask, request, jsonify, send_from_directory, render_template, Response # 👈 YAHAN 'Response' ADD KAR DIYA
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

# Cookies file ka path define kiya jo hum Render par banayein ge
COOKIES_PATH = os.path.join(BASE_DIR, "cookies.txt")

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
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'geo_bypass': True,
        }

        # Agar system mein cookies file maujood hai toh automatically load kare
        if os.path.exists(COOKIES_PATH):
            ydl_opts['cookiefile'] = COOKIES_PATH

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
        
        abs_download_dir = os.path.abspath(DOWNLOAD_DIR)
        if not os.path.exists(abs_download_dir):
            os.makedirs(abs_download_dir)
            
        output_template = os.path.join(abs_download_dir, f"{job_id}_%(title).50s.%(ext)s")

        def progress_hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    jobs[job_id]["progress"] = round((downloaded / total) * 100, 2)

        # 🚀 ULTRA COMPATIBLE OPTIONS
        ydl_opts = {
            'ffmpeg_location': FFMPEG_PATH,
            'no_playlist': True,
            'outtmpl': output_template,
            'geo_bypass': True,
            'ignoreerrors': False, # Error throw karne dein taaki exact reason dikhe skip hone ke bajaye
            'format_sort': ['res:720', 'ext:mp4:m4a'], # Automatic priority routing
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
            }
        }

        if os.path.exists(COOKIES_PATH):
            ydl_opts['cookiefile'] = COOKIES_PATH

        # 🚀 ULTRA-LIGHT CRITICAL FORMAT FORCING
        if quality == "audio":
            ydl_opts['format'] = 'ba/b'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }]
        else:
            # Kuch complex nahi—direct single video stream filter ya default worst-case fallback
            ydl_opts['format'] = 'b/ext:mp4:m4a/worst'

        # Execute download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Smart rename loop
        import time
        file_found = False
        for attempt in range(15):
            current_files = os.listdir(abs_download_dir)
            for f in current_files:
                if f.startswith(job_id) and not any(ext in f for ext in ['.part', '.ytdl', '.temp']):
                    old_path = os.path.join(abs_download_dir, f)
                    ext = os.path.splitext(f)[1] or '.mp4'
                    safe_name = f"{job_id}{ext}"
                    new_path = os.path.join(abs_download_dir, safe_name)
                    
                    if os.path.exists(new_path): os.remove(new_path)
                    os.rename(old_path, new_path)
                    
                    jobs[job_id]["status"] = "done"
                    jobs[job_id]["filename"] = safe_name
                    jobs[job_id]["download_url"] = f"/file/{safe_name}"
                    file_found = True
                    return
            time.sleep(1)

        if not file_found:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = f"Render block active. Files found: {os.listdir(abs_download_dir)}"
            
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = f"Final try error: {str(e)}"

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
        
    feedback_file = os.path.join(BASE_DIR, "user_feedback.txt")
    try:
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(f"--- New Feedback ---\n{feedback_message}\n\n")
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to save feedback: {str(e)}"}), 500

# 👇 ROBOTS.TXT ROUTE ADDED HERE CLEANLY
@app.route("/robots.txt")
def robots_txt():
    # Strict plain text content headers with explicit absolute access
    content = "User-agent: *\nAllow: /\nDisallow:\n"
    response = Response(content, mimetype="text/plain")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# 👇 GOOGLE DIRECT VERIFICATION ROUTE
@app.route("/google877c2bdc7ac64d06.html")
def google_verify():
    return "google-site-verification: google877c2bdc7ac64d06.html", 200, {'Content-Type': 'text/html'}


@app.route("/sitemap.xml")
def sitemap():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://viddrop-7e3b.onrender.com/</loc>
            <changefreq>daily</changefreq>
            <priority>1.0</priority>
        </url>
    </urlset>"""
    return Response(xml_content, mimetype='application/xml')