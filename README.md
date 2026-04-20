# 🎬 Dubify: AI-Powered Video Translation & Dubbing

> Elevate your content globally. Transcribe, translate, and dub videos with professional-grade precision using industry-leading AI models.

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-UI-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Maintainer](https://img.shields.io/badge/Maintainer-thtcsec-red)](https://github.com/thtcsec)

## ✨ Overview

Dubify is a professional end-to-end pipeline for video localization. By combining state-of-the-art Speech-to-Text (WhisperX), Neural Machine Translation (NLLB/LLM), and high-fidelity TTS engines, Dubify allows creators to bridge language barriers with a single click.

---

## 🚀 Professional Pipeline

Dubify doesn't just "replace audio"—it reconstructs the viewing experience:

1.  **Audio Extraction (FFmpeg)**: High-fidelity source extraction.
2.  **Transcription (WhisperX)**: Word-level alignment and speaker diarization.
3.  **Contextual Translation (NLLB / Ollama)**: Beyond literal translation, preserving tone and intent.
4.  **Neural Synthesis (Edge TTS / XTTS)**: Natural sounding voices across 100+ languages.
5.  **Smart Alignment**: Automatic time-stretching and silence insertion to match original visual pacing.
6.  **Production Merge**: Multi-channel audio mixing with background noise preservation.

---

## 📂 Architecture (Standard Skeleton)

```text
/Dubify
├── backend/                # FastAPI Application
│   ├── app/
│   │   ├── api/            # API Endpoints & Routes
│   │   ├── core/           # Config, Security, Database
│   │   ├── services/       # AI Pipeline Logic (ASR, Translate, TTS, Video)
│   │   └── main.py         # Entry point
│   ├── workers/            # Background Processors (Celery/Redis)
│   └── Dockerfile
├── frontend/               # React (Vite + Tailwind + shadcn/ui)
│   ├── src/
│   │   ├── components/     # Reusable UI Blocks
│   │   ├── hooks/          # Custom processing hooks
│   │   └── pages/          # Editor & Dashboard
│   └── package.json
├── models/                 # Local AI Weights (Whisper, TTS)
├── storage/                # Media processing storage
└── docker-compose.yml
```

---

## 🛠️ Tech Stack

-   **Backend:** Python 3.11+, FastAPI, FFmpeg.
-   **AI Engines:** WhisperX, NLLB-200, Edge-TTS, Piper, Ollama.
-   **Frontend:** React 18, TypeScript, TailwindCSS, Framer Motion.
-   **Infrastructure:** Docker, Redis (Queue management).

---

## 🚦 Quick Start (Development)

### 1. Requirements
Ensure you have `ffmpeg` installed on your system.

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # Or venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 📊 Deployment Roadmap

-   [ ] **Phase 1**: Core Pipeline Migration (CLI to FastAPI)
-   [ ] **Phase 2**: Interactive Subtitle Editor (React)
-   [ ] **Phase 3**: Real-time Processing Monitoring
-   [ ] **Phase 4**: Production-ready Dockerization

---

## 📜 License

MIT License - Copyright (c) 2026 **Trinh Hoang Tu (thtcsec)**.

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/thtcsec">thtcsec</a>
</p>
