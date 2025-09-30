# Video Downloader (Flask + yt-dlp)

A tiny web app to download **YouTube videos** and **Instagram Reels** via [yt-dlp](https://github.com/yt-dlp/yt-dlp) on a simple Flask server.  
Frontend uses `fetch()` to trigger a download so the **Download** button never gets stuck on “Processing…”. The UI is also mobile‑friendly.

---

## ✨ Features
- Paste a URL → get a direct video download.
- Works for YouTube and Instagram (public content).
- Button state resets reliably after download.
- Mobile tweaks (viewport, URL keyboard, no iOS zoom on input).
- Auto‑creates a local `downloads/` folder and deletes temp files after sending.

---

## 🏁 Quick Start

### Requirements
- Python 3.9+ (3.11+ recommended)
- pip
- (Optional) **FFmpeg** — required for format merging/conversion  
  - macOS: `brew install ffmpeg`  
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`  
  - Windows (Chocolatey): `choco install ffmpeg`

### Installation
```bash
# 1) Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2) Install dependencies
pip install -r requirements.txt
```

Create a minimal **requirements.txt** if you don’t already have one:
```txt
Flask>=3.0.0
yt-dlp>=2024.8.6
```

### Run
```bash
python app.py
# App runs on http://127.0.0.1:5000
```

Open the app in your browser, paste a video/reel URL, and hit **Download**.

---

## 🧱 Project Structure
```
.
├─ app.py               # Flask server with / and /download routes
├─ templates/
│  └─ index.html        # Simple UI (mobile friendly + fetch-based download)
├─ downloads/           # Temporary files (auto-created)
└─ requirements.txt
```

---

## 🖥️ How It Works
- **Server** uses `yt_dlp.YoutubeDL` to download the media to `downloads/`.
- The file is **sent to the browser** and then **deleted** from the server.
- **Client** intercepts the form submit, `POST`s with `fetch()`, converts the response to a Blob, and triggers a download via a temporary `<a>` element.  
  This keeps the page alive and the button can safely reset its label/state.

Your current code already implements these behaviors. If you prefer **streaming** instead of reading the whole file into memory, see the snippet below.

---

## 📄 Frontend Notes
**Keep your look & feel** (mono font + green button). For better mobile UX:
- Add: `<meta name="viewport" content="width=device-width,initial-scale=1" />`
- Ensure the URL input has comfortable tap size and avoids iOS zoom:  
  `#url { font-size: 16px; min-height: 44px; }`
- Use a URL‑aware field:
```html
<input type="url" id="url" name="url" required inputmode="url"
       autocapitalize="none" autocorrect="off" spellcheck="false"
       autocomplete="off" />
```
**Safari fallback:** Some Safari versions ignore `a.download`. Add a safe fallback that navigates to the Blob URL if needed so users can Share/Save.

---

## ⚙️ Server Options (yt-dlp)
You can tweak `ydl_opts` in `app.py`:
```python
ydl_opts = {
    "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
    "format": "best",              # or "bestvideo+bestaudio/best" (needs FFmpeg)
    "noplaylist": True,
    # For MP4 output (requires FFmpeg):
    # "merge_output_format": "mp4",
    # "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],

    # For private/age-gated content you’re authorized to access:
    # "cookiefile": "cookies.txt",
}
```

> **Instagram private / age-gated / members-only:** you’ll need a `cookies.txt` exported from your browser session and set `cookiefile` as above. Only download content you have rights to.

---

## 🚀 Streaming (Recommended for Large Files)
Instead of reading the whole file into memory, stream it and clean up after the response:

```python
from flask import send_file, after_this_request
import mimetypes, os

@app.route("/download", methods=["POST"])
def download():
    url = request.form["url"]
    try:
        ydl_opts = {
            "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
            "format": "best",
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            basename = os.path.basename(filename)

        file_path = os.path.join(DOWNLOAD_FOLDER, basename)

        @after_this_request
        def cleanup(response):
            try: os.remove(file_path)
            except Exception as e: app.logger.warning(f"Cleanup failed: {e}")
            return response

        mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        return send_file(file_path, as_attachment=True, download_name=basename, mimetype=mime)
    except Exception as e:
        return str(e), 400
```

---

## 🧪 Endpoints
- `GET /` — renders the form.
- `POST /download` — expects form field `url` (string).  
  **Response:** the video file as an attachment (Blob) or an error string with HTTP 400.

---

## 🧰 Troubleshooting
- **Extractor errors / download fails** → Update yt-dlp: `pip install -U yt-dlp`
- **Very slow on YouTube** → Provider throttling; ensure FFmpeg is installed for fastest merges.
- **Instagram private content** → Requires session cookies (`cookiefile`).
- **Safari doesn’t save** → Use the provided fallback that opens the Blob URL to save via Share sheet.
- **Large files & memory usage** → Use the **streaming** approach above.

---

## 🔒 Security
- Validates no input by default; add rate limiting and domain allow‑lists before exposing publicly.
- Run behind a reverse proxy (Nginx/Caddy) and disable debug in production.
- Consider containerizing and running as a low‑privileged user.

---

## 📦 Deploying
Example (Gunicorn):
```bash
pip install gunicorn
gunicorn -w 2 -k gthread -t 120 app:app
```
Place behind Nginx/Caddy, enable HTTPS, and set sensible timeouts for large downloads.

---

## ⚖️ Legal
This project is for **personal/educational** use. Respect each platform’s **Terms of Service** and only download content you **own** or are **authorized** to download.

---

## 📝 License
MIT — do whatever you want; just don’t hold the authors liable.
