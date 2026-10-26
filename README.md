# Video to MP3

A Python Flask backend with a vanilla HTML, CSS, and JavaScript frontend.
Upload a video, preview the extracted audio, and download an MP3.

Requires Python 3.10 or newer. The same application code runs on Windows and
Ubuntu Desktop; only the installation and virtual-environment commands differ.

## Download and extract the ZIP

1. Download the project ZIP. On GitHub, use **Code → Download ZIP**.
2. Extract the entire archive before running anything. On Windows, right-click
   the ZIP and choose **Extract All**. On Ubuntu Desktop, right-click it and
   choose **Extract Here** (the wording may vary with your file manager).
3. Open the extracted project folder. It must contain `app.py`,
   `requirements.txt`, and the `templates` folder. ZIP archives may contain an
   extra outer folder: open the inner folder containing these files.
4. Follow the instructions for your operating system below. Git and Node.js
   are not required. An internet connection is needed for initial installation.

Do not copy or reuse a `.venv` folder from another machine or operating system.
If the archive includes one, remove that `.venv` folder from the extracted
project before setup. The commands below create a new environment for your machine.

## Windows: first-time setup from ZIP

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/windows/).
   Enable **Add Python to PATH** if offered by the installer, then open a new terminal.
2. In File Explorer, open the extracted project folder, type `powershell` in
   the address bar, and press Enter. This opens PowerShell in that folder.
3. Check Python, create the environment, install dependencies, and start:

   ```powershell
   py -3 --version
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe app.py
   ```

   The displayed Python version must be 3.10 or newer. If `py` is not recognized
   but `python --version` reports a suitable version, use `python` instead of
   `py -3` in the first two commands.

4. Keep the terminal open and visit [http://127.0.0.1:5000](http://127.0.0.1:5000).
   Choose a video, click **Extract MP3**, then click **Download MP3**.
5. Stop the server with **Ctrl+C** in the terminal.

For later runs, open PowerShell in the same folder and run only:

```powershell
.\.venv\Scripts\python.exe app.py
```

There is no need to activate the virtual environment or change PowerShell's
execution policy: these commands call its Python executable directly.

## Ubuntu Desktop: first-time setup from ZIP

1. Open the extracted project folder in Files, right-click an empty area, and
   choose **Open in Terminal**. Alternatively, open Terminal and run
   `cd "/full/path/to/extracted/project"`, replacing the path with your own.
2. Install Python, virtual-environment support, and FFmpeg:

   ```bash
   sudo apt update
   sudo apt install python3 python3-venv ffmpeg
   python3 --version
   ```

   The Python version must be 3.10 or newer. `sudo` may ask for your Ubuntu
   password; no characters appear while you type it.

3. Create the environment, install dependencies, and start:

   ```bash
   python3 -m venv .venv
   ./.venv/bin/python -m pip install -r requirements.txt
   ./.venv/bin/python app.py
   ```

4. Keep the terminal open and visit [http://127.0.0.1:5000](http://127.0.0.1:5000)
   in Firefox, Chrome, or another browser. Choose a video, click **Extract MP3**,
   then click **Download MP3**.
5. Stop the server with **Ctrl+C** in the terminal.

For later runs, open Terminal in the same folder and run only:

```bash
./.venv/bin/python app.py
```

Do not run the app or its pip installation commands with `sudo`.

## Troubleshooting setup

- **`app.py` or `requirements.txt` not found:** the terminal is in the wrong
  folder. Navigate to the extracted folder containing both files.
- **Python is not recognized on Windows:** reopen the terminal after installing
  Python. Try `py -3 --version` and `python --version`; if neither works, repair
  the Python installation and enable its PATH option.
- **`No module named flask`:** run the dependency-installation command above
  using the `.venv` Python, then start with that same executable.
- **Ubuntu cannot create the environment / `ensurepip` is unavailable:** install
  `python3-venv`, then rerun the environment-creation command. If you use a
  separately installed Python version, install its matching venv package.
- **Port 5000 is already in use:** stop the other app or choose another port:

  Windows PowerShell:

  ```powershell
  $env:PORT = "5001"
  .\.venv\Scripts\python.exe app.py
  ```

  Ubuntu:

  ```bash
  PORT=5001 ./.venv/bin/python app.py
  ```

  Then open [http://127.0.0.1:5001](http://127.0.0.1:5001).
- **The page does not open:** check that the server is still running, and use
  its HTTP address. Opening `templates/index.html` directly will not start the backend.
- **Installation cannot download packages:** check your internet connection
  and rerun the pip command. On Ubuntu, also check the output from `apt`.

## FFmpeg

An existing FFmpeg on PATH takes precedence. The Ubuntu instructions install
the system FFmpeg; otherwise the app falls back to the binary supplied by
imageio-ffmpeg on supported platforms. Windows does not require a separate
FFmpeg installation.

## Tests

```bash
# Ubuntu
./.venv/bin/python -m unittest -v
```

```powershell
# Windows
.\.venv\Scripts\python -m unittest -v
```

The GitHub Actions workflow is configured to run these tests on Ubuntu and
Windows with Python 3.10 and 3.12, including real video conversion and MP3
decoding. It runs after the project is pushed to GitHub with Actions enabled;
downloading and running a ZIP does not run this workflow. A configured workflow
alone does not confirm that its jobs have passed.

## Limits and file handling

The upload limit shown as 500 MB is 500 × 1024 × 1024 bytes (500 MiB).
Conversion uses the first audio track and produces stereo MP3 audio. The
10-minute timeout applies to FFmpeg processing; upload and transfer time are
additional.

The server transfers the MP3 to the browser for preview before you click
**Download MP3** to save it. Server-side temporary files are removed after that
transfer or on conversion failure; the browser keeps the result available
while the page is open. Abruptly stopping the process can leave temporary files
in the operating system's temporary directory. The original video is not modified.

## Hosting

The app binds to localhost for personal use. Hosting it publicly requires a
production WSGI server, authentication or rate limiting, and resource limits.
