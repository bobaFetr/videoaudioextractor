import io
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from werkzeug.wrappers import Request

import imageio_ffmpeg
import app as converter


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.temp_patch = patch.object(tempfile, "tempdir", self.folder.name)
        self.temp_patch.start()
        self.client = converter.app.test_client()
        self.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    def tearDown(self):
        self.temp_patch.stop()
        self.folder.cleanup()

    def upload(self, data, filename="video.mp4"):
        return self.client.post("/extract", data={"video": (io.BytesIO(data), filename)}, buffered=True)

    def assert_clean(self):
        self.assertEqual(list(Path(self.folder.name).glob("video-audio-*")), [])

    def make_video(self, audio=True):
        path = Path(self.folder.name) / "sample.mkv"
        command = [self.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "color=s=64x64:d=0.2"]
        if audio:
            command += ["-f", "lavfi", "-i", "anullsrc=channel_layout=5.1:sample_rate=48000", "-c:a", "pcm_s16le", "-shortest"]
        subprocess.run(command + ["-c:v", "mpeg4", str(path)], check=True)
        return path.read_bytes()

    def test_surround_audio_converts_to_decodable_mp3(self):
        response = self.upload(self.make_video())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.mimetype, "audio/mpeg")
        subprocess.run([self.ffmpeg, "-v", "error", "-i", "pipe:0", "-f", "null", "-"], input=response.data, check=True)
        response.close()
        self.assert_clean()

    def test_missing_empty_invalid_and_silent_video(self):
        self.assertEqual(self.client.post("/extract").status_code, 400)
        for data, expected in [(b"", 400), (b"invalid", 422), (self.make_video(audio=False), 422)]:
            with self.subTest(expected=expected, size=len(data)):
                self.assertEqual(self.upload(data).status_code, expected)
                self.assert_clean()

    def test_file_limit_excludes_multipart_overhead(self):
        with patch.object(converter, "MAX_VIDEO_BYTES", 100):
            # At the file limit, parsing succeeds and FFmpeg rejects the invalid video.
            self.assertEqual(self.upload(b"x" * 100).status_code, 422)
            self.assertEqual(self.upload(b"x" * 101).status_code, 413)
        self.assert_clean()

    def test_timeout_cleans_files(self):
        with patch.object(converter.subprocess, "run", side_effect=subprocess.TimeoutExpired("ffmpeg", 600)):
            self.assertEqual(self.upload(b"video").status_code, 504)
        self.assert_clean()

    def test_temp_directory_failure_returns_json(self):
        with patch.object(converter.tempfile, "mkdtemp", side_effect=OSError("Disk unavailable")):
            with self.assertLogs(converter.app.logger, level="ERROR"):
                response = self.upload(b"video")
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.json)

    def test_upload_parser_disk_failure_returns_json(self):
        with patch.object(Request, "_get_file_stream", side_effect=OSError("Disk full")):
            with self.assertLogs(converter.app.logger, level="ERROR"):
                response = self.upload(b"video")
        self.assertEqual(response.status_code, 500)
        self.assertIsNotNone(response.json)

    def test_missing_conversion_output_returns_json_and_cleans_files(self):
        with patch.object(converter.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)):
            with self.assertLogs(converter.app.logger, level="ERROR"):
                response = self.upload(b"video")
        self.assertEqual(response.status_code, 500)
        self.assertIsNotNone(response.json)
        self.assert_clean()

    def test_interrupted_download_cleans_files(self):
        response = self.client.post("/extract", data={"video": (io.BytesIO(self.make_video()), "sample.mkv")}, buffered=False)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assert_clean()

    def test_common_video_formats_and_sample_rates(self):
        formats = [
            ("mp4", "mpeg4", "aac", "96000"),
            ("mov", "mpeg4", "pcm_s16le", "44100"),
            ("avi", "mpeg4", "pcm_s16le", "22050"),
            ("webm", "libvpx", "libopus", "48000"),
        ]
        for extension, video_codec, audio_codec, sample_rate in formats:
            with self.subTest(format=extension):
                path = Path(self.folder.name) / f"sample.{extension}"
                subprocess.run([
                    self.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "color=s=64x64:d=0.2",
                    "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate={sample_rate}:duration=0.2",
                    "-c:v", video_codec, "-c:a", audio_codec, "-shortest", str(path),
                ], check=True)
                response = self.upload(path.read_bytes(), f"клип.{extension}")
                self.assertEqual(response.status_code, 200, response.data)
                subprocess.run([self.ffmpeg, "-v", "error", "-i", "pipe:0", "-f", "null", "-"], input=response.data, check=True)
                response.close()
                self.assert_clean()

    def test_request_size_limit_returns_json(self):
        with patch.dict(converter.app.config, MAX_CONTENT_LENGTH=100):
            response = self.upload(b"x" * 200)
        self.assertEqual(response.status_code, 413)
        self.assertIn("error", response.json)
        self.assert_clean()

    def test_concurrent_uploads_keep_results_separate(self):
        video = self.make_video()

        def convert(filename):
            with converter.app.test_client() as client:
                response = client.post("/extract", data={"video": (io.BytesIO(video), filename)}, buffered=True)
                try:
                    return response.status_code, response.headers.get("Content-Disposition"), response.data
                finally:
                    response.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(convert, ["first.mkv", "second.mkv"]))
        for name, (status, disposition, data) in zip(["first", "second"], results):
            self.assertEqual(status, 200, data)
            self.assertIn(f'{name}.mp3', disposition)
            subprocess.run([self.ffmpeg, "-v", "error", "-i", "pipe:0", "-f", "null", "-"], input=data, check=True)
        self.assert_clean()

    def test_unicode_temporary_path(self):
        video = self.make_video()
        directory = Path(self.folder.name) / "временни файлове"
        directory.mkdir()
        with patch.object(tempfile, "tempdir", str(directory)):
            response = self.upload(video)
        self.assertEqual(response.status_code, 200, response.data)
        response.close()
        self.assertEqual(list(directory.iterdir()), [])

    def test_homepage_renders_from_another_working_directory(self):
        # Flask should resolve templates relative to app.py, not the terminal's folder.
        import os
        previous = Path.cwd()
        try:
            os.chdir(self.folder.name)
            response = self.client.get("/")
        finally:
            os.chdir(previous)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'lang="en"', response.data)
        self.assertIn(b'id="video"', response.data)

    def test_empty_conversion_output_is_rejected_and_cleaned(self):
        def empty_conversion(command, **kwargs):
            Path(command[-1]).touch()
            return subprocess.CompletedProcess(command, 0)

        with patch.object(converter.subprocess, "run", side_effect=empty_conversion):
            response = self.upload(b"video")
        self.assertEqual(response.status_code, 422)
        self.assertIn("error", response.json)
        self.assert_clean()

    def test_failed_file_save_returns_json_and_cleans_files(self):
        with patch("werkzeug.datastructures.FileStorage.save", side_effect=OSError("Disk full")):
            with self.assertLogs(converter.app.logger, level="ERROR"):
                response = self.upload(b"video")
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.json)
        self.assert_clean()


if __name__ == "__main__":
    unittest.main()
