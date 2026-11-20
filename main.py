import os, re, uuid, shutil, subprocess
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from faster_whisper import WhisperModel

BASE = Path(__file__).resolve().parent
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

app = FastAPI(title="Clipperdos")
_model = None

def whisper():
    global _model
    if _model is None:
        # Tiny model is selected to fit more comfortably on free, low-memory hosting.
        _model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _model

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-1800:])
    return p.stdout

def fmt(t):
    t = max(0, int(t))
    return f"{t//60}:{t%60:02d}"

def score(text):
    low = text.lower()
    words = ["but", "secret", "mistake", "surprising", "why", "how", "truth",
             "actually", "instead", "unexpected", "crazy", "problem", "trick",
             "never", "everyone", "nobody", "because", "finally"]
    value = 35 + min(28, sum(4 for w in words if re.search(r"\b"+re.escape(w)+r"\b", low)))
    if "?" in text: value += 12
    if 45 < len(text) < 260: value += 10
    if len(text) < 20: value -= 8
    return max(20, min(98, value))

@app.post("/api/clip")
async def make_clips(video: UploadFile = File(...), count: int = Form(5)):
    if count < 1 or count > 8:
        raise HTTPException(400, "Choose between 1 and 8 clips.")
    ext = Path(video.filename or "upload.mp4").suffix.lower()
    if ext not in {".mp4", ".mov", ".mkv", ".webm", ".m4v"}:
        ext = ".mp4"
    job = uuid.uuid4().hex[:10]
    src = UPLOADS / f"{job}{ext}"
    try:
        with src.open("wb") as f:
            shutil.copyfileobj(video.file, f)
        duration = float(run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(src)
        ]).strip())
        if duration <= 0:
            raise RuntimeError("Could not read video duration.")
        segments, _ = whisper().transcribe(str(src), vad_filter=True)
        segs = [{"start": float(s.start), "end": float(s.end), "text": s.text.strip()}
                for s in segments if s.text.strip()]
        if len(segs) < 2:
            raise RuntimeError("Not enough speech detected. Try a video with clear dialogue.")
        candidates = []
        for s in segs:
            start = max(0, s["start"] - 4)
            end = min(duration, max(s["end"] + 18, start + 22))
            text = " ".join(x["text"] for x in segs if x["start"] < end and x["end"] > start).strip()
            candidates.append({"start": start, "end": min(duration, start + 42),
                               "text": text, "score": score(text)})
        candidates.sort(key=lambda x: x["score"], reverse=True)
        chosen = []
        for c in candidates:
            if all(c["end"] < old["start"] or c["start"] > old["end"] for old in chosen):
                chosen.append(c)
            if len(chosen) >= count:
                break
        results = []
        for idx, c in enumerate(chosen, 1):
            outname = f"{job}_clip_{idx}.mp4"
            out = OUTPUTS / outname
            vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
            run(["ffmpeg", "-y", "-ss", str(c["start"]), "-i", str(src),
                 "-t", str(c["end"] - c["start"]), "-vf", vf,
                 "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                 "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)])
            results.append({"url": f"/files/{outname}", "start_label": fmt(c["start"]),
                            "end_label": fmt(c["end"]), "score": c["score"],
                            "caption": c["text"][:280]})
        return {"clips": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        try:
            src.unlink(missing_ok=True)
        except Exception:
            pass

# Mount static routes AFTER API routes so "/" does not swallow /api/clip.
app.mount("/files", StaticFiles(directory=OUTPUTS), name="files")
app.mount("/", StaticFiles(directory=BASE.parent / "frontend", html=True), name="frontend")
