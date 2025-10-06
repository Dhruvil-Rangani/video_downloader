from flask import Flask, render_template, request, Response
import yt_dlp
import os
import unicodedata
import re

app = Flask(__name__)
DOWNLOAD_FOLDER = '/tmp/downloads'  # Render-compatible
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def sanitize_filename(filename):
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    filename = re.sub(r'[^A-Za-z0-9._-]', '_', filename)
    if not filename.lower().endswith('.mp4'):
        filename += '.mp4'
    return filename

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    try:
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'format': 'best[ext=mp4]',  # Prefer MP4 for compatibility
            'cookiefile': 'cookies.txt',
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'retries': 10,  # Aggressive retries
            'sleep_interval': 3,  # Avoid rate-limits
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.instagram.com/' if 'instagram.com' in url else 'https://www.youtube.com/',
                'Sec-Fetch-Mode': 'navigate',
            },
            'verbose': True,
            'ignoreerrors': False,  # Fail fast for debugging
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            basename = os.path.basename(filename)
        
        file_path = os.path.join(DOWNLOAD_FOLDER, basename)
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        os.remove(file_path)
        
        safe_basename = sanitize_filename(basename)
        
        return Response(
            data, 
            mimetype='video/mp4', 
            headers={
                "Content-Disposition": f"inline; filename={safe_basename}",
                "Content-Type": "video/mp4"
            }
        )
    
    except Exception as e:
        print(f"Download error: {str(e)}")
        return render_template('index.html', error="Failed to download. Try a public video/Reel or refresh the page.")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
