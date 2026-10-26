# Video to MP3

A Python Flask backend with a vanilla HTML, CSS, and JavaScript frontend.
Upload a video, preview the extracted audio, and download an MP3.

## Run on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python app.py
```

Open http://127.0.0.1:5000 in your browser. Stop the server with Ctrl+C.

FFmpeg is provided by the imageio-ffmpeg package, so a separate FFmpeg install
is not required. An existing FFmpeg on PATH takes precedence.

Uploads are limited to 500 MB. Conversion uses the first audio track, with a
10-minute processing timeout. Temporary files are removed after the download
or on conversion failure. Abruptly stopping the process can leave temporary
files in the operating system's temporary directory.

The app binds to localhost for personal use. Hosting it publicly requires a
production WSGI server, authentication or rate limiting, and resource limits.
