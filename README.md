# 📚 Vāchanam — AI-Powered Reading Evaluator

> **Vāchanam** (वाचनम्) is a bilingual (English + Hindi) reading assessment platform for primary school students. Teachers record a student reading a passage aloud; the app transcribes the audio via Bhashini's ASR API, scores accuracy, fluency, pace, and pronunciation, and generates AI-driven feedback and personalised practice stories.

---

## Table of Contents
1. [Tech Stack](#tech-stack)
2. [Features](#features)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Running the App](#running-the-app)
7. [Project Structure](#project-structure)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite, Recharts, react-markdown |
| Backend | FastAPI (Python 3.10+), SQLAlchemy, SQLite |
| Speech-to-Text | [Bhashini Dhruva API](https://bhashini.gov.in/) (Hindi & English ASR) |
| AI / LLM | OpenAI `gpt-4o-mini` |
| Real-time audio | WebSocket + Web Audio API (PCM worklet) |
| Browser STT | Web Speech API (live word-highlight) |

---

## Features

### 🎙️ Live Reading Session
- **Real-time word highlighting** — as the student reads, each word is highlighted green (correct) or red (wrong) using the browser's Web Speech API with a fuzzy Hindi/English-aware matcher.
- **3-minute countdown timer** — sessions automatically stop after the time limit.
- **WebSocket audio streaming** — raw PCM audio is streamed to the backend and saved as a WAV file for server-side evaluation.
- **Bilingual support** — works for both English and Hindi passages.

### 📊 Automated Scoring (5 dimensions)
| Metric | Weight | Description |
|--------|--------|-------------|
| **Accuracy** | 45 % | Word-level match between passage and transcript (fuzzy, Hindi-aware) |
| **Fluency** | 25 % | Penalty-based score on pause frequency and length |
| **Completion** | 15 % | Percentage of passage words attempted |
| **Pace** | 10 % | Words-per-minute score (optimal range: 60–130 wpm) |
| **Pronunciation** | 5 % | Derived from ASR confidence (avg log-prob) |

Final score maps to a grade: **A (≥85)** · **B (≥70)** · **C (≥55)** · **D (≥40)** · **E (<40)**

### 🤖 AI Feedback (OpenAI GPT-4o-mini)
- **Per-session AI overview** — 2-3 encouraging sentences personalised to the student's results, generated immediately after evaluation.
- **AI Progress Report** — comprehensive markdown report covering improvement trends, recurring mistakes, fluency patterns, and teacher/parent advice, generated across any selection of sessions.

### 📈 Improvements Module
- **Wrong-word aggregation** — tracks every mispronounced word across all sessions with a frequency count, filterable by language (English / Hindi / All).
- **🔊 Hear word** — text-to-speech playback of any wrong word.
- **✏ Practice word** — speech recognition challenge: say the word correctly 3 times to clear it.
- **📖 AI Practice Story** — generates a short child-friendly story that naturally incorporates the student's top-20 worst words, in the target language (English or Hindi).
- **Practice story reading session** — the generated story is saved as a material and launched directly as a reading session to reinforce learning.

### 📖 Progress History & Charts
- **Performance over time chart** — line chart showing Overall Score, Accuracy, and Fluency across all sessions (Recharts).
- **Session cards** — each past session shows grade, all 6 metrics, wrong word tags, AI feedback, full transcript, and date/time.
- **Teacher notes** — teachers can write and save private notes on any session.

### 📄 Reports Tab
- Generate a full AI-written progress report for any student, covering all sessions or just the most recent 3.
- Rendered as rich markdown with headers and bullet points.

### ⚙️ Management (Add Activity Tab)
- **Add / delete Teachers** (name + subject)
- **Add / delete Students** (name, class, roll number, linked teacher)
- **Upload / delete Reading Materials** (PDF upload, language, class level)

---

## Prerequisites

| Requirement | Version |
|------------|---------|
| Python | 3.10 or later |
| Node.js | 18 or later |
| npm | 9 or later |

You will also need API keys for three services (see [Configuration](#configuration)):
- **Bhashini Dhruva** — for Hindi & English ASR transcription
- **OpenAI** — for AI feedback and story generation
- **NVIDIA** — (optional, legacy field in `.env`)

---

## Installation

### 1. Clone / Download the project
```bash
# If using git
git clone <repo-url>
cd reading_evaluator
```

### 2. Backend — Python environment

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend — Node environment

```bash
cd ../frontend-react
npm install
```

---

## Configuration

Copy the example env file and fill in your API keys:

```bash
cd backend
copy .env.example .env        # Windows
# OR
cp .env.example .env          # macOS / Linux
```

Edit `backend/.env`:

```env
BHASHINI_API_KEY=your_bhashini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
NVIDIA_API_KEY=your_nvidia_api_key_here   # optional / legacy
```

### Getting API Keys

| Service | Where to get it |
|---------|----------------|
| **Bhashini** | Register at [bhashini.gov.in](https://bhashini.gov.in/) → Dhruva API → generate key |
| **OpenAI** | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |

> **Note:** Without `BHASHINI_API_KEY`, audio transcription will return empty results. Without `OPENAI_API_KEY`, AI feedback and story generation will be silently skipped (the rest of the app still works).

---

## Running the App

You need **two terminals** running simultaneously.

### Terminal 1 — Backend (FastAPI)

```bash
cd backend
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive API docs: `http://localhost:8000/docs`

### Terminal 2 — Frontend (Vite dev server)

```bash
cd frontend-react
npm run dev
```

Open your browser at **`http://localhost:5173`**.

---

### Production (optional) — serve frontend from FastAPI

```bash
cd frontend-react
npm run build          # outputs to frontend-react/dist/

cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

FastAPI will automatically serve the built frontend from `/` when the `dist/` folder exists.

---

## Project Structure

```
reading_evaluator/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── reading.py        # Recording, WebSocket, evaluation endpoints
│   │   │   ├── improvements.py   # Wrong-word aggregation, story & report generation
│   │   │   ├── materials.py      # PDF upload & management
│   │   │   ├── students.py       # Student CRUD
│   │   │   └── teachers.py       # Teacher CRUD
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── stt_service.py    # Bhashini ASR integration
│   │   │   ├── eval_service.py   # Scoring engine (accuracy, fluency, pace…)
│   │   │   ├── alignment_service.py  # Fuzzy Hindi/English word alignment
│   │   │   ├── ai_service.py     # OpenAI GPT-4o-mini calls
│   │   │   ├── pdf_service.py    # PyMuPDF text extraction
│   │   │   └── text_processing_service.py
│   │   ├── db/                   # Database setup
│   │   └── main.py               # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env.example
│   └── reading_assessment.db     # SQLite database (auto-created)
│
└── frontend-react/
    ├── src/
    │   ├── App.jsx               # Entire React SPA (single file)
    │   ├── styles.css            # Global styles
    │   └── pcm-worklet.js        # AudioWorklet for raw PCM capture
    ├── package.json
    └── vite.config.js
```

---

## Browser Compatibility

The app requires a modern Chromium-based browser (Chrome, Edge) for:
- **Web Speech API** (live word highlighting during reading)
- **AudioWorklet** (real-time PCM audio capture)

Firefox and Safari do not fully support the Web Speech API and are **not recommended**.

---

*Built with ❤️ for primary school reading assessment.*
