from flask import Flask, render_template, request, Response
import yt_dlp
import os

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    try:
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',  # Save file with title
            'format': 'best',  # Best quality (change to 'bestvideo+bestaudio/best' if FFmpeg merging is desired)
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            basename = os.path.basename(filename)
        
        file_path = os.path.join(DOWNLOAD_FOLDER, basename)
        
        # Read file into memory
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Delete the file immediately after reading (file is closed, no lock)
        os.remove(file_path)
        
        # Return the file as a direct download response
        return Response(data, mimetype='video/mp4', headers={"Content-Disposition": f"attachment; filename={basename}"})
    
    except Exception as e:
        return render_template('index.html', error=str(e))

if __name__ == '__main__':
    app.run(debug=True)