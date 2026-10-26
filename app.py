"""Local video-to-MP3 converter. Run with: python app.py"""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import imageio_ffmpeg
from flask import Flask, Response, jsonify, render_template, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from werkzeug.utils import secure_filename

app = Flask(__name__)
MAX_VIDEO_BYTES = 500 * 1024 * 1024
# Allow room for multipart headers in addition to the advertised file limit.
app.config["MAX_CONTENT_LENGTH"] = MAX_VIDEO_BYTES + 1024 * 1024


@app.get("/")
def index():
    return render_template("index.html")


@app.errorhandler(RequestEntityTooLarge)
def too_large(error):
    return jsonify(error="The upload is too large. The limit is 500 MB."), 413


@app.post("/extract")
def extract():
    workspace = None
    try:
        video = request.files.get("video")
        if video is None or not video.filename:
            return jsonify(error="Please select a video file."), 400

        workspace = Path(tempfile.mkdtemp(prefix="video-audio-"))
        source = workspace / "input"
        output = workspace / "audio.mp3"
        video.save(source)
        if source.stat().st_size > MAX_VIDEO_BYTES:
            shutil.rmtree(workspace, ignore_errors=True)
            return too_large(None)
        if not source.stat().st_size:
            shutil.rmtree(workspace)
            return jsonify(error="The selected file is empty."), 400
        ffmpeg = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
        result = subprocess.run(
            [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
             "-protocol_whitelist", "file,pipe", "-i", str(source),
             "-map", "0:a:0", "-vn", "-ac", "2", "-codec:a", "libmp3lame",
             "-q:a", "2", str(output)],
            capture_output=True, timeout=600,
        )
        if result.returncode != 0:
            shutil.rmtree(workspace)
            return jsonify(error="Could not extract audio. Choose a valid video with an audio track."), 422
        # Check and open the result before sending successful response headers.
        output_size = output.stat().st_size
        if not output_size:
            shutil.rmtree(workspace, ignore_errors=True)
            return jsonify(error="The video did not produce any audio."), 422
        audio = output.open("rb")
    except HTTPException:
        if workspace is not None:
            shutil.rmtree(workspace, ignore_errors=True)
        raise
    except subprocess.TimeoutExpired:
        if workspace is not None:
            shutil.rmtree(workspace, ignore_errors=True)
        return jsonify(error="Conversion took too long. Please try a shorter video."), 504
    except Exception:
        if workspace is not None:
            shutil.rmtree(workspace, ignore_errors=True)
        app.logger.exception("Audio extraction failed")
        return jsonify(error="Audio extraction failed. Please try again."), 500

    filename = f"{Path(secure_filename(video.filename)).stem or 'audio'}.mp3"

    def cleanup():
        audio.close()
        shutil.rmtree(workspace, ignore_errors=True)

    def download():
        try:
            while chunk := audio.read(1024 * 1024):
                yield chunk
        finally:
            cleanup()

    response = Response(download(), mimetype="audio/mpeg")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.headers["Content-Length"] = str(output_size)
    response.headers["Cache-Control"] = "no-store"
    response.call_on_close(cleanup)
    return response


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
