from flask import Flask, render_template, request, send_file, after_this_request, jsonify
import yt_dlp
import os, re, unicodedata, shutil, base64

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
    candidates = [
        os.environ.get('FFMPEG_PATH'),
        shutil.which('ffmpeg'),
        os.path.abspath('./bin/ffmpeg'),
        os.path.abspath('./bin/ffmpeg.exe'),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return os.path.dirname(c) if os.path.isfile(c) else c
    return None

def materialize_cookies():
    """
    Return a cookies.txt path if available via env, otherwise None.
    Priority: YTDLP_COOKIES_B64 -> YTDLP_COOKIES -> ./cookies.txt
    """
    b64 = os.environ.get('YTDLP_COOKIES_B64')
    if b64:
        path = '/tmp/cookies.txt'
        try:
            with open(path, 'wb') as f:
                f.write(base64.b64decode(b64))
            return path
        except Exception:
            pass
    path_env = os.environ.get('YTDLP_COOKIES')
    if path_env and os.path.exists(path_env):
        return path_env
    local = os.path.abspath('cookies.txt')
    if os.path.exists(local):
        return local
    return None

def wants_json():
    # Our frontend sends this header; fall back to Accept sniffing
    if request.headers.get('X-Requested-With', '').lower() == 'fetch':
        return True
    accept = (request.headers.get('Accept') or '').lower()
    return 'application/json' in accept

@app.get('/')
def index():
    return render_template('index.html')

@app.post('/download')
def download():
    url = (request.form.get('url') or '').strip()
    if not url:
        if wants_json():
            return jsonify(error='Please paste a URL.'), 400
        return render_template('index.html', error='Please paste a URL.'), 400

    ffmpeg_loc = find_ffmpeg()
    cookiefile = materialize_cookies()

    # With ffmpeg: best video+audio; otherwise, require progressive single-file fallback
    fmt_with_ffmpeg = 'bv*+ba/b'
    fmt_progressive = 'best[acodec!=none][vcodec!=none][protocol^=http]/best[acodec!=none][vcodec!=none]'

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
        # polite headers
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}

    # Helpful explicit failure if ffmpeg is missing
    if not ffmpeg_loc:
        # Without ffmpeg, many YT links fail because no progressive stream.
        # We allow it to try, but tell users why if it fails.
        no_ffmpeg_hint = ("Server has no ffmpeg; falling back to progressive-only. "
                          "Some YouTube links won't work without cookies or ffmpeg.")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info.get('_type') == 'playlist' and info.get('entries'):
                info = info['entries'][0]

            vid_id = info.get('id')
            candidates = [f'{vid_id}.mp4', f'{vid_id}.{info.get("ext","mp4")}']
            file_path = next((os.path.join(DOWNLOAD_FOLDER, c)
                              for c in candidates
                              if os.path.exists(os.path.join(DOWNLOAD_FOLDER, c))), None)

            if not file_path:
                msg = 'Download finished but output file not found. Check ffmpeg/postprocessing.'
                if wants_json():
                    return jsonify(error=msg), 500
                return render_template('index.html', error=msg), 500

            @after_this_request
            def cleanup(resp):
                try: os.remove(file_path)
                except Exception: pass
                return resp

            dl_name = sanitize_filename(f"{info.get('title') or 'video'}.mp4")
            return send_file(file_path, mimetype='video/mp4', as_attachment=True, download_name=dl_name)

    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        # Friendly hint for the specific bot/cookie case
        if 'confirm you’re not a bot' in msg.lower() or 'sign in' in msg.lower():
            msg = ("YouTube is requiring cookies for this server IP. "
                   "Add browser cookies (Netscape format) via YTDLP_COOKIES_B64 or YTDLP_COOKIES "
                   "and redeploy. See README.")
        elif not ffmpeg_loc:
            msg = f"{msg} — Hint: {no_ffmpeg_hint}"
        if wants_json():
            return jsonify(error=f"Download error: {msg}"), 400
        return render_template('index.html', error=f"Download error: {msg}"), 400

    except Exception as e:
        msg = f"Failed: {e}"
        if wants_json():
            return jsonify(error=msg), 500
        return render_template('index.html', error=msg), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
