# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BiliNote is an AI-powered video note generation tool. It processes videos from platforms like Bilibili, YouTube, and Douyin to automatically generate structured Markdown notes using AI transcription and summarization.

**Tech Stack:**
- Frontend: React + TypeScript + Vite + TailwindCSS
- Backend: FastAPI (Python)
- State Management: Zustand
- Database: SQLAlchemy (SQLite)
- Deployment: Docker Compose, Tauri (desktop)

## Development Commands

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
python main.py
```
The backend runs on port 8483 by default (configurable via `BACKEND_PORT` env var).

### Frontend (React)
```bash
cd BillNote_frontend
pnpm install
pnpm dev      # Start dev server on port 5173
pnpm build    # Build for production
pnpm lint     # Run ESLint
```

### Environment Setup
Copy `.env.example` to `.env` and configure:
- `BACKEND_PORT`: Backend server port (default: 8483)
- `VITE_API_BASE_URL`: Frontend API URL for development
- `TRANSCRIBER_TYPE`: Audio transcription service (fast-whisper, bcut, kuaishou, mlx-whisper, groq)
- `WHISPER_MODEL_SIZE`: Whisper model size (base, small, medium, large)

### Dependencies
- **FFmpeg**: Required for audio/video processing. Must be installed and available in PATH.
- **CUDA (optional)**: For faster transcription with fast-whisper on NVIDIA GPUs.

## Architecture

### Backend Structure
- **Entry point**: `backend/main.py` - FastAPI app with CORS, middleware, and route registration
- **App factory**: `backend/app/__init__.py` - Creates FastAPI app with router registration
- **API routers** (`/api` prefix):
  - `/note` - Video processing and note generation
  - `/provider` - AI model provider configuration
  - `/model` - AI model management
  - `/config` - System configuration

### Key Backend Modules

**Services Layer:**
- `services/note.py` - `NoteGenerator` class orchestrates the video processing pipeline
- `downloaders/` - Platform-specific video downloaders (Bilibili, YouTube, Douyin, etc.)
- `gpt/` - Multiple AI provider support (OpenAI, DeepSeek, Qwen) using factory pattern
- `transcriber/` - Audio-to-text services (Whisper, Fast-Whisper, Groq, MLX)

**Data Layer:**
- `db/models/` - SQLAlchemy ORM models (VideoTask, Providers, Models)
- `db/` - Data Access Objects (DAOs) for each entity

**Processing Pipeline:**
```
Video URL → Platform Detection → Download → Extract Audio → Transcribe → AI Summarize → Generate Markdown
```

### Frontend Structure

**Pages:**
- `HomePage` - Main interface with video input, task tracking, and note viewing
- `SettingPage` - Configuration for providers, models, transcribers, downloaders, and prompts

**State Management (Zustand stores):**
- `taskStore` - Active task management
- `providerStore` - AI provider configurations
- `modelStore` - Model settings
- `configStore` - Application preferences

**Services (`src/services/`):**
- `note.ts` - Video processing API calls
- `downloader.ts` - Downloader management
- `model.ts` - Model management
- `system.ts` - System information

**Key Features:**
- Real-time task progress polling via `useTaskPolling` hook
- Markdown viewer with syntax highlighting and KaTeX math support
- MarkMap integration for mind map visualization
- Theme support (light/dark mode via next-themes)

## Adding New Features

### New Video Platform Support
1. Create downloader class in `backend/downloaders/` inheriting from base downloader
2. Update platform detection logic in downloader factory
3. Add platform icon to `src/components/Icons/platform.tsx`

### New AI Provider Support
1. Add provider class in `backend/app/gpt/providers/`
2. Update provider factory in `backend/app/gpt/`
3. Add provider configuration to frontend model form

### New Transcriber Support
1. Add transcriber class in `backend/app/transcriber/`
2. Update transcriber provider factory
3. Add transcriber option to frontend settings

## File Organization

**Backend:**
- `uploads/` - Temporary video files
- `note_results/` - Generated markdown notes
- `static/screenshots/` - Extracted screenshots
- `data/` - Database and persistent data

**Frontend:**
- `src/components/ui/` - Radix UI primitives
- `src/components/Form/` - Form components for settings
- `src/pages/` - Main page components
- `src/layouts/` - Layout wrappers
- `src/store/` - Zustand stores
- `src/services/` - API service layers

## API Communication

Frontend uses Axios for HTTP requests. Base URLs configured via:
- Development: `VITE_API_BASE_URL` in `.env`
- Production: API endpoints proxied through deployment

Key endpoints:
- `POST /api/generate_note` - Submit video processing task
- `GET /api/task_status/{task_id}` - Check task progress
- `DELETE /api/task/{task_id}` - Delete/cancel task
- `GET /api/providers` - List AI providers
- `POST /api/provider` - Create/update provider

## Database

Uses SQLAlchemy ORM with SQLite by default. Key tables:
- `video_tasks` - Task status and metadata
- `providers` - AI provider configurations
- `models` - Available AI models

Database initialized on startup via `init_db()` in `main.py` lifespan.

## Deployment

**Docker Compose:**
- Three-container setup: frontend, backend, nginx
- See `docker-compose.yml` and `docker-compose.gpu.yml`

**Tauri:**
- Desktop application support via `src-tauri/`
- Requires special CORS configuration for tauri.localhost origin

## Important Notes

- Backend must start before frontend for proper initialization
- FFmpeg must be available in system PATH for video processing
- API rate limiting may be needed for production deployments
- Large videos are processed in segments to handle memory constraints
- Task progress updates are polled by frontend (consider WebSocket for real-time updates)
