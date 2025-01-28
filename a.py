from flask import Flask, render_template, request, send_from_directory
import os
import yt_dlp
from urllib.parse import quote
import browser_cookie3

app = Flask(__name__)
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 500  # 500MB limit

if not os.path.exists(app.config['DOWNLOAD_FOLDER']):
    os.makedirs(app.config['DOWNLOAD_FOLDER'])

def sanitize_filename(filename):
    return "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_')).rstrip()

def get_youtube_cookies():
    """Fetch cookies from Firefox."""
    try:
        return browser_cookie3.firefox(domain_name='youtube.com')
    except Exception as e:
        print(f"Error fetching cookies: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        format_type = request.form['format']
        
        try:
            # Fetch cookies
            cookies = get_youtube_cookies()

            # Fetch video information
            with yt_dlp.YoutubeDL({'quiet': True, 'cookiefile': cookies}) as ydl:
                info = ydl.extract_info(url, download=False)
                video_id = info['id']
                title = sanitize_filename(info['title'])
                filename = f"{video_id}.{format_type}"

            # Check if file already exists
            if os.path.exists(os.path.join(app.config['DOWNLOAD_FOLDER'], filename)):
                return render_template('index.html', 
                                    download_link=quote(filename),
                                    title=title)

            # Download options
            ydl_opts = {
                'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], f'{video_id}.%(ext)s'),
                'quiet': True,
                'nooverwrites': False,
                'overwrites': True,
                'cookiefile': cookies
            }

            if format_type == 'mp3':
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            else:
                ydl_opts.update({
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                })

            # Download video/audio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            return render_template('index.html', 
                                download_link=quote(filename),
                                title=title)

        except Exception as e:
            return render_template('index.html', error=str(e))

    return render_template('index.html')

@app.route('/downloads/<path:filename>')
def download_file(filename):
    return send_from_directory(
        app.config['DOWNLOAD_FOLDER'],
        filename,
        as_attachment=True,
        download_name=f"{request.args.get('title', 'video')}.{filename.split('.')[-1]}"
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
