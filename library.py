import json
from pathlib import Path

import yt_dlp

from logger import LOG

LIB_DIR = Path.home() / '.config' / 'sound-helper' / 'library'


class Library:
    def __init__(self):
        LIB_DIR.mkdir(parents=True, exist_ok=True)

    def list_files(self):
        return sorted([
            f.name for f in LIB_DIR.iterdir()
            if f.is_file() and f.suffix in ('.opus', '.webm', '.m4a', '.mp3', '.ogg', '.wav', '.flac')
        ])

    def path(self, name):
        return str(LIB_DIR / name)

    def delete(self, name):
        p = LIB_DIR / name
        if p.exists():
            p.unlink()

    def download(self, url, progress_cb=None):
        LOG.info('[library] downloading: %s', url)
        out_tmpl = str(LIB_DIR / '%(title).100s.%(ext)s')

        def hook(d):
            if progress_cb:
                status = d.get('status', '')
                if status == 'downloading':
                    pct = d.get('_percent_str', '0%').replace('%', '')
                    try:
                        progress_cb(float(pct) / 100)
                    except ValueError:
                        pass
                elif status == 'finished':
                    progress_cb(1.0)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_tmpl,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'opus',
            }],
            'progress_hooks': [hook],
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if 'requested_downloads' in info:
                filename = info['requested_downloads'][0]['filepath']
            actual_path = Path(filename)
            if actual_path.suffix == '.webm':
                opus_path = actual_path.with_suffix('.opus')
                if opus_path.exists():
                    filename = str(opus_path)
            LOG.info('[library] downloaded: %s', filename)
            return Path(filename).name
