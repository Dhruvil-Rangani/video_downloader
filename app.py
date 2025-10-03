from flask import Flask, render_template, request, send_file, after_this_request
import yt_dlp
import os, re, unicodedata, shutil

app = Flask(__name__)
DOWNLOAD_FOLDER = '/tmp/downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def sanitize_filename(s: str) -> str:
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^A-Za-z0-9._-]', '_', s)
    if not s.lower().endswith('.mp4'):
        s += '.mp4'
    return s

def find_ffmpeg():
    """
    Return a path usable for yt-dlp's ffmpeg_location.
    Priority:
      1) env FFMPEG_PATH (file or directory)
      2) ffmpeg on PATH
      3) ./bin/ffmpeg(.exe) shipped with app
    """
    candidates = [
        os.environ.get('FFMPEG_PATH'),
        shutil.which('ffmpeg'),
        os.path.abspath('./bin/ffmpeg'),
        os.path.abspath('./bin/ffmpeg.exe'),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            # yt-dlp accepts a dir or file path
            return os.path.dirname(c) if os.path.isfile(c) else c
    return None

@app.get('/')
def index():
    return render_template('index.html')

@app.post('/download')
def download():
    url = (request.form.get('url') or '').strip()
    if not url:
        return render_template('index.html', error='Please paste a URL.'), 400

    ffmpeg_loc = find_ffmpeg()

    # If we have ffmpeg, use best video+audio; otherwise, force a single progressive file (lower quality, not guaranteed)
    fmt_with_ffmpeg = 'bv*+ba/b'  # best video+best audio; fallback to best single file
    fmt_progressive = 'best[acodec!=none][vcodec!=none][protocol^=http]/best[acodec!=none][vcodec!=none]'
    # ^ tries to ensure a single file (no merging), preferring HTTP progressive

    cookiefile = os.environ.get('YTDLP_COOKIES') or 'cookies.txt'
    if not os.path.exists(cookiefile):
        cookiefile = None

    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
        'format': fmt_with_ffmpeg if ffmpeg_loc else fmt_progressive,
        'merge_output_format': 'mp4' if ffmpeg_loc else None,
        'noplaylist': True,
        'retries': 10,
        'fragment_retries': 10,
        'sleep_interval_requests': 1,
        'max_sleep_interval_requests': 3,
        'restrictfilenames': True,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': ffmpeg_loc,
        'cookiefile': cookiefile,
    }
    # Strip None values
    ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info.get('_type') == 'playlist' and info.get('entries'):
                info = info['entries'][0]

            vid_id = info.get('id')
            # after postprocessing, ext can change (e.g., .mp4)
            candidates = [f'{vid_id}.mp4', f'{vid_id}.{info.get("ext","mp4")}']
            file_path = next((os.path.join(DOWNLOAD_FOLDER, c) for c in candidates if os.path.exists(os.path.join(DOWNLOAD_FOLDER, c))), None)

            if not file_path:
                return render_template('index.html', error='Download finished but file not found (check ffmpeg).'), 500

            @after_this_request
            def cleanup(resp):
                try: os.remove(file_path)
                except Exception: pass
                return resp

            download_name = sanitize_filename(f"{info.get('title') or 'video'}.mp4")
            return send_file(file_path, mimetype='video/mp4', as_attachment=True, download_name=download_name)

    except yt_dlp.utils.DownloadError as e:
        # Typical causes: private IG without cookies, geo/age restriction, no progressive stream when ffmpeg is absent
        return render_template('index.html', error=f"Download error: {e}"), 400
    except Exception as e:
        return render_template('index.html', error=f"Failed: {e}"), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
