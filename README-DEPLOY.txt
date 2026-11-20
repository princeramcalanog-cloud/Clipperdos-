CLIPPERDOS DEPLOYMENT PATCH

IMPORTANT: This replaces backend/main.py and adds Dockerfile and render.yaml.
The previous backend mount order could intercept the API route; this version fixes that.
It uses Whisper tiny to reduce memory needs on a free host.

GITHUB:
1. Open your clipperdos repository.
2. Upload and replace backend/main.py with the one in this patch.
3. Upload Dockerfile and render.yaml to the repository root.
4. Commit changes.

RENDER:
1. Sign in at https://render.com using GitHub.
2. New + -> Web Service -> select the clipperdos repository.
3. If asked for runtime, choose Docker. Select Free if available.
4. Deploy. Wait for build to finish, then open the generated .onrender.com URL.

LIMITS:
- Free hosting may sleep, have memory/time limits, or change its free-plan availability.
- Large uploads or long videos may fail on free compute.
- This MVP takes an uploaded video file, not a YouTube URL.
- It does not yet add burned-in captions, face tracking, or a trained viral-content model.
- Process only videos you own or are authorized to edit.
