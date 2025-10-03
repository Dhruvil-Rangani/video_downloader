# app.py
from flask import Flask, render_template, request, send_file, after_this_request
import yt_dlp
import os
import unicodedata
import re
import shutil

app = Flask(__name__)

DOWNLOAD_FOLDER = '/tmp/downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def sanitize_filename(filename: str) -> str:
    # ASCII-only & safe
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    filename = re.sub(r'[^A-Za-z0-9._-]', '_', filename)
    if not filename.lower().endswith('.mp4'):
        filename += '.mp4'
    return filename

def find_ffmpeg_location():
    """
    Return a directory or path usable for yt-dlp's ffmpeg_location.
    Priority:
      1) env FFMPEG_PATH
      2) ffmpeg in PATH
      3) ./bin/ffmpeg (bundled)
    """
    candidates = [
        os.environ.get('FFMPEG_PATH'),
        shutil.which('ffmpeg'),
        os.path.abspath('./bin/ffmpeg'),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            # yt-dlp accepts a dir or a file path; both work
            return os.path.dirname(c) if os.path.isfile(c) else c
    return None

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.post('/download')
def download():
    url = (request.form.get('url') or '').strip()
    if not url:
        return render_template('index.html', error='Please paste a URL.')

    ffmpeg_loc = find_ffmpeg_location()
    if not ffmpeg_loc:
        return render_template(
            'index.html',
            error='ffmpeg not found on server. Bundle a static ffmpeg and set FFMPEG_PATH or add it to PATH.'
        )

    # Optional cookies (useful for private IG reels). Set env YTDLP_COOKIES or place cookies.txt next to app.
    cookiefile = os.environ.get('YTDLP_COOKIES') or 'cookies.txt'
    if not os.path.exists(cookiefile):
        cookiefile = None

    ydl_opts = {
        # predictable filename on disk; we rename only for the browser's download name
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
        'format': 'bv*+ba/b',              # best video+audio; fallback to best single file
        'merge_output_format': 'mp4',      # remux/merge to mp4
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

    # Remove None-valued keys to avoid yt-dlp complaining
    ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info.get('_type') == 'playlist' and info.get('entries'):
                info = info['entries'][0]

            vid_id = info.get('id')
            ext = info.get('ext', 'mp4')

            # Account for postprocessing remux rename
            file_path = os.path.join(DOWNLOAD_FOLDER, f'{vid_id}.{ext}')
            mp4_path  = os.path.join(DOWNLOAD_FOLDER, f'{vid_id}.mp4')
            if not os.path.exists(file_path) and os.path.exists(mp4_path):
                file_path = mp4_path

            if not os.path.exists(file_path):
                return render_template('index.html', error='Download finished but output file not found. Check logs/ffmpeg.')

            @after_this_request
            def cleanup(response):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
                return response

            download_name = sanitize_filename(f"{info.get('title') or 'video'}.mp4")
            return send_file(file_path, mimetype='video/mp4', as_attachment=True, download_name=download_name)

    except yt_dlp.utils.DownloadError as e:
        return render_template('index.html', error=f"Download error: {str(e)}")
    except Exception as e:
        return render_template('index.html', error=f"Failed: {str(e)}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
