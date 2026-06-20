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
    # 🚀 NEW PLATFORMS ADDED
    if "drive.google.com" in url: return "google_drive"
    if "terabox.com" in url or "nebx.cc" in url or "teraboxapp" in url: return "terabox"
    return "other"

def download_video(job_id, url, quality, fmt):
    try:
        jobs[job_id]["status"] = "downloading"
        abs_download_dir = os.path.abspath(DOWNLOAD_DIR)
        
        platform = detect_platform(url)

        # =======================================================
        # 🚀 1. GOOGLE DRIVE DOWNLOAD LOGIC
        # =======================================================
        # =======================================================
        # 🚀 1. GOOGLE DRIVE LARGE FILE BYPASS LOGIC
        # =======================================================
        if platform == "google_drive":
            file_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url) or re.search(r'id=([a-zA-Z0-9-_]+)', url)
            if not file_id_match:
                raise Exception("Invalid Google Drive URL structure or file is not public.")
            
            file_id = file_id_match.group(1)
            
            import requests
            safe_name = f"{job_id}_drive_video.mp4"
            output_path = os.path.join(abs_download_dir, safe_name)
            
            # Create a persistent session to hold Google's tracking cookies
            session = requests.Session()
            
            # Step 1: Send a request to see if Google throws a large file confirmation page
            base_url = "https://docs.google.com/uc?export=download"
            response = session.get(base_url, params={'id': file_id}, stream=True)
            
            # Step 2: Extract confirmation token if present in cookies or HTML content
            confirm_token = None
            for key, value in response.cookies.items():
                if key.startswith('download_warning'):
                    confirm_token = value
                    break
                    
            # If token wasn't in cookies, look inside the html page content
            if not confirm_token:
                match = re.search(r'confirm=([A-Za-z0-9_]+)', response.text)
                if match:
                    confirm_token = match.group(1)
            
            # Step 3: If confirmation token is found, make the final request with the token
            params = {'id': file_id}
            if confirm_token:
                params['confirm'] = confirm_token
                
            final_response = session.get(base_url, params=params, stream=True)
            final_response.raise_for_status()
            
            # Step 4: Stream down the actual large video chunk by chunk
            total_length = int(final_response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in final_response.iter_content(chunk_size=1024 * 1024): # 1MB chunks for speed
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_length > 0:
                            jobs[job_id]["progress"] = round((downloaded / total_length) * 100, 2)
                        else:
                            # If content-length is hidden by Google, show mock progress based on megabytes downloaded
                            jobs[job_id]["progress"] = f"Downloaded {round(downloaded / (1024*1024), 1)} MB"
            
            jobs[job_id]["status"] = "done"
            jobs[job_id]["filename"] = safe_name
            jobs[job_id]["download_url"] = f"/file/{safe_name}"
            return

        # =======================================================
        # 🚀 2. TERABOX & OTHER PLATFORMS (Via yt-dlp)
        # =======================================================
        # Default template for standard platforms
        output_template = os.path.join(abs_download_dir, f"{job_id}_%(title).50s.%(ext)s")

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
            'geo_bypass': True,
            'ignoreerrors': True,
            'progress_hooks': [progress_hook],
        }

        # 🚀 CRITICAL FIXED: TeraBox strict single file routing
        if platform == "terabox":
            ydl_opts['format'] = 'best'
            # Force target path to be completely clean and predictible without dynamic titles
            ydl_opts['outtmpl'] = os.path.join(abs_download_dir, f"{job_id}_terabox.mp4")
        else:
            ydl_opts['format'] = 'bestvideo+bestaudio/best'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # 🚀 SMART CAPTURE & RENAME SYSTEM
        import time
        for attempt in range(15):
            current_files = os.listdir(abs_download_dir)
            
            # Special check for forced TeraBox output
            if platform == "terabox":
                forced_name = f"{job_id}_terabox.mp4"
                if forced_name in current_files:
                    old_path = os.path.join(abs_download_dir, forced_name)
                    safe_name = f"{job_id}.mp4"
                    new_path = os.path.join(abs_download_dir, safe_name)
                    
                    if os.path.exists(new_path): os.remove(new_path)
                    os.rename(old_path, new_path)
                    
                    jobs[job_id]["status"] = "done"
                    jobs[job_id]["filename"] = safe_name
                    jobs[job_id]["download_url"] = f"/file/{safe_name}"
                    return

            # Fallback normal checking for other platforms
            for f in current_files:
                if f.startswith(job_id) and not any(ext in f for ext in ['.part', '.ytdl', '.temp', '.download']):
                    old_path = os.path.join(abs_download_dir, f)
                    ext = os.path.splitext(f)[1] or '.mp4'
                    safe_name = f"{job_id}{ext}"
                    new_path = os.path.join(abs_download_dir, safe_name)
                    
                    if os.path.exists(new_path): os.remove(new_path)
                    os.rename(old_path, new_path)
                    
                    jobs[job_id]["status"] = "done"
                    jobs[job_id]["filename"] = safe_name
                    jobs[job_id]["download_url"] = f"/file/{safe_name}"
                    return
            time.sleep(1)

        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = f"File processed but not captured. Active files: {os.listdir(abs_download_dir)}"    
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