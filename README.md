# 🎬 Dubify - Professional AI Video Localization

Dubify is a state-of-the-art AI video translation and dubbing platform. It transforms single-language videos into localized versions with perfect timing, using advanced ASR, NMT, and TTS models.

## 🚀 Quick Start (Automated)

If you are on Windows, you can start both the backend and frontend with a single command:

- **CMD**: Double-click `run_dev.bat`
- **PowerShell**: Run `./run_dev.ps1`

---

## 🏗️ Manual Execution (Developer Mode)

### 1. Manual Execution (Developer Mode)

To run the project manually, you need to start both the backend and frontend services.

#### **Backend (FastAPI)**
```bash
cd backend
# Create virtual environment (Optional but Recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload
```
*API will be available at `http://localhost:8000`*

#### **Frontend (React + Vite)**
```bash
cd frontend
# Install dependencies
pnpm install

# Start the development server
pnpm dev
```
*UI will be available at `http://localhost:5173`*

---

### 2. Docker Execution (One-Click Setup)

The easiest way to deploy Dubify is via Docker Compose. This starts both services and manages environment variables and persistence automatically.

```bash
# Build and start services
docker compose up --build -d

# Check logs
docker compose logs -f
```
*Frontend: `http://localhost`, Backend API: `http://localhost:8000`*

---

## 🏗️ Project Architecture

- **Backend**: FastAPI modular architecture.
  - `VideoService`: FFmpeg audio/video processing.
  - `ASRService`: faster-whisper transcription.
  - `TranslateService`: NLLB-200 / Google / Ollama integration.
  - `TTSService`: Edge-TTS with time-stretching.
- **Frontend**: React 18, TailwindCSS, Shadcn/ui (Migrated from LingFilm).
- **Core Orchestrator**: `DubbingPipeline` for end-to-end async processing.

## 📂 Directory Structure
- `backend/`: FastAPI source code and logic.
- `frontend/`: React source code and UI.
- `storage/`: Input/Output and temporary processing files.
- `models/`: Weights for local AI models (Whisper, NLLB).
- `scripts/`: Legacy autodub and reference logic.

## 🤝 Maintainer
**Trinh Hoang Tu (thtcsec)**
© 2026 Dubify AI

## 🔐 Douyin/TikTok Cookie Setup (Important)

Some Douyin/TikTok videos require fresh browser cookies. If you see errors like `Fresh cookies are needed`, add these values in `.env` at project root:

```bash
YTDLP_COOKIES_FROM_BROWSERS=chrome,edge,firefox
# optional: exported Netscape cookies file path
YTDLP_COOKIE_FILE=
# optional: proxy if your network is restricted
YTDLP_PROXY=
YTDLP_SOCKET_TIMEOUT=20

# optional: self-hosted external parser API base (for hard anti-bot cases)
# example: https://your-douyin-parser.example.com
DOUYIN_FALLBACK_API_BASE=
# optional: API key for external parser (if provider requires auth)
DOUYIN_FALLBACK_API_KEY=
```

Tips:
- Open the target video in your browser first, then retry quickly in Dubify.
- Keep your browser signed in if the source platform requires account/session checks.
- For highest stability, deploy your own parser API and set `DOUYIN_FALLBACK_API_BASE`.
