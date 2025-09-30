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
    """Sanitize filename by normalizing Unicode and removing non-ASCII characters."""
    # Normalize Unicode (e.g., convert '｜' to '|')
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    # Replace invalid characters with underscores
    filename = re.sub(r'[^A-Za-z0-9._-]', '_', filename)
    # Ensure .mp4 extension
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
            'format': 'best[ext=mp4]',
            'cookiefile': 'cookies.txt',
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'retries': 3,
            'sleep_interval': 1,
            'verbose': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            basename = os.path.basename(filename)
        
        file_path = os.path.join(DOWNLOAD_FOLDER, basename)
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        os.remove(file_path)
        
        # Sanitize filename for headers
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
        return render_template('index.html', error=str(e))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)