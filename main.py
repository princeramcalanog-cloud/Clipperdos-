import os, re, uuid, shutil, subprocess
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from faster_whisper import WhisperModel

BASE = Path(__file__).resolve().parent
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

app = FastAPI(title="Clipperdos")
app.mount("/files", StaticFiles(directory=OUTPUTS), name="files")
app.mount("/", StaticFiles(directory=BASE.parent / "frontend", html=True), name="frontend")

_model = None
def whisper():
    global _model
    if _model is None:
        # CPU mode keeps this compatible with free machines; first run downloads model weights.
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-2500:])
    return p.stdout

def fmt(t):
    t = max(0, int(t))
    return f"{t//60}:{t%60:02d}"

def score(text):
    low = text.lower()
    words = ["but", "secret", "mistake", "surprising", "why", "how", "truth",
             "actually", "instead", "unexpected", "crazy", "problem", "trick",
             "never", "everyone", "nobody", "because", "finally"]
    value = 35 + min(28, sum(4 for w in words if re.search(r"\\b"+re.escape(w)+r"\\b", low)))
    if "?" in text: value += 12
    if len(text) > 45 and len(text) < 260: value += 10
    if len(text) < 20: value -= 8
    return max(20, min(98, value))

def srt_time(t):
    ms = int((t-int(t))*1000); whole=int(t)
    h=whole//3600; m=(whole%3600)//60; s=whole%60
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

@app.post("/api/clip")
async def make_clips(video: UploadFile = File(...), count: int = Form(5)):
    if count < 1 or count > 8: raise HTTPException(400, "Choose between 1 and 8 clips.")
    ext = Path(video.filename or "upload.mp4").suffix.lower()
    if ext not in {".mp4",".mov",".mkv",".webm",".m4v"}: ext = ".mp4"
    job = uuid.uuid4().hex[:10]
    src = UPLOADS / f"{job}{ext}"
    try:
        with src.open("wb") as f: shutil.copyfileobj(video.file, f)
        # Get duration and extract speech transcript with timestamps.
        probe = run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(src)])
        duration = float(probe.strip())
        if duration <= 0: raise RuntimeError("Could not read video duration.")
        model = whisper()
        segments, info = model.transcribe(str(src), vad_filter=True, word_timestamps=False)
        segs = [{"start":float(s.start),"end":float(s.end),"text":s.text.strip()} for s in segments if s.text.strip()]
        if len(segs) < 2: raise RuntimeError("Not enough speech was detected. Try a video with clear dialogue.")
        # Candidate windows centered on each transcript segment, grouped to about 25–45 sec.
        candidates=[]
        for i,s in enumerate(segs):
            start=max(0,s["start"]-4); end=min(duration, max(s["end"]+18, start+22))
            if end-start < 12: continue
            nearby=[x["text"] for x in segs if x["start"] < end and x["end"] > start]
            text=" ".join(nearby).strip()
            candidates.append({"start":start,"end":min(end,start+45),"text":text,"score":score(text)})
        candidates.sort(key=lambda x:x["score"], reverse=True)
        chosen=[]
        for c in candidates:
            if all(c["end"] < old["start"] or c["start"] > old["end"] for old in chosen):
                chosen.append(c)
            if len(chosen)>=count: break
        if not chosen: raise RuntimeError("No suitable highlight sections found.")
        result=[]
        for idx,c in enumerate(chosen,1):
            outname=f"{job}_clip_{idx}.mp4"; out=OUTPUTS/outname
            # Center-crop to 9:16; scale to 1080x1920. Re-encode for compatibility.
            vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
            run(["ffmpeg","-y","-ss",str(c["start"]),"-i",str(src),"-t",str(c["end"]-c["start"]),
                 "-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","24","-c:a","aac","-b:a","128k","-movflags","+faststart",str(out)])
            result.append({"url":f"/files/{outname}","start_label":fmt(c["start"]),"end_label":fmt(c["end"]),
                           "score":c["score"],"caption":c["text"][:280]})
        return {"clips":result}
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        try: src.unlink(missing_ok=True)
        except Exception: pass
