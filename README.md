# Clipperdos — Free-first automatic clipping MVP

This version automatically transcribes an uploaded video, ranks candidate highlight windows, crops them to vertical 9:16, and creates downloadable MP4 clips.

## Important limits
- This MVP accepts **video files**, not arbitrary YouTube URLs. A YouTube link does not itself grant permission to download or process a video. Use your own video file or a file you have permission to edit.
- The highlight ranker is a lightweight heuristic, not a trained viral-prediction model.
- Video processing is resource-intensive. On a free host, jobs may time out or run slowly. The first run downloads the Whisper `base` model.
- Center-cropping is used; smart face tracking and animated captions are not included yet.

## Requirements
- Python 3.10+
- FFmpeg and FFprobe installed and available on PATH
- A computer/server with enough disk space and RAM

## Run locally
From the `backend` folder:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`.

## Free deployment note
You can test on your own computer without paying for hosting. For an always-online public site, free hosting tiers often sleep, limit CPU/RAM, or do not support long-running FFmpeg jobs. Do not promise unlimited free processing.

## Next upgrades
1. Add authorized cloud-storage import / user-owned source integrations.
2. Add face-aware reframing.
3. Generate word-timed subtitles and burn them into clips.
4. Improve ranking with audio energy, scene changes, and semantic scoring.
5. Add job queue, progress updates, storage cleanup, and authentication.
