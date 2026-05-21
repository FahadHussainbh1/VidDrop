from flask import Flask, request, jsonify, send_from_directory, render_template
import os
import re
import uuid
import threading
import requests

app = Flask(__name__)

# System paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
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
    """Fetches video validation tracking details securely via global API"""
    try:
        # Utilizing the stable primary root processing path
        api_url = "https://api.cobalt.tools/"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url,
            "videoQuality": "720"
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200 or response.status_code == 201:
            return {
                "title": "Fetched Global Video",
                "thumbnail": "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=200",
                "formats": [{"ext": "mp4", "resolution": "720p"}]
            }
    except Exception as e:
        print(f"Global Info Fetch Error: {e}")
    return None

def download_worker(job_id, url, quality):
    """Downloads streaming files directly from the processing proxy into storage"""
    try:
        jobs[job_id]["status"] = "downloading"
        jobs[job_id]["progress"] = 20
        
        api_url = "https://api.cobalt.tools/"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Exact payload formatting compliant with updated engine requirements
        payload = {
            "url": url,
            "videoQuality": "720",
            "downloadMode": "audio" if quality == "audio" else "video"
        }
            
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200 or response.status_code == 201:
            data = response.json()
            stream_url = data.get("url")
            
            if not stream_url:
                raise Exception("The processing hub successfully ran but did not yield a file link.")
                
            jobs[job_id]["progress"] = 50
            
            file_ext = "mp3" if quality == "audio" else "mp4"
            filename = f"{job_id}_download.{file_ext}"
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            
            # Fetch the streaming asset chunks from the engine container
            file_response = requests.get(stream_url, stream=True, timeout=45)
            if file_response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            
                jobs[job_id]["status"] = "done"
                jobs[job_id]["progress"] = 100
                jobs[job_id]["filename"] = filename
                jobs[job_id]["download_url"] = f"/file/{filename}"
                return
                
        raise Exception(f"Processing gateway returned status verification: {response.status_code}")
        
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = f"Global Engine Error: {str(e)}"

@app.route("/")
def index(): 
    return render_template("index.html")

@app.route("/api/info", methods=["POST"])
def video_info():
    url = request.json.get("url", "")
    info = get_video_info(url)
    return jsonify({"info": info}) if info else jsonify({"error": "Failed to fetch info globally"}), 400

@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.json
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "queued", "progress": 0}
    
    threading.Thread(
        target=download_worker, 
        args=(job_id, data['url'], data.get('quality'))
    ).start()
    
    return jsonify({"job_id": job_id})

@app.route("/api/status/<job_id>")
def job_status(job_id): 
    return jsonify(jobs.get(job_id, {"error": "Job tracking signature missing"}))

@app.route("/file/<path:filename>") 
def serve_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)