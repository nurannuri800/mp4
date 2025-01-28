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
    """Dosya adını güvenli hale getirir."""
    return "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_')).rstrip()

def save_cookies_to_file(filepath):
    """Browser'dan alınan çerezleri dosyaya kaydeder."""
    try:
        cookies = browser_cookie3.firefox(domain_name='youtube.com')
        with open(filepath, 'w') as f:
            for cookie in cookies:
                f.write(f"{cookie.domain}\tTRUE\t{cookie.path}\t{'TRUE' if cookie.secure else 'FALSE'}\t{cookie.expires or 0}\t{cookie.name}\t{cookie.value}\n")
        return filepath
    except Exception as e:
        print(f"Error saving cookies: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        format_type = request.form['format']
        
        try:
            # Çerez dosyasını oluştur
            cookie_file = save_cookies_to_file('youtube_cookies.txt')
            if not cookie_file:
                return render_template('index.html', error="Çerez dosyası oluşturulamadı.")

            # Video bilgilerini al
            with yt_dlp.YoutubeDL({'quiet': True, 'cookiefile': cookie_file}) as ydl:
                info = ydl.extract_info(url, download=False)
                video_id = info['id']
                title = sanitize_filename(info['title'])
                filename = f"{video_id}.{format_type}"

            # Eğer dosya zaten varsa, kullanıcıya göster
            if os.path.exists(os.path.join(app.config['DOWNLOAD_FOLDER'], filename)):
                return render_template('index.html', 
                                       download_link=quote(filename),
                                       title=title)

            # İndirme ayarları
            ydl_opts = {
                'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], f'{video_id}.%(ext)s'),
                'quiet': True,
                'cookiefile': cookie_file,
                'nooverwrites': False,
                'overwrites': True
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

            # İndirme işlemi
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
    """İndirilebilir dosyayı kullanıcıya sunar."""
    return send_from_directory(
        app.config['DOWNLOAD_FOLDER'],
        filename,
        as_attachment=True,
        download_name=f"{request.args.get('title', 'video')}.{filename.split('.')[-1]}"
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
