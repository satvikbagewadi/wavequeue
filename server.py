"""Local web server for the WaveQueue PWA and MP3 downloader."""
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
from urllib.parse import parse_qs, unquote, urlparse
import yt_dlp

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / 'downloads'

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        if self.path != '/api/download':
            self.send_error(404)
            return
        size = int(self.headers.get('Content-Length', 0))
        payload = json.loads(self.rfile.read(size))
        urls = [url.strip() for url in payload.get('urls', []) if isinstance(url, str) and url.startswith(('http://', 'https://'))]
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            self.send_error(500, 'FFmpeg is not available on PATH. Reopen the terminal after installing it.')
            return
        OUTPUT_DIR.mkdir(exist_ok=True)
        existing_mp3 = {path.name for path in OUTPUT_DIR.glob('*.mp3')}
        downloaded = []
        browser = os.environ.get('YTDLP_BROWSER', '').strip().lower()

        def on_postprocess(info):
            if info.get('status') == 'finished' and info.get('postprocessor') == 'FFmpegExtractAudio':
                filepath = Path(info.get('filepath') or info.get('info_dict', {}).get('_filename', ''))
                if filepath.suffix.lower() == '.mp3':
                    downloaded.append(filepath.name)

        options = {'format': 'bestaudio/best', 'outtmpl': str(OUTPUT_DIR / '%(title)s.%(ext)s'), 'noplaylist': True, 'ffmpeg_location': ffmpeg, 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}], 'postprocessor_hooks': [on_postprocess]}
        if browser in {'chrome', 'chromium', 'edge', 'firefox', 'brave', 'opera', 'vivaldi'}:
            options['cookiesfrombrowser'] = (browser,)
        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                for url in urls:
                    downloader.download([url])
        except yt_dlp.utils.DownloadError as error:
            message = str(error)
            if 'not a bot' in message.lower() or 'sign in to confirm' in message.lower():
                message = 'YouTube requires browser authentication for this request. Run the local app with YTDLP_BROWSER=chrome (or edge), rather than uploading browser cookies to the hosted service.'
            body = json.dumps({'error': message}).encode()
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        # Some yt-dlp versions expose the final path differently, so include
        # any recently generated MP3s as a safe fallback.
        if not downloaded:
            downloaded = [path.name for path in OUTPUT_DIR.glob('*.mp3') if path.name not in existing_mp3]
        body = json.dumps({'count': len(downloaded), 'files': sorted(set(downloaded))}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.path.startswith('/api/file?'):
            return super().do_GET()
        name = unquote(parse_qs(urlparse(self.path).query).get('name', [''])[0])
        requested = (OUTPUT_DIR / name).resolve()
        if requested.parent != OUTPUT_DIR.resolve() or requested.suffix.lower() != '.mp3' or not requested.is_file():
            self.send_error(404)
            return
        data = requested.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'audio/mpeg')
        self.send_header('Content-Disposition', f'attachment; filename="{requested.name}"')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8000'))
    host = '0.0.0.0' if os.environ.get('PORT') else 'localhost'
    print(f'WaveQueue running at http://{host}:{port}')
    ThreadingHTTPServer((host, port), Handler).serve_forever()
