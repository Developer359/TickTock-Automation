<h1 align="center">🎬 TickTock Automation</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Badge"/>
  <img src="https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase Badge"/>
  <img src="https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white" alt="GitHub Actions Badge"/>
  <img src="https://img.shields.io/badge/FFmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFmpeg Badge"/>
</p>

> **An end-to-end automated pipeline to generate, edit, and post short-form videos (Reels, Shorts, TikToks) entirely on autopilot.**

---

## 📑 Table of Contents
- [🚀 Features](#-features)
- [📂 Directory Structure](#-directory-structure)
- [⚙️ Setup & Installation](#️-setup--installation)
- [🔄 Workflow Pipeline](#-workflow-pipeline)
- [📖 How It Works](#-how-it-works)
- [💻 Usage](#-usage)
- [🤖 CI/CD Automation](#-cicd-automation)

---

## 🚀 Features

- **End-to-End Automation**: Handles everything from script generation to final posting without any human intervention required.
- **Data Generation**: Automatically creates scripts/quotes, generates high-quality text-to-speech (TTS) voiceovers, fetches relevant background footage, and overlays background music.
- **Advanced Video Editing**: Programmatically trims clips to the perfect length, syncs audio tracks, and burns perfectly timed, dynamic subtitles into the video for maximum viewer retention.
- **Cloud Database & Storage**: Deeply integrated with Supabase to store comprehensive metadata (viral titles, trending tags, query names, posting statuses) and securely hosts the final MP4 video files in cloud storage buckets.
- **Multi-Platform Posting**: Automatically schedules and publishes the finalized short-form videos directly to Instagram via the Buffer GraphQL API.
- **CI/CD Scheduling**: Utilizes GitHub Actions to execute the posting scripts on a strict, defined schedule (e.g., daily), ensuring consistent content delivery.

---

## 📂 Directory Structure

```text
TickTock-Automation/
├── .github/workflows/         # CI/CD actions for automated scheduled posting (e.g. post-tiktok.yml)
├── Metadata/                  # Generates viral titles, tags, and handles Supabase DB syncing
│   └── metadata.py
├── Video-Generate/            # Pipeline to generate audio, fetch videos, and add music
│   ├── main-video-data.py     # Stage 1 execution script
│   └── Video-Eddit/           # Edits video: trims and burns perfectly timed subtitles
│       └── main-subtitle.py   # Stage 2 execution script
├── Video-Store/               # Moves and organizes finalized videos for uploading
│   └── store_videos.py        # Stage 3 execution script
├── Video-Post/                # Scripts to publish videos to social media
│   └── Instagram-post/
│       └── post_instagram.py  # Buffer posting script
├── Remove-Data/               # Utilities to clean up temporary/intermediate files after generation
│   └── remove.py
├── main.py                    # The master orchestrator script that runs the entire pipeline
├── requirements.txt           # Python dependencies and packages
└── .env                       # Environment variables for API keys and credentials
```

---

## ⚙️ Setup & Installation

### 1. Prerequisites

Before running anything, make sure these are installed on your system:

| Requirement | Version | Why it's needed |
|---|---|---|
| **Python** | 3.10 or higher | The entire project is written in Python |
| **FFmpeg** | Latest stable | Core video/audio processing for trim, mix, and subtitle burn-in |
| **pip** | Latest | For installing Python packages |

> **FFmpeg Note**: FFmpeg does NOT need to be installed separately. The project uses `imageio-ffmpeg` which bundles its own FFmpeg binary automatically. You do not need to add anything to your system PATH.

---

### 2. Clone the Repository

```bash
git clone <your-repo-url>
cd TickTock-Automation
```

---

### 3. Install Python Dependencies

Install all required libraries with a single command:

```bash
pip install -r requirements.txt
```

Below is every library the project uses and exactly what each one does:

| Library | Used In | What It Does |
|---|---|---|
| `python-dotenv` | All scripts | Loads API keys and credentials from the `.env` file securely |
| `requests` | `voice.py` | Sends HTTP requests to the Fish Audio TTS API to generate MP3 voiceovers |
| `google-genai` | `quotes.py`, `metadata.py` | Official Google Gemini SDK — used to generate motivational quotes and viral titles/tags |
| `pydantic` | `quotes.py`, `metadata.py` | Enforces strict structured JSON output schema from Gemini responses |
| `imageio-ffmpeg` | `trim.py`, `subtitle.py` | Bundles its own FFmpeg binary — used for video trimming, audio mixing, and subtitle burn-in via subprocess |
| `moviepy` | `trim.py` | Used to get accurate audio duration from the voiceover MP3 file |

To install them individually if needed:

```bash
pip install python-dotenv
pip install requests
pip install google-genai
pip install pydantic
pip install imageio-ffmpeg
pip install moviepy
```

---

### 4. Environment Variables (`.env` file)

Create a file called `.env` in the **root of the project** (same folder as `main.py`). This file holds all your private API keys. It is already listed in `.gitignore` so it will **never be pushed to GitHub**.

```env
# ── Google Gemini API ──────────────────────────────────────────
# Used by: quotes.py, metadata.py
# Get it from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# ── Fish Audio TTS API ─────────────────────────────────────────
# Used by: voice.py
# Get it from: https://fish.audio  →  Dashboard → API Keys
# The script uses model: s2.1-pro-free
# Voice model used: "Commanding Male Motivator" (Reference ID is hardcoded in voice.py)
FISH_API_KEY=your_fish_audio_api_key_here

# ── Supabase ───────────────────────────────────────────────────
# Used by: metadata.py, post_instagram.py, post_tiktok.py
# Get it from: https://supabase.com  →  Project Settings → API
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_supabase_anon_or_service_key_here

# ── Buffer API (Social Media Scheduler) ───────────────────────
# Used by: post_instagram.py, post_tiktok.py
# Get it from: https://buffer.com  →  Account Settings → API Access
BUFFER_API_KEY=your_buffer_personal_access_token_here

# Buffer Channel IDs — found in your Buffer channel settings
BUFFER_CHANNEL_ID_Ticktock=your_tiktok_channel_id_here
BUFFER_CHANNEL_ID_Instagram=your_instagram_channel_id_here
```

> **Important**: Each key is used by a specific script. If a key is missing, the script that needs it will print a clear error message and exit. You only need the keys for the scripts you plan to run.

---

### 5. Prepare Your Local Video & Music Library

The pipeline picks background videos and music automatically at random from local folders. You must manually populate these folders before running `main.py`:

```text
Video-Data/
├── Videos/
│   ├── Gym/          ← Place MP4/MOV/MKV background videos for "The Wake-Up Call" category here
│   ├── Mindset/      ← Background videos for "Mindset & Psychology" category
│   └── Hardwork/     ← Background videos for "Hardwork & Self-Belief" category
└── Music/
    ├── Gym/          ← Background music tracks (MP3/WAV/M4A) for Gym videos
    ├── Mindset/      ← Music tracks for Mindset videos
    └── Hardwork/     ← Music tracks for Hardwork videos
```

Each subfolder must contain **at least 1 file**. The script will randomly pick one from each folder every run so your content stays fresh and varied.

---

### 6. Set Up Supabase Table

The metadata and posting scripts write to and read from a Supabase PostgreSQL table called `SocialMedia-Automation`. Create it in your Supabase project with these columns:

| Column | Type | Notes |
|---|---|---|
| `id` | `int8` | Primary key, auto-increment |
| `query_name` | `text` | e.g. "The Wake-Up Call" |
| `title` | `text` | Generated viral title |
| `tags` | `text` | Space-separated hashtag string |
| `platform` | `text` | Either `"Tiktok"` or `"Instagram"` |
| `status` | `text` | Starts as `"pending"`, changes to `"posted"` after publishing |

---

## 🔄 Pipeline Flow — How the system works

The system operates as **two independent pipelines** triggered manually or via GitHub Actions:

### Pipeline 1 — Video Generation & Storage (`python main.py`)

```text
    ┌────────────────────────────────────────────────────────────┐
    │                 MASTER PIPELINE  (main.py)                 │
    └─────────────────────────────┬──────────────────────────────┘
                                  │
    ┌─────────────────────────────▼──────────────────────────────┐
    │                 STEP 1 - Data Generation                   │
    │            Video-Generate/main-video-data.py               │
    └─────────────────────────────┬──────────────────────────────┘
                                  │
    ┌─────────────────────────────▼──────────────────────────────┐
    │                 STEP 2 - Video Editing                     │
    │       Video-Generate/Video-Eddit/main-subtitle.py          │
    └─────────────────────────────┬──────────────────────────────┘
                                  │
    ┌─────────────────────────────▼──────────────────────────────┐
    │                 STEP 3 - Video Storage                     │
    │               Video-Store/store_videos.py                  │
    └─────────────────────────────┬──────────────────────────────┘
                                  │
    ┌─────────────────────────────▼──────────────────────────────┐
    │               STEP 4 - Metadata & Supabase                 │
    │                  Metadata/metadata.py                      │
    └─────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
         [Final Video in Final-Video/ & Row pending in Supabase]
```

### Pipeline 2 — Automated Social Media Posting (`python Video-Post/Instagram-post/post_instagram.py`)

```text
    ┌────────────────────────────────────────────────────────────┐
    │                 POSTING PIPELINE (Instagram)               │
    │         Video-Post/Instagram-post/post_instagram.py        │
    └─────────────────────────────┬──────────────────────────────┘
                                  │
    ┌─────────────────────────────▼──────────────────────────────┐
    │                      Fetch Pending Row                     │
    │       Queries Supabase for oldest 'pending' video data     │
    └─────────────────────────────┬──────────────────────────────┘
                                  │
    ┌─────────────────────────────▼──────────────────────────────┐
    │                      Retrieve Video URL                    │
    │         Gets public storage URL from Supabase Storage      │
    └─────────────────────────────┬──────────────────────────────┘
                                  │
    ┌─────────────────────────────▼──────────────────────────────┐
    │                      Buffer GraphQL API                    │
    │        Sends video URL, title, and tags to Buffer Queue    │
    └─────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
                     [Update Supabase to 'posted']
```

---

## 📖 How It Works

The entire architecture is divided into four distinct stages that run sequentially to produce a final, viral-ready video.

### **Stage 1: Data Generation** (`Video-Generate`)
- **Script & Voice**: The system pulls or generates high-engaging quotes (e.g., "The Wake-Up Call", "Mindset & Psychology") and converts them into clear, high-quality TTS audio.
- **Visuals**: Fetches high-retention background videos suited for short-form content.
- **Audio**: Mixes the generated voiceover with atmospheric background music.

### **Stage 2: Video Editing** (`Video-Eddit`)
- **Composition**: Merges the mixed audio track directly onto the background video.
- **Transcription**: Automatically transcribes the spoken audio to generate precise, word-by-word timestamps.
- **Subtitles**: Burns dynamic, eye-catching subtitles directly into the center of the video frame to ensure high viewer engagement, even when the sound is off.

### **Stage 3: Video Storage & Metadata** (`Video-Store` & `Metadata`)
- **Organization**: Moves the polished, finalized video to a dedicated final output folder.
- **Metadata Generation**: Creates viral captions, optimized titles, and relevant hashtags tailored to the specific video topic.
- **Cloud Sync**: Uploads the video directly to a Supabase Storage bucket and inserts a corresponding metadata row in the Supabase PostgreSQL database with its status set to `pending`.

### **Stage 4: Automated Posting** (`Video-Post`)
- **Trigger**: A scheduled script (run locally or via GitHub Actions) executes.
- **Fetch**: It securely queries the Supabase database for the absolute oldest video that still has a `pending` status.
- **Publish**: Pushes the video file and its generated caption/tags to social media platforms via the Buffer API.
- **Update**: Upon a successful post, the system updates the database row status from `pending` to `posted`, ensuring no duplicate uploads occur.

---

## 💻 Usage

### 1. Run the Full Master Pipeline
To generate a brand new video from scratch, edit it, apply subtitles, and store the metadata in Supabase, simply run the master orchestrator script:

```bash
python main.py
```
*(This will execute Stages 1 through 4 sequentially, displaying a rich terminal output with exact timings, and ultimately output a final ready-to-post video.)*

### 2. Manual Posting
If you wish to manually trigger the publishing of the next available `pending` video in your database to Instagram:

```bash
python Video-Post/Instagram-post/post_instagram.py
```
*(This script will read from Supabase, send the GraphQL request to Buffer, and update your database records accordingly.)*

### 3. Clean Up Intermediate Files
After a successful video generation pipeline run, you will have leftover intermediate audio and video segments. To remove these and save space:

```bash
python Remove-Data/remove.py
```

---

## 🤖 CI/CD Automation

The repository includes a configured GitHub Actions workflow located at `.github/workflows/post-tiktok.yml`. This workflow is designed to automatically execute the posting script on a rigid schedule using cron syntax. 

```yaml
name: Auto Post Video
on:
  schedule:
    - cron: "0 12 * * *" # Example: Runs automatically every day at 12:00 PM UTC
```
*(By pushing this to your repository, GitHub's servers will wake up and run the posting process for you every single day—allowing you to run an entirely hands-off social media page.)*
