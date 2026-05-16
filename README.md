# VidDrop 🎬
### Download videos from YouTube, Instagram, Facebook, Twitter, Pinterest & more

---

## 🚀 Quick Setup (3 Steps)

### Step 1 — Install Python dependencies
```bash
pip install flask yt-dlp
```

### Step 2 — Start the server
```bash
cd viddrop
python app.py
```

### Step 3 — Open in browser
```
http://localhost:5000
```

---

## 📦 Supported Platforms
| Platform     | Videos | Audio |
|-------------|--------|-------|
| YouTube     | ✅     | ✅    |
| Instagram   | ✅     | ✅    |
| Facebook    | ✅     | ✅    |
| Twitter / X | ✅     | ✅    |
| Pinterest   | ✅     | —     |
| TikTok      | ✅     | ✅    |
| Reddit      | ✅     | ✅    |
| Vimeo       | ✅     | ✅    |
| Dailymotion | ✅     | ✅    |
| 1000+ more  | ✅     | ✅    |

---

## 🎯 Quality Options
- **Best Quality** — Highest available (up to 4K)
- **HD 720p** — Standard HD
- **SD 480p** — Mobile-friendly
- **Low 360p** — Small file size
- **Audio Only** — MP3 extraction

---

## 📁 Project Structure
```
viddrop/
├── app.py              ← Flask backend server
├── requirements.txt    ← Python dependencies
├── README.md           ← This file
├── templates/
│   └── index.html      ← Beautiful frontend
└── downloads/          ← Downloaded files (auto-cleaned)
```

---

## ⚙️ Configuration
Edit `app.py` to change:
- **Port**: Change `port=5000` in the last line
- **Download folder**: Change `DOWNLOAD_DIR`
- **File retention**: Change `7200` (seconds) in cleanup function

---

## 🛡️ Notes
- Downloaded files are auto-deleted after 2 hours
- No user accounts or signups needed
- Only download content you have the right to download
- Requires `ffmpeg` for merging HD video+audio (recommended)

### Install ffmpeg (optional but recommended)
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows — download from https://ffmpeg.org/download.html
```

---

## 🐛 Troubleshooting
- **"yt-dlp not installed"** → Run `pip install yt-dlp`
- **Download fails** → Update yt-dlp: `pip install -U yt-dlp`
- **No video+audio merge** → Install ffmpeg (see above)
- **Port in use** → Change port in `app.py`
